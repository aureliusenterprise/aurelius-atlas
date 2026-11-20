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
 * The type-to-icon map (DET-26, DD-378, MMS-05). Parity source: the
 * legacy `apps/atlas/src/app/search/meta/icons-by-type.ts` of
 * `.scratch/aurelius` (commit b057389828c10497dd52d9efd4c16547c282c005) —
 * every key, glyph, and colour class below is read from that file; the
 * FA5 names ride FA7's alias exports. The map carries the twelve keys of
 * the metamodel and none of the legacy's connector and kubernetes types
 * (ADR 058, ADR 068, DD-717).
 */
describe("type-icons (DET-26, DD-378, MMS-05)", () => {
    it("holds every entry of the metamodel, keyed and coloured as the legacy has them", () => {
        // The twelve Aurelius types a catalogue can hold, each with its glyph and family.
        expect(Object.keys(TYPE_ICONS)).toHaveLength(12);
        expect(TYPE_ICONS).toEqual({
            m4i_data_attribute: { icon: faTag, classIcon: "business" },
            m4i_data_entity: { icon: faTable, classIcon: "business" },
            m4i_data_domain: { icon: faProjectDiagram, classIcon: "business" },
            m4i_field: { icon: faTag, classIcon: "technical" },
            m4i_dataset: { icon: faTable, classIcon: "technical" },
            m4i_collection: { icon: faProjectDiagram, classIcon: "technical" },
            m4i_system: { icon: faServer, classIcon: "technical" },
            m4i_person: { icon: faUser, classIcon: "business" },
            m4i_generic_process: { icon: faCog, classIcon: "technical-process" },
            m4i_data_quality: { icon: faCheckCircle, classIcon: "technical" },
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
        // A retired connector type answers nothing: no catalogue entity carries it.
        expect(typeIcon("m4i_kafka_topic")).toBeUndefined();
        expect(typeIcon(undefined)).toBeUndefined();
        // A prototype key is not an entry: the lookup is own-property
        // only, so no Object.prototype member leaks out as an "icon".
        expect(typeIcon("constructor")).toBeUndefined();
        expect(typeIcon("toString")).toBeUndefined();
    });
});
