/**
 * Atlas metrics DTOs — the wire shapes of the `/api/atlas/admin/metrics*` reads
 * (MET-01..MET-04, MHS-01..MHS-04, AAC-08, AAC-09).
 *
 * Field names are the camelCase names the server writes, mirrored from
 * `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/metrics.py`, ported
 * from Apache Atlas 2.4.0 `org.apache.atlas.model.metrics`): keep the two in
 * step when the Python model changes. The Python twin of this cluster is
 * `AtlasClient.admin.metrics` / `metrics_stats` / `metrics_stat` /
 * `metrics_in_range` / `metrics_charts` (CLW-08, CLW-09).
 */

/** `AtlasMetrics`: each group's metrics by name; no groups is no `data` (MET-01..MET-04). */
export type AtlasMetrics = {
    data?: Record<string, Record<string, unknown>> | null;
};

/**
 * `AtlasMetricsStat`: the metrics collected at a time, kept `timeToLiveMillis`;
 * `typeData` the counts of the types a range asks for, by state (MHS-01).
 */
export type AtlasMetricsStat = {
    guid?: string | null;
    metricsId?: string | null;
    /** Epoch milliseconds. */
    collectionTime?: number | null;
    /** Milliseconds. */
    timeToLiveMillis?: number | null;
    typeData?: Record<string, Record<string, number>> | null;
    metrics?: AtlasMetrics | null;
};

/**
 * `AtlasMetricsMapToChart`: one state's counts of a type, as
 * `[collectionTime, count]` pairs (MHS-04).
 */
export type AtlasMetricsMapToChart = {
    key?: string | null;
    values?: [number, number][] | null;
};

/**
 * What `admin/metricsstats/charts` answers (MHS-04): per type name, its counts
 * in the range by state.
 */
export type AtlasMetricsCharts = Record<string, AtlasMetricsMapToChart[]>;
