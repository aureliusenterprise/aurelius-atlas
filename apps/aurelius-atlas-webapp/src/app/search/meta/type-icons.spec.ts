import {
    faCheckCircle,
    faCog,
    faFileImport,
    faProjectDiagram,
    faServer,
    faTable,
    faTag,
    faUser,
} from "@fortawesome/free-solid-svg-icons";

import { TYPE_ICONS, typeIcon } from "./type-icons";

/**
 * The type-to-icon map (DET-26, DD-378). Parity source: the legacy
 * `apps/atlas/src/app/search/meta/icons-by-type.ts` of `.scratch/aurelius`
 * (commit b057389828c10497dd52d9efd4c16547c282c005) — every key, glyph,
 * and colour class below is read from that file; the FA5 names ride FA7's
 * alias exports.
 */
describe("type-icons (DET-26, DD-378)", () => {
    it("holds every entry of the legacy map, keyed and coloured as it has them", () => {
        // The legacy map's 37 keys, each with its glyph and family.
        expect(Object.keys(TYPE_ICONS)).toHaveLength(37);
        expect(TYPE_ICONS).toEqual({
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
        });
    });

    it("resolves a mapped type and answers nothing for an unmapped one", () => {
        expect(typeIcon("m4i_data_domain")).toEqual({
            icon: faProjectDiagram,
            classIcon: "business",
        });
        // The legacy's `iconsByType[typeName]` for a stock type answers
        // nothing and its template renders no icon.
        expect(typeIcon("DataSet")).toBeUndefined();
        expect(typeIcon(undefined)).toBeUndefined();
        // A prototype key is not an entry: the lookup is own-property
        // only, so no Object.prototype member leaks out as an "icon".
        expect(typeIcon("constructor")).toBeUndefined();
        expect(typeIcon("toString")).toBeUndefined();
    });
});
