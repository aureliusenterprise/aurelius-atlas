import { createNodesFromFiles, CreateNodesResult, CreateNodes } from "@nx/devkit";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

export interface DockerComposePluginOptions {
    readonly upTargetName?: string;
}

const glob = "**/docker-compose.{yml,yaml}";

export const createNodes: CreateNodes<DockerComposePluginOptions> = [
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
    { upTargetName = "up" }: DockerComposePluginOptions = {},
): CreateNodesResult {
    const projectRoot = dirname(configFilePath);

    // The docker-compose file must be in the same directory as the project.json file
    if (!existsSync(join(projectRoot, "project.json"))) {
        return {};
    }

    // Projects that own TLS material must generate their certificates before any
    // container that mounts ./certs is started.
    const certgen = existsSync(join(projectRoot, "tls.json")) ? [{ target: "certgen" }] : [];

    return {
        projects: {
            [projectRoot]: {
                tags: ["docker-compose"],
                targets: {
                    // No foreground "serve" target: `docker compose up` in the
                    // foreground tears the stack down when it exits, which
                    // takes the shared dev infrastructure with it. The discrete
                    // `up` target below is the only entry point; `--wait`
                    // already blocks until every service is healthy, so no
                    // readiness probe is needed.
                    [upTargetName]: {
                        command: "docker compose up -d --wait",
                        dependsOn: [
                            { target: "decrypt" },
                            ...certgen,
                            { target: "docker-build" },
                            { target: "docker-build", dependencies: true },
                            { target: upTargetName, dependencies: true },
                        ],
                        metadata: {
                            description: "Start the service in the background and wait for it to become healthy.",
                        },
                        options: {
                            cwd: projectRoot,
                        },
                    },
                },
            },
        },
    };
}
