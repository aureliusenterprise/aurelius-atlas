import { join } from "node:path";
import type { ProjectGraph, Tree } from "@nx/devkit";
import { VersionActions } from "nx/release";

/**
 * Version actions for Gradle/Java projects, which have no first-class Nx
 * release support yet (@nx/gradle only infers build/test targets).
 *
 * The source of truth is the `version = "..."` line in the project's
 * `build.gradle.kts` (or `build.gradle`). Dependency versions are not
 * written: Gradle subproject dependencies (`project(":...")`) always
 * resolve to the current source of the dependency, so there is nothing to
 * pin.
 */
export default class GradleVersionActions extends VersionActions {
    validManifestFilenames = ["build.gradle.kts", "build.gradle"];

    private findManifestPath(tree: Tree): string | null {
        for (const filename of this.validManifestFilenames) {
            const path = join(this.projectGraphNode.data.root, filename);
            if (tree.exists(path)) {
                return path;
            }
        }
        return null;
    }

    async readCurrentVersionFromSourceManifest(tree: Tree): Promise<{
        currentVersion: string;
        manifestPath: string;
    } | null> {
        const manifestPath = this.findManifestPath(tree);
        if (!manifestPath) {
            throw new Error(
                `No build.gradle(.kts) file found for project "${this.projectGraphNode.name}" in ${this.projectGraphNode.data.root}`,
            );
        }
        const match = tree.read(manifestPath, "utf-8")?.match(/^(\s*)version\s*=\s*"([^"]+)"/m);
        if (!match) {
            throw new Error(
                `Unable to determine the current version for project "${this.projectGraphNode.name}" from ${manifestPath}, please ensure that a 'version = "<semver>"' line is set within the build script`,
            );
        }
        return { currentVersion: match[2], manifestPath };
    }

    async readCurrentVersionFromRegistry(): Promise<{
        currentVersion: string | null;
        logText: string;
    } | null> {
        return null;
    }

    async readCurrentVersionOfDependency(): Promise<{
        currentVersion: string | null;
        dependencyCollection: string | null;
    }> {
        // Gradle project dependencies are not version-pinned in any manifest.
        return { currentVersion: null, dependencyCollection: null };
    }

    async updateProjectVersion(tree: Tree, newVersion: string): Promise<string[]> {
        const manifestPath = this.findManifestPath(tree);
        if (!manifestPath) {
            throw new Error(
                `No build.gradle(.kts) file found for project "${this.projectGraphNode.name}" in ${this.projectGraphNode.data.root}`,
            );
        }
        const content = tree.read(manifestPath, "utf-8");
        const updated = content.replace(/^(\s*)version\s*=\s*"[^"]+"/m, `$1version = "${newVersion}"`);
        if (updated === content) {
            throw new Error(`Unable to write the new version to ${manifestPath}, no 'version = "..."' line was found`);
        }
        tree.write(manifestPath, updated);
        return [`✍️  New version ${newVersion} written to manifest: ${manifestPath}`];
    }

    async updateProjectDependencies(
        _tree: Tree,
        _projectGraph: ProjectGraph,
        _dependenciesToUpdate: Record<string, string>,
    ): Promise<string[]> {
        return [];
    }
}
