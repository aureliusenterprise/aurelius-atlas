import { createNodesFromFiles, CreateNodesResult, CreateNodes } from "@nx/devkit";
import { existsSync } from "node:fs";
import { basename, dirname, join } from "node:path";

export interface SonarQubePluginOptions {
    readonly sonarTargetName?: string;
}

const glob = "**/sonar-project.properties";

export const createNodes: CreateNodes<SonarQubePluginOptions> = [
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

function createNodesInternal(
    configFilePath: string,
    { sonarTargetName = "sonar" }: SonarQubePluginOptions = {},
): CreateNodesResult {
    const projectRoot = dirname(configFilePath);
    // The scanner authenticates with SONAR_TOKEN, which lives in the
    // project's decrypted .env. The task env Nx snapshots at pre-hash is
    // read before this target's `decrypt` dependency runs, so hand the file
    // to run-commands to load at spawn; gated on `.env.enc` so a project
    // without an encrypted env (whose decrypt writes nothing) stays clear of
    // a missing-file error.
    const envFile = existsSync(join(projectRoot, ".env.enc")) ? join(projectRoot, ".env") : undefined;

    return {
        projects: {
            [projectRoot]: {
                name: basename(projectRoot),
                targets: {
                    [sonarTargetName]: {
                        dependsOn: ["decrypt"],
                        executor: "nx:run-commands",
                        metadata: {
                            description: "Run SonarQube analysis on the project",
                        },
                        options: {
                            command: `sonar-scanner -Dproject.settings=${projectRoot}/sonar-project.properties -Dsonar.working.directory=${projectRoot}/.scannerwork`,
                            ...(envFile ? { envFile } : {}),
                        },
                    },
                },
            },
        },
    };
}
