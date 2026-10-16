import { createNodesFromFiles, CreateNodes, CreateNodesResult } from "@nx/devkit";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

export interface OpenLineagePluginOptions {
    readonly registerTargetName?: string;
}

const glob = "**/openlineage.yaml";

export const createNodes: CreateNodes<OpenLineagePluginOptions> = [
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
    { registerTargetName = "openlineage-register" }: OpenLineagePluginOptions = {},
): CreateNodesResult {
    const projectRoot = dirname(configFilePath);

    if (!existsSync(join(projectRoot, "project.json")) && !existsSync(join(projectRoot, "build.gradle.kts"))) {
        return {
            projects: {},
        };
    }

    return {
        projects: {
            [projectRoot]: {
                tags: ["openlineage"],
                targets: {
                    [registerTargetName]: {
                        // register.py uses the version-pinned metadata.sdk
                        // (openmetadata-ingestion, a root dev-group
                        // dependency), so it runs right on the host. It mints
                        // its own bot token via kc_token.py when
                        // OPENLINEAGE_JWT_TOKEN is unset; the client
                        // credentials live in dev/governance/.env, so its
                        // decrypted file must exist.
                        dependsOn: [{ projects: "aurelius-dev-governance", target: "decrypt" }],
                        executor: "@nxlv/python:run-commands",
                        metadata: {
                            description: "Register OpenLineage pipeline and optional lineage edges",
                        },
                        options: {
                            command: `uv run tools/openmetadata/register.py --config ${projectRoot}/openlineage.yaml`,
                        },
                        parallelism: false,
                    },
                },
            },
        },
    };
}
