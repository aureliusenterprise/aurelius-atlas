import { HttpClient, HttpErrorResponse } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { EntityView, ViewConflict, ViewSaveRequest } from "../atlas/atlas-view";

/**
 * The client of the view family's mutation door (VDE-05, ADR 064): one entity's
 * desired state as a view in, that entity's live view out (AVW-01, AVW-07),
 * behind the same {@link API_BASE_URL} and authentication as the read door.
 * One request applies attributes, tags, term assignments and ends together
 * (AVW-05), so the caller sends no second call for any of them.
 *
 * The door's two 409 answers ride through untouched for the caller to tell
 * apart (VDE-07, VDE-08): the version conflict carries the stored view beside
 * the code, read with {@link viewConflictFrom}, and the name-taken answer is
 * the Atlas error shape that `isAtlasErrorBody` reads.
 */
@Injectable({
    providedIn: "root",
})
export class ViewSaveService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * Save one entity through the door (VDE-05): the body names the desired
     * state; the answer is the stored entity's live view, `stale` false
     * (AVW-07). A create names no guid and the answer carries the server's
     * (AVW-06); an update names the `updateTime` of the view it edited (AVW-04).
     * @param request the entity's desired state as a view
     * @returns the entity's live view after the write
     */
    save(request: ViewSaveRequest): Observable<EntityView> {
        return this.http.post<EntityView>(`${this.baseUrl}/aurelius/v1/entity`, request);
    }
}

/**
 * The lost-update conflict of a save, or null for any other failure (AVW-04,
 * VDE-07): the door answers the conflict code beside the stored view, a shape
 * {@link isAtlasErrorBody} does not match, so the editor reads it here.
 * @param error the failed response of {@link ViewSaveService.save}
 * @returns the conflict with the stored view to re-edit from, or null
 */
export function viewConflictFrom(error: HttpErrorResponse): ViewConflict | null {
    const body = error.error as Partial<ViewConflict> | null;
    if (error.status !== 409 || body == null || body.errorCode !== "ENTITY_VERSION_CONFLICT" || body.view == null) {
        return null;
    }
    return { errorCode: body.errorCode, view: body.view };
}
