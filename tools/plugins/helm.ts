import { createNodesFromFiles, CreateNodesResult, CreateNodes } from "@nx/devkit";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, posix } from "node:path";

export interface HelmPluginOptions {
    readonly lintTargetName?: string;
    readonly templateTargetName?: string;
    readonly publishTargetName?: string;
    readonly signTargetName?: string;
    readonly verifyTargetName?: string;
}

const glob = "**/Chart.yaml";

/**
 * The composite version-actions module chart owners get (DD-250): it versions
 * the owner's ecosystem manifest (pyproject.toml — python.ts wires the same
 * module for the uv projects) AND the chart's Chart.yaml, re-pins the
 * umbrella, and refreshes its Chart.lock. Owners with a project.json (dev/*)
 * set it there; python.ts (wired after helm) overwrites this field with the
 * same module plus its lock-skip options.
 */
const VERSION_ACTIONS = "tools/plugins/chart-yaml-version-actions.ts";

export const createNodes: CreateNodes<HelmPluginOptions> = [
    glob,
    async (configFiles, options, context) => {
        return await createNodesFromFiles(
            (configFile) => createNodesInternal(configFile, options),
            configFiles,
            options,
            context,
        );
    },
];

/**
 * Infer a chart's targets and merge them onto its OWNER project (DD-247,
 * DD-250). Mirroring the docker plugin: `helm-lint` + `helm-template` gate
 * every change without a cluster (CHT-06), `helm-publish` ships the OCI
 * artifact in the release workflow (CHT-05). Every chart is a component chart
 * living next to the project it deploys (DD-247); the recursive Chart.yaml
 * glob picks them up wherever they sit; the result is keyed at the OWNER's
 * root — the chart dir's parent (`helm` at the workspace root merges onto the
 * root project) — so Nx adds the targets to the existing project node.
 *
 * The plugin sets no `name` and no `projectType`: a chart is not a project,
 * and a node's name belongs to the first plugin that claims its root — helm
 * runs early in the plugin list, so naming here would rename the owner.
 * `release` rides along only at the root project, where the umbrella lives
 * and the field is merged (not overwritten) with the python plugin's; for
 * every other chart owner, the release config is owned by its ecosystem
 * (python.ts / project.json — both wire the same composite module, DD-250),
 * and a chart-only owner (no manifest of its own) inherits the composite
 * field set here. The umbrella's `dependencies:` block becomes
 * implicitDependencies on the OWNING projects (chart → chart dir → owner),
 * which is what pulls the component charts into the umbrella's release
 * group and makes `helm-publish` cascade (CHT-05).
 * @param configFilePath The path of the Chart.yaml that matched.
 * @param options Target-name overrides from nx.json.
 * @returns The inferred project nodes, keyed at the owner's root.
 */
