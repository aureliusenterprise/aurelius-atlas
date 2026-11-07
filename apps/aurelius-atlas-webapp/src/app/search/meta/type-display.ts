/**
 * The display name of every catalogue type and classification name — the
 * legacy's `| translate` over the Aurelius dictionary, ported to the
 * `$localize` catalogue bridge (DD-128, DD-379).
 *
 * The legacy templates pipe the raw name through ngx-translate: the type
 * badge (`type-name.component.html`, `{{ typeName | translate }}`), the
 * classification chips (`classification.component.html`), and the editor's
 * type select (`displayField="translatedName"`). The catalogue's keys ride
 * the vendored dictionary (`tests/fixtures/en-US.json`, DD-128), so each
 * entry carries its dictionary id as its `$localize` id and the English
 * catalogue value as its fallback; `messages.nl-NL.xlf` carries the Dutch
 * side, picked per locale at build time — the same two locales the shell
 * ships.
 *
 * A name outside the dictionary keeps its raw spelling — the answer
 * ngx-translate gives for a missing key, which is what the legacy renders
 * for a name the catalogue never saw (`DataSet`, every `spark_*` name).
 * The resolver answers display strings only: the values stored or sent
 * never change (EDT-16), and the ui components take display strings as
 * inputs (UIC-15).
 */
export const NAME_DISPLAY: Record<string, string> = {
    PII: $localize`:@@PII:Has PII`,
    high_risk: $localize`:@@high_risk:High risk`,
    key_data: $localize`:@@key_data:Is key`,
    low_risk: $localize`:@@low_risk:Low risk`,
    m4i_collection: $localize`:@@m4i_collection:Collection`,
    m4i_data_attribute: $localize`:@@m4i_data_attribute:Data Attribute`,
    m4i_data_domain: $localize`:@@m4i_data_domain:Data Domain`,
    m4i_data_entity: $localize`:@@m4i_data_entity:Data Entity`,
    m4i_data_field: $localize`:@@m4i_data_field:Data Field`,
    m4i_data_quality: $localize`:@@m4i_data_quality:Data Quality`,
    m4i_dataset: $localize`:@@m4i_dataset:Dataset`,
    m4i_field: $localize`:@@m4i_field:Data Field`,
    m4i_generic_process: $localize`:@@m4i_generic_process:Generic Process`,
    m4i_gov_data_quality: $localize`:@@m4i_gov_data_quality:Gov. Quality`,
    m4i_person: $localize`:@@m4i_person:Person`,
    m4i_referenceable: $localize`:@@m4i_referenceable:Referenceable`,
    m4i_source: $localize`:@@m4i_source:Source`,
    m4i_system: $localize`:@@m4i_system:System`,
    medium_risk: $localize`:@@medium_risk:Medium risk`,
};

/**
 * Resolve a type or classification name's display name (DET-26, DET-19,
 * SRH-05, DET-09, DD-379): the legacy `name | translate` lookup over the
 * dictionary above.
 * @param name the raw type or classification name, or nothing
 */
export function nameDisplay(name: string): string;
export function nameDisplay(name: string | undefined): string | undefined;
export function nameDisplay(name: string | undefined): string | undefined {
    return name !== undefined && Object.hasOwn(NAME_DISPLAY, name) ? NAME_DISPLAY[name] : name;
}
