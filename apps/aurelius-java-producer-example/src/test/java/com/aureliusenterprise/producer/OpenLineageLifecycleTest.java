package com.aureliusenterprise.producer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import io.openlineage.client.OpenLineage.OutputDataset;
import io.openlineage.client.OpenLineage.RunEvent;
import io.openlineage.client.OpenLineageClient;
import io.openlineage.client.transports.Transport;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for the OpenLineage event contract emitted by {@link OpenLineageLifecycle}.
 *
 * <p>The OpenMetadata OpenLineage connector is treated as working-as-advertised infra:
 * what these tests pin is the <em>identity</em> this producer contributes to every event —
 * the job namespace/name and the {@code kafka://host:port} dataset namespace the
 * connector matches against the Kafka service's bootstrapServers, plus the output
 * dataset name. Renaming any of these silently detaches the producer from the catalog
 * graph (the connector resolves by exact match), so the values asserted here mirror
 * the AppConfig defaults and the wiring contract in openlineage.yaml / AGENTS.md.
 *
 * <p>Events are captured with an in-memory transport through the package-private
 * constructor seam; no broker is involved.
 */
class OpenLineageLifecycleTest {

    private static final String TOPIC = "example.entity";
    private static final String JOB_NAME = "aurelius-java-producer-example";
    private static final String JOB_NAMESPACE = "aurelius-openlineage";
    private static final String KAFKA_NAMESPACE = "kafka://localhost:9092";

    /**
     * Transport that records emitted events instead of publishing them.
     */
    private static final class RecordingTransport extends Transport {

        /**
         * Events emitted so far, in order.
         */
        private final List<RunEvent> events = new ArrayList<>();

        @Override
        public void emit(RunEvent event) {
            events.add(event);
        }

        @Override
        public void emit(io.openlineage.client.OpenLineage.DatasetEvent event) {
            // Not used by the producer lifecycle.
        }

        @Override
        public void emit(io.openlineage.client.OpenLineage.JobEvent event) {
            // Not used by the producer lifecycle.
        }
    }

    private final RecordingTransport transport = new RecordingTransport();

    private OpenLineageLifecycle newLifecycle() {
        return new OpenLineageLifecycle(
            OpenLineageClient.builder().transport(transport).build(),
            TOPIC,
            JOB_NAME,
            JOB_NAMESPACE,
            KAFKA_NAMESPACE
        );
    }

    /**
     * The recorded events' types, in emission order. A loop rather than a stream:
     * JDT null analysis rejects the {@code RunEvent::getEventType} method reference
     * (unannotated list elements vs the jar's {@code @Nonnull} receiver) and
     * SonarLint rejects the equivalent lambda.
     *
     * @return the event types of every recorded event
     */
    private List<RunEvent.EventType> recordedEventTypes() {
        List<RunEvent.EventType> types = new ArrayList<>();
        for (RunEvent event : transport.events) {
            types.add(event.getEventType());
        }
        return types;
    }

    @Test
    void constructorEmitsStartEventWithJobAndDatasetIdentity() {
        OpenLineageLifecycle lifecycle = newLifecycle();

        assertEquals(1, transport.events.size(), "constructor must emit exactly the START event");
        RunEvent start = transport.events.get(0);
        assertEquals(RunEvent.EventType.START, start.getEventType());

        // Job identity: the connector derives the pipeline as "{namespace}-{name}";
        // these values must stay aligned with openlineage.yaml and AppConfig defaults.
        assertEquals(JOB_NAMESPACE, start.getJob().getNamespace());
        assertEquals(JOB_NAME, start.getJob().getName());

        // Dataset identity: the connector requires the kafka:// namespace to treat
        // the dataset as a topic and resolves the service by matching host:port.
        assertEquals(1, start.getOutputs().size());
        OutputDataset output = start.getOutputs().get(0);
        assertEquals(KAFKA_NAMESPACE, output.getNamespace());
        assertEquals(TOPIC, output.getName());

        assertNotNull(start.getRun().getRunId(), "every event carries the run id");
        assertNotNull(lifecycle);
    }

    @Test
    void allEventsShareOneRunIdAndJobIdentity() {
        OpenLineageLifecycle lifecycle = newLifecycle();
        lifecycle.recordOutput(3, 300);
        lifecycle.emitRunning();
        lifecycle.emitComplete();

        assertEquals(
            List.of(RunEvent.EventType.START, RunEvent.EventType.RUNNING, RunEvent.EventType.COMPLETE),
            recordedEventTypes()
        );

        UUID runId = transport.events.get(0).getRun().getRunId();
        for (RunEvent event : transport.events) {
            assertEquals(runId, event.getRun().getRunId(), "run id must be stable across the lifecycle");
            assertEquals(JOB_NAMESPACE, event.getJob().getNamespace());
            assertEquals(JOB_NAME, event.getJob().getName());
        }
    }

    @Test
    void runningAndCompleteCarryAccumulatedOutputStatistics() {
        OpenLineageLifecycle lifecycle = newLifecycle();
        lifecycle.recordOutput(2, 240);
        lifecycle.emitRunning();
        lifecycle.recordOutput(1, 60);
        lifecycle.emitComplete();

        RunEvent running = transport.events.get(1);
        var runningStats = running.getOutputs().get(0).getOutputFacets().getOutputStatistics();
        assertEquals(2L, runningStats.getRowCount());
        assertEquals(240L, runningStats.getSize());

        RunEvent complete = transport.events.get(2);
        var completeStats = complete.getOutputs().get(0).getOutputFacets().getOutputStatistics();
        assertEquals(3L, completeStats.getRowCount(), "statistics accumulate across the run");
        assertEquals(300L, completeStats.getSize());

        // The terminal event still describes the same dataset.
        assertEquals(KAFKA_NAMESPACE, complete.getOutputs().get(0).getNamespace());
        assertEquals(TOPIC, complete.getOutputs().get(0).getName());
    }

    @Test
    void emitFailRecordsTheErrorMessageRunFacet() {
        OpenLineageLifecycle lifecycle = newLifecycle();
        lifecycle.emitFail("broker went away");

        RunEvent fail = transport.events.get(1);
        assertEquals(RunEvent.EventType.FAIL, fail.getEventType());
        assertNotNull(fail.getRun().getFacets().getErrorMessage());
        assertEquals("broker went away", fail.getRun().getFacets().getErrorMessage().getMessage());
    }

    @Test
    void onlyOneTerminalEventIsEmitted() {
        OpenLineageLifecycle lifecycle = newLifecycle();
        lifecycle.emitComplete();
        lifecycle.emitComplete();
        lifecycle.emitFail("too late");

        List<RunEvent.EventType> types = recordedEventTypes();
        assertEquals(
            List.of(RunEvent.EventType.START, RunEvent.EventType.COMPLETE),
            types,
            "the first terminal event wins; the later FAIL must be suppressed"
        );
    }

    @Test
    void emitFailAfterCompleteIsSuppressed() {
        OpenLineageLifecycle lifecycle = newLifecycle();
        lifecycle.emitFail("boom");
        lifecycle.emitComplete();

        List<RunEvent.EventType> types = recordedEventTypes();
        assertEquals(List.of(RunEvent.EventType.START, RunEvent.EventType.FAIL), types);
        assertEquals("boom", transport.events.get(1).getRun().getFacets().getErrorMessage().getMessage());
    }
}
