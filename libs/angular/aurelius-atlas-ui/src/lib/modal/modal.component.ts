import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, input, model, output } from "@angular/core";

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
     * Handle a confirm press: emits `confirmRequested` unless a caller-owned
     * action is pending.
     */
    protected onConfirmClick(): void {
        if (!this.confirmPending()) {
            this.confirmRequested.emit();
        }
    }
}
