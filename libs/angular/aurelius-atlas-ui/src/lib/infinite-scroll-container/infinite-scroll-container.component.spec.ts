import { ComponentFixture, TestBed } from "@angular/core/testing";

import { InfiniteScrollContainer } from "./infinite-scroll-container.component";

/** The entries an IntersectionObserver mock hands its callback (UIC-22's test hook). */
type ObserverCallback = (entries: { isIntersecting: boolean }[]) => void;

/**
 * A controllable IntersectionObserver mock: the spec registers it, the
 * component builds one, and the test fires `trigger` to scroll the sentinel
 * into view. jsdom ships no IntersectionObserver, so its absence is the
 * fallback path (UIC-22) and this is the watching path.
 */
class MockIntersectionObserver {
    static instances: MockIntersectionObserver[] = [];

    private readonly callback: ObserverCallback;

    observed = 0;

    disconnected = false;

    constructor(callback: ObserverCallback) {
        this.callback = callback;
        MockIntersectionObserver.instances.push(this);
    }

    observe(): void {
        this.observed += 1;
    }

    disconnect(): void {
        this.disconnected = true;
    }

    trigger(isIntersecting: boolean): void {
        this.callback([{ isIntersecting }]);
    }
}

describe("InfiniteScrollContainer", () => {
    let fixture: ComponentFixture<InfiniteScrollContainer>;
    let component: InfiniteScrollContainer;

    const setNativeInput = (key: "loading" | "allLoaded", value: boolean) => {
        fixture.componentRef.setInput(key, value);
        fixture.detectChanges();
    };

    beforeEach(async () => {
        MockIntersectionObserver.instances = [];
        vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);

        await TestBed.configureTestingModule({
            imports: [InfiniteScrollContainer],
        }).compileComponents();

        fixture = TestBed.createComponent(InfiniteScrollContainer);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("renders a full-width load button labelled by loadLabel (UIC-21)", () => {
        fixture.componentRef.setInput("loadLabel", "Load next page...");
        fixture.detectChanges();
        const button = fixture.nativeElement.querySelector("p button.button.is-fullwidth");
        expect(button).toBeTruthy();
        expect(button.textContent.trim()).toBe("Load next page...");
    });

    it("emits nextPage on a button click (UIC-21)", () => {
        const emitted = vi.fn();
        component.nextPage.subscribe(emitted);
        const button: HTMLButtonElement = fixture.nativeElement.querySelector("p button");
        button.click();
        expect(emitted).toHaveBeenCalledTimes(1);
    });

    it("shows the Bulma spinner while loading (UIC-21)", () => {
        setNativeInput("loading", true);
        const button: HTMLButtonElement = fixture.nativeElement.querySelector("p button");
        expect(button.classList.contains("is-loading")).toBe(true);
    });

    it("suppresses the button while a page is in flight (UIC-22)", () => {
        const emitted = vi.fn();
        component.nextPage.subscribe(emitted);
        setNativeInput("loading", true);
        const button: HTMLButtonElement = fixture.nativeElement.querySelector("p button");
        button.click();
        expect(emitted).not.toHaveBeenCalled();
    });

    it("removes the sentinel row when every page is loaded (UIC-21)", () => {
        setNativeInput("allLoaded", true);
        expect(fixture.nativeElement.querySelector("p")).toBeNull();
    });

    it("watches the sentinel and emits nextPage when it enters the viewport (UIC-22)", () => {
        const emitted = vi.fn();
        component.nextPage.subscribe(emitted);

        const observer = MockIntersectionObserver.instances.at(-1);
        expect(observer).toBeDefined();
        expect(observer?.observed).toBe(1);

        observer?.trigger(true);
        expect(emitted).toHaveBeenCalledTimes(1);
    });

    it("ignores an intersection that leaves the viewport, and one while loading (UIC-22)", () => {
        const emitted = vi.fn();
        component.nextPage.subscribe(emitted);
        const observer = MockIntersectionObserver.instances.at(-1);

        observer?.trigger(false);
        expect(emitted).not.toHaveBeenCalled();

        setNativeInput("loading", true);
        observer?.trigger(true);
        expect(emitted).not.toHaveBeenCalled();
    });

    it("disconnects the observer when the row disappears and rebuilds it when it returns (UIC-22)", () => {
        const first = MockIntersectionObserver.instances.at(-1);

        setNativeInput("allLoaded", true);
        expect(first?.disconnected).toBe(true);
        expect(MockIntersectionObserver.instances).toHaveLength(1);

        setNativeInput("allLoaded", false);
        expect(MockIntersectionObserver.instances).toHaveLength(2);
        expect(MockIntersectionObserver.instances.at(-1)?.observed).toBe(1);
    });

    it("keeps the button as the working path without IntersectionObserver (UIC-22)", () => {
        vi.unstubAllGlobals();
        fixture = TestBed.createComponent(InfiniteScrollContainer);
        component = fixture.componentInstance;
        fixture.detectChanges();

        const emitted = vi.fn();
        component.nextPage.subscribe(emitted);
        const button: HTMLButtonElement = fixture.nativeElement.querySelector("p button");
        button.click();
        expect(emitted).toHaveBeenCalledTimes(1);
    });
});
