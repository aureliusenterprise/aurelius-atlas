# 18.8 One prose attribute

- **Status:** in review
- **Pull request:** #455
- **Records:** DD-832, DD-833 (here), DV-196, ADR 070 (Proposed). Adds SPA-01
  to SPA-07 and EDT-37. Amends VEC-01 (11.3), ASD-03 (14.2), AVR-04 (16.2),
  AVS-01 (16.1, the card's `definition` line), DET-10 (7.20), VCF-03 (16.5d),
  DBS-06 and DBS-07 (13.3), EDT-03 and EDT-20 (7.7a) and the `definition`
  alias line of 12.7's VEV-05 note in place. Relies on ADR 058 (the m4i
  dictionary ships with the server), ADR 046 (the Apache Atlas contract),
  increment 18.6 (ACA, DD-829) and 18.7 (FFB, DD-830, the rebuild stance),
  increment 18.1 (MMS-01/MMS-02, the shipped model set), MMS-07 (DV-180, the
  twelve creatable types), PME-13 (12.7a, every shipped rule names a declared
  attribute), DV-181 (the bare legacy dictionary), SHL-08 (7.33, the catalogue
  guard), and DD-614 (the card's one description field).

## Scope

The shipped model gives an m4i record two prose attributes at once. Apache
Atlas's base model puts `description` on `Asset`, and every entity type
descends from `Asset`. The m4i data dictionary adds its own `definition` to
eight types. The screens grew around both: the editor shows an m4i dataset two
prose boxes, and the details box reads `definition` first and falls back to
`description` (DET-10, DD-320). The server reads the pair in four more places,
the search document, the card line, the search matcher, and the entity vector,
each with its own order.

The sample corpus answers which key the product uses: 181 records hold
`definition` and 4 hold `description`, and no record holds both texts. The four
sit on records that carry no `definition` at all. `owner`, `displayName` and
`userDescription` hold one non-null value between them across all 1,231 m4i
entities. The m4i dictionary is Aurelius's own model (ADR 058), and Apache
Atlas is the key's owner ([ADR 070](../../docs/architecture/adr/070-the-catalogue-ships-one-prose-attribute.md)),
so the dictionary moves to `description` and the other three retire from the
screens without touching Apache Atlas's model.

In scope:

1. The dictionary drops its `definition` attribute definition from the eight
   types that declare it, and each of those types goes to the next type
   version (SPA-01). Two of the eight (`m4i_dataset`, `m4i_generic_process`)
   inherit `description` from Apache Atlas's `Asset`, and the six chain
   terminals that do not (`m4i_collection`, `m4i_data_attribute`,
   `m4i_data_domain`, `m4i_data_entity`, `m4i_field`, `m4i_system`) declare it
   themselves in the same version bump (DD-832). The editor already answers a
   markdown field for `description` on every shipped type (EDT-03), so one
   prose field is what every editor now builds.
2. The three sample bundles carry the new type definitions. Every record's
   `definition` text moves to `description`, and every shipped rule expression
   that named `definition` names `description` (SPA-02). The rule counts do not
   change.
3. A new catalogue reaches the shape in one load. A catalogue that already
   holds the attribute keeps it: the store hands back every attribute a stored
   type holds and the model lacks (ACA-04, DD-829), so the load succeeds and
   that catalogue still answers `definition`. The change lands on a new store,
   which is the store the product ships and tests (SPA-03, DD-832).
4. The database scanner and the Kafka scanner write their reflected and parsed
   text to `description` (SPA-04). The m4i types they create keep their other
   attributes.
5. The server readers name one key (SPA-05): the entity vector, the App Search
   document, the view search matcher, and the card's description line. The
   App Search document's field and the view card's field keep their existing
   names (DD-833), so the vendored engine, the parity fixtures and the
   hand-mirrored Angular card family read as they do today.
6. The webapp details box and every prose reader read `description` alone
   (SPA-06): the details box loses its `definition` fallback (DET-10), the
   editor's prose keys lose `definition`, and the governance banner loses its
   one-way `definition` alias.
7. The editor builds no field for `owner`, `displayName` or `userDescription`
   (EDT-37). The three attributes stay declared, because `Asset` is Apache
   Atlas's own model (DV-181's ground), and every read path that names them
   stays: the owner facet, the details rows, the display-text fallbacks and the
   audit prose keys.
