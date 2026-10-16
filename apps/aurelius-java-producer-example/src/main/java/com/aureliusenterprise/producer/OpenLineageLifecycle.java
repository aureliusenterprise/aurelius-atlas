package com.aureliusenterprise.producer;

import io.openlineage.client.OpenLineage;
import io.openlineage.client.OpenLineage.RunEvent;
import io.openlineage.client.OpenLineageClient;
import io.openlineage.client.transports.KafkaConfig;
import io.openlineage.client.transports.KafkaTransport;
import java.net.URI;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Manages the OpenLineage run lifecycle for the Kafka entity producer.
 * Emits lifecycle events (START, RUNNING, COMPLETE, FAIL) to a Kafka topic
 * that the OpenMetadata OpenLineage connector consumes to create lineage edges.
 *
 * <p>The lifecycle follows the OpenLineage spec:
 * <ul>
 *   <li>{@code START} — emitted when the lifecycle is initialized</li>
 *   <li>{@code RUNNING} — emitted periodically during execution</li>
 *   <li>{@code COMPLETE} — emitted on graceful shutdown</li>
 *   <li>{@code FAIL} — emitted on error</li>
 * </ul>
 *
 * <p>Only one terminal event (COMPLETE or FAIL) is emitted, even if both are requested.
 * This class is thread-safe for concurrent use from the main loop and shutdown hook.
 */
public class OpenLineageLifecycle {

    /**
     * Logger instance for this class.
     */
    private static final Logger logger = LoggerFactory.getLogger(OpenLineageLifecycle.class);

    /**
     * Canonical producer URL recorded in every event ({@code event producer} field).
     * Must be a valid URI per the OpenLineage spec — a bare token like
     * "kafka-producer" is not one (no scheme) — so use the repository URL,
     * the convention for producer identity in OL events.
     */
    private static final String PRODUCER_URL = "https://github.com/aureliusenterprise/project-template";

    /**
     * The OpenLineage client used to emit events to Kafka.
     */
    private final OpenLineageClient client;

    /**
     * Unique run ID shared across all lifecycle events.
     */
    private final UUID runId;

    /**
     * Job metadata for the entity producer.
     */
    private final OpenLineage.Job job;

    /**
     * Output dataset metadata for the Kafka topic.
     */
    private final OpenLineage.OutputDataset outputDataset;

    /**
     * Thread-safe message counter for output statistics.
     */
    private final AtomicLong messageCount = new AtomicLong(0);

    /**
     * Thread-safe byte counter for output statistics.
     */
    private final AtomicLong totalBytes = new AtomicLong(0);

    /**
     * Tracks whether a terminal event (COMPLETE or FAIL) has already been emitted.
     * Ensures idempotency — only one terminal event fires.
     */
    private final AtomicReference<RunEvent.EventType> terminalState = new AtomicReference<>(null);

    /**
     * The namespace used for the Kafka dataset (derived from bootstrap servers).
     */
    private final String kafkaNamespace;

    /**
     * The job name for OpenLineage (derived from environment or default).
     */
    private final String jobName;

    /**
     * The namespace used for the job (derived from environment or default).
     */
    private final String jobNamespace;

    /**
     * Creates a new {@link OpenLineageLifecycle} and emits a START event.
     *
     * @param kafkaTransportProperties the raw Kafka producer properties for the OpenLineage
     *                                 event transport (bootstrap servers plus the TLS/SASL
     *                                 settings required by the target listener)
     * @param topicName                the Kafka topic name for the output dataset
     * @param jobNamespace             the namespace for OpenLineage job identification
     * @param kafkaDatasetNamespace    the OpenLineage Kafka dataset namespace in {@code kafka://host:port} format
     *                                 (e.g. {@code "kafka://broker:9094"}). The OpenMetadata OpenLineage connector
     *                                 uses this to detect Kafka topics (namespace must start with {@code kafka://})
     *                                 and resolves the messaging service by matching the broker hostname against
     *                                 the {@code bootstrapServers} configured in OpenMetadata.
     */
    public OpenLineageLifecycle(
        java.util.Properties kafkaTransportProperties,
        String topicName,
        String jobName,
        String jobNamespace,
        String kafkaDatasetNamespace
    ) {
        // Create the OpenLineage client with Kafka transport.
        // Events are published to the "openlineage-events" Kafka topic,
        // which the OpenMetadata OpenLineage connector consumes to create lineage edges.
        // The properties carry the listener security settings (TLS truststore /
        // OAUTHBEARER) so events reach the same broker the entity topic lives on.
        // The client construction is inlined because the delegating this(...) call must be
        // the first statement of the constructor.
        this(
            OpenLineageClient.builder()
                .transport(new KafkaTransport(new KafkaConfig("openlineage-events", null, kafkaTransportProperties)))
                .build(),
            topicName,
            jobName,
            jobNamespace,
            kafkaDatasetNamespace
        );

        String olBootstrap = kafkaTransportProperties.getProperty("bootstrap.servers");
        logger.info(
            "OpenLineage lifecycle initialized: runId={}, topic={}, kafkaBootstrapServers={}",
            runId,
            topicName,
            olBootstrap
        );
    }

