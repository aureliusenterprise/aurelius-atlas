/**
 * Atlas export/import DTOs — the wire shapes of `/api/atlas/admin/export`,
 * `/import` and `/importfile` (EXP-01, IMS-01, APC-03).
 *
 * Field names are the camelCase names the server writes, mirrored from
 * `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/impexp.py`, ported
 * from Apache Atlas 2.4.0 `org.apache.atlas.model.impexp`): keep the two in
 * step when the Python model changes. Atlas writes both with `NON_NULL`: an
 * absent field is left out, an empty list or map kept. The Python twin of this
 * cluster is `AtlasClient.admin.export` / `import_data` / `import_file`
 * (CL-11, CLW-03..CLW-05).
 */

import type { AtlasObjectId } from "./atlas-entity";
import type { AtlasTypesDef } from "./atlas-typedef";

/** How an export or import ended (`AtlasExportResult.OperationStatus`). */
export type OperationStatus = "SUCCESS" | "PARTIAL_SUCCESS" | "FAIL";

/**
 * `AtlasExportRequest`: the entities to start from and the options of the
 * export (EXP-01). The option keys are the server's texts — `fetchType`,
 * `matchType`, `skipLineage`, `replicatedTo`, `changeMarker`,
 * `omitZipResponseForEmptyExport`.
 */
export type AtlasExportRequest = {
    itemsToExport?: AtlasObjectId[] | null;
    options?: Record<string, unknown> | null;
};

/** `AtlasImportRequest`: an import's options, each a text (IMS-01). */
export type AtlasImportRequest = {
    options?: Record<string, unknown> | null;
};

/** `AtlasExportData`: the type definitions an export collected, and the order it added entities in. */
export type AtlasExportData = {
    typesDef?: AtlasTypesDef | null;
    entityCreationOrder?: string[] | null;
};

/** `AtlasExportResult`: who exported what, when, from where, its counts and status (EXP-06). */
export type AtlasExportResult = {
    request?: AtlasExportRequest | null;
    userName?: string | null;
    clientIpAddress?: string | null;
    hostName?: string | null;
    /** Epoch milliseconds. */
    timeStamp?: number | null;
    metrics?: Record<string, number> | null;
    data?: AtlasExportData | null;
    operationStatus?: OperationStatus | null;
    sourceClusterName?: string | null;
    changeMarker?: number | null;
};

/** `AtlasImportResult`: who imported, when, its counts, the entities it wrote and its status. */
export type AtlasImportResult = {
    request?: AtlasImportRequest | null;
    userName?: string | null;
    clientIpAddress?: string | null;
    hostName?: string | null;
    /** Epoch milliseconds. */
    timeStamp?: number | null;
    metrics?: Record<string, number> | null;
    processedEntities?: string[] | null;
    operationStatus?: OperationStatus | null;
    exportResult?: AtlasExportResult | null;
};

/**
 * The answer of `POST /export` (AAC-04, DD-315): the ZIP bytes and the
 * `Content-Type` the server answered, the twin of the Python client's
 * `(bytes, content-type)` tuple (CLW-03, DD-310). The server's 204 for an
 * empty export asked to omit its ZIP (EXP-05) reads as
 * `{ body: null, contentType: "" }`.
 */
export type AtlasExportAnswer = {
    body: ArrayBuffer | null;
    contentType: string;
};

/** How one imported row ended (`BulkImportResponse.ImportStatus`). */
export type ImportStatus = "SUCCESS" | "FAILED";

/**
 * `ImportInfo`: the glossary and term of an imported row, its status and
 * remarks. Java's getter for `rowNumber` does not exist, so the server never
 * writes it — the DTO omits it (APC-03, `bulk_import.py`).
 */
export type ImportInfo = {
    parentObjectName?: string | null;
    childObjectName?: string | null;
    importStatus?: ImportStatus | null;
    remarks?: string | null;
};

/**
 * `BulkImportResponse`: the rows an import made and those it could not
 * (GIM-02, ACL-07) — the answer of the business-metadata and glossary file
 * imports. Atlas writes each list only when it holds an entry.
 */
export type BulkImportResponse = {
    failedImportInfoList?: ImportInfo[] | null;
    successImportInfoList?: ImportInfo[] | null;
};

/**
 * `AtlasServer`: a catalogue an export or import names, and the replication it
 * recorded (REP-01, AAC-10). The Python twin is `AtlasClient.admin.server`.
 */
export type AtlasServer = {
    guid?: string | null;
    name?: string | null;
    fullName?: string | null;
    displayName?: string | null;
    additionalInfo?: Record<string, string> | null;
    urls?: string[] | null;
};

/**
 * `ExportImportAuditEntry`: one export or import, its user, servers, times and
 * result (REP-02, REP-05, AAC-10). The Python twin is
 * `AtlasClient.admin.export_import_audit`.
 */
export type ExportImportAuditEntry = {
    guid?: string | null;
    userName?: string | null;
    operation?: string | null;
    operationParams?: string | null;
    /** Epoch milliseconds. */
    startTime?: number | null;
    /** Epoch milliseconds. */
    endTime?: number | null;
    resultSummary?: string | null;
    sourceServerName?: string | null;
    targetServerName?: string | null;
};
