import { execSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, posix } from "node:path";

import nxlvModule, {
    afterAllProjectsVersioned as nxlvAfterAllProjectsVersioned,
} from "@nxlv/python/release/version-actions";

import type { VersionActions as NxVersionActionsBase } from "nx/release";
import type { ReleaseGroupWithName } from "nx/src/command-line/release/config/filter-release-groups";
import type { FinalConfigForProject } from "nx/src/command-line/release/utils/release-graph";
import type { ResolveVersionForDependency } from "nx/src/command-line/release/version/version-actions";
import type { NxReleaseVersionConfiguration } from "nx/src/config/nx-json";
import type { ProjectGraphProjectNode } from "nx/src/config/project-graph";
import type { ProjectGraph } from "nx/src/config/project-graph";
import type { Tree } from "nx/src/generators/tree";

/**
 * Nx's module loader imports version-actions modules as ESM; `@nxlv/python`
 * is CJS, so its default export arrives as the module namespace. Unwrap it
 * the same way Nx unwraps loaded version-actions modules (`loaded.default ??
 * loaded`) so the class extends cleanly under every loader.
 *
 * Typed through a ctor signature over the Nx base class's instance type,
 * with the base's abstract members re-declared as concrete: at runtime every
 * method is Nxlv's (the base's abstracts are implemented by it), and the
 * base signatures are the contract this composite overrides — Nxlv's own
 * declarations drop parameters its implementations ignore, and `super` calls
 * against abstract base members are a type error.
 */
const PythonVersionActions = ((nxlvModule as { default?: unknown }).default ??
    nxlvModule) as unknown as ChartOwnerVersionActionsCtor;

/** The instance shape: Nx's base contract with the abstracts made concrete. */
interface ChartOwnerVersionActionsInstance extends NxVersionActionsBase {
    validManifestFilenames: string[] | null;
    init(tree: Tree): Promise<void>;
    validate(tree: Tree): Promise<void>;
    readCurrentVersionFromSourceManifest(tree: Tree): Promise<{ currentVersion: string; manifestPath: string } | null>;
    readCurrentVersionFromRegistry(
        tree: Tree,
        currentVersionResolverMetadata: NxReleaseVersionConfiguration["currentVersionResolverMetadata"],
    ): Promise<{ currentVersion: string | null; logText: string } | null>;
    readCurrentVersionOfDependency(
        tree: Tree,
        projectGraph: ProjectGraph,
        dependencyProjectName: string,
    ): Promise<{ currentVersion: string | null; dependencyCollection: string | null }>;
    updateProjectVersion(tree: Tree, newVersion: string): Promise<string[]>;
    updateProjectDependencies(
        tree: Tree,
        projectGraph: ProjectGraph,
        dependenciesToUpdate: Record<string, string>,
        resolveVersionForDependency?: ResolveVersionForDependency,
    ): Promise<string[]>;
}

/** The ctor shape Nx calls for every project in the release plan. */
type ChartOwnerVersionActionsCtor = new (
    releaseGroup: ReleaseGroupWithName,
    projectGraphNode: ProjectGraphProjectNode,
    finalConfigForProject: FinalConfigForProject,
) => ChartOwnerVersionActionsInstance;

/**
 * Composite version actions for chart-owning projects (ADR 057, DD-245,
 * DD-250). Charts are not projects (DD-250): their targets merge onto the
 * owner project, and release works the same way — one version-actions module
 * per OWNER, doing the owner's ecosystem versioning AND the chart's.
 *
 * The ecosystem side is `@nxlv/python`'s actions extended here: the owner's
 * `pyproject.toml` (uv workspace members: the root, the Python apps) is
 * versioned exactly as before DD-250. Owners without a pyproject (the dev
 * charts, the webapp chart) get no ecosystem manifest — the chart is their
 * version manifest, current version read from it directly.
 *
 * The chart side: `version:` carries the chart's own version and
 * `appVersion:` the image tag the chart ships by default (DD-245). Release
 * writes both: chart version = the owner's release semver, appVersion = the
 * same with the `v` prefix `publish.yaml` puts on the git tag and the image
 * tags (`v1.2.3`), so a chart installed by version resolves its component's
 * image by default. The umbrella's `dependencies[].version` pins are updated
 * in the same pass (its chart dependencies are implicitDependencies on the
 * OWNING projects — DD-250), re-pinning the umbrella to exactly the
 * component-chart versions the release publishes (DD-245's
 * mixing-is-impossible rule).
 *
 * The line-based edits below are deliberate: these Chart.yaml files are ours
 * (single-line scalars), the workspace has no YAML library, and prettier
 * keeps the formatting stable.
 */
