import { NOOP_VERSION_ACTIONS } from "nx/src/command-line/release/version/version-actions";

/**
 * Version actions for projects that have no version manifest of their own,
 * such as the dev infrastructure projects (docker-compose only) or Gradle
 * modules without a package.json.
 *
 * Nx's default JS version actions read `<projectRoot>/package.json` when
 * resolving the current version of a dependency, which crashes with
 * "Cannot find <root>/package.json" for the manifest-less projects above
 * whenever a released project depends on them in the project graph.
 *
 * This implementation keeps the no-op behavior (the fixed release group
 * still tags these projects via the shared git tag) but reports "no known
 * dependency version" so dependents skip manifest updates for them.
 */
export default class NoopVersionActions extends NOOP_VERSION_ACTIONS {
    async readCurrentVersionOfDependency(): Promise<{
        currentVersion: string | null;
        dependencyCollection: string | null;
    }> {
        return { currentVersion: null, dependencyCollection: null };
    }
}
