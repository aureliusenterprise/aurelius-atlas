import {
    ChangeDetectionStrategy,
    Component,
    ElementRef,
    effect,
    inject,
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
let nextDrawerId = 0;

/**
 * What Tab can land on inside the panel, for the focus wraparound
 * (MODAL-TRAP-001). The panel itself (tabindex="-1") is the open landing
 * and stays focusable programmatically, not through the tab order.
 */
const PANEL_FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

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
     *
     * Content carrying the `drawer-actions` attribute projects into the
     * head between the title and the close button (DD-176), so a
     * drawer's content actions (Clear all on the alerts feed) sit in the
     * sticky head and never scroll away with a long body. Content
     * carrying `drawer-subhead` projects into a full-width strip below
     * the head (DD-180, the alerts inbox bar) — also outside the
     * scrolling body.
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
     * takes effect at once (DD-157) — while the panel plays its exit
     * animation, and the layer stays rendered until the animation ends
     * (DD-162).
     */
    protected readonly closing = signal(false);

    /** What was focused when the drawer opened, to restore focus on close. */
    private opener: HTMLElement | null = null;

    /**
     * The id of the head's title heading, so the dialog names itself
     * through aria-labelledby (DLG-HEAD-002). A module counter pairs them,
     * as the select's label does.
     */
    protected readonly headingId = `aurelius-atlas-ui-drawer-heading-${nextDrawerId++}`;

    private readonly element = inject(ElementRef<HTMLElement>);

    constructor() {
        // The aria-modal claim (MODAL-TRAP-001): while the drawer is open,
        // everything outside its own element chain becomes inert — the
        // page behind goes un-focusable and unannounced, which is what the
        // panel's aria-modal="true" tells the screen reader anyway. The
        // walk marks the siblings at every level up to <body>, so nested
        // mounts (the webapp's aux outlet) still cover the whole shell.
        // Declared before the focus effect so its cleanup removes the
        // marks before focus returns to the opener. Unit hosts attach the
        // fixture to <body>, where the marks land on the test's own
        // siblings and unwind the same way.
        effect((onCleanup) => {
            if (!this.active()) {
                return;
            }
            const marked: HTMLElement[] = [];
            let node: HTMLElement | null = this.element.nativeElement;
            while (node && node !== document.body) {
                for (const sibling of Array.from(node.parentElement?.children ?? [])) {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.hasAttribute("inert")) {
                        sibling.setAttribute("inert", "");
                        marked.push(sibling);
                    }
                }
                node = node.parentElement;
            }
            onCleanup(() => {
                for (const markedElement of marked) {
                    markedElement.removeAttribute("inert");
                }
            });
        });

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

        // Reopening mid-slide-out cancels the exit (DD-162): the layer is
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
     * removed when it ends (DD-162); the open state, focus restoration
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
     * Keep Tab inside the open panel (MODAL-TRAP-001): from the last
     * focusable, Tab wraps to the first; Shift+Tab from the first — or
     * from the panel landing itself — wraps to the last. The background
     * inert already blocks leaving the layer, but focus would otherwise
     * stall at its edges instead of cycling. The parameter is the bare
     * Event the template types for (keydown.tab); the key check makes the
     * KeyboardEvent access safe.
     * @param event the tab keydown, cancellable
     */
    protected onPanelTab(event: Event): void {
        if (!(event instanceof KeyboardEvent)) {
            return;
        }
        const panel = this.panel()?.nativeElement;
        if (!panel) {
            return;
        }
        const focusables = Array.from(panel.querySelectorAll<HTMLElement>(PANEL_FOCUSABLE));
        if (focusables.length === 0) {
            return;
        }
        const first = focusables[0];
        const last = focusables.at(-1) ?? first;
        const current = document.activeElement;
        if (event.shiftKey && (current === first || current === panel)) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && current === last) {
            event.preventDefault();
            first.focus();
        }
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
