import { TestBed } from "@angular/core/testing";
import { provideRouter, Routes } from "@angular/router";

import { App } from "./app.component";

describe("App", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [App],
            providers: [provideRouter([] as Routes)],
        }).compileComponents();
    });

    it("creates", () => {
        expect(TestBed.createComponent(App).componentInstance).toBeTruthy();
    });

    it("renders a router outlet and nothing else, as the Aurelius root (SHL-03)", () => {
        const fixture = TestBed.createComponent(App);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;

        expect(compiled.querySelector("router-outlet")).toBeTruthy();
        expect(compiled.children).toHaveLength(1);
        expect(compiled.textContent?.trim()).toBe("");
    });
});
