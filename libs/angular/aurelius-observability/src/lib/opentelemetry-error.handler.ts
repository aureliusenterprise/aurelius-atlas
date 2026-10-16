import { ErrorHandler } from "@angular/core";
import { SpanStatusCode, trace } from "@opentelemetry/api";
import {
    ATTR_EXCEPTION_MESSAGE,
    ATTR_EXCEPTION_STACKTRACE,
    ATTR_EXCEPTION_TYPE,
} from "@opentelemetry/semantic-conventions";

/**
 * Angular `ErrorHandler` that mirrors every uncaught error into OpenTelemetry.
 *
 * Wire it alongside `provideBrowserGlobalErrorListeners()` — those listeners
 * hand `window.onerror` / `unhandledrejection` to the DI `ErrorHandler`, so
 * this one captures the whole class of browser errors, not just failing HTTP
 * calls. Delegates to the default handler afterwards so Angular keeps
 * re-throwing in dev mode.
 */
export class AureliusTraceErrorHandler implements ErrorHandler {
    private readonly fallback = new DefaultErrorHandlerShim();

    handleError(error: unknown): void {
        try {
            this.record(error);
        } catch {
            // Telemetry must never break the app's error path.
        }
        this.fallback.handleError(error);
    }

    private record(error: unknown): void {
        const span = trace.getActiveSpan();
        const err = toError(error);
        const attributes = {
            [ATTR_EXCEPTION_TYPE]: err.name,
            [ATTR_EXCEPTION_MESSAGE]: err.message,
            [ATTR_EXCEPTION_STACKTRACE]: err.stack ?? "",
        };
        if (span) {
            span.recordException({ name: err.name, message: err.message, stack: err.stack });
            span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
            return;
        }
        // No active span (e.g. a rejection outside any request): create a
        // one-off error span so the failure is still searchable in Tempo.
        const errorSpan = trace.getTracer("aurelius-observability").startSpan("uncaught exception", {
            attributes: { "exception.type": err.name },
        });
        errorSpan.addEvent("exception", attributes);
        errorSpan.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
        errorSpan.end();
    }
}

/**
 * Normalise a thrown value into an Error without relying on implicit
 * object stringification (which yields "[object Object]").
 * @param error Thrown value of unknown shape.
 * @returns An Error carrying the original message when recoverable.
 */
function toError(error: unknown): Error {
    if (error instanceof Error) {
        return error;
    }
    if (typeof error === "string") {
        return new Error(error);
    }
    try {
        return new Error(JSON.stringify(error) ?? "unknown uncaught error");
    } catch {
        return new Error("non-serialisable uncaught error");
    }
}

/**
 * Fallback behaviour: keep errors visible in the console. Deliberately does
 * not rethrow asynchronously — with `provideBrowserGlobalErrorListeners()`
 * active, an async rethrow would land back in `window.onerror` and
 * re-enter this handler.
 */
class DefaultErrorHandlerShim {
    handleError(error: unknown): void {
        console.error(error);
    }
}
