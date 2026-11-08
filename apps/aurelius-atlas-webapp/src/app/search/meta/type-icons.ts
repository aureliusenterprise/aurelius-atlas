import {
    faCheckCircle,
    faCog,
    faFileImport,
    faProjectDiagram,
    faServer,
    faTable,
    faTag,
    faUser,
    type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";

/**
 * The colour class of a type icon — the family the icon is inked with.
 * The ui components carry the matching `.business` / `.technical` /
 * `.technical-process` / `.meta` rules (UIC-12, UIC-15); this map names
 * the family per type.
 */
export type TypeIconClass = "business" | "technical" | "technical-process" | "meta";

/**
 * A type's icon and its colour class — the legacy
 * `AtlasTypeIconDefinition`, with the lodash `Dictionary` dropped.
 */
export interface TypeIcon {
    /** The glyph to render. */
    readonly icon: IconDefinition;
    /** The colour class to ink it with. */
    readonly classIcon: TypeIconClass;
}

/**
 * The type-to-icon map (DET-26, DD-378): the legacy
 * `search/meta/icons-by-type.ts` — the Aurelius app metadata that gives
 * every m4i type its glyph and colour family.
 *
 * The legacy components read this index directly; the ui parts never do
 * (UIC-15): each consumer resolves the entry here and passes the
 * `IconDefinition` and class as inputs. This file is the only place in
 * the webapp that names a type icon (DD-378, which supersedes the map
 * refusals of DD-341 and DD-371).
 *
 * The FA5 names ride the alias exports FA7 kept for them — the same
 * glyphs the legacy renders. The `m4i_data_quilt` and
 * `m4i_kubenetes_serce_process` spellings are the legacy's own (a
 * catalogue string matches them, and no key is corrected away).
 */
export const TYPE_ICONS: Record<string, TypeIcon> = {
    m4i_data_attribute: { icon: faTag, classIcon: "business" },
    m4i_data_entity: { icon: faTable, classIcon: "business" },
    m4i_data_domain: { icon: faProjectDiagram, classIcon: "business" },
    m4i_field: { icon: faTag, classIcon: "technical" },
    m4i_dataset: { icon: faTable, classIcon: "technical" },
    m4i_collection: { icon: faProjectDiagram, classIcon: "technical" },
    m4i_system: { icon: faServer, classIcon: "technical" },
    m4i_person: { icon: faUser, classIcon: "business" },
    m4i_dashboard: { icon: faTable, classIcon: "technical" },
    m4i_generic_process: { icon: faCog, classIcon: "technical-process" },
    m4i_kafka_topic: { icon: faTable, classIcon: "technical" },
    m4i_confluent_cloud: { icon: faServer, classIcon: "technical" },
    m4i_index_pattern: { icon: faProjectDiagram, classIcon: "technical" },
    m4i_confluent_environment: { icon: faServer, classIcon: "technical" },
    m4i_elastic_index: { icon: faTable, classIcon: "technical" },
    m4i_visualization: { icon: faTable, classIcon: "technical" },
    m4i_elastic_cluster: { icon: faServer, classIcon: "technical" },
    m4i_connector_process: { icon: faCog, classIcon: "technical-process" },
    m4i_elastic_field: { icon: faTag, classIcon: "technical" },
    m4i_kafka_field: { icon: faTag, classIcon: "technical" },
    m4i_kibana_space: { icon: faProjectDiagram, classIcon: "technical" },
    m4i_kafka_cluster: { icon: faServer, classIcon: "technical" },
    m4i_elastic: { icon: faServer, classIcon: "technical" },
    m4i_kubernetes_cluster: { icon: faServer, classIcon: "technical" },
    m4i_kubernetes_cronjob: { icon: faServer, classIcon: "technical" },
    m4i_kubernetes_deployment: { icon: faServer, classIcon: "technical" },
    m4i_kubernetes_environment: { icon: faServer, classIcon: "technical" },
    m4i_kubernetes_namespace: { icon: faServer, classIcon: "technical" },
    m4i_kubernetes_pod: { icon: faServer, classIcon: "technical" },
    m4i_data_quality: { icon: faCheckCircle, classIcon: "technical" },
    m4i_api_operation_process: { icon: faCog, classIcon: "technical-process" },
    m4i_ingress_controller_process: { icon: faCog, classIcon: "technical-process" },
    m4i_ingress_object_process: { icon: faCog, classIcon: "technical-process" },
    m4i_kubenetes_serce_process: { icon: faCog, classIcon: "technical-process" },
    m4i_microservice_process: { icon: faCog, classIcon: "technical-process" },
    m4i_gov_data_quality: { icon: faCheckCircle, classIcon: "meta" },
    m4i_source: { icon: faFileImport, classIcon: "meta" },
};

/**
 * Resolve an entity type's icon (the legacy `iconsByType[typeName]`
 * lookup). An unknown or missing type answers `undefined` — the legacy
 * template's `*ngIf="iconsByType[typeName] as iconDef"` rendered no icon
 * at all, so a `DataSet` or any type outside the map keeps a plain
 * badge.
 * @param typeName the entity's type name, or nothing
 */
export function typeIcon(typeName: string | undefined): TypeIcon | undefined {
    return typeName !== undefined && Object.hasOwn(TYPE_ICONS, typeName) ? TYPE_ICONS[typeName] : undefined;
}
