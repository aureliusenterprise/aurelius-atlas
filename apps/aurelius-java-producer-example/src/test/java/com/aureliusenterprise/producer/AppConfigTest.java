package com.aureliusenterprise.producer;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AppConfigTest {

    private static final String BOOTSTRAP_SERVERS = "bootstrap:9092";

    /** Namespace under which AppConfig reads its variables (see AppConfig.ENV_PREFIX). */
    private static final String P = AppConfig.ENV_PREFIX;

    private static Map<String, String> baseEnv() {
        Map<String, String> env = new HashMap<>();
        env.put(P + "KAFKA_BOOTSTRAP_SERVERS", BOOTSTRAP_SERVERS);
        env.put(P + "SCHEMA_REGISTRY_URL", "http://localhost:8085");
        env.put(P + "KAFKA_TOPIC_NAME", "entities");
        return env;
    }

    @Test
    void loadShouldApplyDefaultsForOptionalTruststoreSettings() {
        AppConfig config = AppConfig.load(baseEnv());

        assertEquals(BOOTSTRAP_SERVERS, config.kafkaBootstrapServers());
        assertEquals("http://localhost:8085", config.schemaRegistryUrl());
        assertEquals("entities", config.kafkaTopicName());
        assertEquals(10_000L, config.messageIntervalMillis());
        assertEquals("", config.kafkaTruststoreFile());
        assertEquals("", config.kafkaTruststorePassword());
    }

    @Test
    void loadShouldReadTruststoreSettingsWhenSet() {
        Map<String, String> env = baseEnv();
        env.put(P + "KAFKA_TRUSTSTORE_FILE", "/certs/truststore.p12");
        env.put(P + "KAFKA_TRUSTSTORE_PASSWORD", "secret");

        AppConfig config = AppConfig.load(env);

        assertEquals("/certs/truststore.p12", config.kafkaTruststoreFile());
        assertEquals("secret", config.kafkaTruststorePassword());
    }

    @Test
    void loadShouldRejectTruststoreFileWithoutPassword() {
        Map<String, String> env = baseEnv();
        env.put(P + "KAFKA_TRUSTSTORE_FILE", "/certs/truststore.p12");

        MissingKeyException exception = assertThrows(MissingKeyException.class, () -> AppConfig.load(env));
        assertEquals(
            P + "KAFKA_TRUSTSTORE_PASSWORD is required when " + P + "KAFKA_TRUSTSTORE_FILE is set",
            exception.getMessage()
        );
    }

    @Test
    void toStringShouldRedactTruststorePassword() {
        Map<String, String> env = baseEnv();
        env.put(P + "KAFKA_TRUSTSTORE_FILE", "/certs/truststore.p12");
        env.put(P + "KAFKA_TRUSTSTORE_PASSWORD", "super-secret");

        String repr = AppConfig.load(env).toString();

        assertFalse(repr.contains("super-secret"), "toString must not leak the truststore password");
        assertTrue(repr.contains(BOOTSTRAP_SERVERS), "non-secret fields remain visible");
    }

    @Test
    void loadShouldAllowTruststorePasswordWithoutFile() {
        Map<String, String> env = baseEnv();
        env.put(P + "KAFKA_TRUSTSTORE_PASSWORD", "secret");

        AppConfig config = assertDoesNotThrow(() -> AppConfig.load(env));

        assertEquals("", config.kafkaTruststoreFile());
        assertEquals("secret", config.kafkaTruststorePassword());
    }

    @Test
    void loadShouldRejectMissingRequiredSetting() {
        Map<String, String> env = baseEnv();
        env.remove(P + "KAFKA_TOPIC_NAME");

        assertThrows(MissingKeyException.class, () -> AppConfig.load(env));
    }

    @Test
    void loadShouldApplyEmptyDefaultsForOptionalOauthSettings() {
        AppConfig config = AppConfig.load(baseEnv());

        assertEquals("", config.kafkaOauthTokenEndpointUrl());
        assertEquals("", config.kafkaOauthClientId());
        assertEquals("", config.kafkaOauthClientSecret());
    }

    @Test
    void loadShouldReadOauthSettingsWhenSet() {
        Map<String, String> env = baseEnv();
        env.put(
            P + "KAFKA_OAUTH_TOKEN_ENDPOINT_URL",
            "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
        );
        env.put(P + "KAFKA_OAUTH_CLIENT_ID", "kafka-producer");
        env.put(P + "KAFKA_OAUTH_CLIENT_SECRET", "s3cr3t");

        AppConfig config = AppConfig.load(env);

        assertEquals(
            "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token",
            config.kafkaOauthTokenEndpointUrl()
        );
        assertEquals("kafka-producer", config.kafkaOauthClientId());
        assertEquals("s3cr3t", config.kafkaOauthClientSecret());
    }

    @Test
    void loadShouldRejectTokenEndpointWithoutCredentials() {
        Map<String, String> env = baseEnv();
        env.put(
            P + "KAFKA_OAUTH_TOKEN_ENDPOINT_URL",
            "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
        );
        env.put(P + "KAFKA_OAUTH_CLIENT_ID", "kafka-producer");

        MissingKeyException exception = assertThrows(MissingKeyException.class, () -> AppConfig.load(env));
        assertEquals(
            P +
                "KAFKA_OAUTH_TOKEN_ENDPOINT_URL, " +
                P +
                "KAFKA_OAUTH_CLIENT_ID and " +
                P +
                "KAFKA_OAUTH_CLIENT_SECRET must all be set together",
            exception.getMessage()
        );
    }

    @Test
    void loadShouldRejectCredentialsWithoutTokenEndpoint() {
        // Without the endpoint, buildProducerProperties() silently stays on a
        // non-OAuth listener: partial configuration must fail, not downgrade.
        Map<String, String> env = baseEnv();
        env.put(P + "KAFKA_OAUTH_CLIENT_ID", "kafka-producer");
        env.put(P + "KAFKA_OAUTH_CLIENT_SECRET", "s3cr3t");

        MissingKeyException exception = assertThrows(MissingKeyException.class, () -> AppConfig.load(env));
        assertEquals(
            P +
                "KAFKA_OAUTH_TOKEN_ENDPOINT_URL, " +
                P +
                "KAFKA_OAUTH_CLIENT_ID and " +
                P +
                "KAFKA_OAUTH_CLIENT_SECRET must all be set together",
            exception.getMessage()
        );
    }

    @Test
    void loadShouldRejectClientIdAlone() {
        Map<String, String> env = baseEnv();
        env.put(P + "KAFKA_OAUTH_CLIENT_ID", "kafka-producer");

        assertThrows(MissingKeyException.class, () -> AppConfig.load(env));
    }

    @Test
    void toStringShouldRedactOauthClientSecret() {
        Map<String, String> env = baseEnv();
        env.put(
            P + "KAFKA_OAUTH_TOKEN_ENDPOINT_URL",
            "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
        );
        env.put(P + "KAFKA_OAUTH_CLIENT_ID", "kafka-producer");
        env.put(P + "KAFKA_OAUTH_CLIENT_SECRET", "super-secret");

        String repr = AppConfig.load(env).toString();

        assertFalse(repr.contains("super-secret"), "toString must not leak the OAuth client secret");
        assertTrue(repr.contains("kafka-producer"), "the client id is not a secret and remains visible");
    }
}
