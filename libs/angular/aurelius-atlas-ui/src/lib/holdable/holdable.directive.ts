import { Directive, ElementRef, HostBinding, HostListener, inject, input, output, signal } from "@angular/core";
import { Subscription, timer } from "rxjs";

/** The fill's refresh step, in milliseconds — smooth enough to read as motion. */
const TICK_MS = 50;

/**
 * A press-and-hold confirmation for a destructive control (the legacy
 * `models4insight-holdable`, 7.7c): the host fires `held(true)` only once the
 * pointer has been held for `holdFor` seconds; a release, leave or cancel
 * before that fires `held(false)` and resets, so nothing happens on a click.
 *
 * The fill is the caller's: while held the directive writes a
 * `--aurelius-hold-progress` custom property (0 to 1) on the host, and the
 * consumer paints it (the editor's Delete draws a donut from a CSS animation
 * instead, and reads the holding state the directive marks on the host),
 * keeping colour out of the directive (UIC-03). Without a caller style the
 * directive still gates the action and just carries no fill.
 *
 * Pointer only, matching the reference: a keyboard hold is a separate
 * affordance the legacy control never had (the deviation is recorded at the
 * increment).
 */
@Directive({
    selector: "[aurelius-atlas-ui-hold]",
    exportAs: "aureliusHold",
})
export class Holdable {
    /** How long, in seconds, the pointer must be held to confirm. */
    readonly holdFor = input(3);

    /**
     * Emits `true` when the hold completes, `false` when it is released
     * early. Named for the reference's `(held)` output; not a DOM event.
     */
    readonly held = output<boolean>();

    /** The hold's fraction (0 to 1) — readable by a spec; the fill reads the CSS var. */
    readonly progress = signal(0);

    /** Reflects the fraction so a caller's CSS can fill without a binding. */
    @HostBinding("attr.data-aurelius-hold")
    protected readonly holdState = signal<"idle" | "holding">("idle");

    private readonly el = inject(ElementRef<HTMLElement>);

    private running: Subscription | null = null;

    /** Pointer goes down: start the clock and sweep the fill. */
    @HostListener("pointerdown")
    protected onDown(): void {
        const totalMs = this.holdFor() * 1000;
        this.holdState.set("holding");
        this.running?.unsubscribe();
        this.running = timer(0, TICK_MS).subscribe((tick) => {
            const fraction = Math.min((tick * TICK_MS) / totalMs, 1);
            this.setProgress(fraction);
            if (fraction >= 1) {
                this.finish(true);
            }
        });
    }

    /** Pointer leaves or lifts: an unfinished hold is a cancellation. */
    @HostListener("pointerup")
    @HostListener("pointerleave")
    @HostListener("pointercancel")
    protected onRelease(): void {
        if (this.holdState() === "holding") {
            this.finish(false);
        }
    }

    /** Stop the clock, reset the fill, report the outcome once. */
    private finish(completed: boolean): void {
        this.running?.unsubscribe();
        this.running = null;
        this.holdState.set("idle");
        this.setProgress(0);
        this.held.emit(completed);
    }

    /** Publish the fraction as a host custom property (the caller's fill). */
    private setProgress(fraction: number): void {
        this.progress.set(fraction);
        this.el.nativeElement.style.setProperty("--aurelius-hold-progress", `${fraction}`);
    }
}
