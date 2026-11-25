import { HttpTestingController } from "@angular/common/http/testing";

import { TYPEDEF_URL } from "./api";

/**
 * Collapse run-together whitespace so a template's indentation never leaks
 * into an assertion. Identical in ten specs' heads; one copy now.
 *
 * @param text the element's `textContent`, possibly absent
 * @returns the collapsed text, or undefined for an absent element
 */
export function normalize(text: string | undefined | null): string | undefined {
    return text?.replace(/\s+/g, " ").trim();
}

/**
 * Settle the DET-15 layout walk: a type with no layout of its own reads its
 * typedef, and a "no typedef" answer ends the walk and keeps the default
 * layout. Flushing every in-flight typedef read that way is how a screen spec
 * reaches a quiet HTTP state without caring which types the walk touched.
 *
 * @param httpMock the controller
 */
export function settleTypeDefs(httpMock: HttpTestingController): void {
    for (const request of httpMock.match((r) => r.url.startsWith(TYPEDEF_URL))) {
        request.flush({}, { status: 404, statusText: "Not Found" });
    }
}
