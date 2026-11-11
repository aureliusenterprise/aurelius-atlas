# 14.1 The legacy search documents: records and rules

- **Status:** in progress
- **Pull request:** [#320](https://github.com/aureliusenterprise/aurelius-atlas/pull/320)
- **Records:** ADR 060 (Proposed); DD-484 to DD-486 (here); relies on ADR 047 (one store), ADR 054 (whose
  retirement of the App Search surface ADR 060 supersedes), ADR 059 (search by meaning), and 12.2 (the
  `m4i_dq_score` entities, DQS-01..10)

## Scope

The original Aurelius Atlas webapp reads three App Search engines: `atlas-dev`, one document per entity with its
breadcrumb, its derived relations and its quality scores; `atlas-dev-quality`, one document per data quality
result; and `atlas-dev-gov-quality`, one document per governance rule verdict. Flink jobs and two post-install
scripts filled them from Apache Atlas's notifications. ADR 060 brings the search API back as a view over the one
store; series 14 builds it.

This increment writes down what those documents hold, as rules of the catalogue's state, so that every later
increment of the series implements the same rules and tests them by id. It delivers:

- ADR 060;
- the legacy engines' documents for the sample catalogue as test fixtures, with their provenance (DD-484);
- the rules below, and the differences between the fixtures and the catalogue they came from (DD-485);
- a test that the fixtures obey the rules that can be read from the fixtures alone;
- the roadmap rows of series 14.

Not delivered, with the increment that will:

| Not delivered                                                   | Lands with |
| --------------------------------------------------------------- | ---------- |
| The derived fields on the entity documents (LAS-01..LAS-08)     | 14.2       |
| Their upkeep when entities change (LAS-09, LAS-10)              | 14.3       |
| `POST /api/as/v1/engines/atlas-dev/search` (`/elastic`)         | 14.4       |
| The data quality results and the score roll-up (LAS-11, LAS-12) | 14.5       |
| The governance verdicts (LAS-13) and `atlas-dev-gov-quality`    | 14.6       |
| The derived fields in the text an entity's embedding is made of | 14.7       |

## Semantics

The m4i types the documents know are the data dictionary's (ADR 058). The _mapped types_ and their relation
fields are:

| Type                  | Relation field         |
| --------------------- | ---------------------- |
| `m4i_data_domain`     | `deriveddatadomain`    |
| `m4i_data_entity`     | `deriveddataentity`    |
| `m4i_data_attribute`  | `deriveddataattribute` |
| `m4i_field`           | `derivedfield`         |
| `m4i_dataset`         | `deriveddataset`       |
| `m4i_collection`      | `derivedcollection`    |
| `m4i_system`          | `derivedsystem`        |
| `m4i_person`          | `derivedperson`        |
| `m4i_generic_process` | `derivedprocess`       |

An entity's _parents_, in this order:

| Type                 | Parents                             |
| -------------------- | ----------------------------------- |
| `m4i_data_entity`    | `parentEntity`, then `dataDomain`   |
| `m4i_data_attribute` | `dataEntity`                        |
| `m4i_system`         | `parentSystem`                      |
| `m4i_collection`     | `systems`                           |
| `m4i_dataset`        | `parentDataset`, then `collections` |
| `m4i_field`          | `parentField`, then `datasets`      |
| `m4i_data_quality`   | `fields`                            |
| any other type       | none                                |

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LAS-01 | `atlas-dev` holds one document per active entity whose type is an m4i type other than `m4i_source`; its `id` is the entity's GUID. A deleted entity has none                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| LAS-02 | A document's `guid` and `typename` are the entity's; `supertypenames` is `[typename]`; `name` is the `name` attribute, else the qualified name; `referenceablequalifiedname` is the `qualifiedName` attribute, else the GUID; `definition` is the `definition` attribute, else `""`; an `m4i_person`'s `email` is its `email` attribute                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| LAS-03 | `sourcetype` is `Technical` for `m4i_system`, `m4i_collection`, `m4i_dataset` and `m4i_field`, `Business` for `m4i_data_domain`, `m4i_data_entity` and `m4i_data_attribute`, and `""` for every other type                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| LAS-04 | The breadcrumb of an entity of a mapped type is its first parent's breadcrumb followed by that parent: `breadcrumbguid`, `breadcrumbname` and `breadcrumbtype` hold the GUIDs, names and type names in that order, from the top. The first parent is the first active entity in the parents' order above; an entity already in the chain ends it. Without a parent the three are empty. `parentguid` is the last GUID of the breadcrumb, and absent when it is empty. A type that is not mapped has no breadcrumb                                                                                                                                                                                                                                                                                                                                           |
| LAS-05 | For every relationship between two active entities of mapped types, each document lists the other: its GUID in the other's type's `<relation field>guid`, and its name at the same position in `<relation field>`, once. A type that is not mapped has no derived relations, and is in none                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| LAS-06 | A field also joins each of its datasets with each data entity of each of its data attributes, both ways, in `deriveddataset` and `deriveddataentity`, as LAS-05 lists a relation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| LAS-07 | These fields are present on every document and never filled: `businessruleid`, `classificationstext`, `deriveddataownerguid`, `deriveddatastewardguid`, `deriveddomainleadguid`, `deriveddatasetguids`, `deriveddatasetnames`, `derivedentityguids`, `derivedentitynames`, `entityname`; each holds the empty value of its kind (`0`, `[]` or none)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| LAS-08 | A change of an entity's `name`, `definition` or `email` shows on its document, and its new name in every breadcrumb and derived relation that names it                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| LAS-09 | A deleted entity's document goes, and it leaves every derived relation. A breadcrumb that went through it is the one LAS-04 gives without it, as are those below                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| LAS-10 | A change in the catalogue reaches the documents it affects without an operator's step                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| LAS-11 | `atlas-dev-quality` holds one document per data quality rule (`m4i_data_quality`) that has a score: `id` and `qualityqualifiedname` are the rule's qualified name, `guid` and `qualityguid` its GUID; `expression`, `dataqualityruledescription` (the rule's `ruleDescription`) and `dataqualityruledimension` (its `qualityDimension`) are the rule's; `fieldguid` and `fieldqualifiedname` are those of a field of the rule's `fields`; `dqscore` is the rule's latest score, between 0 and 1. `name`, `businessruleid` and `datadomainname` are present; what fills them is 14.5's to decide (DD-485)                                                                                                                                                                                                                                                    |
| LAS-12 | On `atlas-dev`, each of the five dimensions (accuracy, completeness, timeliness, validity, uniqueness) has `dqscoresum_<d>`, `dqscorecnt_<d>` and `dqscore_<d>`, and `qualityguid_<d>` lists rule GUIDs. A field adds, per dimension, each of its results' `dqscore` to the sum, 1 to the count, and the rule's GUID to the list. Each field then adds its sums and counts to each of its data attributes; then each data attribute and each field adds its sums and counts to every entity of its breadcrumb. Last, `dqscoresum_overall` and `dqscorecnt_overall` add up the five dimensions. Each `dqscore_*` is its sum over its count, and 0 when the count is 0                                                                                                                                                                                        |
| LAS-13 | `atlas-dev-gov-quality` holds one document per active entity and governance rule (`m4i_gov_data_quality`) for the entity's type: `id` and `qualifiedname` are `<entity GUID>--<rule GUID>`; `guid` is the rule's GUID, `qualityqualifiedname` its qualified name, `name` its name; `expression`, `dataqualitytype` (`ruleType`), `dataqualityruledescription` (`ruleDescription`), `dataqualityruledimension` (`qualityDimension`) and `noncompliant_message` (`nonCompliantMessage`) are the rule's; `dataqualityruletypename` is the entity's type and `entity_guid` its GUID; `result_id` is `"0"` and `business_rule_id` `"1"`; `compliant` is `"1"` when the entity meets the rule and `"0"` when not; `usedattributes` holds the first quoted name in the rule's expression. A rule is for the type its qualified name starts with (`m4i_dataset--…`) |

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389:

- `libs/m4i-flink-tasks/m4i_flink_tasks/model/app_search_document.py`, `gov_data_quality_document.py`: the
  document shapes (LAS-07, LAS-13).
- `libs/m4i-flink-tasks/.../synchronize_app_search/event_handlers/entity_created/entity_created.py`: the
  document, `sourcetype`, the relation fields, the blacklist and the breadcrumb (LAS-01..LAS-05).
- `.../attribute_changed/update_attributes.py`, `update_breadcrumbs.py`, `update_derived_entities.py`, and
  `.../entity_deleted/delete_breadcrumbs.py`, `delete_derived_entities.py`: the changes (LAS-08, LAS-09).
- `libs/m4i-flink-tasks/m4i_flink_tasks/operations/get_rules/get_rules.py`: the governance verdicts (LAS-13).
- `libs/m4i-atlas-core/m4i_atlas_core/entities/atlas/data_dictionary/*.py`: each type's `get_parents`, the
  parents' order (LAS-04).
- `backend/m4i-atlas-post-install/scripts/connect_datasets_with_entities.py`: the dataset to data entity join
  (LAS-06).
- `backend/m4i-atlas-post-install/scripts/propagate_quality.py`: the score roll-up (LAS-12).
- `backend/m4i-atlas-post-install/data/atlas-dev*.json`: the fixtures (DD-484).

## Differences from the legacy documents

The fixtures are a snapshot the legacy pipeline produced from the sample catalogue
(`data/atlas-sample/sample_data.zip`, 687 entities, all active).

**`atlas-dev` is a reference for values.** Recomputed from the catalogue, LAS-01 to LAS-07 and LAS-12 give the
snapshot back, except for these, where the documents follow the catalogue (DD-485):

| Field                              | Documents | Snapshot                                                                                       |
| ---------------------------------- | --------- | ---------------------------------------------------------------------------------------------- |
| `referenceablequalifiedname`       | 19        | every `m4i_generic_process` carries its GUID, the code's fallback                              |
| `referenceablequalifiedname`       | 1         | a governance rule under an older qualified name                                                |
| `name`                             | 1         | a governance rule under its title, where the catalogue has a qualified name                    |
| `definition`                       | 87        | 86 business entities without the definition they have; one governance rule with one it has not |
| `breadcrumb*`, `parentguid`        | 2         | a dataset with two parent datasets, under the second                                           |
| `derivedfield*`, `derivedprocess*` | 5         | datasets without 15 relations that their other ends list                                       |

**The result engines are a reference for shape only.** The legacy jobs wrote them as entities and rules changed,
and never again: of the 50 data quality rules, 42 have a document, whose expression or description differs from
the rule's in 15; of the 5,675 pairs of an active entity and a governance rule for its type, 1,628 have a
document, and 199 of those name attributes their own expression does not. Their fields, identities and links
hold (LAS-11, LAS-13); their values are not compared. Aurelius Atlas scores every rule and judges every pair.

Each difference becomes a deviation of the increment that derives the field. Against Apache Atlas, none: its API
is untouched.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__legacy_app_search_fixtures.py`, against the fixtures and the
  sample catalogue:
    - LAS-01, LAS-02, LAS-03 and LAS-07 on all 684 `atlas-dev` documents, with the differences above as the only
      exceptions;
    - LAS-12: the roll-up recomputed from the quality documents and the breadcrumbs gives every document's 23
      score fields;
    - LAS-11 and LAS-13: every result document's identity, links and rule fields.
- LAS-04 to LAS-06 and LAS-08 to LAS-10 need the store, and are 14.2's and 14.3's.
