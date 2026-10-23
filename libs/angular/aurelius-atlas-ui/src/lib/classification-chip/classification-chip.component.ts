import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faAngleDoubleRight, faHashtag } from "@fortawesome/free-solid-svg-icons";

/**
 * The Aurelius classification chip (`models4insight-classification`): the
 * Bulma `tags.has-addons` chip — a lead tag (type icon, as the legacy
 * hashtag) and a label tag carrying the classification name with the
 * type's description as its tooltip (UIC-16).
 *
 * The legacy `ClassificationService` (type-definition lookup by name) and
 * `ClassificationSourceService` (the repository-fed source rows) are data
 * wiring: name, description and `propagated` arrive as inputs, and the
 * propagation dropdown's sources are caller-projected (DD-099). The
 * glossary-term chip (`models4insight-term`) is the same atom with the
 * kind's label as lead and `is-info` — colour is an input, not a twin
 * component (DD-099).
 */
@Component({
    selector: "aurelius-atlas-ui-classification-chip",
    imports: [CommonModule, FontAwesomeModule],
    templateUrl: "./classification-chip.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClassificationChip {
    /**
     * The chip's label: the classification (or term) name, as the legacy
     * component resolved from its service.
     */
    readonly label = input("");

    /**
     * The label tag's tooltip — the type's (or term's) description. The
     * caller localises the fallback; the chip renders no title when unset.
     */
    readonly tooltip = input<string | undefined>(undefined);

    /**
     * The lead tag's text, for chips whose lead is a word, not the
     * hashtag glyph — the term chip's "Term". The legacy term lead was
     * text-only, the classification lead glyph-only; this input picks.
     */
    readonly leadLabel = input<string | undefined>(undefined);

    /**
     * The lead tag's title. The Aurelius lead carried the literal
     * 'Classification'.
     */
    readonly leadTitle = input("Classification");

    /**
     * The lead tag's colour class: `is-primary` for classifications,
     * `is-info` for the term chip (DD-099).
     */
    readonly leadColor = input("is-primary");

    /**
     * Swap the label for the loader tag — the legacy
     * `isRetrievingTypeDefinition$` state.
     */
    readonly loading = input(false);

    /**
     * The classification is propagated from other entities: add the
     * hoverable trigger tag whose dropdown lists the sources (projected).
     */
    readonly propagated = input(false);

    /**
     * The propagation trigger's glyph and the lead's hashtag — the legacy
     * chrome, owned by the component as the breadcrumbs own their warning
     * icon (UIC-15: the caller's icons are data, the chip's glyphs are chrome).
     */
    protected readonly hashtagIcon = faHashtag;

    /**
     * The propagation trigger's glyph — the legacy angle-double-right.
     */
    protected readonly propagatedIcon = faAngleDoubleRight;

    /**
     * The propagation trigger's title. The Aurelius default, 'Is
     * propagated' (`search.components.classification.isPropagated`).
     */
    readonly propagatedLabel = input<string | undefined>(undefined);

    /**
     * The dropdown's origin line. The Aurelius default, 'originates from
     * the following sources:' (`search.components.classification.originates`).
     */
    readonly originLabel = input<string | undefined>(undefined);

    /**
     * The Aurelius English strings behind the optional labels (DD-047).
     */
    protected readonly propagatedLabelDefault = "Is propagated";

    /**
     * The Aurelius English origin line (DD-047).
     */
    protected readonly originLabelDefault = "originates from the following sources:";
}
