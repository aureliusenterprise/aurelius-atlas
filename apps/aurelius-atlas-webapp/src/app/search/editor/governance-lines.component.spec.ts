import { describe, it } from "vitest";

import {
    ANSWER,
    DATASET_CHAIN,
    RA_ANSWER,
    arrive,
    arriveChain,
    arriveSlices,
    govVerdict,
    raChain,
    setup,
} from "./editor-testing";
import { VIEW_URL, VALIDATE_URL } from "../../../testing/api";
import { normalize } from "../../../testing/dom";

/**
 * The drawer's governance banner lines (EDT-24 as amended by 12.7, DD-446/
 * DD-498): the verdicts that name a control, one line each, warning or success
 * by `compliant`, message from the verdict — none for the retired key
 * (SPA-06), one anyOf rule shown under each control it names (VEV-09, DD-636).
 * Moved with the lines out of the main drawer spec at 7.48 (DD-874); they
 * still drive the whole drawer, which owns the verdict routing
 * (`validationItems`), so the banner's rule ids stay attributed to the drawer.
 */
describe("GovernanceLines banner", () => {
    it("renders one banner line per verdict that names a control, nothing for the rest (EDT-24)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // The engine answers four verdicts (VEV-02); the DataSet drawer renders
        // controls for two of their attributes — the `description` verdict
        // names the one prose control (EDT-24 as amended by 12.7 and 18.8,
        // SPA-06). The attributes no control carries (`dataEntity`,
        // `domainLead`) render nowhere (DD-446).
        const lines = [...compiled.querySelectorAll<HTMLElement>("[data-gov-line]")];
        expect(lines).toHaveLength(2);
        // The DOM order is the form's (EDT-03's rank): the name control's
        // line first, the description control's after it.
        expect(lines.map((line) => normalize(line.textContent))).toEqual([
            "This entity has a name",
            "This entity has a description",
        ]);

        // The lines sit under their own control, at the legacy's small size,
        // with the success icon (compliant true) in Bulma's icon seat.
        const nameLine = lines.find((line) => line.closest(".aurelius-editor-field")?.querySelector("#editor-name"));
        expect(normalize(nameLine?.textContent)).toBe("This entity has a name");
        expect(nameLine?.classList.contains("is-size-7")).toBe(true);
        expect(nameLine?.querySelector(".icon.has-text-success svg")).toBeTruthy();
        const descriptionLine = lines.find((line) =>
            line.closest(".aurelius-editor-field")?.querySelector("textarea#editor-description"),
        );
        expect(normalize(descriptionLine?.textContent)).toBe("This entity has a description");
        expect(descriptionLine?.querySelector(".icon.has-text-success svg")).toBeTruthy();
    });

    it("a non-compliant verdict paints the warning icon (EDT-24)", () => {
        const { fixture, compiled, httpMock } = setup();
        arriveSlices(fixture, httpMock, false);
        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(ANSWER);
        fixture.detectChanges(); // the answer's type fires the chain read (VDE-02)
        arriveChain(httpMock, "DataSet", DATASET_CHAIN);
        fixture.detectChanges();

        httpMock.expectOne(VALIDATE_URL).flush({
            verdicts: [govVerdict("name", "This entity is missing a name", false)],
            unreadRules: [],
        });
        fixture.detectChanges();

        const line = compiled.querySelector<HTMLElement>("[data-gov-line]")!;
        expect(normalize(line.textContent)).toBe("This entity is missing a name");
        expect(line.querySelector(".icon.has-text-warning svg")).toBeTruthy();
        expect(line.querySelector(".icon.has-text-success")).toBeNull();
    });

    it("the retired key's verdict borrows nothing (EDT-24, SPA-06, DD-633 superseded)", () => {
        // The alias DD-633 drew — a `definition` verdict naming the
        // description control while the form carried no definition control —
        // fell away with the attribute (18.8, ADR 070). On the shipped DataSet
        // chain a `definition` verdict measures no control and paints no
        // line; the description verdict paints under its own control alone.
        const { fixture, compiled, httpMock } = setup();
        arriveSlices(fixture, httpMock, false);
        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(ANSWER);
        fixture.detectChanges();
        arriveChain(httpMock, "DataSet", DATASET_CHAIN);
        fixture.detectChanges();

        httpMock.expectOne(VALIDATE_URL).flush({
            verdicts: [
                govVerdict("definition", "This entity has a definition", true),
                govVerdict("description", "This entity has a description", true),
            ],
            unreadRules: [],
        });
        fixture.detectChanges();

        const lines = [...compiled.querySelectorAll<HTMLElement>("[data-gov-line]")];
        expect(lines.map((line) => normalize(line.textContent))).toEqual(["This entity has a description"]);
        expect(lines[0].closest(".aurelius-editor-field")?.querySelector("textarea#editor-description")).toBeTruthy();
    });

    it("an anyOf verdict paints under each control the rule names (EDT-24, VEV-09, DD-636)", () => {
        // The paired rule measures two names: its verdict carries `attribute`
        // plus `anyOf` and sits once under each control it names — the fields
        // rule's line rides both the fields picker and the child picker.
        const pair = {
            ruleGuid: "rule-fields-pair",
            ruleName: "Dataset has a field or a child dataset",
            attribute: "inputToProcesses",
            anyOf: ["model"],
            dimension: "COMPLETENESS",
            compliant: true,
            message: "This dataset has a field or a child dataset",
        };
        const solo = {
            ...pair,
            ruleGuid: "rule-model",
            ruleName: "Dataset has a model",
            attribute: "model",
            message: "This dataset has a model",
        };
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock, RA_ANSWER, raChain(), false);
        httpMock.expectOne(VALIDATE_URL).flush({ verdicts: [pair, solo], unreadRules: [] });
        fixture.detectChanges();

        const lines = [...compiled.querySelectorAll<HTMLElement>("[data-gov-line]")];
        expect(lines).toHaveLength(3); // once per control per naming verdict — no copies
        const inputs = [...compiled.querySelectorAll<HTMLElement>('[data-field="inputToProcesses"] [data-gov-line]')];
        const models = [...compiled.querySelectorAll<HTMLElement>('[data-field="model"] [data-gov-line]')];
        expect(inputs.map((line) => normalize(line.textContent))).toEqual([
            "This dataset has a field or a child dataset",
        ]);
        expect(models.map((line) => normalize(line.textContent))).toEqual([
            "This dataset has a field or a child dataset",
            "This dataset has a model",
        ]);
    });
});