8. The editor's attribute label map and both locale catalogues retire the
   `definition` editor key, the three hidden keys stay, and the bare legacy
   dictionary entries stay (SPA-07, the FFB-05 pattern).

Out of scope:

| Deferred                                                                                    | Lands with        | Why                                                                                                                                          |
| ------------------------------------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Retiring `owner`, `displayName` and `userDescription` from the model                        | never planned     | `Asset` is Apache Atlas's own model, and the catalogue keeps its contract (ADR 046, DV-181). The store keeps values a client writes to them. |
| Technical ownership screens over `owner` and the people ends                                | a later increment | Chosen on 2026-11-23: ownership returns with the screens that show it.                                                                       |
| Migrating a catalogue that holds `definition`                                               | not planned       | No door changes a stored shape (FFB-04's stance), and the sample store is a development catalogue (DV-194, DD-829).                          |
| Renaming the App Search document's `definition` field or the view card's `definition` field | not planned       | The vendored engine and the parity fixtures name the document field, and the card name is the 16.x family's contract (DD-833, DV-196).       |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SPA-01 | The m4i data dictionary declares no `definition` attribute on any type. The eight definitions that carried it (collection, data attribute, data domain, data entity, dataset, field, generic process, system) each hold the next type version, and the registry answers no attribute of that name for any m4i type. The six of those that no supertype gives `description` declare `description` themselves, so every m4i type answers the prose attribute through the registry. Every other attribute and relationship stays.                                                                                                     |
| SPA-02 | Each bundle under `data/atlas-sample/` declares the eight types at those versions and without the dropped attribute, names no `definition` key in any entity's `attributes` or `relationshipAttributes`, and ships no rule whose expression names the dropped attribute. Each of the 181 texts that sat under `definition` sits under `description`, and the corpus's four `description` records keep their text. Each rule bundle ships 65 rules.                                                                                                                                                                                 |
| SPA-03 | A store that holds the dropped attribute on a shipped m4i type does not take the change. The load reports the model file as failed and keeps every stored definition and version, and an import of a record that names the dropped attribute fails whole. A new catalogue reaches the shape in one load.                                                                                                                                                                                                                                                                                                                           |
| SPA-04 | The database scanner writes a table comment or a primary-key mark to the dataset's or field's `description`, and the Kafka scanner writes an Avro doc or a JSON-schema description to the field's `description`. Neither writes the dropped key. DBS-06 and DBS-07 are amended in place, and every other attribute of a scanned record stays as 13.3 and 13.1 left it.                                                                                                                                                                                                                                                             |
| SPA-05 | The server's prose readers name one attribute. VEC-01 is amended: the embedded text reads `name`, `displayName`, `qualifiedName` and `description`. ASD-03 is amended: the document's own fields read `description` into the document's `definition` field, whose name and index mapping stay, and `DERIVATION_VERSION` goes to 4 so a stored document re-derives (DD-833). AVR-04 is amended: the matcher's name paths hold the dropped attribute's path for no shipped type, because no shipped type declares it. AVS-01 is amended: the card's `definition` field is the entity's `description`, and DD-614's fallback is gone. |
| SPA-06 | The webapp's prose readers name one attribute. DET-10 is amended: the description box shows `attributes.description` when that value is a string, and the `definition` step is gone. VCF-03 is amended: a card's description text is the card's `definition` field, which the server derives from `description`. The editor's prose keys hold `description` alone, the banner answers a `description` verdict under the `description` control (EDT-24, the alias line of 12.7's VEV-05 note falls away), and the audit change tables diff the one prose key (EDT-20).                                                              |
| SPA-07 | The editor's attribute label map holds no `definition` entry, and both locale catalogues and both fixtures hold no `search.components.editor.attribute.definition` key. The bare legacy dictionary entry stays (DV-181), the `description` key stays, and SHL-08 still compares the catalogues and the fixtures set-equal.                                                                                                                                                                                                                                                                                                         |
| EDT-37 | The editor builds no field for `owner`, `displayName` or `userDescription`. The attribute walk of EDT-03 drops the three names, whether a definition names them itself or inherits them, which is every shipped entity type. A save carries no key for a dropped attribute, and the door leaves a stored value it does not name unchanged (AVW-05). The read side is untouched: the owner facet, the details rows, the display-text fallbacks and the audit prose keys keep the three. Every other attribute still answers its input (EDT-03).                                                                                     |

## Aurelius origin

- `m4i_atlas_core`'s data dictionary and its sample exports declare
  `definition` on the eight types, and the legacy Flask screens pair it with
  Apache Atlas's `description`. The legacy stock editor lists every attribute
  of the type, so a legacy m4i dataset form shows both prose boxes. The legacy
  details box reads `definition` alone (DD-320's note), because the legacy store
  held its catalogue in the m4i dictionary.
- The Apache Atlas 2.4.0 base model is `description`'s owner: `Asset` declares
  it in `0010-base_model.json`, and `TYPEDEF_PATCH_0005_001` adds
  `displayName` and `userDescription`. The stock dashboards Aurelius serves
  unchanged read `description` and `displayName`
  (`dashboardv2/public/js/views/detail_page/DetailPageLayoutView.js`), so the
  key that wins is the one Apache Atlas's own screens read.

## Deviations

Against the m4i dictionary: DV-196. The shipped dictionary carries no
`definition` attribute, its eight types move a version, and the sample corpus
holds its prose in `description` alone. The vendored App Search engine and the
16.x card family keep their `definition` field names, because the engine's
mapping and the hand-mirrored card are contracts (DD-833).

Against the legacy editor: covered by EDT-37's shape and 7.41's DV-193. The
stock forms list every attribute; the Aurelius editor lists no field for the
three base attributes, and its saves leave any stored value untouched.

## Acceptance

- Model: `libs/python/aurelius-atlas-core/tests/test__m4i_models.py` (SPA-01:
  no definition declares the attribute, and the eight types hold their new
  versions; SPA-02: every bundle agrees with the model file and names no
  dropped key; SPA-02's rule half: every shipped rule names an attribute the
  model declares, PME-13).
- Loader: `libs/python/aurelius-atlas-core/tests/test__model_loader.py`
  (SPA-03: a new catalogue answers no dropped attribute, and a store that
  already holds it keeps it and still loads, the ACA-04 pair).
- Scanners: `apps/aurelius-atlas-db-scanner/tests/test__graph.py` and
  `test__reflect.py`, `apps/aurelius-atlas-kafka-scanner/tests/test__graph.py`
  (SPA-04: the text lands on `description`).
- Core readers: `tests/test__entity_embedding.py` (VEC-01),
  `tests/test__app_search_document.py` and `test__app_search_engine.py`
  (ASD-02), `tests/test__view_derivation.py` (AVS-01), `tests/test__view_search.py`
  (AVR-04) (SPA-05).
- Webapp: `attribute-labels.spec.ts` and `i18n-completeness.spec.ts` (SPA-07,
  SHL-08), `form-fields.spec.ts` and `entity-editor.component.spec.ts`
  (EDT-37, EDT-03: the three names answer no field and `description` still
  answers its prose control; EDT-06: a save carries no key for a dropped name),
  `details.component.spec.ts` (SPA-06: the box shows `description` alone),
  `related-sections.state.spec.ts` and `catalogue-card` fixtures (VCF-03).
- e2e: the editor prose scenarios keep their shape on `DataSet` (EDT-12,
  EDT-20), the governance banner scenario's refusal line rides the
  `description` control (EDT-24), and the m4i e2e seeds name `description`.
- Run from the repo root: `uv run pytest libs/python/aurelius-atlas-core/tests`
  (one suite at a time per the conftest note), `nx test aurelius-atlas-webapp
-c ci`, `nx e2e aurelius-atlas-server` and `nx e2e aurelius-atlas-webapp`
  against a wiped store and a fresh import (the SPA-03 stance).
- Data: each bundle's type-definition file, entity entries and rule entries
  change with the model, which `test__m4i_models.py` compares (SPA-02). The
  App Search gates re-baseline to the moved texts; the 654 documents and the
  1,785 verdicts of DV-195 keep their counts. The move changes no record's
  existence, and the three `completeness` rules over `definition` (domain,
  entity, attribute) flip to `description` and answer met on the same records,
  because those are the records whose text moves (DV-196 records the count).
