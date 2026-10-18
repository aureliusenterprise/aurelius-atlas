import {
    createNodesFromFiles,
    CreateNodesResult,
    CreateNodes,
    ProjectConfiguration,
    readJsonFile,
    TargetConfiguration,
} from "@nx/devkit";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

export interface DockerComposePluginOptions {
    readonly serveTargetName?: string;
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
    { serveTargetName = "serve", upTargetName = "up" }: DockerComposePluginOptions = {},
): CreateNodesResult {
    const projectRoot = dirname(configFilePath);

    // The docker-compose file must be in the same directory as the project.json file
    if (!existsSync(join(projectRoot, "project.json"))) {
        return {};
    }

    // Projects that own TLS material must generate their certificates before any
    // container that mounts ./certs is started.
    const certgen = existsSync(join(projectRoot, "tls.json")) ? [{ target: "certgen" }] : [];
    // Dependency stacks mount *their* projects' certificates too (the dashboard stack mounts
    // ../aurelius-atlas-server/certs), so their certgen runs before this stack starts — on a fresh
    // checkout those PEM files exist only after it. Projects without a certgen target are skipped.
    const certgenDeps = [{ target: "certgen", dependencies: true }];

    const targets: Record<string, TargetConfiguration> = {};
    targets[serveTargetName] = {
        continuous: true,
        command: "docker compose up",
        dependsOn: [
            { target: "decrypt" },
            ...certgen,
            { target: "docker-build" },
            { target: "docker-build", dependencies: true },
            ...certgenDeps,
            { target: serveTargetName, dependencies: true },
        ],
        metadata: {
            description: "Run the service locally.",
        },
        options: {
            cwd: projectRoot,
        },
    };

    targets[upTargetName] = {
        command: "docker compose up -d --wait",
        dependsOn: [
            { target: "decrypt" },
            ...certgen,
            { target: "docker-build" },
            { target: "docker-build", dependencies: true },
            ...certgenDeps,
            { target: upTargetName, dependencies: true },
        ],
        metadata: {
            description: "Start the service in the background and wait for it to become healthy.",
        },
        options: {
            cwd: projectRoot,
        },
    };

    return {
        projects: {
            [projectRoot]: {
                tags: ["docker-compose"],
                targets,
            },
        },
    };
}
