import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { type IconDefinition } from "@fortawesome/free-solid-svg-icons";

/**
 * The Aurelius type-name badge (`models4insight-type-name`): icon,
 * `typeAlias ?? typeName`, and the optional base-type suffix — the shape
 * the details header, the propagated-sources rows, and 7.7's editor all
 * render (DD-100).
 *
 * The legacy component read `iconsByType[typeName]`, an application index;
 * the icon and its colour class arrive as inputs here (UIC-15). The
 * legacy component's `| translate` on the names is the app's job: the
 * caller passes display strings.
 *
 * `entity-card` renders this component for its badge (DD-100) — UIC-12's
 * output is the extraction's regression proof.
 */
@Component({
    selector: "aurelius-atlas-ui-type-name",
    imports: [CommonModule, FontAwesomeModule],
    templateUrl: "./type-name.component.html",
    styleUrl: "./type-name.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TypeName {
    /**
     * The entity type name — the badge's text when no alias is given.
     */
    readonly typeName = input<string | undefined>(undefined);

    /**
     * The display name overriding the type name, as the legacy
     * `typeAlias` attribute did.
     */
    readonly typeAlias = input<string | undefined>(undefined);

    /**
     * The badge's icon — the legacy `iconsByType[typeName].icon`, app
     * meta the caller resolves (UIC-15).
     */
    readonly icon = input<IconDefinition | undefined>(undefined);

    /**
     * The colour class of the icon: business, technical, technical-process, meta.
     */
    readonly iconClass = input<string | undefined>(undefined);

    /**
     * Whether to display the base type in parentheses when a type alias is given.
     */
    readonly showBaseTypeName = input(false);

    /**
     * Whether to display the type icon.
     */
    readonly showIcon = input(true);

    /**
     * Whether to display the type name or type alias.
     */
    readonly showTypeName = input(true);
}
