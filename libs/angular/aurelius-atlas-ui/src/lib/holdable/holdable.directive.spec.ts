import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Holdable } from "./holdable.directive";

/**
 * The hold-to-confirm directive (7.7c): the legacy `models4insight-holdable`
 * mechanic, ported. A host counts the completed and cancelled holds so a spec
 * sees the two outcomes; the timer idiom is the picker's (`vi.useFakeTimers`)
 * — the zoneless test env runs no `fakeAsync`.
 */
@Component({
    imports: [Holdable],
    template: `<button aurelius-atlas-ui-hold [holdFor]="2" (held)="onHeld($event)">Delete</button>`,
})
class Host {
    completed = 0;
    cancelled = 0;

    onHeld(confirmed: boolean): void {
        if (confirmed) {
            this.completed += 1;
        } else {
            this.cancelled += 1;
        }
    }
}

describe("Holdable (7.7c)", () => {
    let fixture: ComponentFixture<Host>;
    let host: Host;
    let button: HTMLButtonElement;

    beforeEach(() => {
        vi.useFakeTimers();
        TestBed.configureTestingModule({ imports: [Host] });
        fixture = TestBed.createComponent(Host);
        fixture.detectChanges();
        host = fixture.componentInstance;
        button = fixture.nativeElement.querySelector("button");
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    /** A pointer event that bubbles and points at the button (jsdom has no PointerEvent). */
    function pointer(type: string): Event {
        return new Event(type, { bubbles: true });
    }

    it("does nothing on a quick press and release (no accidental delete)", () => {
        button.dispatchEvent(pointer("pointerdown"));
        vi.advanceTimersByTime(100);
        button.dispatchEvent(pointer("pointerup"));
        fixture.detectChanges();

        expect(host.completed).toBe(0);
        expect(host.cancelled).toBe(1);
    });

    it("confirms once the hold passes its time (held true)", () => {
        button.dispatchEvent(pointer("pointerdown"));
        // The host sets holdFor 2 → the fill reaches 1 at 2s.
        vi.advanceTimersByTime(2000);
        fixture.detectChanges();

        expect(host.completed).toBe(1);
        expect(host.cancelled).toBe(0);
        // The sweep stops at the top: a longer hold does not re-fire.
        vi.advanceTimersByTime(2000);
        expect(host.completed).toBe(1);
    });

    it("cancels when the pointer leaves mid-hold", () => {
        button.dispatchEvent(pointer("pointerdown"));
        vi.advanceTimersByTime(1000);
        button.dispatchEvent(pointer("pointerleave"));
        vi.advanceTimersByTime(2000);

        expect(host.completed).toBe(0);
        expect(host.cancelled).toBe(1);
    });

    it("sweeps the fill as a host custom property, then clears it", () => {
        button.dispatchEvent(pointer("pointerdown"));
        vi.advanceTimersByTime(1000);
        fixture.detectChanges();
        // Half of holdFor 2 → 0.5.
        expect(button.style.getPropertyValue("--aurelius-hold-progress")).toBe("0.5");

        button.dispatchEvent(pointer("pointerup"));
        fixture.detectChanges();
        expect(button.style.getPropertyValue("--aurelius-hold-progress")).toBe("0");
    });
});
