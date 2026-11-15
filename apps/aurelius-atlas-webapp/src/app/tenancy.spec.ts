import {
    loadTenancy,
    NO_TENANCY,
    parseTenancy,
    rememberedTenant,
    rememberTenant,
    silentScope,
    type Tenancy,
    tenantGroups,
    tenantOf,
} from "./tenancy";
import { TENANT_KEY } from "./settings/user-preference";

const ON: Tenancy = { enabled: true, operatorOrganization: "operators", operatorRole: "atlas-operator" };

describe("tenancy", () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("reads the server's answer, off or on with its operators (TNW-02)", () => {
        expect(parseTenancy({ enabled: false })).toBe(NO_TENANCY);
        expect(parseTenancy({ enabled: false, operatorOrganization: "x" })).toEqual({ enabled: false });
        expect(parseTenancy({ ...ON })).toEqual(ON);
        expect(() => parseTenancy({})).toThrow(/expected \{"enabled": boolean\}/);
        expect(() => parseTenancy({ enabled: true })).toThrow(/names its operator organization and role/);
    });

    it("loads the answer below the API base, and fails the start when it can't (TNW-02)", async () => {
        const fetch = vi.fn(async () => new Response(JSON.stringify(ON), { status: 200 }));
        vi.stubGlobal("fetch", fetch);

        expect(await loadTenancy("/api/")).toEqual(ON);
        expect(fetch).toHaveBeenCalledWith("/api/aurelius/v1/tenancy");

        vi.stubGlobal(
            "fetch",
            vi.fn(async () => new Response("down", { status: 503, statusText: "Unavailable" })),
        );

        await expect(loadTenancy("/api")).rejects.toThrow(
            /Failed to load the tenancy \(\/api\/aurelius\/v1\/tenancy\): 503 Unavailable/,
        );
    });

    it("reads the one organization a token names, as the server does (TNW-06, TEN-02)", () => {
        expect(tenantOf({ organization: { acme: { groups: ["/atlas-read"] } } })).toBe("acme");
        expect(tenantOf({ organization: ["acme"] })).toBe("acme");
        expect(tenantOf({ organization: { acme: {}, globex: {} } })).toBeUndefined();
        expect(tenantOf({ organization: {} })).toBeUndefined();
        expect(tenantOf({ organization: "acme" })).toBeUndefined();
        expect(tenantOf({})).toBeUndefined();
        expect(tenantOf(undefined)).toBeUndefined();
    });

    it("reads the tenant's own groups alone (TNW-07, TEN-05)", () => {
        const token = { organization: { acme: { groups: ["/atlas-write", 3] }, globex: { groups: ["/atlas-admin"] } } };

        expect(tenantGroups(token, "acme")).toEqual(["/atlas-write"]);
        expect(tenantGroups({ organization: ["acme"] }, "acme")).toEqual([]);
        expect(tenantGroups(token, "initech")).toEqual([]);
    });

    it("remembers the tenant in the browser, and forgets a value that isn't one (TNW-05, DD-634)", () => {
        expect(rememberedTenant()).toBeUndefined();

        rememberTenant("acme");

        expect(rememberedTenant()).toBe("acme");

        localStorage.setItem(TENANT_KEY, "42");

        expect(rememberedTenant()).toBeUndefined();
    });

    it("asks the silent check for the remembered organization only, and nothing with tenancy off (TNW-05, TNW-10)", () => {
        expect(silentScope(NO_TENANCY, "acme")).toBeUndefined();
        expect(silentScope(ON, undefined)).toBe("openid organization");
        expect(silentScope(ON, "acme")).toBe("openid organization:acme");
    });
});
