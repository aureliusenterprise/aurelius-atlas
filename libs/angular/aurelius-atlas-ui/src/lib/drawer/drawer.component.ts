import {
    ChangeDetectionStrategy,
    Component,
    computed,
    ElementRef,
    effect,
    input,
    model,
    output,
    signal,
    viewChild,
} from "@angular/core";

/**
 * A panel that slides in from the right edge of the viewport over a
 * scrim, and projects its content. The Bulma stack has no drawer layer
 * (the overlay primitives are the modal and the navbar dropdown), so the
 * anatomy is this component's own, styled on Bulma's tokens; the dismissal
 * set copies the {@link Modal}'s card anatomy — backdrop click, close
 * button, Escape.
 */
@Component({
    selector: "aurelius-atlas-ui-drawer",
    imports: [],
    templateUrl: "./drawer.component.html",
    styleUrl: "./drawer.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Drawer {
    /**
     * Whether the drawer is open. A `model()` so the caller can two-way
     * bind it; `dismiss()` (backdrop, close button, Escape) writes through
     * it, like the {@link Modal}'s `active`.
     */
    readonly active = model(false);

    /**
     * The panel's heading, rendered in the header and used as the
     * dialog's accessible name. The caller localises it.
     */
    readonly title = input<string>();

    /**
     * Accessible name of the close control, localised by the caller (the
     * {@link Modal}'s `ariaLabel` pattern — a translated static attribute
     * would be overwritten by the binding).
     */
    readonly ariaLabel = input("Close");

    /**
     * Emits when the user dismisses the drawer — backdrop, close button,
     * or Escape. Named for the same reason as the modal's: no standard DOM
     * event names on outputs.
     */
    readonly cancelRequested = output<void>();

    /** The panel element, the focus target while the drawer is open. */
    private readonly panel = viewChild<ElementRef<HTMLElement>>("panel");

    /**
     * The drawer is sliding out: `active` is already false — dismissal
     * takes effect at once (DD-069) — while the panel plays its exit
     * animation, and the layer stays rendered until the animation ends
     * (DD-074).
     */
    protected readonly closing = signal(false);

    /** What was focused when the drawer opened, to restore focus on close. */
    private opener: HTMLElement | null = null;

    /** The dialog's accessible name: the title. */
    protected readonly label = computed(() => this.title());

    constructor() {
        // The drawer is an ARIA dialog: focus moves into the panel on open
        // (the modal leaves focus to its buttons; a drawer's form controls
        // need the panel itself) and back to the opener on close. The open
        // pass records the opener as soon as `active` flips; the guarded
        // panel query re-runs this effect when the rendered panel appears,
        // and that is when focus moves in.
        effect((onCleanup) => {
            if (!this.active()) {
                return;
            }
            this.opener ??= document.activeElement instanceof HTMLElement ? document.activeElement : null;
            this.panel()?.nativeElement.focus();
            onCleanup(() => {
                this.opener?.focus();
                this.opener = null;
            });
        });

        // Reopening mid-slide-out cancels the exit (DD-074): the layer is
        // still rendered, so only the flag needs to go away.
        effect(() => {
            if (this.active()) {
                this.closing.set(false);
            }
        });
    }

    /**
     * Open the drawer.
     */
    open(): void {
        this.active.set(true);
    }

    /**
     * Close the drawer. The layer lingers for the exit animation and is
     * removed when it ends (DD-074); the open state, focus restoration
     * and the caller's `active` binding all take effect immediately.
     */
    close(): void {
        this.active.set(false);
        if (this.panel()) {
            this.closing.set(true);
        }
    }

    /**
     * Open the drawer if it is closed, or close it if it is open.
     */
    toggle(): void {
        this.active.update((active) => !active);
    }

    /**
     * Close the drawer as a user action: emits `cancelRequested` and closes
     * (the backdrop, the close button and Escape all take this path).
     */
    dismiss(): void {
        this.cancelRequested.emit();
        this.close();
    }

    /** Handle a scrim click — the pointer dismissal path. */
    protected onBackdropClick(): void {
        this.dismiss();
    }

    /** Handle Escape on the panel — the dialog's keyboard dismissal path. */
    protected onEscape(): void {
        this.dismiss();
    }

    /**
     * The panel's exit animation has ended (the name check keeps bubbled
     * animations from the drawer's own content out of it; it is a
     * containment because Angular scopes keyframe names, decorating them
     * `_ngcontent-ng-…_aurelius-drawer-out`): drop the layer.
     */
    protected onAnimationEnd(event: AnimationEvent): void {
        if (this.closing() && event.animationName.includes("aurelius-drawer-out")) {
            this.closing.set(false);
        }
    }
}