    /**
     * Creates a new {@link OpenLineageLifecycle} emitting through a caller-supplied client
     * and emits a START event.
     *
     * <p>Package-private seam used by the unit tests to record events with an in-memory
     * transport instead of a Kafka broker; production code uses the properties-based
     * constructor, which wires the Kafka transport and logs the resolved bootstrap servers.
     *
     * @param client                  the OpenLineage client (and its transport) to emit through
     * @param topicName               the Kafka topic name for the output dataset
     * @param jobName                 the OpenLineage job name
     * @param jobNamespace            the namespace for OpenLineage job identification
     * @param kafkaDatasetNamespace   the OpenLineage Kafka dataset namespace in {@code kafka://host:port} format
     */
    OpenLineageLifecycle(
        OpenLineageClient client,
        String topicName,
        String jobName,
        String jobNamespace,
        String kafkaDatasetNamespace
    ) {
        // Use the kafka:// URL-format namespace so the OpenMetadata OpenLineage connector
        // detects this dataset as a Kafka topic (not a database table) and resolves the
        // messaging service by matching the broker hostname to bootstrapServers in OM.
        this.kafkaNamespace = kafkaDatasetNamespace;

        // Store the job name from configuration
        this.jobName = jobName;

        // Store the job namespace from configuration
        this.jobNamespace = jobNamespace;

        // Generate a unique run ID for this lifecycle
        this.runId = UUID.randomUUID();

        // Create the OpenLineage client instance
        OpenLineage openLineage = new OpenLineage(URI.create(PRODUCER_URL));

        // Build the job metadata
        this.job = openLineage
            .newJobBuilder()
            .namespace(this.jobNamespace)
            .name(this.jobName)
            .facets(openLineage.newJobFacetsBuilder().build())
            .build();

        // Build the output dataset metadata
        this.outputDataset = openLineage
            .newOutputDatasetBuilder()
            .namespace(this.kafkaNamespace)
            .name(topicName)
            .facets(
                openLineage
                    .newDatasetFacetsBuilder()
                    .version(openLineage.newDatasetVersionDatasetFacet("1.0"))
                    .documentation(
                        openLineage
                            .newDocumentationDatasetFacetBuilder()
                            .description("Kafka topic for entity messages")
                            .build()
                    )
                    .build()
            )
            .build();

        this.client = client;

        // Emit the START event
        emitStartEvent();
    }

    /**
     * Builds the OpenLineage run facets with nominal time information.
     *
     * <p>For a standalone producer with no upstream orchestrator (e.g., Airflow DAG),
     * no parent facet is included. The parent facet is only meaningful when this run
     * is a child of an orchestrated pipeline run.
     *
     * @param openLineage the OpenLineage instance to use for building the facets
     * @param now         the current UTC timestamp
     * @return the run facets with nominal time
     */
    private OpenLineage.RunFacets buildRunFacets(OpenLineage openLineage, ZonedDateTime now) {
        return openLineage
            .newRunFacetsBuilder()
            .nominalTime(openLineage.newNominalTimeRunFacetBuilder().nominalStartTime(now).nominalEndTime(now).build())
            .build();
    }

    /**
     * Emits a START event to OpenLineage.
     * This is called automatically by the constructor.
     */
    private void emitStartEvent() {
        try {
            ZonedDateTime now = ZonedDateTime.now(ZoneId.of("UTC"));
            OpenLineage openLineage = new OpenLineage(URI.create(PRODUCER_URL));

            OpenLineage.RunFacets runFacets = buildRunFacets(openLineage, now);

            OpenLineage.Run run = openLineage.newRunBuilder().runId(runId).facets(runFacets).build();

            RunEvent runEvent = openLineage
                .newRunEventBuilder()
                .eventType(RunEvent.EventType.START)
                .eventTime(now)
                .run(run)
                .job(job)
                .outputs(List.of(outputDataset))
                .build();

            client.emit(runEvent);
            logger.info("Emitted START event for run: {}", runId);
        } catch (Exception e) {
            logger.warn("Failed to emit START event: {}", e.getMessage());
        }
    }

