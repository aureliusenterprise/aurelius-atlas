import { Resource, resourceFromAttributes } from "@opentelemetry/resources";

/**
 * OTel semantic convention for the browser session (incubating registry).
 * {@link https://opentelemetry.io/docs/specs/semconv/attributes-registry/session/}
 */
export const ATTR_SESSION_ID = "session.id";

const SESSION_STORAGE_KEY = "aurelius.session.id";

/**
 * One id per browser tab, persisted in `sessionStorage` so reloads keep it.
 *
 * Groups a user's traces/metrics into a journey without identifying the
 * person: the id is random, tab-scoped, and never leaves the tab on its own.
 * @returns The session id for this browser tab.
 */
export function createOrLoadSessionId(): string {
    let id: string | null = null;
    try {
        id = sessionStorage.getItem(SESSION_STORAGE_KEY);
    } catch {
        // Storage unavailable (private mode, sandboxed iframe): fall back to
        // a fresh id scoped to this document only.
    }
    if (!id) {
        id = crypto.randomUUID();
        try {
            sessionStorage.setItem(SESSION_STORAGE_KEY, id);
        } catch {
            // Best effort: the id still works for this document.
        }
    }
    return id;
}

/**
 * Resource carrying `session.id`, merged into the tracer/meter providers so
 * every span and metric from this tab is joinable (`resource.session.id` in
 * TraceQL, `session_id` via `target_info` in Prometheus).
 * @returns The session resource.
 */
export function createAureliusSessionResource(): Resource {
    return resourceFromAttributes({ [ATTR_SESSION_ID]: createOrLoadSessionId() });
}
