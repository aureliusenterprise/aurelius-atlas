import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { Field, FieldTree, FormField } from "@angular/forms/signals";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faXmark } from "@fortawesome/free-solid-svg-icons";

import { MarkdownEditor, Select } from "aurelius-atlas-ui";
import { type GovernanceVerdict } from "aurelius-atlas-data-access";

import { type EditorField, type EnumRow, type EditorValue } from "./form-fields";
import { GovernanceLines } from "./governance-lines.component";

/**
 * The plain attribute fields of the editor form (EDT-03, EDT-07, EDT-20): one
 * control per editable attribute in the field set, each bound to the signal
 * form through `[formField]`. It renders every kind the legacy form had —
 * boolean, enum, multi, markdown, number, date, and the text default — each
 * with its required star (FORM-REQ-001), its error line (EDT-07,
 * FORM-ERR-002), and its governance banner lines (EDT-24, DD-874).
 *
 * It is a renderer, not a store: the form tree, its values, and the "show this
 * error now?" decision (which reads Save-attempted and touched state, EDT-07)
 * all belong to the drawer. The tree and the values ride in as signal inputs,
 * the error predicate as a function input, and the enum pick and multi-row
 * delete ride out. The relationship pickers, the classification box, the
 * quality form, and the commit foot are each their own component (EDT-13,
 * EDT-05, EDT-25, EDT-19), so this one holds only the attribute loop.
 */
