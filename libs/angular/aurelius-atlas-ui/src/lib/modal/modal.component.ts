import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, ElementRef, effect, input, model, output, viewChild } from "@angular/core";

let nextModalId = 0;

@Component({
    selector: "aurelius-atlas-ui-modal",
    imports: [CommonModule],
    templateUrl: "./modal.component.html",
    styleUrl: "./modal.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Modal {
    /**
     * Whether or not the modal is currently open.
     */
    readonly active = model(false);

    /**
     * Whether or not to show the close button.
     */
    readonly showCloseButton = input(true);

    /**
     * The modal's title. When set, the modal renders the legacy Aurelius card
     * anatomy — header with title and close button, body, and a footer with
     * confirm/cancel buttons — and a backdrop click dismisses it, as the
     * Aurelius modal did. When unset, the modal keeps the plain content
     * anatomy and an inert backdrop.
     */
    readonly title = input<string>();

    /**
     * Label of the footer's confirm button (card anatomy). Unset means no
     * confirm button; the caller localises the label it passes, as the
     * Aurelius modal's context did.
     */
    readonly confirmLabel = input<string>();

    /**
     * Label of the footer's cancel button (card anatomy). Unset means no
     * cancel button — the Aurelius footer label came from the caller's
     * context, so there is no chrome string to default to.
     */
    readonly cancelLabel = input<string>();

    /**
     * Shows the confirm button as loading (a pending async action owned by
     * the caller). While pending, confirm presses are ignored.
     */
    readonly confirmPending = input(false);

    /**
     * Accessible name of the close controls. The caller localises it — a
     * translated static attribute would be overwritten by this binding, so
     * the close label is caller-supplied chrome, like the footer labels.
     */
    readonly ariaLabel = input("Close");

    /**
     * Accessible name of the layer for the plain content anatomy (title
     * unset), where no visible title exists to name the dialog
     * (MODAL-NAME-001). Plain-anatomy callers must set it; the card anatomy
     * is named by its header heading instead and ignores this input.
     */
    readonly label = input<string>();

    /**
     * Emits when the user presses the confirm button (card anatomy). Named
     * `confirmRequested` — `confirm` is a standard DOM event name, which the
     * Angular ESLint rule bans for outputs.
     */
    readonly confirmRequested = output<void>();

    /**
     * Emits when the user dismisses the modal — backdrop, close button, or
     * cancel button. Named `cancelRequested` (no standard DOM event names);
     * the modal also closes itself, and a caller that two-way binds `active`
     * reacts to this to clear its own state.
     */
    readonly cancelRequested = output<void>();

    /**
     * The id of the card header's title heading, so the dialog can name
     * itself through aria-labelledby (DLG-HEAD-001). Angular 22 has no
     * public id generator, so a module counter pairs them, as the select's
     * label does.
     */
    protected readonly headingId = `aurelius-atlas-ui-modal-heading-${nextModalId++}`;

    /** The native dialog element, once the layer renders. */
    private readonly host = viewChild<ElementRef<HTMLDialogElement>>("host");

    /** What was focused when the modal opened, to restore focus on close. */
    private opener: HTMLElement | null = null;

    constructor() {
        // The dialog's open choreography (UIC-40, DD-543): while `active`
        // is set the effect records the focused element as the opener and
        // calls showModal() on the rendered dialog (top layer, focus
        // confined, the page behind inert); the cleanup closes the dialog
        // and restores focus when the layer goes away. The guards keep a
        // dialog the platform already opened, or one without the API (the
        // jsdom unit suite), from throwing — there the Bulma layer renders
        // in place of the top layer, and only the focus work is skipped.
        // The `active()` and `host()` reads make the effect re-run when the
        // flag flips and when the panel appears (the drawer's pattern).
        effect((onCleanup) => {
            if (!this.active()) {
                return;
            }
            this.opener ??= document.activeElement instanceof HTMLElement ? document.activeElement : null;
            const dialog = this.host()?.nativeElement;
            if (!dialog) {
                return;
            }
            if (!dialog.open) {
                if (typeof dialog.showModal === "function") {
                    dialog.showModal();
                } else {
                    // No top-layer API (the jsdom unit suite): the open
                    // attribute shows the Bulma layer in place — the
                    // drawer's fallback path — with the focus work skipped.
                    dialog.open = true;
                }
            }
            onCleanup(() => {
                if (dialog.open && typeof dialog.close === "function") {
                    dialog.close();
                }
                this.opener?.focus();
                this.opener = null;
            });
        });
    }

    /**
     * Close the modal.
     */
    close(): void {
        this.active.set(false);
    }

    /**
     * Open the modal.
     */
    open(): void {
        this.active.set(true);
    }

    /**
     * Open the modal if it is closed, or close it if it is open.
     */
    toggle(): void {
        this.active.update((active) => !active);
    }

    /**
     * Dismiss the modal as a user action: emits `cancelRequested` and closes
     * (the Aurelius modal's cancel path — backdrop click, close, cancel
     * button).
     */
    dismiss(): void {
        this.cancelRequested.emit();
        this.close();
    }

    /**
     * Handle a backdrop click: dismisses the card anatomy (Aurelius parity),
     * ignores the plain content anatomy, whose existing callers manage
     * closing themselves.
     */
    protected onBackdropClick(): void {
        if (this.title() !== undefined) {
            this.dismiss();
        }
    }

    /**
     * Handle the dialog's `cancel` (the platform's Escape path, UIC-40):
     * prevent the bare close only for the card anatomy, so dismissal stays
     * its `cancelRequested` path. The plain anatomy lets the browser close
     * the dialog (MODAL-ESC-001 — preventing there killed Escape for it
     * too); its callers learn of the close through the `close` event, and
     * emit nothing, as with backdrop clicks.
     * @param event the cancel event, cancellable
     */
    protected onCancel(event: Event): void {
        if (this.title() !== undefined) {
            event.preventDefault();
            this.dismiss();
        }
    }

    /**
     * Handle the dialog's `close` (a native close, from the platform Escape
     * path on the plain anatomy): mirror it into the `active` model so the
     * layer and the caller's state stay in step. The card anatomy's Escape
     * and the component's own close paths go through the model, where the
     * effect already closes the dialog.
     */
    protected onNativeClose(): void {
        this.active.set(false);
    }

    /**
     * Handle a confirm press: emits `confirmRequested` unless a caller-owned
     * action is pending.
     */
    protected onConfirmClick(): void {
        if (!this.confirmPending()) {
            this.confirmRequested.emit();
        }
    }
}