export default class ChartYamlVersionActions extends PythonVersionActions {
    // ONLY the ecosystem manifest: Nx's base init() resolves the first of
    // these that exists at the project ROOT, and a chart lives one level
    // down (`helm/Chart.yaml`, DD-247). The chart side is driven by the
    // overrides below, which read/write it by path — the ecosystem's
    // manifestsToUpdate stays a pure pyproject list (DD-250).
    override validManifestFilenames = ["pyproject.toml"];

    /** Workspace-relative prefix for this owner's root ("" at the root). */
    private get prefix(): string {
        const root = this.projectGraphNode.data.root;
        return root === "." ? "" : `${root}/`;
    }

    /** The chart manifest is always at `<owner>/helm/Chart.yaml` (DD-247). */
    private get chartPath(): string {
        return `${this.prefix}helm/Chart.yaml`;
    }

    override async init(tree: Tree): Promise<void> {
        // Chart-only owners (the dev charts, the webapp chart) have no
        // pyproject.toml, so the base init resolves no manifest root and the
        // ecosystem actions become inert for them: the chart is their only
        // manifest, handled by the overrides below.
        await super.init(tree);
    }

    override async validate(tree: Tree): Promise<void> {
        await super.validate(tree);
        // The chart is a release manifest too (DD-250): the umbrella is
        // versioned and re-pinned by the root project's actions, a component
        // chart by its owner's. A chart owner without its Chart.yaml is a
        // wiring bug, caught here rather than at publish time.
        if (this.ownsChart() && !tree.exists(this.chartPath)) {
            throw new Error(
                `ChartYamlVersionActions: no Chart.yaml at ${this.chartPath} — project "${this.projectGraphNode.name}" is in the release plan as a chart owner but has no chart.`,
            );
        }
    }

    /**
     * Whether this project is a chart owner: it has a `helm/Chart.yaml` on
     * disk. Read from disk (not the tree) so it is stable during graph
     * construction, before any release write.
     * @returns True when the owner ships a chart.
     */
    private ownsChart(): boolean {
        return existsSync(this.chartPath);
    }

    override async readCurrentVersionFromSourceManifest(tree: Tree): Promise<{
        currentVersion: string;
        manifestPath: string;
    }> {
        // The ecosystem manifest wins when the owner has one (the uv apps,
        // the root workspace); chart-only owners (dev/*, the webapp chart)
        // read their version straight from Chart.yaml (DD-250).
        if (tree.exists(`${this.prefix}pyproject.toml`)) {
            return super.readCurrentVersionFromSourceManifest(tree);
        }
        const version = readScalarField(readDisk(this.chartPath), "version");
        if (version === null) {
            throw new Error(`ChartYamlVersionActions: no 'version:' in ${this.chartPath}`);
        }
        return { currentVersion: version, manifestPath: this.chartPath };
    }

    override async readCurrentVersionOfDependency(
        tree: Tree,
        projectGraph: ProjectGraph,
        dependencyProjectName: string,
    ): Promise<{ currentVersion: string | null; dependencyCollection: string | null }> {
        // Chart dependencies first: the umbrella pins its component charts as
        // `version: "=x.y.z"`; Nx needs the current pin to know a dependency
        // is releasable (returning null skips it) and reads the leading =/^/~
        // from it as the protocol to keep (versionPrefix auto). The dep's
        // CHART name is found by following the umbrella's `repository:` path
        // to the owning project (charts are not projects — DD-250).
        if (tree.exists(this.chartPath)) {
            const charts = tree.read(this.chartPath, "utf8");
            const chartName = chartNameForDependency(charts, dirname(this.chartPath), dependencyProjectName, tree);
            if (chartName !== null) {
                const entry = parseDependencyEntries(charts).find((dep) => dep.name === chartName);
                return !entry?.version
                    ? { currentVersion: null, dependencyCollection: null }
                    : { currentVersion: entry.version, dependencyCollection: "dependencies" };
            }
        }
        // Ecosystem dependencies (uv requirements) only exist for pyproject
        // owners; a chart-only owner has no manifest for the provider to read.
        if (!existsSync(`${this.prefix}pyproject.toml`)) {
            return { currentVersion: null, dependencyCollection: null };
        }
        return super.readCurrentVersionOfDependency(tree, projectGraph, dependencyProjectName);
    }