function createNodesInternal(
    configFilePath: string,
    {
        lintTargetName = "helm-lint",
        templateTargetName = "helm-template",
        publishTargetName = "helm-publish",
        signTargetName = "helm-sign",
        verifyTargetName = "helm-verify",
    }: HelmPluginOptions = {},
): CreateNodesResult {
    const chartDir = dirname(configFilePath);
    // The OWNER root: the chart dir's parent. A component chart under
    // apps/<x>/helm (or dev/<x>/helm) merges onto the app; `helm` at the
    // workspace root merges onto the root project (`.`).
    const ownerRoot = chartDir === "helm" ? "." : dirname(chartDir);
    const chartYaml = readFileSync(configFilePath, "utf-8");
    // Validates the file is a chart; identity lives in Chart.yaml. The chart
    // name (not the owner's Nx project name) is the OCI repository suffix —
    // it keys the sign/verify references too (CHT-95).
    const chartName = readChartName(chartYaml, configFilePath);
    // The umbrella's dependencies list IS its component-chart edges: as
    // implicitDependencies it gives helm-publish its cascade (the
    // `{ dependencies: true }` dependsOn) and pulls every component chart
    // into the umbrella's release group (DD-250).
    const dependencyCharts = readDependencyCharts(chartYaml);

    // The chart's own render inputs (CHT-06): tests/values.test.yaml, plus
    // every environments/*.yaml overlay (CHT-04: environment = values). The
    // umbrella's minikube overlay renders here, so the cloud-agnostic render
    // is proven on every change, not only in the 10.5 cluster run. Each set
    // renders on its own — DD-246: separate renders name the failing file;
    // overlays stack only in a real install.
    const valueFiles: string[] = [];
    if (existsSync(`${chartDir}/tests/values.test.yaml`)) {
        valueFiles.push(`${chartDir}/tests/values.test.yaml`);
    }
    if (existsSync(`${chartDir}/environments`)) {
        for (const name of readdirSync(`${chartDir}/environments`).sort()) {
            if (name.endsWith(".yaml")) {
                valueFiles.push(`${chartDir}/environments/${name}`);
            }
        }
    }
    const renders =
        valueFiles.length > 0
            ? valueFiles.map((f) => `helm template atlas ${chartDir} --namespace atlas -f ${f}`)
            : [`helm template atlas ${chartDir} --namespace atlas`];

    const targets: Record<string, unknown> = {
        [lintTargetName]: {
            command: `helm lint ${chartDir} --namespace atlas`,
            metadata: {
                description: "Lint the Helm chart (CHT-06: no cluster needed)",
            },
        },
        [templateTargetName]: {
            command: `helm dep update ${chartDir} >/dev/null && ${renders.join(" && ")}`,
            dependsOn: [{ target: lintTargetName }],
            metadata: {
                description: "Render the Helm chart with its test values and environment overlays (CHT-06)",
            },
        },
        [publishTargetName]: {
            // The tarball is named after the CHART (helm package), the Nx
            // project after its OWNER, so glob the artifact rather than
            // build a name. The OCI repository takes the chart name: the
            // artifact lands at oci://<ns>/<chart>.
            command:
                `helm dep update ${chartDir} >/dev/null && ` +
                `helm package ${chartDir} --version {args.version} -d {args.outDir} && ` +
                `helm push "$(ls {args.outDir}/*.tgz)" oci://{args.namespace}`,
            dependsOn: [
                { target: templateTargetName },
                { target: publishTargetName, dependencies: true, params: "forward" },
            ],
            metadata: {
                description: "Publish the chart as an OCI artifact to the registry (CHT-05)",
            },
            options: {
                namespace: "ghcr.io/aureliusenterprise/charts",
                outDir: "{tmpDir}",
                version: "0.0.0-local",
            },
        },
        // The cosign keyless pair on the OCI chart artifact (CHT-95, DD-278):
        // the docker plugin's docker-sign/docker-verify shape, keyed on the
        // chart name (the same reference helm push wrote). The publish
        // workflow signs and verifies right after helm-publish, under the
        // same id-token identity as the image chain.
        [signTargetName]: {
            command: `cosign sign --yes {args.namespace}/${chartName}:{args.version}`,
            options: {
                namespace: "ghcr.io/aureliusenterprise/charts",
                version: "0.0.0-local",
            },
            metadata: {
                description: "Sign the published chart OCI artifact with Cosign (CHT-95)",
            },
        },
        [verifyTargetName]: {
            command:
                `cosign verify {args.namespace}/${chartName}:{args.version} ` +
                `--certificate-identity-regex '{args.identity}' ` +
                `--certificate-oidc-issuer-regexp '{args.issuer}'`,
            options: {
                identity: ".*",
                issuer: ".*",
                namespace: "ghcr.io/aureliusenterprise/charts",
                version: "0.0.0-local",
            },
            metadata: {
                description: "Verify Cosign signatures for the chart OCI artifact (CHT-95)",
            },
        },
    };

    // Merge onto the OWNER (DD-250). The result is keyed at the owner's root
    // so Nx adds these targets to the existing project node — no `*-chart`
    // project. The plugin sets no `name`/`projectType`: a node's name belongs
    // to the first plugin that claims its root, helm runs early in the plugin
    // list, and naming here would rename the owner. `release` points every
    // chart owner at the composite module (chart-yaml-version-actions.ts),
    // which versions the owner's ecosystem manifest (pyproject.toml for the
    // uv apps and the root — python.ts runs after helm and overwrites this
    // field with the same module plus its options) AND the chart's
    // Chart.yaml/appVersion, re-pins the umbrella, and refreshes its
    // Chart.lock. Owners with a project.json (dev/*) set the composite there
    // — project.json overrides inference (DD-250).
    return {
        projects: {
            [ownerRoot]: {
                release: { version: { versionActions: VERSION_ACTIONS } },
                ...(ownerRoot === "."
                    ? { implicitDependencies: ownerNamesForDependencyCharts(dependencyCharts, chartDir) }
                    : {}),
                tags: ["helm"],
                targets,
            },
        },
    };
}

/**
 * A dependency entry of a Chart.yaml `dependencies:` block.
 */
