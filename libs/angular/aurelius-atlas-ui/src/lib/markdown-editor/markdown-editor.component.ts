import {
    ChangeDetectionStrategy,
    Component,
    computed,
    ElementRef,
    input,
    model,
    output,
    signal,
    viewChild,
} from "@angular/core";
import { FormValueControl } from "@angular/forms/signals";

import { Markdown } from "../markdown/markdown.component";

/** The active pane. */
type MarkdownEditorTab = "write" | "preview";

/** The next editor's element-id suffix (pane/tab pairing without a caller id). */
let nextMarkdownEditorId = 0;

/**
 * The Aurelius markdown-writing field (`models4insight-markdown-editor`,
 * UIC-26, DD-352): the legacy's side-by-side `columns` pair (textarea beside
 * preview) cannot fit the editor drawer's 28rem, so the pair becomes Bulma
 * `tabs` — Write over the textarea, Preview over the {@link Markdown} block
 * (DD-321). The component is a Signal Forms control (a `FormValueControl`
 * over a string field, DD-354): the model is the markdown source, so the
 * preview renders exactly the string the caller's save sends, through the one
 * renderer and the one sanitizer the details box already rides (DD-352 — no
 * second parser, no `dompurify`).
 *
 * Both panes stay mounted and the inactive one carries `hidden`, so a tab
 * switch re-parses nothing and the textarea keeps its caret and undo history.
 * The labels and the placeholder are caller inputs (UIC-04, DD-136): the
 * legacy's hardcoded placeholder default is dropped, the same way the search
 * field's defaults were. The component carries no colour of its own (UIC-03).
 *
 * Bound with `[formField]`, Signal Forms keeps the contract signals in sync:
 * `value` carries the source both ways, and `disabled`, `invalid` and
 * `touched` mirror the bound field's state (UIC-26). Loose, with no bound
 * field, the field still edits its own `value` — the story rides it that way.
 */
@Component({
    selector: "aurelius-atlas-ui-markdown-editor",
    imports: [Markdown],
    templateUrl: "./markdown-editor.component.html",
    styleUrl: "./markdown-editor.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MarkdownEditor implements FormValueControl<string> {
    /** The `Write` tab's label (the caller's bridge string, DD-353). */
    readonly writeLabel = input("");

    /** The `Preview` tab's label (the caller's bridge string, DD-353). */
    readonly previewLabel = input("");

    /** The textarea's placeholder (caller-supplied, DD-136 — the legacy's
     * hardcoded "Please type some markdown to get started..." was dropped). */
    readonly placeholder = input("");

    /** The id seated on the textarea so a `<label for>` reaches the field
     * (the same seam the relationship combobox carries, DD-335). */
    readonly textareaId = input<string | undefined>(undefined);

    /** The id of the line describing the control (FORM-ERR-002): the caller's
     * error line, carried to the textarea as `aria-describedby`; nothing
     * rides when the caller names none. */
    readonly describedBy = input<string | undefined>(undefined);

    /** Whether the field must hold a value (FORM-REQ-001): bound through
     * `[formField]`, Signal Forms mirrors the bound field's required rule
     * here, and the control forwards it to the textarea as the native
     * attribute, so a reader hears "required" from the field itself. */
    readonly required = input(false);

    /**
     * The markdown source — the control's model, edited by the textarea.
     * The `FormValueControl` contract: bound to a field, the directive
     * mirrors the field's value in and the typed source back out (UIC-26).
     */
    readonly value = model("");

    /** The bound field's disabled state, mirrored in by the directive
     * (UIC-26). Loose, nothing writes it and the textarea stays enabled. */
    readonly disabled = input(false);

    /** The bound field's invalid state, mirrored in by the directive. */
    readonly invalid = input(false);

    /** The bound field's touched state, mirrored in by the directive — the
     * editor's refused Save marks the whole tree touched (EDT-07), and this
     * follows without the caller wiring anything extra. */
    readonly touched = input(false);

    /** The textarea's blur reaches here as the contract's output: the bound
     * directive marks the field touched (the contract's blur rule). */
    readonly touch = output();

    /** The active pane; the field starts on Write (EDT-20). */
    protected readonly tab = signal<MarkdownEditorTab>("write");

    /** Whether the textarea paints Bulma's `is-danger` (UIC-26): invalid and
     * marked. A plain computed over the two mirrored inputs, so a caller's
     * refused Save (EDT-07) reaches the class under zoneless change
     * detection without any event subscription. */
    protected readonly danger = computed(() => this.invalid() && this.touched());

    /** The fallback id suffix for the pane/tab pairing without a caller id. */
    private readonly uid = nextMarkdownEditorId++;

    /** The Write pane's id (the active tab's `aria-controls`, UIC-26). */
    protected readonly writePaneId = computed(() => `${this.paneBase()}-write`);

    /** The Preview pane's id (the active tab's `aria-controls`, UIC-26). */
    protected readonly previewPaneId = computed(() => `${this.paneBase()}-preview`);

    /** The Write tab's id (the pane's `aria-labelledby`). */
    protected readonly writeTabId = computed(() => `${this.paneBase()}-write-tab`);

    /** The Preview tab's id (the pane's `aria-labelledby`). */
    protected readonly previewTabId = computed(() => `${this.paneBase()}-preview-tab`);

    /** The id stem: the caller's seat when given, else the counter fallback. */
    private readonly paneBase = computed(() => this.textareaId() ?? `aurelius-markdown-editor-${this.uid}`);

    /** The tabs in display order — the pair the arrow keys walk (FORM-CUSTOM-002). */
    private static readonly TAB_ORDER: readonly MarkdownEditorTab[] = ["write", "preview"];

    /** The tab buttons, so an arrow-key switch carries focus with the active
     * tab (the roving-tabindex pattern, FORM-CUSTOM-002). */
    private readonly writeTabRef = viewChild<ElementRef<HTMLButtonElement>>("writeTab");
    private readonly previewTabRef = viewChild<ElementRef<HTMLButtonElement>>("previewTab");

    /** Switch panes (the tab click; both panes stay mounted, UIC-26). */
    protected showTab(tab: MarkdownEditorTab): void {
        this.tab.set(tab);
    }

    /**
     * The tablist's keys (FORM-CUSTOM-002): Left/Right move the active tab
     * (wrapping), Home/End jump to the ends — the buttons carry the roving
     * tabindex, so focus follows the active tab. Activation is the native
     * button's (click/Space/Enter), nothing to re-implement here.
     * @param event The keydown event bubbling from the active tab.
     */
    protected onTabKeys(event: KeyboardEvent): void {
        const order = MarkdownEditor.TAB_ORDER;
        const current = order.indexOf(this.tab());
        let next: number;
        switch (event.key) {
            case "ArrowRight":
                next = (current + 1) % order.length;
                break;
            case "ArrowLeft":
                next = (current - 1 + order.length) % order.length;
                break;
            case "Home":
                next = 0;
                break;
            case "End":
                next = order.length - 1;
                break;
            default:
                return;
        }
        event.preventDefault();
        this.tab.set(order[next]);
        const active = order[next] === "write" ? this.writeTabRef() : this.previewTabRef();
        active?.nativeElement.focus();
    }

    /** The textarea's keystroke: the model rides the source string, live. */
    protected typed(event: Event): void {
        this.value.set((event.target as HTMLTextAreaElement).value);
    }
}