    override async updateProjectVersion(tree: Tree, newVersion: string): Promise<string[]> {
        const lines: string[] = [];
        if (this.manifestsToUpdate.length > 0) {
            lines.push(...(await super.updateProjectVersion(tree, newVersion)));
        }
        if (tree.exists(this.chartPath)) {
            let content = tree.read(this.chartPath, "utf8");
            content = replaceScalarField(content, "version", newVersion, this.chartPath);
            content = replaceScalarField(content, "appVersion", `v${newVersion}`, this.chartPath);
            tree.write(this.chartPath, content);
            lines.push(`  - Updated ${this.chartPath} (version: ${newVersion}, appVersion: v${newVersion})`);
        }
        return lines;
    }

    override async updateProjectDependencies(
        tree: Tree,
        projectGraph: ProjectGraph,
        dependenciesToUpdate: Record<string, string>,
        resolveVersionForDependency?: ResolveVersionForDependency,
    ): Promise<string[]> {
        const lines: string[] = [];
        if (tree.exists(this.chartPath)) {
            const charts = tree.read(this.chartPath, "utf8");
            const { content, updated } = updateDependencyPins(
                charts,
                dependenciesToUpdate,
                this.chartPath,
                dirname(this.chartPath),
                tree,
            );
            if (updated.length > 0) {
                tree.write(this.chartPath, content);
            }
            lines.push(...updated);
        }
        if (this.manifestsToUpdate.length > 0) {
            lines.push(
                ...(await super.updateProjectDependencies(
                    tree,
                    projectGraph,
                    dependenciesToUpdate,
                    resolveVersionForDependency,
                )),
            );
        }
        return lines;
    }

    // Registry resolution is not supported for charts: chart versions live
    // in the manifest. pyproject owners keep the ecosystem's registry reader.
    override async readCurrentVersionFromRegistry(
        tree: Tree,
        metadata: NxReleaseVersionConfiguration["currentVersionResolverMetadata"],
    ): Promise<{ currentVersion: string | null; logText: string } | null> {
        return this.manifestsToUpdate.length > 0 ? super.readCurrentVersionFromRegistry(tree, metadata) : null;
    }
}

/**
 * After every project is versioned, refresh the ecosystem lockfiles (the uv
 * locks of the versioned pyproject projects) and the umbrella's Chart.lock
 * (CHT-07). The lock pins the resolved dependency versions (and a digest
 * over them), so a release that bumps the component charts leaves it stale;
 * only helm itself can compute the digest, and the tree is flushed to disk
 * by this point, so the refresh runs `helm dep update` there. Dry runs skip
 * the helm lock — nothing is on disk to lock against.
 * @param cwd The workspace root.
 * @param opts dryRun/verbose/rootVersionActionsOptions from the release command.
 * @returns The changed files (the locks), for staging and commit.
 */
export async function afterAllProjectsVersioned(
    cwd: string,
    opts: { dryRun?: boolean; verbose?: boolean; rootVersionActionsOptions?: Record<string, unknown> },
): Promise<{ changedFiles: string[]; deletedFiles: string[] }> {
    const ecosystem = await nxlvAfterAllProjectsVersioned(cwd, opts);
    if (opts.dryRun) {
        return { changedFiles: [], deletedFiles: [] };
    }
    execSync("helm dep update helm", { cwd, stdio: "pipe" });
    return {
        changedFiles: [...ecosystem.changedFiles, "helm/Chart.lock"],
        deletedFiles: ecosystem.deletedFiles,
    };
}

