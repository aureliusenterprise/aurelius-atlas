import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";

import { Select, TypeName } from "aurelius-atlas-ui";
import { nameDisplay } from "../meta/type-display";
import { typeIcon } from "../meta/type-icons";
import { type PickerType } from "./editor-state";

/** What the edit-mode badge shows (EDT-04, DD-330): the stored entity's raw
 * type and the alias it carries, when it does (MMS-09). The drawer answers it
 * off the entity; the field resolves the display name and the icon (DD-379,
 * DD-378) and renders the shared type-name part in the details header's shape. */
export type EditorTypeBadge = { typeName: string; alias?: string };

/**
 * The type field above the entity form (EDT-04, DD-330) as its own component
 * (DD-873). Create mode picks the type from it — a plain dropdown over the
 * shipped entity typedefs (the rows the drawer reads off `EditorState`, VDE-02)
 * — and a pick rides out as {@link picked} for the drawer to navigate: the
 * chosen type lives in the route (`create/<type>`), never here. Edit mode
 * shows the entity's type as a static badge instead (the type never changes
 * there), so the field is never a control.
 *
 * The field is presentational: it injects nothing — not the store, not the
 * router — and holds no state. It renders and asks; the drawer owns the route,
 * the seed, and the form rebuild. The two wrapper classes it paints
 * (`.aurelius-editor-picker`, `.aurelius-editor-static-type`/.`aurelius-editor-type`)
 * are what the e2e suite and the drawer's specs pin, so they stay verbatim.
 */
@Component({
    imports: [Select, TypeName],
    selector: "aurelius-atlas-webapp-type-field",
    template: `
        @if (badge()) {
            <!-- Editing renders the type as a static badge (EDT-04, DD-330):
             the type never changes there, so no control — unlike create,
             where the picker below is how the type is chosen and switched.
             The badge is the shared type-name part, the details header's
             shape: the entity's alias when it carries one, the display
             name of the base type beside it, the icon of the raw type
             (MMS-09, DD-721). -->
            <div class="field aurelius-editor-static-type">
                <p class="label">{{ pickerLabel }}</p>
                <p class="aurelius-editor-type">
                    <aurelius-atlas-ui-type-name
                        [typeName]="badgeName()"
                        [typeAlias]="badge()?.alias"
                        [showBaseTypeName]="true"
                        [icon]="badgeIcon()?.icon"
                        [iconClass]="badgeIcon()?.classIcon"
                    />
                </p>
            </div>
        } @else if (picker()) {
            <!-- Create mode: the type field over the shipped entity typedefs
             (EDT-04, DD-330). It stays above the form after the pick — the
             chosen type rides the route, so re-picking switches the type and
             re-seeds the form. The ui-lib Select as a plain dropdown. -->
            <div class="aurelius-editor-picker">
                <aurelius-atlas-ui-select
                    [options]="rows()"
                    displayField="label"
                    [label]="pickerLabel"
                    [value]="selected()"
                    [searchVisible]="false"
                    (valueChange)="picked.emit($event)"
                ></aurelius-atlas-ui-select>
            </div>
        }
    `,
    styleUrl: "./type-field.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TypeField {
    /** Whether the create-mode picker shows (EDT-04): the drawer answers —
     * create mode, and nothing else. Edit mode answers it a badge instead
     * via {@link badge}, which wins when both somehow arrive. */
    readonly picker = input(false);

    /** The shipped entity typedefs the picker offers (VDE-02, MMS-07): the
     * store's picker-types slice, already filtered and label-ordered. */
    readonly pickerTypes = input<readonly PickerType[]>([]);

    /** The route's type (DD-330): the picker's selection, matched by name.
     * The URL owns the pick — the field only shows it. */
    readonly typeName = input("");

    /** The edit-mode badge (EDT-04, DD-330): when present it renders and the
     * picker never does. The drawer answers it off the stored entity — null
     * until the read lands. */
    readonly badge = input<EditorTypeBadge | null>(null);

    /** The row the person picked (EDT-04): the drawer navigates the drawer
     * segment to it. The placeholder (a null pick) rides out too — the drawer
     * ignores it, as it did before the field moved out. */
    readonly picked = output<PickerType | null>();

    /** The rows for the ui-lib Select (EDT-04). The Select's `options` input
     * is a mutable array, so the map yields a fresh one (not readonly); the
     * Select matches the selected row by identity, and {@link selected}
     * resolves within this same cached array. */
    protected readonly rows = computed<PickerType[]>(() =>
        this.pickerTypes().map(({ name, label }) => ({ name, label })),
    );

    /** The picker's selected row (DD-330), found in {@link rows} so the
     * identity holds. */
    protected readonly selected = computed<PickerType | null>(
        () => this.rows().find((row) => row.name === this.typeName()) ?? null,
    );

    /** The badge's name (DD-379): the dictionary display name of the raw type —
     * the legacy's type select shows `translatedName`, `nameDisplay` here. */
    protected readonly badgeName = computed(() => nameDisplay(this.badge()?.typeName ?? ""));

    /** The badge's icon (DD-378): the app's type map, resolved for the raw type. */
    protected readonly badgeIcon = computed(() => typeIcon(this.badge()?.typeName));

    /** The field's label — the one catalogue string both states share
     * (byte-identical key, SHL-08). */
    protected readonly pickerLabel = $localize`:@@search.details.typeSelect.label:Entity type`;
}
