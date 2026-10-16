import { createNodesFromFiles, CreateNodes, CreateNodesResult, workspaceRoot } from "@nx/devkit";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

export interface OpenMetadataPluginOptions {
    readonly ingestTargetName?: string;
}

const glob = "**/openmetadata.yaml";

export const createNodes: CreateNodes<OpenMetadataPluginOptions> = [
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
    { ingestTargetName = "openmetadata-ingest" }: OpenMetadataPluginOptions = {},
): CreateNodesResult {
    const projectRoot = dirname(configFilePath);

    if (!existsSync(join(projectRoot, "project.json"))) {
        return {
            projects: {},
        };
    }

    return {
        projects: {
            [projectRoot]: {
                tags: ["openmetadata"],
                targets: {
                    [ingestTargetName]: {
                        // certgen: scan configs reference the project's
                        // certificates by path (/certs/... in the container,
                        // bind-mounted below); the broker/listeners are TLS-only.
                        // governance decrypt: OPENMETADATA_VERSION resolves at
                        // command time from dev/governance/.env (see the
                        // version arg below), so that file must be decrypted.
                        dependsOn: ["decrypt", "certgen", { projects: "aurelius-dev-governance", target: "decrypt" }],
                        executor: "nx:run-commands",
                        metadata: {
                            description: "Run OpenMetadata ingestion",
                        },
                        options: {
                            command:
                                // --env-file also seeds ${VAR} substitution in
                                // the config (metadata's parser expands from
                                // the process env); certs mount exposes the
                                // project's certgen output to path-based
                                // client settings (libpq, librdkafka).
                                // kc_token.py mints a short-lived Keycloak
                                // service-account token (openmetadata-bot
                                // client, resolved by the OM claims mapping to
                                // the seeded ingestion-bot) and passes it as
                                // OM_JWT_TOKEN via -e (after --env-file, so a
                                // stale dotenv key cannot shadow it) — no
                                // committed PAT anywhere.
                                // render_inline.py resolves `inline:/certs/...`
                                // markers to certificate content first: the
                                // ingestion SSLManager treats sslConfig values
                                // as content (temp-files them for the driver),
                                // and the CA is generated per dev, never
                                // committed. The rendered config stays in the
                                // container's /tmp — only the committed
                                // template is mounted.
                                'sh -c \'OM_TOKEN="$(python3 "{args.tokenScript}")" && [ -n "$OM_TOKEN" ] && exec docker run --rm --env-file="{args.dotenv}" -e "OM_JWT_TOKEN=$OM_TOKEN" -v="{args.configPath}:/config/openmetadata.template.yaml:ro" -v="{args.renderScript}:/tools/render_inline.py:ro" -v="{args.certsPath}:/certs:ro" --entrypoint="sh" --net="host" openmetadata/ingestion:{args.version} -c "python3 /tools/render_inline.py /config/openmetadata.template.yaml /tmp/openmetadata.yaml && exec metadata ingest -c /tmp/openmetadata.yaml"\'',
                            tokenScript: `${workspaceRoot}/tools/openmetadata/kc_token.py`,
                            renderScript: `${workspaceRoot}/tools/openmetadata/render_inline.py`,
                            configPath: `${workspaceRoot}/${projectRoot}/openmetadata.yaml`,
                            certsPath: `${workspaceRoot}/${projectRoot}/certs`,
                            dotenv: `${projectRoot}/.env`,
                            // The server image (dev/governance/docker-compose.yaml),
                            // the OL ingestion image
                            // (dev/governance/integrations/docker-compose.yaml) and
                            // this one must stay on the same version — the
                            // ingestion client refuses cross-major talks — so all
                            // three resolve OPENMETADATA_VERSION from the
                            // governance env file (its .env.enc is the source of
                            // truth). Resolved when the command runs, i.e. after
                            // decrypt; the script falls back to a pinned default
                            // only for pre-decrypt graph inference.
                            version: `$(python3 ${workspaceRoot}/tools/openmetadata/om_version.py)`,
                        },
                        parallelism: false,
                    },
                },
            },
        },
    };
}
