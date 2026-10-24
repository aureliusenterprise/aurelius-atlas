/**
 * The browser-session id (7.13, DD-103): one random id per tab, persisted in
 * `sessionStorage` so a reload keeps the journey. When storage is denied
 * (private mode, sandboxed iframe) the id still works for the current
 * document — telemetry keeps flowing, it just does not survive a reload.
 *
 * SHL-14: storage failures are swallowed, never propagated into app boot.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ATTR_SESSION_ID, createAureliusSessionResource, createOrLoadSessionId } from "./opentelemetry-session";

describe("createOrLoadSessionId (SHL-14)", () => {
    beforeEach(() => sessionStorage.clear());

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("reads an id stored by an earlier page load", () => {
        sessionStorage.setItem("aurelius.session.id", "11111111-1111-4111-8111-111111111111");

        expect(createOrLoadSessionId()).toBe("11111111-1111-4111-8111-111111111111");
    });

    it("falls back to a fresh id when reading storage is denied (SHL-14)", () => {
        vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
            throw new Error("storage denied");
        });

        const id = createOrLoadSessionId();

        expect(id).toMatch(/^[0-9a-f-]{36}$/);
        expect(() => createOrLoadSessionId()).not.toThrow();
    });

    it("keeps working for this document when writing storage is denied (SHL-14)", () => {
        vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
            throw new Error("storage denied");
        });

        const first = createOrLoadSessionId();

        expect(first).toMatch(/^[0-9a-f-]{36}$/);
        // Nothing was persisted: each call yields a fresh id, still usable.
        expect(createOrLoadSessionId()).not.toBe(first);
    });

    it("names the resource attribute session.id (SHL-14)", () => {
        const resource = createAureliusSessionResource();

        expect(resource.attributes[ATTR_SESSION_ID]).toBe(createOrLoadSessionId());
    });
});
