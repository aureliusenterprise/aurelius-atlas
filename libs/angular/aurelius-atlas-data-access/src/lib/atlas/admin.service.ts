import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { map, Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import type { AtlasExportAnswer, AtlasExportRequest, AtlasImportRequest, AtlasImportResult } from "./atlas-impexp";
import type { EntityMutationResponse } from "./atlas-mutation";
import type { AtlasPatch } from "./atlas-patches";
import type { AtlasTask } from "./atlas-tasks";

/**
 * What `GET /api/atlas/admin/version` answers (ADM-01). The keys are capitalised the way
 * Apache Atlas's `AdminResource.Version` serialises them, which Aurelius Atlas keeps
 * (DV-03) — `Name` is `aurelius-atlas`, not `Atlas`.
 */
export type AtlasVersion = {
    readonly Version: string;
    readonly Revision: string;
    readonly Name: string;
    readonly Description: string;
};

/** What `GET /api/atlas/admin/status` answers (ADM-02): the only state is `ACTIVE`. */
export type AtlasStatus = {
    readonly Status: "ACTIVE";
};

/**
 * What `GET /api/atlas/admin/session` answers (ADM-05): the Atlas UI settings under
 * their dotted keys, plus this session's user (AUT-09, since 6.1a), the time zone ids
 * the date pickers list, and the CSRF token.
 */
export type AtlasSession = {
    [setting: `atlas.${string}`]: string | boolean;
    readonly userName: string | null;
    readonly groups: string[];
    readonly timezones: string[];
    readonly _csrfToken: string;
};

/** The bare-JSON answer of `GET /patches` before the list is unwrapped (AAC-02). */
type PatchesEnvelope = {
    patches: AtlasPatch[];
};

/**
 * The admin endpoints of the Atlas server (`AdminResource`, ADM-01..05,
 * AAC-01..07, APC-02): version, status, this session's settings, the health
 * answers, the patch records, purge, export/import, and the task list. Every
 * URL composes from the injected {@link API_BASE_URL} (APC-01). The Python twin
 * is `AtlasClient.admin` (CL-11, CLW-01..06).
 */
@Injectable({
    providedIn: "root",
})
export class AdminService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * The server's name, release and revision (ADM-01, APC-02).
     * @returns the version document
     */
    getVersion(): Observable<AtlasVersion> {
        return this.http.get<AtlasVersion>(`${this.baseUrl}/atlas/admin/version`);
    }

    /**
     * The service state, `ACTIVE` while the server runs (ADM-02, APC-02).
     * @returns the status document
     */
    getStatus(): Observable<AtlasStatus> {
        return this.http.get<AtlasStatus>(`${this.baseUrl}/atlas/admin/status`);
    }

    /**
     * The UI settings and user of this session (ADM-05, APC-02).
     * @returns the session document
     */
    getSession(): Observable<AtlasSession> {
        return this.http.get<AtlasSession>(`${this.baseUrl}/atlas/admin/session`);
    }

    /**
     * `OK` while the server lives (ADM-03, AAC-01) — the plain-text answer.
     * @returns the health text
     */
    liveness(): Observable<string> {
        return this.http.get(`${this.baseUrl}/atlas/admin/liveness`, { responseType: "text" });
    }

    /**
     * The readiness text (ADM-04, AAC-01); a server that is not ready answers its
     * Atlas error through the error channel (APC-04).
     * @returns the health text
     */
    readiness(): Observable<string> {
        return this.http.get(`${this.baseUrl}/atlas/admin/readiness`, { responseType: "text" });
    }

    /**
     * The typedef patch records (ENS-10, CLW-01, AAC-02), unwrapped from the
     * server's `{"patches": [...]}` envelope — the Python twin's shape.
     * @returns the patch records
     */
    patches(): Observable<AtlasPatch[]> {
        return this.http
            .get<PatchesEnvelope>(`${this.baseUrl}/atlas/admin/patches`)
            .pipe(map((envelope) => envelope.patches));
    }

    /**
     * Remove the `DELETED` entities of the guid array (EDL-01..EDL-03, CLW-02,
     * AAC-03). An empty list still sends `[]`: the server reads a missing body as
     * `BAD_REQUEST` (DV-10), never as "purge nothing".
     * @param guids the guids to purge
     * @returns what the purge mutated
     */
    purge(guids: string[]): Observable<EntityMutationResponse> {
        return this.http.put<EntityMutationResponse>(`${this.baseUrl}/atlas/admin/purge`, guids);
    }

    /**
     * The export ZIP (EXP-01..EXP-06, CLW-03, AAC-04, DD-315). No request sends
     * no body — the empty one the server builds from a missing body (DV-120).
     * The 204 of an empty export asked to omit its ZIP (EXP-05) answers
     * `{ body: null, contentType: "" }`.
     * @param request the entities and options of the export
     * @returns the ZIP bytes and the content type the server answered
     */
    export(request?: AtlasExportRequest | null): Observable<AtlasExportAnswer> {
        return this.http
            .post(`${this.baseUrl}/atlas/admin/export`, request ?? null, {
                responseType: "arraybuffer",
                observe: "response",
            })
            .pipe(
                map((response) => ({
                    body: response.body,
                    contentType: response.headers.get("content-type") ?? "",
                })),
            );
    }

    /**
     * The export ZIP imported as the request asks (IMS-01..IMS-05, CLW-04,
     * AAC-05). The `data` part carries the bytes as the file `export.zip`; the
     * `request` part, when given, is a plain text field holding the request as
     * JSON — never a file part (DD-313).
     * @param content the export ZIP
     * @param request the import options
     * @returns what the import did
     */
    importData(content: Blob, request?: AtlasImportRequest): Observable<AtlasImportResult> {
        const form = new FormData();
        form.append("data", content, "export.zip");
        if (request !== undefined) {
            form.append("request", JSON.stringify(request));
        }
        return this.http.post<AtlasImportResult>(`${this.baseUrl}/atlas/admin/import`, form);
    }

    /**
     * The ZIP named by the request's `fileName` option, opened by the server from
     * its import folder (IMS-06, DV-125, CLW-05, AAC-05). This client reads no
     * folder of its own (DD-310) — the name travels as the request's option.
     * @param request the import options, with `fileName`
     * @returns what the import did
     */
    importFile(request: AtlasImportRequest): Observable<AtlasImportResult> {
        return this.http.post<AtlasImportResult>(`${this.baseUrl}/atlas/admin/importfile`, request);
    }

    /**
     * The tasks of the guids given, or every task (TSK-06, CLW-06, AAC-06). Each
     * guid travels as a repeated `guids` parameter; none given sends no parameter,
     * which the server reads as "every task".
     * @param guids the guids whose tasks are asked for
     * @returns the tasks
     */
    tasks(guids?: string[]): Observable<AtlasTask[]> {
        return this.http.get<AtlasTask[]>(`${this.baseUrl}/atlas/admin/tasks`, {
            params: this.guidsParams(guids),
        });
    }

    /**
     * Remove the tasks of the guids given (TSK-06, CLW-06, AAC-06). Answers 204.
     * @param guids the guids whose tasks are removed
     */
    deleteTasks(guids: string[]): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/atlas/admin/tasks`, {
            params: this.guidsParams(guids),
        });
    }

    /**
     * The repeated `guids` parameter of the task routes (AAC-06).
     * @param guids the guids, when given
     * @returns the query parameters to send
     */
    private guidsParams(guids?: string[]): HttpParams {
        let params = new HttpParams();
        for (const guid of guids ?? []) {
            params = params.append("guids", guid);
        }
        return params;
    }
}
