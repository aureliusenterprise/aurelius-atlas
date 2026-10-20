import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "./api-config";

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
 * their dotted keys, plus this session's user — which is `null` until increment 6.1
 * (DV-04) — the time zone ids the date pickers list, and the CSRF token.
 */
export type AtlasSession = {
    [setting: `atlas.${string}`]: string | boolean;
    readonly userName: string | null;
    readonly groups: string[];
    readonly timezones: string[];
    readonly _csrfToken: string;
};

/**
 * The admin endpoints of the Atlas server (`AdminResource`, ADM-01/02/05, APC-02):
 * version, status, and this session's settings. Every URL composes from the injected
 * {@link API_BASE_URL} (APC-01).
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
}
