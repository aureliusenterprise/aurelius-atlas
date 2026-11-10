import { HttpErrorResponse } from "@angular/common/http";
import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from "@angular/core";
import { AtlasEntityHeader, SearchByMeaningService } from "aurelius-atlas-data-access";
import { EntityCard } from "aurelius-atlas-ui";
import { Subscription } from "rxjs";

import { nameDisplay } from "../../meta/type-display";
import { typeIcon } from "../../meta/type-icons";

/** How many neighbours the box shows: two rows of the three-across grid (SBW-07, DD-446). */
const SHOWN = 6;

/** The server's codes the box answers to (SBM-05, SBM-06). */
const EMBEDDING_OFF = "AURELIUS-404-00-001";
const NOT_EMBEDDED = "AURELIUS-409-00-001";

/** What the box shows (SBW-07). */
type SimilarState =
    | { readonly kind: "loading" }
    | { readonly kind: "found"; readonly entities: readonly AtlasEntityHeader[] }
    | { readonly kind: "notYet" | "none" | "failed" | "off" };

/**
 * The Similar entities box of the details page (SBW-07, DD-446): the six
 * entities nearest in meaning to the shown one, as entity cards that lead to
 * their own details page. It owns its fetch and its states, as the Lineage
 * Model box does (DD-388): a spinner, the cards, a note when the entity is
 * not analysed yet, when none is found, or when they could not be loaded —
 * and no box at all on a server without search by meaning.
 */
@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [EntityCard],
    selector: "aurelius-atlas-webapp-similar-entities",
    styleUrl: "./similar-entities.component.scss",
    templateUrl: "./similar-entities.component.html",
})
export class SimilarEntities {
    private readonly meaning = inject(SearchByMeaningService);

    /** The shown entity's GUID; a new one fetches its neighbours. */
    readonly guid = input.required<string>();

    /** A card was clicked: the details page routes to it. */
    readonly entityClicked = output<string>();

    protected readonly state = signal<SimilarState>({ kind: "loading" });

    /** The neighbours found, empty in every other state. */
    protected readonly found = computed(() => {
        const state = this.state();
        return state.kind === "found" ? state.entities : [];
    });

    protected readonly title = $localize`:@@search.details.similar.title:Similar entities`;

    protected readonly notYet = $localize`:@@search.details.similar.notYet:This entity is not analysed yet. Try again in a moment.`;

    protected readonly none = $localize`:@@search.details.similar.none:No similar entities found.`;

    protected readonly failed = $localize`:@@search.details.similar.failed:Similar entities could not be loaded.`;

    private request: Subscription | undefined;

    constructor() {
        effect(() => this.load(this.guid()));
    }

    /**
     * Fetch the neighbours of ``guid``, cancelling a fetch still in flight for
     * the entity shown before.
     * @param guid the shown entity's GUID
     */
    private load(guid: string): void {
        this.request?.unsubscribe();
        this.state.set({ kind: "loading" });
        this.request = this.meaning.similar(guid, { limit: SHOWN, excludeDeletedEntities: true }).subscribe({
            next: (result) => {
                const entities = result.searchResults?.entities ?? [];
                this.state.set(entities.length > 0 ? { kind: "found", entities } : { kind: "none" });
            },
            error: (error: unknown) => this.state.set({ kind: refusal(error) }),
        });
    }

    /**
     * The card's name: the header's display text, else its name attribute.
     * @param entity the neighbour
     */
    protected nameOf(entity: AtlasEntityHeader): string | undefined {
        const name = entity.attributes?.["name"];
        return entity.displayText ?? (typeof name === "string" ? name : undefined);
    }

    /**
     * The card's type as the catalogue names it (DV-84's display names).
     * @param typeName the neighbour's type
     */
    protected typeOf(typeName: string | null | undefined): string | undefined {
        return nameDisplay(typeName ?? undefined);
    }

    /**
     * The card's type icon.
     * @param typeName the neighbour's type
     */
    protected iconOf(typeName: string | null | undefined) {
        return typeIcon(typeName ?? undefined);
    }
}

/**
 * The box's state for a failed fetch (SBW-07): off without search by meaning,
 * a note for an entity not embedded yet, else the failure note.
 * @param error what the fetch failed with
 */
function refusal(error: unknown): "off" | "notYet" | "failed" {
    if (!(error instanceof HttpErrorResponse)) {
        return "failed";
    }
    const code = (error.error as { errorCode?: string } | null)?.errorCode;
    if (error.status === 404 && code === EMBEDDING_OFF) {
        return "off";
    }
    return error.status === 409 && code === NOT_EMBEDDED ? "notYet" : "failed";
}
