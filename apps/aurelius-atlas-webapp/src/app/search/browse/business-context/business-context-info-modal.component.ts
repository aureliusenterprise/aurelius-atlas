import { ChangeDetectionStrategy, Component, model } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faProjectDiagram, faTable, faTag } from "@fortawesome/free-solid-svg-icons";
import { Modal, SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

/**
 * One row of the business-context type table — the legacy `tableData`
 * constant, ported as a static const (BRW-03). The icon is a FontAwesome
 * definition; the two text cells are the dictionary-translated strings,
 * localized at compile time by `@@` ids.
 */
type InfoRow = {
    readonly icon: typeof faProjectDiagram;
    readonly typeName: string;
    readonly description: string;
};

/**
 * The Aurelius business-context info modal: a description paragraph and the
 * static table of the three business entity types (BRW-03), composed from the
 * 7.2 `aurelius-atlas-ui` modal (card anatomy) and sortable table.
 *
 * The modal's `active` model is bound by the card component — open state
 * lives there (BRW-05). Every string carries its legacy dictionary key as an
 * i18n id; strings that must live in TypeScript (the modal's title inputs,
 * the table cells) use `$localize` with the same `@@` ids (BRW-02), the
 * built-in-localize form of the DD-039 bridge.
 */
@Component({
    imports: [FontAwesomeModule, Modal, SortableTable, TableColumn, TableRow],
    selector: "aurelius-atlas-webapp-business-context-info-modal",
    templateUrl: "./business-context-info-modal.component.html",
    styleUrl: "./business-context-info-modal.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BusinessContextInfoModal {
    /**
     * Whether the modal is open — a model, so the card can open it with
     * `[(active)]` and the ui-lib modal's close/backdrop path writes back
     * (BRW-05).
     */
    readonly active = model(false);

    protected readonly rows: InfoRow[] = [
        {
            icon: faProjectDiagram,
            typeName: $localize`:@@m4i_data_domain:Data Domain`,
            description: $localize`:@@search.browse.businessContext.infoModal.dataDomainDescription:Represents departments, business units and process owners accountable for data due to their accountability in the organization.`,
        },
        {
            icon: faTable,
            typeName: $localize`:@@m4i_data_entity:Data Entity`,
            description: $localize`:@@search.browse.businessContext.infoModal.dataEntityDescription:Represents the meaning and ownership of business process data artifacts that are used in a specific data domain.`,
        },
        {
            icon: faTag,
            typeName: $localize`:@@m4i_data_attribute:Data Attribute`,
            description: $localize`:@@search.browse.businessContext.infoModal.dataAttributeDescription:Represents the meaning and ownership of an atomic data point that is part of a specific data entity.`,
        },
    ];

    protected readonly title = $localize`:@@search.browse.businessContext.infoModal.title:Business context`;

    protected readonly closeLabel = $localize`:@@components.modal.close:Close`;

    protected readonly iconTitle = $localize`:@@search.browse.businessContext.infoModal.iconDisplayName:Icon`;

    protected readonly iconHint = $localize`:@@search.browse.businessContext.infoModal.iconDescription:The icon representing the entity type`;

    protected readonly typeNameTitle = $localize`:@@search.browse.businessContext.infoModal.typeNameDisplayName:Type name`;

    protected readonly typeNameHint = $localize`:@@search.browse.businessContext.infoModal.typeNameDescription:The name of the entity type`;

    protected readonly descriptionTitle = $localize`:@@search.browse.businessContext.infoModal.descriptionDisplayName:Description`;

    protected readonly descriptionHint = $localize`:@@search.browse.businessContext.infoModal.descriptionDescription:The definition of the entity type`;
}
