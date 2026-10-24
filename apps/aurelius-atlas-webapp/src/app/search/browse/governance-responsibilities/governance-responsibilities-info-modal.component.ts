import { ChangeDetectionStrategy, Component, model } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import { Modal, SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

/**
 * One row of the governance-context role table — the legacy `tableData`
 * constant, ported as a static const (BRW-03). Unlike the entity-type
 * tables, the Aurelius rows carry a role label (a dictionary key) as their
 * type name, not an entity-type name.
 */
type InfoRow = {
    readonly icon: typeof faUser;
    readonly typeName: string;
    readonly description: string;
};

/**
 * The Aurelius governance-responsibilities info modal: a description
 * paragraph and the static table of the three data-governance roles
 * (BRW-03), composed from the 7.2 `aurelius-atlas-ui` modal (card anatomy)
 * and sortable table.
 *
 * The modal's `active` model is bound by the card component (BRW-05). Every
 * string carries its legacy dictionary key as an i18n id; strings that must
 * live in TypeScript use `$localize` with the same `@@` ids (BRW-02), the
 * built-in-localize form of the DD-128 bridge.
 */
@Component({
    imports: [FontAwesomeModule, Modal, SortableTable, TableColumn, TableRow],
    selector: "aurelius-atlas-webapp-governance-responsibilities-info-modal",
    templateUrl: "./governance-responsibilities-info-modal.component.html",
    styleUrl: "./governance-responsibilities-info-modal.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GovernanceResponsibilitiesInfoModal {
    /**
     * Whether the modal is open — a model, so the card can open it with
     * `[(active)]` and the ui-lib modal's close/backdrop path writes back
     * (BRW-05).
     */
    readonly active = model(false);

    protected readonly rows: InfoRow[] = [
        {
            icon: faUser,
            typeName: $localize`:@@search.browse.governanceContext.infoModal.domainLeadTypeName:Domain lead`,
            description: $localize`:@@search.browse.governanceContext.infoModal.domainLeadDescription:Accountable for the implementation of data management within a data domain.`,
        },
        {
            icon: faUser,
            typeName: $localize`:@@search.browse.governanceContext.infoModal.dataOwnerTypeName:Data owner`,
            description: $localize`:@@search.browse.governanceContext.infoModal.dataOwnerDescription:Responsible for defining data entities within his or her data domain and the effectiveness of related control measures.`,
        },
        {
            icon: faUser,
            typeName: $localize`:@@search.browse.governanceContext.infoModal.dataStewardTypeName:Data steward`,
            description: $localize`:@@search.browse.governanceContext.infoModal.dataStewardDescription:Responsible for the implementation of data management controls and related initiatives.`,
        },
    ];

    protected readonly title = $localize`:@@search.browse.governanceContext.infoModal.title:Data governance organization`;

    protected readonly closeLabel = $localize`:@@components.modal.close:Close`;

    protected readonly iconTitle = $localize`:@@search.browse.governanceContext.infoModal.iconDisplayName:Icon`;

    protected readonly iconHint = $localize`:@@search.browse.governanceContext.infoModal.iconDescription:The icon representing the role`;

    protected readonly typeNameTitle = $localize`:@@search.browse.governanceContext.infoModal.typeNameDisplayName:Type name`;

    protected readonly typeNameHint = $localize`:@@search.browse.governanceContext.infoModal.typeNameDescription:The name of the role`;

    protected readonly descriptionTitle = $localize`:@@search.browse.governanceContext.infoModal.descriptionDisplayName:Description`;

    protected readonly descriptionHint = $localize`:@@search.browse.governanceContext.infoModal.descriptionDescription:The definition of the role`;
}
