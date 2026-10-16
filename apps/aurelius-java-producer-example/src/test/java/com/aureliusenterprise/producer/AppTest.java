package com.aureliusenterprise.producer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.util.Properties;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.junit.jupiter.api.Test;

class AppTest {

    private static AppConfig config(String truststoreFile, String truststorePassword, String oauthTokenEndpointUrl) {
        return new AppConfig(
            "bootstrap:9092",
            "http://localhost:8085",
            "entities",
            10_000L,
            truststoreFile,
            truststorePassword,
            oauthTokenEndpointUrl,
            oauthTokenEndpointUrl.isBlank() ? "" : "kafka-producer",
            oauthTokenEndpointUrl.isBlank() ? "" : "producer-secret",
            "aurelius-java-producer-example",
            "aurelius-openlineage",
            "kafka://localhost:9092"
        );
    }

    @Test
    void buildProducerPropertiesShouldSetBaseConfiguration() {
        Properties props = App.buildProducerProperties(config("", "", ""));

        assertEquals(StringSerializer.class, props.get(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG));
        assertEquals("bootstrap:9092", props.get(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG));
        assertEquals("http://localhost:8085", props.get("schema.registry.url"));
    }

    @Test
    void buildProducerPropertiesWithoutTruststoreStaysPlaintext() {
        Properties props = App.buildProducerProperties(config("", "", ""));

        assertNull(props.get("security.protocol"));
        assertNull(props.get("ssl.truststore.location"));
        assertNull(props.get("schema.registry.ssl.truststore.location"));
    }

    @Test
    void buildProducerPropertiesWithTruststoreEnablesTls() {
        Properties props = App.buildProducerProperties(config("/certs/truststore.p12", "secret", ""));

        assertEquals("SSL", props.get("security.protocol"));
        // Without a token endpoint there is no SASL layer on top of TLS.
        assertNull(props.get("sasl.mechanism"));
        assertEquals("PKCS12", props.get("ssl.truststore.type"));
        assertEquals("/certs/truststore.p12", props.get("ssl.truststore.location"));
        assertEquals("secret", props.get("ssl.truststore.password"));
        assertEquals("https", props.get("ssl.endpoint.identification.algorithm"));

        // The schema registry REST client needs its own truststore settings.
        assertEquals("PKCS12", props.get("schema.registry.ssl.truststore.type"));
        assertEquals("/certs/truststore.p12", props.get("schema.registry.ssl.truststore.location"));
        assertEquals("secret", props.get("schema.registry.ssl.truststore.password"));
        assertEquals("https", props.get("schema.registry.ssl.endpoint.identification.algorithm"));
    }

    @Test
    void buildProducerPropertiesWithTokenEndpointEnablesOauthBearer() {
        Properties props = App.buildProducerProperties(
            config(
                "/certs/truststore.p12",
                "secret",
                "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
            )
        );

        // The OAuth branch upgrades the TLS transport to SASL_SSL.
        assertEquals("SASL_SSL", props.get("security.protocol"));
        assertEquals("OAUTHBEARER", props.get("sasl.mechanism"));
        assertEquals(
            "org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;",
            props.get("sasl.jaas.config")
        );
        // Kafka 4.x defaults to the UNSECURED login handler; the client-credentials
        // handler must be named explicitly or no token is ever fetched.
        assertEquals(
            "org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginCallbackHandler",
            props.get("sasl.login.callback.handler.class")
        );
        assertEquals(
            "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token",
            props.get("sasl.oauthbearer.token.endpoint.url")
        );
        assertEquals("kafka-producer", props.get("sasl.oauthbearer.client.credentials.client.id"));
        assertEquals("producer-secret", props.get("sasl.oauthbearer.client.credentials.client.secret"));

        // Broker certificate verification is kept from the TLS branch.
        assertEquals("/certs/truststore.p12", props.get("ssl.truststore.location"));
    }

    @Test
    void buildProducerPropertiesTrustsGeneratedAvroPackage() {
        App.buildProducerProperties(config("", "", ""));

        String trusted = System.getProperty("org.apache.avro.SERIALIZABLE_PACKAGES");
        assertEquals("com.aureliusenterprise.example", trusted);
        assertFalse(trusted.isEmpty());
    }

    @Test
    void buildOpenLineageTransportPropertiesOverridesSerializersButKeepsSecurity() {
        Properties props = App.buildOpenLineageTransportProperties(
            config(
                "/certs/truststore.p12",
                "secret",
                "https://keycloak.localhost:8443/realms/kafka/protocol/openid-connect/token"
            )
        );

        // OL events are plain JSON strings, never Avro records.
        assertEquals(StringSerializer.class, props.get(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG));
        assertEquals(StringSerializer.class, props.get(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG));
        // The listener security settings are inherited from the entity producer.
        assertEquals("SASL_SSL", props.get("security.protocol"));
        assertEquals("bootstrap:9092", props.get(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG));
    }
}