@Component({
    imports: [FontAwesomeModule, FormField, GovernanceLines, MarkdownEditor, Select],
    selector: "aurelius-atlas-webapp-entity-fields",
    styleUrl: "./entity-fields.component.scss",
    template: `
        @for (field of fields(); track field.name) {
            <div class="field aurelius-editor-field" [attr.data-field]="field.name">
                @if (field.kind === "boolean") {
                    <!-- Bulma's checkbox anatomy (EDT-03): the label wraps
                     the input and a bare text node — no wrapper span,
                     which would drop the gap Bulma gives the text. -->
                    <label class="checkbox aurelius-editor-checkbox">
                        <input type="checkbox" [formField]="booleanField(field.name)" />
                        {{ field.label }}
                    </label>
                } @else if (field.kind === "enum") {
                    <aurelius-atlas-ui-select
                        [options]="enumRows(field)"
                        displayField="value"
                        [label]="field.label"
                        [value]="enumSelected(field)"
                        [invalid]="errorFor()(field)"
                        [required]="field.required"
                        [requiredErrorMessage]="nameRequired()"
                        [searchVisible]="false"
                        (valueChange)="enumPicked.emit({ field, row: $event })"
                    ></aurelius-atlas-ui-select>
                } @else if (field.kind === "multi") {
                    <label class="label" [for]="'editor-' + field.name + '-0'">
                        {{ field.label }}
                        @if (field.required) {
                            <!-- FORM-REQ-001: the star stays the sighted
                             mark, the words are the announced one. -->
                            <span class="has-text-danger" aria-hidden="true">*</span>
                            <span class="is-sr-only" i18n="@@search.components.editor.attribute.requiredMark"
                                >(required)</span
                            >
                        }
                    </label>
                    <div class="control aurelius-editor-multi">
                        @for (row of multiRows(field.name); track row; let i = $index) {
                            <div class="aurelius-editor-multi-row">
                                <input
                                    type="text"
                                    class="input"
                                    [id]="'editor-' + field.name + '-' + i"
                                    [attr.aria-label]="field.label"
                                    [attr.aria-invalid]="errorFor()(field) ? 'true' : null"
                                    [attr.aria-describedby]="
                                        errorFor()(field) ? 'editor-' + field.name + '-error' : null
                                    "
                                    [class.is-danger]="errorFor()(field)"
                                    [formField]="row"
                                />
                                <button
                                    type="button"
                                    class="button is-small is-ghost aurelius-editor-multi-delete"
                                    [attr.aria-label]="deleteLabel()"
                                    (click)="multiDelete.emit({ field, index: $index })"
                                >
                                    <fa-icon [icon]="faXmark"></fa-icon>
                                </button>
                            </div>
                        }
                    </div>
                } @else {
                    <label class="label" [for]="'editor-' + field.name">
                        {{ field.label }}
                        @if (field.required) {
                            <!-- FORM-REQ-001: the red star is paint only
                             (aria-hidden); the words beside it carry
                             the fact to a reader. -->
                            <span class="has-text-danger" aria-hidden="true">*</span>
                            <span class="is-sr-only" i18n="@@search.components.editor.attribute.requiredMark"
                                >(required)</span
                            >
                        }
                    </label>
                    <div class="control">
                        @switch (field.kind) {
                            @case ("markdown") {
                                <!-- The description keys (EDT-20, DD-352):
                                 the ui library's markdown field. The
                                 control keeps the markdown source
                                 exactly as the textarea did, so the
                                 save body (EDT-06) is untouched. The
                                 component seats the EDT-11 label's
                                 'for' target through textareaId;
                                 its danger state reads this form's
                                 field state (UIC-26, DD-354). -->
                                <aurelius-atlas-ui-markdown-editor
                                    [formField]="textField(field.name)"
                                    [textareaId]="'editor-' + field.name"
                                    [writeLabel]="markdownWriteLabel"
                                    [previewLabel]="markdownPreviewLabel"
                                    [placeholder]="markdownPlaceholder"
                                    [describedBy]="errorFor()(field) ? 'editor-' + field.name + '-error' : undefined"
                                ></aurelius-atlas-ui-markdown-editor>
                            }
                            @case ("number") {
                                <input
                                    type="number"
                                    class="input"
                                    [class.is-danger]="errorFor()(field)"
                                    [id]="'editor-' + field.name"
                                    [attr.aria-invalid]="errorFor()(field) ? 'true' : null"
                                    [attr.aria-describedby]="
                                        errorFor()(field) ? 'editor-' + field.name + '-error' : null
                                    "
                                    [formField]="numberField(field.name)"
                                />
                            }
                            @case ("date") {
                                <input
                                    type="datetime-local"
                                    class="input"
                                    [class.is-danger]="errorFor()(field)"
                                    [id]="'editor-' + field.name"
                                    [attr.aria-invalid]="errorFor()(field) ? 'true' : null"
                                    [attr.aria-describedby]="
                                        errorFor()(field) ? 'editor-' + field.name + '-error' : null
                                    "
                                    [formField]="textField(field.name)"
                                />
                            }
                            @default {
                                <input
                                    type="text"
                                    class="input aurelius-editor-text"
                                    [class.is-danger]="errorFor()(field)"
                                    [id]="'editor-' + field.name"
                                    [attr.aria-invalid]="errorFor()(field) ? 'true' : null"
                                    [attr.aria-describedby]="
                                        errorFor()(field) ? 'editor-' + field.name + '-error' : null
                                    "
                                    [formField]="textField(field.name)"
                                />
                            }
                        }
                    </div>
                }
                <!-- The error line under the control (EDT-07). The enum
                     rides the Select's own help line (its 'invalid'
                     input, DD-332), so it is not duplicated here. The
                     line carries the id every control of this field
                     names (FORM-ERR-002), so the reason travels with
                     the field, not only as red paint. -->
                @if (errorFor()(field) && field.kind !== "enum") {
                    <p class="help is-danger aurelius-editor-error" [id]="'editor-' + field.name + '-error'">
                        {{ nameRequired() }}
                    </p>
                }
                <!-- The governance banner lines under the control (EDT-24,
                     DD-446, DD-874): the verdicts that name this control. -->
                <aurelius-atlas-webapp-governance-lines
                    [verdicts]="verdictsFor()(field.name)"
                ></aurelius-atlas-webapp-governance-lines>
            </div>
        }
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityFields {
    /** The attribute fields to render, in the resolved order (EDT-03). */
    readonly fields = input<readonly EditorField[]>([]);

    /** The signal form the controls bind to (DD-354). The drawer owns it and
     * rebuilds it when the field set changes (EDT-03's type switch). */
    readonly form = input.required<FieldTree<Record<string, EditorValue>>>();

    /** The form's values, one slot per field — the model {@link form} reads.
     * The drawer owns it (the save body and the validate draft read it). */
    readonly values = input.required<Record<string, EditorValue>>();

    /** Whether one field shows its error now (EDT-07): touched or a Save was
     * tried, and invalid. The decision reads the drawer's Save-attempted state. */
    readonly errorFor = input.required<(field: EditorField) => boolean>();

    /** Which governance verdicts measure a control, by its name (EDT-24). The
     * drawer routes the last validation's verdicts; the banner renders them. */
    readonly verdictsFor = input.required<(name: string) => readonly GovernanceVerdict[]>();

    /** "Name is required." — the control error line (EDT-07) and the enum's
     * required message (DD-332). Shared with the relationship picker, so the
     * drawer owns the string and passes it in. */
    readonly nameRequired = input("");

    /** The multi row's delete aria-label (EDT-03). */
    readonly deleteLabel = input("");

    /** An enum pick (EDT-03). The drawer writes it into the values model. */
    readonly enumPicked = output<{ field: EditorField; row: EnumRow | null }>();

    /** A multi row's delete (EDT-03). The drawer splices the list. */
    readonly multiDelete = output<{ field: EditorField; index: number }>();

    /** The banner line's verdict icons live in {@link GovernanceLines}. */
    protected readonly faXmark = faXmark;

    /** The markdown field's three labels (EDT-20, DD-352). */
    protected readonly markdownWriteLabel = $localize`:@@components.markdownEditor.writeLabel:Write`;

    /** The markdown field's preview tab label. */
    protected readonly markdownPreviewLabel = $localize`:@@components.markdownEditor.previewLabel:Preview`;

    /** The markdown field's empty placeholder. */
    protected readonly markdownPlaceholder = $localize`:@@components.markdownEditor.placeholder:Please type some markdown to get started...`;

    /** A text/textarea/date slot, typed for the text-like inputs. */
    protected textField(name: string): Field<string> {
        return this.form()[name] as unknown as Field<string>;
    }

    /** A number slot, typed for the number input (`null` is its empty). */
    protected numberField(name: string): Field<number | null> {
        return this.form()[name] as unknown as Field<number | null>;
    }

    /** A boolean slot, typed for the checkbox. */
    protected booleanField(name: string): Field<boolean> {
        return this.form()[name] as unknown as Field<boolean>;
    }

    /** A multi slot's rows (EDT-03's repeating text list) — the iterable
     * tree over the string array. */
    protected multiRows(name: string): FieldTree<string[]> {
        return this.form()[name] as unknown as FieldTree<string[]>;
    }

    /** The enum field's options (EDT-03's enum kind). */
    protected enumRows(field: EditorField): EnumRow[] {
        return (field.enumValues ?? []).map((value) => ({ value }));
    }

    /** The enum field's selected row, read off the model. */
    protected enumSelected(field: EditorField): EnumRow | null {
        const current = String(this.values()[field.name] ?? "");

        return (field.enumValues ?? []).includes(current) ? { value: current } : null;
    }
}
