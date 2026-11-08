import { ComponentFixture, TestBed } from "@angular/core/testing";

import { ColorSquare } from "./color-square.component";

describe("ColorSquare", () => {
    let component: ColorSquare;
    let fixture: ComponentFixture<ColorSquare>;

    function swatch(): HTMLInputElement {
        return fixture.nativeElement.querySelector("input[type='color']");
    }

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [ColorSquare],
        }).compileComponents();

        fixture = TestBed.createComponent(ColorSquare);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("draws the native colour input with the current colour (UIC-32)", () => {
        fixture.componentRef.setInput("color", "#3366cc");
        fixture.detectChanges();

        expect(swatch().value).toBe("#3366cc");
    });

    it("emits colorPicked with the picked hex (UIC-32)", () => {
        const picked: string[] = [];
        component.colorPicked.subscribe((color) => picked.push(color));
        const field = swatch();
        field.value = "#ff0000";
        field.dispatchEvent(new Event("input"));

        expect(picked).toEqual(["#ff0000"]);
    });

    it("draws a plain square and stays silent when not editable (UIC-32)", () => {
        fixture.componentRef.setInput("editable", false);
        fixture.componentRef.setInput("color", "#dc3912");
        fixture.detectChanges();

        const square = fixture.nativeElement.querySelector("span.color-square");
        expect(swatch()).toBeNull();
        expect(square.getAttribute("title")).toBe("#dc3912");

        const picked: string[] = [];
        component.colorPicked.subscribe((color) => picked.push(color));
        square.dispatchEvent(new Event("input"));
        expect(picked).toEqual([]);
    });

    it("carries the caller's accessible name on the picker", () => {
        fixture.componentRef.setInput("label", "bronze");
        fixture.detectChanges();

        expect(swatch().getAttribute("aria-label")).toBe("bronze");
    });
});
