import {
    createNodesFromFiles,
    type CreateNodes,
    type CreateNodesResult,
    type CreateNodesContext,
    type TargetDependencyConfig,
} from "@nx/devkit";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export interface TlsPluginOptions {
    readonly certgenTargetName?: string;
    readonly certcleanTargetName?: string;
}

/**
 * Per-project manifest: each project owns a `tls.json` listing the
 * certificates it presents (service name → SANs), plus optional JVM key
 * material (`keystore`) and trust material (`truststore`). Passwords for the
 * latter come from the project's decrypted `.env` (`TLS_TRUSTSTORE_PASSWORD`).
 */
interface TlsConfig {
    readonly services: Record<string, readonly string[]>;
    readonly keystore?: boolean;
    readonly truststore?: boolean;
}

const glob = "**/tls.json";

export const createNodes: CreateNodes<TlsPluginOptions> = [
    glob,
    async (configFiles, options, context) => {
        return await createNodesFromFiles(
            (configFile, _options, context) => createNodesInternal(configFile, options, context),
            configFiles,
            options,
            context,
        );
    },
];

function createNodesInternal(
    configFilePath: string,
    { certgenTargetName = "certgen", certcleanTargetName = "certclean" }: TlsPluginOptions = {},
    context: CreateNodesContext,
): CreateNodesResult {
    const projectRoot = configFilePath.replace(/\/tls\.json$/, "");
    const config = JSON.parse(readFileSync(join(context.workspaceRoot, configFilePath), "utf8")) as TlsConfig;

    // Each project certgen bootstraps the root CA itself (certgen.sh does it
    // under an exclusive lock, so parallel runs are safe); no workspace-level
    // prewarm target exists.
    const dependsOn: TargetDependencyConfig[] = [];

    // Keystores/truststores are password-protected PKCS12; the password must
    // be decrypted into the project's .env first.
    const needsPassword = Boolean(config.keystore || config.truststore);

    if (needsPassword) {
        dependsOn.push({ target: "decrypt" });
    }

    return {
        projects: {
            [projectRoot]: {
                tags: ["tls"],
                targets: {
                    [certgenTargetName]: {
                        command: `bash tools/tls/certgen.sh ${projectRoot}`,
                        // Not Nx-cached, and certgen.sh keeps no Nx-visible
                        // outputs: services run with certs/ bind-mounted, so
                        // the task must never churn that directory. Nx
                        // deletes declared outputs before every run (cache
                        // hits included), which orphans the containers'
                        // mounts, and an output-less cache hit can skip
                        // execution while the material is missing (e.g. after
                        // certclean). Idempotency therefore lives in the
                        // script itself: certs/.stamp fingerprints the root
                        // CA, tls.json, and the PKCS12 password, and the run
                        // is a no-op while the material is current — a
                        // re-run touches nothing, while rotation, deletion,
                        // or certclean regenerate it.
                        cache: false,
                        dependsOn,
                        metadata: {
                            description: "Generate this project's local development TLS material",
                        },
                    },
                    [certcleanTargetName]: {
                        command: `bash tools/tls/certclean.sh ${projectRoot}`,
                        cache: false,
                        metadata: {
                            description: "Remove this project's generated local TLS material",
                        },
                    },
                },
            },
        },
    };
}
