ARG CONNECT_VERSION=8.2.4
ARG KAFKA_VERSION=4.3-debian13

# Use a Confluent image for the build stage
FROM confluentinc/cp-kafka-connect:${CONNECT_VERSION} AS builder

# Switch to the root user
USER root

# Install build tools
RUN --mount=type=cache,target="/var/cache/dnf",sharing="locked" \
    microdnf install -y gzip tar

# Install Apache AVRO converter
ARG CONNECT_AVRO_CONVERTER_VERSION=8.2.4
# The confluent-hub CLI runs on the JVM, which can pick a broken IPv6 route in
# some build networks; force IPv4 for the install step.
RUN JAVA_TOOL_OPTIONS="-Djava.net.preferIPv4Stack=true" \
    confluent-hub install "confluentinc/kafka-connect-avro-converter:${CONNECT_AVRO_CONVERTER_VERSION}" --no-prompt

# Download Debezium
ARG DEBEZIUM_CONNECTOR_JDBC_VERSION=3.7.0.Final
ADD "https://repo1.maven.org/maven2/io/debezium/debezium-connector-jdbc/${DEBEZIUM_CONNECTOR_JDBC_VERSION}/debezium-connector-jdbc-${DEBEZIUM_CONNECTOR_JDBC_VERSION}-plugin.tar.gz" "/usr/share/confluent-hub-components/"

# Install Debezium
RUN tar -xvf "/usr/share/confluent-hub-components/debezium-connector-jdbc-${DEBEZIUM_CONNECTOR_JDBC_VERSION}-plugin.tar.gz" -C "/usr/share/confluent-hub-components/"

# OpenLineage integration for the JDBC sink (native since Debezium 3.3.0): the
# plugin tarball bundles only debezium-openlineage-api; the ServiceLoader
# implementation (debezium-openlineage-core) plus the OpenLineage client and
# its runtime deps must be added next to it, or the integration silently
# falls back to a no-op emitter. Versions mirror debezium-parent 3.7.0.Final
# (<version.openlineage>) and the client's own dependency closure; Jackson is
# reused from the patched 2.22.x set below (jackson-annotations/jsr310/yaml +
# snakeyaml are the only Jackson artifacts the client needs that Connect lacks).
ARG OPENLINEAGE_CLIENT_VERSION=1.31.0
ARG HTTPCLIENT5_VERSION=5.4.3
ARG HTTPCORE5_VERSION=5.3.4
ARG COMMONS_LANG3_VERSION=3.17.0
ARG COMMONS_LOGGING_VERSION=1.3.5
ARG MICROMETER_VERSION=1.14.5
ARG HDRHISTOGRAM_VERSION=2.2.2
ARG LATENCYUTILS_VERSION=2.0.3
ARG SNAKEYAML_VERSION=2.5
RUN set -eux; \
    ol_libs="/usr/share/confluent-hub-components/debezium-connector-jdbc"; \
    for spec in \
    "io/debezium/debezium-openlineage-core:${DEBEZIUM_CONNECTOR_JDBC_VERSION}" \
    "io/openlineage/openlineage-java:${OPENLINEAGE_CLIENT_VERSION}" \
    "org/apache/httpcomponents/client5/httpclient5:${HTTPCLIENT5_VERSION}" \
    "org/apache/httpcomponents/core5/httpcore5:${HTTPCORE5_VERSION}" \
    "org/apache/commons/commons-lang3:${COMMONS_LANG3_VERSION}" \
    "commons-logging/commons-logging:${COMMONS_LOGGING_VERSION}" \
    "io/micrometer/micrometer-core:${MICROMETER_VERSION}" \
    "io/micrometer/micrometer-commons:${MICROMETER_VERSION}" \
    "io/micrometer/micrometer-observation:${MICROMETER_VERSION}" \
    "org/hdrhistogram/HdrHistogram:${HDRHISTOGRAM_VERSION}" \
    "org/latencyutils/LatencyUtils:${LATENCYUTILS_VERSION}" \
    "org/yaml/snakeyaml:${SNAKEYAML_VERSION}"; do \
    group_path="${spec%%:*}"; version="${spec##*:}"; artifact="${group_path##*/}"; \
    curl -fsSL -o "${ol_libs}/${artifact}-${version}.jar" \
    --proto "=https" \
    "https://repo1.maven.org/maven2/${group_path}/${version}/${artifact}-${version}.jar"; \
    done

