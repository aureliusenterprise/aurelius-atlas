import { ChangeDetectionStrategy, Component, model } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faProjectDiagram, faServer, faTable, faTag } from "@fortawesome/free-solid-svg-icons";
import { Modal, SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

/**
 * One row of the technical-context type table — the legacy `tableData`
 * constant, ported as a static const (BRW-03).
 */
type InfoRow = {
    readonly icon: typeof faServer;
    readonly typeName: string;
    readonly description: string;
};

/**
 * The Aurelius technical-context info modal: a description paragraph and the
 * static table of the four technical entity types (BRW-03), composed from
 * the 7.2 `aurelius-atlas-ui` modal (card anatomy) and sortable table.
 *
 * The modal's `active` model is bound by the card component (BRW-05). Every
 * string carries its legacy dictionary key as an i18n id; strings that must
 * live in TypeScript use `$localize` with the same `@@` ids (BRW-02), the
 * built-in-localize form of the DD-039 bridge.
 */
@Component({
    imports: [FontAwesomeModule, Modal, SortableTable, TableColumn, TableRow],
    selector: "aurelius-atlas-webapp-technical-context-info-modal",
    templateUrl: "./technical-context-info-modal.component.html",
    styleUrl: "./technical-context-info-modal.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TechnicalContextInfoModal {
    /**
     * Whether the modal is open — a model, so the card can open it with
     * `[(active)]` and the ui-lib modal's close/backdrop path writes back
     * (BRW-05).
     */
    readonly active = model(false);

    protected readonly rows: InfoRow[] = [
        {
            icon: faServer,
            typeName: $localize`:@@m4i_system:System`,
            description: $localize`:@@search.browse.technicalContext.infoModal.systemDescription:Represents the computing environment on which many data collections can be stored and application processes are run.`,
        },
        {
            icon: faProjectDiagram,
            typeName: $localize`:@@m4i_collection:Collection`,
            description: $localize`:@@search.browse.technicalContext.infoModal.collectionDescription:Represents a set of datasets, e.g. a database which usually contains multiple tables.`,
        },
        {
            icon: faTable,
            typeName: $localize`:@@m4i_dataset:Dataset`,
            description: $localize`:@@search.browse.technicalContext.infoModal.datasetDescription:Represents a set of data fields. The most common example of a dataset is a table.`,
        },
        {
            icon: faTag,
            typeName: $localize`:@@m4i_field:Data Field`,
            description: $localize`:@@search.browse.technicalContext.infoModal.fieldDescription:Represents a single, indivisible unit of data. The most common example of a field is a column in a table.`,
        },
    ];

    protected readonly title = $localize`:@@search.browse.technicalContext.infoModal.title:Technical context`;

    protected readonly closeLabel = $localize`:@@components.modal.close:Close`;

    protected readonly iconTitle = $localize`:@@search.browse.technicalContext.infoModal.iconDisplayName:Icon`;

    protected readonly iconHint = $localize`:@@search.browse.technicalContext.infoModal.iconDescription:The icon representing the entity type`;

    protected readonly typeNameTitle = $localize`:@@search.browse.technicalContext.infoModal.typeNameDisplayName:Type name`;

    protected readonly typeNameHint = $localize`:@@search.browse.technicalContext.infoModal.typeNameDescription:The name of the entity type`;

    protected readonly descriptionTitle = $localize`:@@search.browse.technicalContext.infoModal.descriptionDisplayName:Description`;

    protected readonly descriptionHint = $localize`:@@search.browse.technicalContext.infoModal.descriptionDescription:The definition of the entity type`;
}
