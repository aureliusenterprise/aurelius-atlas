package com.aureliusenterprise.producer;

import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Type-safe configuration class for the Kafka producer application.
 * Uses environment variables with automatic validation, similar to Pydantic Settings in Python.
 * <p>
 * Configure using environment variables (all names carry the
 * {@code AURELIUS_JAVA_PRODUCER_} prefix — mirroring the Python apps'
 * pydantic {@code env_prefix} — so configuration from other workspace
 * projects can never populate this application):
 * <ul>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_KAFKA_BOOTSTRAP_SERVERS}: Kafka bootstrap servers (required)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_SCHEMA_REGISTRY_URL}: URL for the schema registry (required)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_KAFKA_TOPIC_NAME}: Name of the Kafka topic to produce messages to (required)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_MESSAGE_INTERVAL_MILLIS}: Interval in milliseconds between messages (optional, defaults to 10000)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_FILE}: PKCS12 truststore used to verify brokers and the schema registry over TLS (optional)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_PASSWORD}: Password for the truststore (required when a truststore is set)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_TOKEN_ENDPOINT_URL}: OIDC token endpoint of the Kafka realm (optional; enables OAUTHBEARER when set)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_CLIENT_ID}: Keycloak client id for the token grant (required with the token endpoint)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_CLIENT_SECRET}: Keycloak client secret for the token grant (required with the token endpoint)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_OPENLINEAGE_JOB_NAME}: OpenLineage job name (optional, defaults to the project name)</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_OPENLINEAGE_JOB_NAMESPACE}: OpenLineage job namespace (optional, defaults to {@code aurelius-openlineage})</li>
 *   <li>{@code AURELIUS_JAVA_PRODUCER_OPENLINEAGE_KAFKA_NAMESPACE}: OpenLineage Kafka dataset namespace in {@code kafka://host:port} format (optional, defaults to {@code kafka://localhost:9092}; the host:port must match the bootstrapServers of the Kafka service registered in OpenMetadata so the OpenLineage ingestion can resolve the topic)</li>
 * </ul>
 * The three OAuth settings are all-or-none: any partial combination is rejected, so a
 * deployment typo can never silently fall back to a non-OAuth listener.
 */
public record AppConfig(
    String kafkaBootstrapServers,
    String schemaRegistryUrl,
    String kafkaTopicName,
    long messageIntervalMillis,
    String kafkaTruststoreFile,
    String kafkaTruststorePassword,
    String kafkaOauthTokenEndpointUrl,
    String kafkaOauthClientId,
    String kafkaOauthClientSecret,
    String openLineageJobName,
    String openLineageJobNamespace,
    String openLineageKafkaNamespace
) {
    private static final Logger logger = LoggerFactory.getLogger(AppConfig.class);

    /**
     * Namespace for this application's environment variables, mirroring the
     * Python apps' pydantic {@code env_prefix}. The per-developer PKCS12
     * password (TLS_TRUSTSTORE_PASSWORD) is deliberately NOT read here and
     * stays unprefixed: certgen.sh and the dev stacks consume it by that name.
     */
    public static final String ENV_PREFIX = "AURELIUS_JAVA_PRODUCER_";

    /**
     * Creates a new {@link AppConfig} instance by loading configuration from environment variables.
     * Uses type-safe binding with validation, similar to Pydantic Settings in Python.
     *
     * @return a configured {@link AppConfig} instance
     * @throws MissingKeyException if any required configuration is missing or invalid
     */
    public static AppConfig load() {
        Map<String, String> env = System.getenv();
        return load(env);
    }

    /**
     * Returns a string representation with the truststore password redacted, so
     * logging the configuration (see {@code App.main}) cannot leak the secret.
     *
     * @return the redacted representation
     */
    @Override
    public String toString() {
        return (
            "AppConfig[kafkaBootstrapServers=" +
            kafkaBootstrapServers +
            ", schemaRegistryUrl=" +
            schemaRegistryUrl +
            ", kafkaTopicName=" +
            kafkaTopicName +
            ", messageIntervalMillis=" +
            messageIntervalMillis +
            ", kafkaTruststoreFile=" +
            kafkaTruststoreFile +
            ", kafkaTruststorePassword=******" +
            ", kafkaOauthTokenEndpointUrl=" +
            kafkaOauthTokenEndpointUrl +
            ", kafkaOauthClientId=" +
            kafkaOauthClientId +
            ", kafkaOauthClientSecret=******" +
            ", openLineageJobName=" +
            openLineageJobName +
            ", openLineageJobNamespace=" +
            openLineageJobNamespace +
            ", openLineageKafkaNamespace=" +
            openLineageKafkaNamespace +
            "]"
        );
    }

    /**
     * Creates a new {@link AppConfig} instance from the given environment map.
     * Extracted from {@link #load()} so the binding and validation rules can be
     * unit-tested with a synthetic environment.
     *
     * @param env the environment variables to bind
     * @return a configured {@link AppConfig} instance
     * @throws MissingKeyException if any required configuration is missing or invalid
     */
    public static AppConfig load(Map<String, String> env) {
        String kafkaBootstrapServers = getRequiredString(env, ENV_PREFIX + "KAFKA_BOOTSTRAP_SERVERS");
        String schemaRegistryUrl = getRequiredString(env, ENV_PREFIX + "SCHEMA_REGISTRY_URL");
        String kafkaTopicName = getRequiredString(env, ENV_PREFIX + "KAFKA_TOPIC_NAME");

        long messageIntervalMillis = getOptionalLong(env, ENV_PREFIX + "MESSAGE_INTERVAL_MILLIS", 10_000);
        String kafkaTruststoreFile = getOptionalString(env, ENV_PREFIX + "KAFKA_TRUSTSTORE_FILE", "");
        String kafkaTruststorePassword = env.getOrDefault(ENV_PREFIX + "KAFKA_TRUSTSTORE_PASSWORD", "");
        if (!kafkaTruststoreFile.isEmpty() && kafkaTruststorePassword.isEmpty()) {
            throw new MissingKeyException(
                ENV_PREFIX + "KAFKA_TRUSTSTORE_PASSWORD is required when " + ENV_PREFIX + "KAFKA_TRUSTSTORE_FILE is set"
            );
        }

        String kafkaOauthTokenEndpointUrl = getOptionalString(env, ENV_PREFIX + "KAFKA_OAUTH_TOKEN_ENDPOINT_URL", "");
        String kafkaOauthClientId = getOptionalString(env, ENV_PREFIX + "KAFKA_OAUTH_CLIENT_ID", "");
        String kafkaOauthClientSecret = env.getOrDefault(ENV_PREFIX + "KAFKA_OAUTH_CLIENT_SECRET", "");
        // All-or-none: every partial combination must fail. Validating only
        // "endpoint set but credentials missing" would let credentials
        // without an endpoint through, after which buildProducerProperties()
        // sees a blank endpoint and silently stays on a non-OAuth listener.
        int oauthSettingsSet = 0;
        if (!kafkaOauthTokenEndpointUrl.isEmpty()) {
            oauthSettingsSet++;
        }
        if (!kafkaOauthClientId.isEmpty()) {
            oauthSettingsSet++;
        }
        if (!kafkaOauthClientSecret.isEmpty()) {
            oauthSettingsSet++;
        }
        if (oauthSettingsSet > 0 && oauthSettingsSet < 3) {
            throw new MissingKeyException(
                ENV_PREFIX +
                    "KAFKA_OAUTH_TOKEN_ENDPOINT_URL, " +
                    ENV_PREFIX +
                    "KAFKA_OAUTH_CLIENT_ID and " +
                    ENV_PREFIX +
                    "KAFKA_OAUTH_CLIENT_SECRET must all be set together"
            );
        }

        String openLineageJobName = getOptionalString(
            env,
            ENV_PREFIX + "OPENLINEAGE_JOB_NAME",
            "aurelius-java-producer-example"
        );
        String openLineageJobNamespace = getOptionalString(
            env,
            ENV_PREFIX + "OPENLINEAGE_JOB_NAMESPACE",
            "aurelius-openlineage"
        );
        String openLineageKafkaNamespace = getOptionalString(
            env,
            ENV_PREFIX + "OPENLINEAGE_KAFKA_NAMESPACE",
            "kafka://localhost:9092"
        );

        return new AppConfig(
            kafkaBootstrapServers,
            schemaRegistryUrl,
            kafkaTopicName,
            messageIntervalMillis,
            kafkaTruststoreFile,
            kafkaTruststorePassword,
            kafkaOauthTokenEndpointUrl,
            kafkaOauthClientId,
            kafkaOauthClientSecret,
            openLineageJobName,
            openLineageJobNamespace,
            openLineageKafkaNamespace
        );
    }

    /**
     * Gets a required string value from the environment.
     *
     * @param env the environment map
     * @param key the environment variable name
     * @return the string value
     * @throws MissingKeyException if the value is missing or empty
     */
    private static String getRequiredString(Map<String, String> env, String key) {
        String value = env.get(key);
        if (value == null || value.isBlank()) {
            throw new MissingKeyException(
                String.format(
                    "Environment variable %s is required but was not set. Please check your configuration.",
                    key
                )
            );
        }
        return value;
    }

    /**
     * Gets an optional long value from the environment, with a default fallback.
     *
     * @param env the environment map
     * @param key the environment variable name
     * @param defaultValue the default value if not set or invalid
     * @return the parsed long value or the default
     */
    private static long getOptionalLong(Map<String, String> env, String key, long defaultValue) {
        String value = env.get(key);
        if (value == null || value.isBlank()) {
            logger.warn("Environment variable {} is not set. Using default of {} ms.", key, defaultValue);
            return defaultValue;
        }
        try {
            long parsedValue = Long.parseLong(value);
            if (parsedValue < 0) {
                logger.warn("{} value must be non-negative. Using default of {} ms.", key, defaultValue);
                return defaultValue;
            }
            return parsedValue;
        } catch (NumberFormatException e) {
            logger.warn(
                "Invalid {} value '{}' ({}). Using default of {} ms.",
                key,
                value,
                e.getMessage(),
                defaultValue
            );
            return defaultValue;
        }
    }

    /**
     * Gets an optional string value from the environment, with a default fallback.
     *
     * @param env the environment map
     * @param key the environment variable name
     * @param defaultValue the default value if not set or blank
     * @return the value or the default
     */
    private static String getOptionalString(Map<String, String> env, String key, String defaultValue) {
        String value = env.get(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return value;
    }
}