    /**
     * Emits a RUNNING event with current output statistics.
     * Called periodically during message production.
     */
    public void emitRunning() {
        try {
            long currentMessages = messageCount.get();
            long currentBytes = totalBytes.get();
            ZonedDateTime now = ZonedDateTime.now(ZoneId.of("UTC"));
            OpenLineage openLineage = new OpenLineage(URI.create(PRODUCER_URL));

            OpenLineage.RunFacets runFacets = buildRunFacets(openLineage, now);

            OpenLineage.Run run = openLineage.newRunBuilder().runId(runId).facets(runFacets).build();

            // Add output statistics facet (rowCount, bytes, fileCount)
            OpenLineage.OutputDataset outputWithStats = openLineage
                .newOutputDatasetBuilder()
                .namespace(this.kafkaNamespace)
                .name(outputDataset.getName())
                .outputFacets(
                    openLineage
                        .newOutputDatasetOutputFacetsBuilder()
                        .outputStatistics(
                            openLineage.newOutputStatisticsOutputDatasetFacet(currentMessages, currentBytes, 1L)
                        )
                        .build()
                )
                .build();

            RunEvent runEvent = openLineage
                .newRunEventBuilder()
                .eventType(RunEvent.EventType.RUNNING)
                .eventTime(now)
                .run(run)
                .job(job)
                .outputs(List.of(outputWithStats))
                .build();

            client.emit(runEvent);
            logger.debug("Emitted RUNNING event: {} messages, {} bytes", currentMessages, currentBytes);
        } catch (Exception e) {
            logger.warn("Failed to emit RUNNING event: {}", e.getMessage());
        }
    }

    /**
     * Records output statistics after a successful message produce.
     * Thread-safe — can be called from any thread.
     *
     * @param messageCount the number of messages produced in this batch
     * @param bytes        the approximate byte size of the produced data
     */
    public void recordOutput(long messageCount, long bytes) {
        this.messageCount.addAndGet(messageCount);
        this.totalBytes.addAndGet(bytes);
    }

    /**
     * Emits a COMPLETE event with final output statistics.
     * Idempotent — no-op if a terminal event (COMPLETE or FAIL) has already been emitted.
     * Called from the shutdown hook on graceful shutdown.
     */
    public void emitComplete() {
        if (!terminalState.compareAndSet(null, RunEvent.EventType.COMPLETE)) {
            logger.debug("Terminal event already emitted ({}), skipping COMPLETE", terminalState.get());
            return;
        }

        try {
            long finalMessages = messageCount.get();
            long finalBytes = totalBytes.get();
            ZonedDateTime now = ZonedDateTime.now(ZoneId.of("UTC"));
            OpenLineage openLineage = new OpenLineage(URI.create(PRODUCER_URL));

            OpenLineage.RunFacets runFacets = buildRunFacets(openLineage, now);

            OpenLineage.Run run = openLineage.newRunBuilder().runId(runId).facets(runFacets).build();

            // Add output statistics facet (rowCount, bytes, fileCount)
            OpenLineage.OutputDataset outputWithStats = openLineage
                .newOutputDatasetBuilder()
                .namespace(this.kafkaNamespace)
                .name(outputDataset.getName())
                .outputFacets(
                    openLineage
                        .newOutputDatasetOutputFacetsBuilder()
                        .outputStatistics(
                            openLineage.newOutputStatisticsOutputDatasetFacet(finalMessages, finalBytes, 1L)
                        )
                        .build()
                )
                .build();

            RunEvent runEvent = openLineage
                .newRunEventBuilder()
                .eventType(RunEvent.EventType.COMPLETE)
                .eventTime(now)
                .run(run)
                .job(job)
                .outputs(List.of(outputWithStats))
                .build();

            client.emit(runEvent);
            logger.info("Emitted COMPLETE event: {} messages, {} bytes", finalMessages, finalBytes);
        } catch (Exception e) {
            logger.warn("Failed to emit COMPLETE event: {}", e.getMessage());
        }
    }

    /**
     * Emits a FAIL event with an error message.
     * Idempotent — no-op if a terminal event (COMPLETE or FAIL) has already been emitted.
     * Called from the error handler on failure.
     *
     * @param errorMessage the error message describing why the run failed
     */
    public void emitFail(String errorMessage) {
        if (!terminalState.compareAndSet(null, RunEvent.EventType.FAIL)) {
            logger.debug("Terminal event already emitted ({}), skipping FAIL", terminalState.get());
            return;
        }

        try {
            ZonedDateTime now = ZonedDateTime.now(ZoneId.of("UTC"));
            OpenLineage openLineage = new OpenLineage(URI.create(PRODUCER_URL));

            OpenLineage.RunFacets runFacets = openLineage
                .newRunFacetsBuilder()
                .nominalTime(
                    openLineage.newNominalTimeRunFacetBuilder().nominalStartTime(now).nominalEndTime(now).build()
                )
                .errorMessage(openLineage.newErrorMessageRunFacetBuilder().message(errorMessage).build())
                .build();

            OpenLineage.Run run = openLineage.newRunBuilder().runId(runId).facets(runFacets).build();

            RunEvent runEvent = openLineage
                .newRunEventBuilder()
                .eventType(RunEvent.EventType.FAIL)
                .eventTime(now)
                .run(run)
                .job(job)
                .outputs(List.of(outputDataset))
                .build();

            client.emit(runEvent);
            logger.warn("Emitted FAIL event: {}", errorMessage);
        } catch (Exception e) {
            logger.warn("Failed to emit FAIL event: {}", e.getMessage());
        }
    }
}
