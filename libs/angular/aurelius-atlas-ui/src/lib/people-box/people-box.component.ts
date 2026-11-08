import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faUser } from "@fortawesome/free-solid-svg-icons";

/** One person of a row: the address and the name the link shows. */
export interface PersonLink {
    /** The person's guid — the payload of `personClicked`. */
    guid: string;
    /** The person's display text — the link's text. */
    displayText: string;
}

/** One People-box row: its label ("Domain Lead(s)") and its people. */
export interface PeopleRow {
    /** The row's label. The caller localises it. */
    label: string;
    /** The people of the row, in order; an empty row renders nothing. */
    people: PersonLink[];
}

/**
 * The Aurelius People box (`models4insight-people`, UIC-28, DET-23): the
 * labelled rows of person links the legacy details pages show — the
 * `faUser` icon, "Label : ", the comma-joined links. Ported dumb (WBP-04):
 * the legacy read the entity store and routed itself; here the rows arrive
 * as an input and a click emits `personClicked(guid)` — grouping, dedupe,
 * and routing are the app's.
 *
 * A row with no people renders nothing, and a box whose every row is empty
 * shows the italic centered placeholder line (the legacy `empty` state) in
 * place of the rows.
 */
@Component({
    selector: "aurelius-atlas-ui-people-box",
    imports: [FontAwesomeModule],
    templateUrl: "./people-box.component.html",
    styleUrl: "./people-box.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PeopleBox {
    /**
     * The rows, in order. The caller filters empty ends and dedupes
     * before handing them over (DET-23 keeps both rules app-side).
     */
    readonly rows = input<PeopleRow[]>([]);

    /**
     * The placeholder line shown when no row has people. The caller
     * localises it; the Aurelius string was "No people assigned.".
     */
    readonly emptyLabel = input("No people assigned.");

    /**
     * Whether the placeholder line shows at all — the legacy
     * `showPlaceholder`. The details box turns it on; the card body turns
     * it off (a card with no people just has no people block).
     */
    readonly showEmpty = input(true);

    /**
     * The row icon — the legacy `faUser`, chrome the component owns
     * (UIC-15: icons with no application meaning are the part's own).
     */
    readonly personIcon = faUser;

    /**
     * Emits the guid of a clicked person link. The app routes; the lib
     * does not (DD-154's split).
     */
    readonly personClicked = output<string>();

    /**
     * Whether every row is empty — the legacy `noPeople$` state.
     * @returns whether no row carries a person
     */
    protected get allEmpty(): boolean {
        return this.rows().every((row) => row.people.length === 0);
    }

    /**
     * Handle a person activation — the legacy `directToDetailsPage`,
     * turned into an emit (the anchor's `href` is the keyboard path, so
     * the default navigation is cancelled).
     * @param event The click event.
     * @param person The person activated.
     */
    protected onPersonClick(event: Event, person: PersonLink): void {
        event.preventDefault();
        this.personClicked.emit(person.guid);
    }
}
