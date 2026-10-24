import { context, trace } from "@opentelemetry/api";
import { BasicTracerProvider, InMemorySpanExporter, SimpleSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { StackContextManager } from "@opentelemetry/sdk-trace-web";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AureliusTraceErrorHandler } from "./opentelemetry-error.handler";

describe("AureliusTraceErrorHandler", () => {
    let exporter: InMemorySpanExporter;
    let provider: BasicTracerProvider;

    beforeEach(() => {
        exporter = new InMemorySpanExporter();
        provider = new BasicTracerProvider({ spanProcessors: [new SimpleSpanProcessor(exporter)] });
        context.disable();
        trace.disable();
        context.setGlobalContextManager(new StackContextManager().enable());
        trace.setGlobalTracerProvider(provider);
    });

    afterEach(async () => {
        await provider.shutdown();
        context.disable();
        trace.disable();
        exporter.reset();
        vi.restoreAllMocks();
    });

    it("attaches the exception to the active span", () => {
        const span = trace.getTracer("test").startSpan("request");
        context.with(trace.setSpan(context.active(), span), () => {
            new AureliusTraceErrorHandler().handleError(new TypeError("boom"));
        });
        span.end();

        const spans = exporter.getFinishedSpans();
        expect(spans).toHaveLength(1);
        expect(spans[0].name).toBe("request");
        expect(spans[0].status.code).toBe(2); // ERROR
        const exception = spans[0].events.find((e) => e.name === "exception");
        expect(exception?.attributes?.["exception.type"]).toBe("TypeError");
        expect(exception?.attributes?.["exception.message"]).toBe("boom");
    });

    it("creates a standalone error span without an active span", () => {
        new AureliusTraceErrorHandler().handleError(new Error("orphan"));

        const spans = exporter.getFinishedSpans();
        expect(spans).toHaveLength(1);
        expect(spans[0].name).toBe("uncaught exception");
        expect(spans[0].status.code).toBe(2);
        expect(spans[0].events[0]?.attributes?.["exception.message"]).toBe("orphan");
    });

    it("records non-Error throwables", () => {
        new AureliusTraceErrorHandler().handleError("string failure");
        const spans = exporter.getFinishedSpans();
        expect(spans[0].events[0]?.attributes?.["exception.message"]).toBe("string failure");
    });

    it("serialises an object throwable into the exception message", () => {
        new AureliusTraceErrorHandler().handleError({ status: 503, detail: "gateway down" });
        const spans = exporter.getFinishedSpans();
        expect(spans[0].events[0]?.attributes?.["exception.message"]).toBe('{"status":503,"detail":"gateway down"}');
    });

    it("labels a non-serialisable throwable instead of stringifying it", () => {
        const cyclic: Record<string, unknown> = { name: "loop" };
        cyclic["self"] = cyclic;

        new AureliusTraceErrorHandler().handleError(cyclic);
        const spans = exporter.getFinishedSpans();
        expect(spans[0].events[0]?.attributes?.["exception.message"]).toBe("non-serialisable uncaught error");
    });

    it("never throws out of handleError", () => {
        vi.spyOn(trace, "getTracer").mockImplementation(() => {
            throw new Error("telemetry exploded");
        });
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
        expect(() => new AureliusTraceErrorHandler().handleError(new Error("original"))).not.toThrow();
        expect(consoleError).toHaveBeenCalled();
    });
});
