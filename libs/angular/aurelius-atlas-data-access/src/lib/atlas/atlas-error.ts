import { HttpErrorResponse } from "@angular/common/http";

/**
 * The Atlas error body (SRV-04): every failed REST call answers with this, from the
 * server's `atlas_error_handler` — the shape Apache Atlas writes and Aurelius Atlas
 * reproduces.
 */
export type AtlasErrorBody = {
    /** The Atlas error code, e.g. `ATLAS-400-00-001` (`AtlasErrorCode`). */
    readonly errorCode: string;
    /** The human-readable message. */
    readonly errorMessage: string;
    /** The cause's text, present when the server chains one. */
    readonly errorCause?: string;
};

/**
 * A failed Atlas REST call: the HTTP status plus the parsed {@link AtlasErrorBody}
 * (APC-04). Consumers narrow an `HttpErrorResponse` with {@link isAtlasErrorBody} and
 * map from there; the client does not swallow statuses.
 */
export function isAtlasErrorBody(body: unknown): body is AtlasErrorBody {
    return (
        typeof body == "object" &&
        body != null &&
        typeof (body as AtlasErrorBody).errorCode == "string" &&
        typeof (body as AtlasErrorBody).errorMessage == "string"
    );
}

/**
 * Extract the typed Atlas error from an `HttpErrorResponse` — the Atlas JSON body when
 * the server sent one, `null` for a transport failure or a non-Atlas body (APC-04).
 */
export function atlasErrorFrom(error: HttpErrorResponse): AtlasErrorBody | null {
    return isAtlasErrorBody(error.error) ? error.error : null;
}