# Overwrite the vulnerable jars vendored by the plugins above with patched
# versions: the plugins ship jackson 2.22.1 and mariadb 3.5.3, which have
# known vulnerabilities fixed in the versions below (drop-in patches).
ARG JACKSON_VERSION=2.22.3
ARG MARIADB_JDBC_VERSION=3.5.10
# The Kafka runtime's Jackson line (/opt/kafka/libs). The OpenLineage client
# binds to it rather than carrying its own: plugin classloading is child-first
# for classes, but ObjectMapper.findModules() ServiceLoader-scans the whole
# classpath — with a plugin-local databind, the parent-registered modules
# (jackson-module-blackbird et al. on the runtime classpath) load against the
# parent's databind and fail Hibernate's findModules() inside the JDBC sink
# ("BlackbirdModule not a subtype"). Ship no databind in the plugin dir and
# keep this version in sync with the base image's jackson-databind-* jars.
ARG PARENT_JACKSON_VERSION=2.21.7
RUN set -eux; \
    jackson_libs="/usr/share/confluent-hub-components/confluentinc-kafka-connect-avro-converter/lib"; \
    debezium_libs="/usr/share/confluent-hub-components/debezium-connector-jdbc"; \
    for spec in \
    "jackson-core:com/fasterxml/jackson/core" \
    "jackson-databind:com/fasterxml/jackson/core" \
    "jackson-dataformat-csv:com/fasterxml/jackson/dataformat" \
    "jackson-datatype-jdk8:com/fasterxml/jackson/datatype"; do \
    artifact="${spec%%:*}"; group_path="${spec##*:}"; \
    rm -f "${jackson_libs}/${artifact}-"*".jar"; \
    curl -fsSL -o "${jackson_libs}/${artifact}-${JACKSON_VERSION}.jar" \
    --proto "=https" \
    "https://repo1.maven.org/maven2/${group_path}/${artifact}/${JACKSON_VERSION}/${artifact}-${JACKSON_VERSION}.jar"; \
    done; \
    # The OpenLineage client reuses the Kafka runtime's Jackson (parent-first
    # delegation for every artifact the plugin dir does not carry). Only
    # jsr310 is absent there and the client's JavaTimeModule needs it, so
    # ship exactly that one artifact at the runtime's version — a plugin-local
    # copy of databind/core would split jackson across classloaders (see
    # PARENT_JACKSON_VERSION above).
    curl -fsSL -o "${debezium_libs}/jackson-datatype-jsr310-${PARENT_JACKSON_VERSION}.jar" \
    --proto "=https" \
    "https://repo1.maven.org/maven2/com/fasterxml/jackson/datatype/jackson-datatype-jsr310/${PARENT_JACKSON_VERSION}/jackson-datatype-jsr310-${PARENT_JACKSON_VERSION}.jar"; \
    rm -f "${debezium_libs}/mariadb-java-client-"*".jar"; \
    curl -fsSL -o "${debezium_libs}/mariadb-java-client-${MARIADB_JDBC_VERSION}.jar" \
    --proto "=https" \
    "https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/${MARIADB_JDBC_VERSION}/mariadb-java-client-${MARIADB_JDBC_VERSION}.jar"

# Use a hardened Kafka image during runtime
# Note: the hardened image does not have a package manager
FROM dhi.io/kafka:${KAFKA_VERSION} AS runtime

ARG VERSION=local

# Add image metadata
LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="This is an example Kafka Connect JDBC sink connector."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/project-template
LABEL org.opencontainers.image.title="Aurelius Kafka Connect JDBC Sink Example"
LABEL org.opencontainers.image.version="${VERSION}"

# Copy runtime dependencies from the builder stage
COPY --chown=root:root --chmod=0755 --from=builder "/usr/share/confluent-hub-components" "/usr/share/confluent-hub-components"

# Switch to the non-root user
USER kafka
