import {
    ChangeDetectionStrategy,
    Component,
    ElementRef,
    effect,
    input,
    OnDestroy,
    output,
    viewChild,
} from "@angular/core";

/**
 * The results list's paged footer (UIC-21, UIC-22): the legacy
 * `models4insight-infinite-scroll-container`, ported dumb (WBP-04, DD-135) —
 * the Aurelius container read `allResultsLoaded$`/`isLoadingPage$` from the
 * App Search store and called `nextPage()` on it; here the three states are
 * inputs and the one event is an output, the caller's store owning them.
 *
 * The projected content is the list; below it, while `!allLoaded()`, a
 * sentinel row: a full-width button that emits {@link nextPage} on click
 * (the legacy keyboard/no-API fallback, carrying the Bulma spinner while
 * `loading()`), watched by an `IntersectionObserver` so scrolling the
 * sentinel into view emits it too (the legacy `IntersectionObserverService`
 * directive, inlined: the DOM behaviour belongs to the component that owns
 * the sentinel, the UIC-15 split). Environments without `IntersectionObserver`
 * (jsdom) keep the working path: the button (UIC-22's fallback rule).
 *
 * The label is caller-supplied and localised (DD-136); the Aurelius app
 * translated "Load next page...".
 */
@Component({
    selector: "aurelius-atlas-ui-infinite-scroll-container",
    imports: [],
    templateUrl: "./infinite-scroll-container.component.html",
    styleUrl: "./infinite-scroll-container.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InfiniteScrollContainer implements OnDestroy {
    /**
     * A page is in flight: the button shows the Bulma spinner and the
     * sentinel stops emitting, so one scroll triggers one page (UIC-22).
     */
    readonly loading = input(false);

    /**
     * Every result is loaded: the sentinel row disappears (the legacy
     * `*ngIf="!(allResultsLoaded$ | async)"`).
     */
    readonly allLoaded = input(false);

    /**
     * Accessible name of the load button. The caller localises it; the
     * Aurelius default was "Load next page...".
     */
    readonly loadLabel = input("Load next page...");

    /**
     * The next page is asked for: sentinel intersection or button click
     * (the legacy `nextPage()`).
     */
    readonly nextPage = output<void>();

    private readonly sentinel = viewChild<ElementRef<HTMLElement>>("sentinel");

    private observer?: IntersectionObserver;

    constructor() {
        effect(() => this.observe(this.sentinel()));
    }

    /**
     * (Re)watch the sentinel row: the observer is rebuilt when the row is
     * added (first page loaded) or removed (all loaded), and each
     * intersection emits {@link nextPage} once, suppressed while a page is
     * in flight (UIC-22).
     * @param element the sentinel element, `undefined` when the row is gone
     */
    private observe(element: ElementRef<HTMLElement> | undefined): void {
        this.observer?.disconnect();
        this.observer = undefined;
        if (!element || !("IntersectionObserver" in window)) {
            // The jsdom fallback: no observer, the button is the trigger (UIC-22).
            return;
        }
        this.observer = new IntersectionObserver((entries) => {
            if (entries.some((entry) => entry.isIntersecting) && !this.loading() && !this.allLoaded()) {
                this.nextPage.emit();
            }
        });
        this.observer.observe(element.nativeElement);
    }

    /**
     * Emit the page request, guarded as the sentinel is (a click during a
     * flight is a no-op, SRH-04's one-request-per-page).
     */
    protected requestPage(): void {
        if (!this.loading() && !this.allLoaded()) {
            this.nextPage.emit();
        }
    }

    ngOnDestroy(): void {
        this.observer?.disconnect();
    }
}
