import { HttpErrorResponse } from "@angular/common/http";
import { atlasErrorFrom, AtlasErrorBody, isAtlasErrorBody } from "./atlas-error";

describe("atlas-error (APC-04)", () => {
    const body: AtlasErrorBody = {
        errorCode: "ATLAS-400-00-001",
        errorMessage: "Unknown type __AtlasProcess for entity.def",
    };

    it("recognises the Atlas error body shape", () => {
        expect(isAtlasErrorBody({ ...body, errorCause: "java.lang.IllegalArgumentException" })).toBe(true);
    });

    it("rejects bodies that are not Atlas errors", () => {
        expect(isAtlasErrorBody(null)).toBe(false);
        expect(isAtlasErrorBody("ATLAS-400-00-001")).toBe(false);
        expect(isAtlasErrorBody({ errorCode: 400, errorMessage: "x" })).toBe(false);
        expect(isAtlasErrorBody({ errorMessage: "x" })).toBe(false);
    });

    it("extracts the typed error from an HttpErrorResponse (APC-04)", () => {
        const response = new HttpErrorResponse({ status: 400, statusText: "Bad Request", error: body });
        expect(atlasErrorFrom(response)).toEqual(body);
    });

    it("yields null for a transport failure or a non-Atlas body", () => {
        const transport = new HttpErrorResponse({ status: 0, statusText: "Unknown Error" });
        expect(atlasErrorFrom(transport)).toBeNull();
        expect(atlasErrorFrom(new HttpErrorResponse({ status: 502, error: "<html>bad gateway</html>" }))).toBeNull();
    });
});