/**
 * One parsed entry of a Chart.yaml `dependencies:` list. The fields arrive
 * in declaration order — the umbrella writes name, version, repository,
 * condition — so an entry is only complete once the block is parsed; all
 * pin reads/rewrites go through entries, never line-adjacency.
 */
interface DependencyEntry {
    /** The chart name (`- name:`). */
    readonly name: string;
    /** The raw `version:` pin (constraint prefix included), null when absent. */
    readonly version: string | null;
    /** The `repository:` value, null when absent (external chart). */
    readonly repository: string | null;
    /** The 0-based line index of the `version:` line, for in-place rewrites. */
    readonly versionLine: number | null;
}

/**
 * Parse a Chart.yaml `dependencies:` list into entries. The block runs from
 * `dependencies:` to the next top-level key (column 0); each `- name:` opens
 * an entry, the keys under it fill its fields. Comments and blank lines are
 * skipped. Line-based: these files are ours (single-line scalars), matching
 * the no-YAML-library convention of this module.
 * @param content The Chart.yaml content.
 * @returns The dependency entries, in file order.
 */
function parseDependencyEntries(content: string): DependencyEntry[] {
    const entries: DependencyEntry[] = [];
    const lines = content.split("\n");
    let inDeps = false;
    let current: {
        name: string;
        version: string | null;
        repository: string | null;
        versionLine: number | null;
    } | null = null;
    const flush = (): void => {
        if (current) entries.push(current);
        current = null;
    };
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (/^dependencies:\s*(#.*)?$/.test(line)) {
            inDeps = true;
            continue;
        }
        if (!inDeps) continue;
        if (/^\S/.test(line)) {
            flush();
            break;
        }
        const nameMatch = line.match(/^\s*-\s+name:\s*(\S+)\s*$/);
        if (nameMatch) {
            flush();
            current = {
                name: nameMatch[1].replace(/^["']|["']$/g, ""),
                version: null,
                repository: null,
                versionLine: null,
            };
            continue;
        }
        if (!current) continue;
        const versionMatch = line.match(/^\s*version:\s*(\S+)\s*$/);
        if (versionMatch && current.version === null) {
            current.version = versionMatch[1].replace(/^["']|["']$/g, "");
            current.versionLine = i;
            continue;
        }
        const repoMatch = line.match(/^\s*repository:\s*(\S+)\s*$/);
        if (repoMatch && current.repository === null) {
            current.repository = repoMatch[1].replace(/^["']|["']$/g, "");
        }
    }
    flush();
    return entries;
}

/**
 * Read a top-level `key: value` scalar from a Chart.yaml body (ignores
 * indented keys, so dependency-block `version:` lines are not picked up).
 * @param content The Chart.yaml content.
 * @param key The top-level key to read.
 * @returns The unquoted value, or null when the key is absent.
 */
function readScalarField(content: string, key: string): string | null {
    const match = content.match(new RegExp(`^${key}:\\s*(\\S.*?)\\s*$`, "m"));
    if (!match) {
        return null;
    }
    return match[1].replace(/^["']|["']$/g, "");
}

/**
 * Replace a top-level `key: value` scalar in a Chart.yaml body.
 * @param content The Chart.yaml content.
 * @param key The top-level key.
 * @param value The new raw value (quoted as the convention for appVersion).
 * @param manifestPath The file being written, for the error message.
 * @returns The new content.
 * @throws When the key is not present.
 */
function replaceScalarField(content: string, key: string, value: string, manifestPath: string): string {
    const quoted = key === "appVersion" ? `"${value}"` : value;
    const pattern = new RegExp(`^${key}:\\s*\\S.*$`, "m");
    if (!pattern.test(content)) {
        throw new Error(`ChartYamlVersionActions: no top-level '${key}:' to update in ${manifestPath}`);
    }
    return content.replace(pattern, `${key}: ${quoted}`);
}

/**
 * Rewrite the `version:` pin inside each `- name: <chart>` block of a
 * Chart.yaml `dependencies:` list, for charts whose OWNING project is in
 * this release (DD-250: the release plan speaks in project names; a chart
 * is reached through its owner, via the dependency's `repository:` path).
 * @param content The umbrella Chart.yaml content.
 * @param dependenciesToUpdate Project names and their new versions.
 * @param manifestPath The file being written, for the log lines.
 * @param chartDir The directory of the manifest being updated (repo paths are relative to it).
 * @param tree The release tree, for reading owner project manifests.
 * @returns The new content and the log lines for the pins that changed.
 */
function updateDependencyPins(
    content: string,
    dependenciesToUpdate: Record<string, string>,
    manifestPath: string,
    chartDir: string,
    tree: Tree,
): { content: string; updated: string[] } {
    const updated: string[] = [];
    const lines = content.split("\n");
    for (const entry of parseDependencyEntries(content)) {
        if (entry.version === null || entry.versionLine === null) continue;
        const owner = entry.repository ? ownerProjectName(entry.repository, chartDir, tree) : null;
        const newVersion = owner ? dependenciesToUpdate[owner] : undefined;
        if (!newVersion || entry.version === newVersion) continue;
        const indent = /^\s*/.exec(lines[entry.versionLine])?.[0] ?? "";
        // Nx hands the new version WITH the constraint prefix (it reads
        // the =/^/~ from readCurrentVersionOfDependency as versionPrefix
        // "auto"), so the pin is the value verbatim.
        lines[entry.versionLine] = `${indent}version: "${newVersion}"`;
        updated.push(`  - Pinned ${manifestPath} dependency ${entry.name} (owner ${owner}) → ${newVersion}`);
    }
    return { content: lines.join("\n"), updated };
}

/**
 * The chart name of a dependency entry whose OWNING project is `projectName`
 * — found by following the entry's `repository: file://<path>` to the chart
 * dir, the chart dir's parent to the owner root, and the owner's manifests
 * to its Nx project name (DD-250: charts are not projects, the release plan
 * speaks in owner names).
 * @param content The umbrella Chart.yaml content.
 * @param chartDir The directory of the manifest being read (repo paths are relative to it).
 * @param projectName The dependency's OWNING project name.
 * @param tree The release tree, for reading owner project manifests.
 * @returns The chart name, or null when no dependency of this chart is owned by that project.
 */
function chartNameForDependency(content: string, chartDir: string, projectName: string, tree: Tree): string | null {
    for (const entry of parseDependencyEntries(content)) {
        const owner = entry.repository ? ownerProjectName(entry.repository, chartDir, tree) : null;
        if (owner === projectName) return entry.name;
    }
    return null;
}

/**
 * The Nx project name of the owner of a `file://` chart repository (the
 * chart dir's parent): `name` from the owner's project.json, else
 * `[project] name` in its pyproject.toml, else (workspace root) the root
 * package.json name. Null for repositories outside the workspace.
 * @param repository The raw repository value (file:// relative path).
 * @param chartDir The directory of the manifest declaring it (paths are relative to it).
 * @param tree The release tree, for reading owner project manifests.
 * @returns The owner project name, or null.
 */
function ownerProjectName(repository: string, chartDir: string, tree: Tree): string | null {
    if (!repository.startsWith("file://")) return null;
    const depChartDir = posix.normalize(`${chartDir}/${repository.slice("file://".length)}`);
    const ownerRoot = depChartDir === "helm" ? "." : dirname(depChartDir);
    const prefix = ownerRoot === "." ? "" : `${ownerRoot}/`;
    if (tree.exists(`${prefix}project.json`)) {
        const name = (JSON.parse(tree.read(`${prefix}project.json`, "utf8") ?? "{}").name ?? "") as string;
        if (name) return name;
    }
    if (tree.exists(`${prefix}pyproject.toml`)) {
        const match = /\[project\][^[]*?^name\s*=\s*"([^"]+)"/m.exec(
            tree.read(`${prefix}pyproject.toml`, "utf8") ?? "",
        );
        if (match) return match[1];
    }
    if (ownerRoot === "." && tree.exists("package.json")) {
        const name = (JSON.parse(tree.read("package.json", "utf8") ?? "{}").name ?? "") as string;
        if (name) return name;
    }
    return null;
}

/**
 * Read a workspace file straight from disk (the read happens before any
 * release write touches it).
 * @param path The workspace-relative path.
 * @returns The file content.
 */
function readDisk(path: string): string {
    return readFileSync(path, "utf8");
}
