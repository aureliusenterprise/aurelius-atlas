import { TestBed } from "@angular/core/testing";
import Keycloak from "keycloak-js";

import { AppConfig } from "../config";
import { APP_CONFIG } from "../tokens";
import { AccountLanguage, keycloakLanguage, realmUrl } from "./account-language.service";

const ACCOUNT = "https://localhost:9000/auth/realms/atlas/account/";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://localhost:9000/auth" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
};

const USER = { username: "meyn_steward", email: "meyn.steward@example.com", attributes: { team: ["data"] } };

function service({ tokenParsed = {}, token = "t0ken" }: { tokenParsed?: object; token?: string | null } = {}) {
    TestBed.configureTestingModule({
        providers: [
            { provide: APP_CONFIG, useValue: config },
            { provide: Keycloak, useValue: { token: token ?? undefined, tokenParsed } },
        ],
    });

    return TestBed.inject(AccountLanguage);
}

function respond(...responses: (Response | Error)[]) {
    const fetchMock = vi.fn();
    for (const response of responses) {
        if (response instanceof Error) {
            fetchMock.mockRejectedValueOnce(response);
        } else {
            fetchMock.mockResolvedValueOnce(response);
        }
    }
    vi.stubGlobal("fetch", fetchMock);

    return fetchMock;
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

describe("keycloakLanguage (SHC-10)", () => {
    it("names Dutch for nl-NL and English for every other locale", () => {
        expect(keycloakLanguage("nl-NL")).toBe("nl");
        expect(keycloakLanguage("en-US")).toBe("en");
        expect(keycloakLanguage("")).toBe("en");
    });
});

describe("realmUrl (SHC-05)", () => {
    it("keeps the path of a Keycloak URL with or without a trailing slash", () => {
        expect(realmUrl(config.keycloak, "account/")).toBe(ACCOUNT);
        expect(realmUrl({ ...config.keycloak, url: "https://keycloak.example/" }, "account")).toBe(
            "https://keycloak.example/realms/atlas/account",
        );
    });
});

describe("AccountLanguage (SHC-10, DD-665)", () => {
    afterEach(() => vi.unstubAllGlobals());

    it("saves the webapp's language with the user's other attributes kept", async () => {
        const fetchMock = respond(json(USER), new Response(null, { status: 204 }));

        expect(await service().save("nl-NL")).toBe(true);

        expect(fetchMock).toHaveBeenCalledTimes(2);
        const [readUrl, read] = fetchMock.mock.calls[0];
        expect(readUrl).toBe(ACCOUNT);
        expect(read.headers.Authorization).toBe("Bearer t0ken");
        const [saveUrl, saved] = fetchMock.mock.calls[1];
        expect(saveUrl).toBe(ACCOUNT);
        expect(saved.method).toBe("POST");
        expect(JSON.parse(saved.body)).toEqual({ ...USER, attributes: { team: ["data"], locale: ["nl"] } });
    });

    it("asks nothing when the token already names the language", async () => {
        const fetchMock = respond();

        expect(await service({ tokenParsed: { locale: "en" } }).save("en-US")).toBe(false);
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("asks nothing without a signed-in user", async () => {
        const fetchMock = respond();

        expect(await service({ token: null }).save("nl-NL")).toBe(false);
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("writes nothing when the saved language already is the webapp's", async () => {
        const fetchMock = respond(json({ ...USER, attributes: { locale: ["nl"] } }));

        expect(await service({ tokenParsed: { locale: "en" } }).save("nl-NL")).toBe(false);
        expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it("leaves the language as it was when the realm refuses or Keycloak is unreachable", async () => {
        respond(json({ error: "forbidden" }, 403));
        expect(await service().save("nl-NL")).toBe(false);

        TestBed.resetTestingModule();
        respond(new TypeError("Failed to fetch"));
        expect(await service().save("nl-NL")).toBe(false);
    });
});