interface ChartDependency {
    readonly name: string;
    readonly repository: string | null;
}

/**
 * Map the umbrella's dependency charts to the OWNING project names by
 * following each `repository: file://<path>` to its chart dir (the chart
 * file's sibling owner: `<dir>/helm/Chart.yaml` → owner `<dir>`) and reading
 * the owner's name (project.json, pyproject.toml `[project] name`,
 * package.json). These implicitDependencies are what pull the component
 * charts into the umbrella's release group (DD-250) and give
 * `helm-publish` its cascade (CHT-05).
 * @param dependencies The umbrella's dependency charts (name + repository).
 * @param chartDir The umbrella chart dir, the base for the relative repo paths.
 * @returns The owner project names, in dependency order.
 */
function ownerNamesForDependencyCharts(dependencies: ReadonlyArray<ChartDependency>, chartDir: string): string[] {
    const owners: string[] = [];
    for (const dep of dependencies) {
        if (!dep.repository?.startsWith("file://")) continue; // external chart: not a workspace project
        const depChartDir = posix.normalize(`${chartDir}/${dep.repository.slice("file://".length)}`);
        const depOwnerRoot = depChartDir === "helm" ? "." : dirname(depChartDir);
        const name = readProjectName(depOwnerRoot);
        if (name) owners.push(name);
    }
    return owners;
}

/**
 * The Nx project name for a workspace root: `name` from its project.json,
 * else `[project] name` in its pyproject.toml, else (workspace root) the
 * root package.json name. Null when the root declares none of those.
 * @param ownerRoot The workspace-relative root to read.
 * @returns The project name, or null.
 */
function readProjectName(ownerRoot: string): string | null {
    const prefix = ownerRoot === "." ? "" : `${ownerRoot}/`;
    if (existsSync(`${prefix}project.json`)) {
        const name = (JSON.parse(readFileSync(`${prefix}project.json`, "utf-8")).name ?? "") as string;
        if (name) return name;
    }
    if (existsSync(`${prefix}pyproject.toml`)) {
        const match = /\[project\][^[]*?^name\s*=\s*"([^"]+)"/m.exec(readFileSync(`${prefix}pyproject.toml`, "utf-8"));
        if (match) return match[1];
    }
    if (ownerRoot === "." && existsSync("package.json")) {
        const name = (JSON.parse(readFileSync("package.json", "utf-8")).name ?? "") as string;
        if (name) return name;
    }
    return null;
}

/**
 * Read the chart's `name:` scalar from a Chart.yaml (the chart's own name,
 * which Helm also uses for the packaged artifact and the OCI repository).
 * Line-based: these files are ours (single-line scalars), matching
 * chart-yaml-version-actions.ts's no-YAML-library convention.
 * @param content The Chart.yaml content.
 * @param path The file path, for the error message.
 * @returns The chart name.
 */
function readChartName(content: string, path: string): string {
    const match = content.match(/^name:\s*(.+)$/m);
    if (!match) {
        throw new Error(`helm plugin: no 'name:' in ${path} — not a chart.`);
    }
    return match[1].trim().replace(/^["']|["']$/g, "");
}

/**
 * Read the `dependencies:` block of a Chart.yaml (the umbrella has one;
 * component charts have none), capturing each entry's `name:` and its
 * `repository:` when present. The block ends at the first top-level key
 * (column 0) after it started.
 * @param content The Chart.yaml content.
 * @returns The dependency entries, in file order.
 */
function readDependencyCharts(content: string): ChartDependency[] {
    const deps: ChartDependency[] = [];
    let inDeps = false;
    let pending: { name: string; repository: string | null } | null = null;
    for (const line of content.split("\n")) {
        if (/^dependencies:\s*(#.*)?$/.test(line)) {
            inDeps = true;
            continue;
        }
        if (!inDeps) continue;
        if (/^\S/.test(line)) break;
        const nameMatch = line.match(/^\s*-\s+name:\s*(.+)$/);
        if (nameMatch) {
            if (pending) deps.push(pending);
            pending = { name: nameMatch[1].trim().replace(/^["']|["']$/g, ""), repository: null };
            continue;
        }
        const repoMatch = line.match(/^\s*repository:\s*(.+)$/);
        if (repoMatch && pending && pending.repository === null) {
            pending.repository = repoMatch[1].trim().replace(/^["']|["']$/g, "");
        }
    }
    if (pending) deps.push(pending);
    return deps;
}
