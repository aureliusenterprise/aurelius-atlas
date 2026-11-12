# 14.6 The App Search API: `/gov_quality`

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-533 to DD-537 (here), DV-160; relies on ADR 060, 14.1 (LAS-13), 14.2 (ASD-01), 14.3
  (ASU-06), 14.4 (ASE-01 to ASE-11), 14.5 (DD-531) and 12.6 (GQ-01 to GQ-07, amended here)

## Scope

The original webapp reads the governance verdicts from the `atlas-dev-gov-quality` engine, which its reverse
proxy reaches at `<base>/gov_quality`: the governance cards and the list of what an entity misses on its details
page, the editor's verdicts, and the entities that meet or miss a rule on the rule's page. 14.4 and 14.5 answer
that engine 404. This increment judges the governance rules for every entity of their type and answers the
engine from the verdicts. In `aurelius-atlas-quality`, a stored rule's legacy expression read in the two forms
the rule corpus uses (`atlas.py`). In `aurelius-atlas-core`:

- the verdict of each rule for each entity of its type, judged again when the entity's document or the type's
  rules change (`app_search_governance.py`);
- the marks of an entity judged, dropped by a write that changes what its verdicts read, and the verdicts'
  mapping (`app_search_document.py`);
- the engine as its documents and fields (`app_search_engine.py`);
- the verdicts' index, and the listing of the entities to judge (`entity_documents.py`).

In `aurelius-atlas-server`, `POST /api/as/v1/engines/atlas-dev-gov-quality/search` and `.../search.json`
(`routes/app_search.py`), and the governance round in the App Search worker (`app_search.py`).

Not delivered, with the increment that will:

| Not delivered                                                                     | Lands with |
| --------------------------------------------------------------------------------- | ---------- |
| A deployment's route from the original webapp's `gov_quality` to this endpoint    | none       |
| The rules of another expression, such as the sample's 46 `conditional_value(...)` | none       |
| A verdict over a draft: 12.7's `validate-entity` answers the editor's banner      | 12.7       |

The first row is the operator's, as 14.4's `elastic`; the server's README shows the route. The rules of the second
row stay unread, as 12.7 records them; the 7.27 editor writes them again in the vocabulary.

## Semantics

A governance rule is an `m4i_gov_data_quality` entity that is active, whose `active` attribute is not `false`,
and that reads as a rule (ASG-02). It is for the entity type its `qualifiedName` names before the first `--`,
as `m4i_dataset--name` is for `m4i_dataset` (LAS-13): that type, not its subtypes. The entities it judges are
the active entities of that type with an App Search document (ASD-01).

The documents of `atlas-dev-gov-quality`, one per rule and entity it judges (LAS-13, DD-534, DV-160):

| Field                           | Value                                                                  |
| ------------------------------- | ---------------------------------------------------------------------- |
| `id`, `qualifiedname`           | `<entity GUID>--<rule GUID>`                                           |
| `guid`                          | the rule's GUID                                                        |
| `qualityqualifiedname`          | the rule's `qualifiedName`                                             |
| `name`                          | the rule's `name`, else its `qualifiedName`                            |
| `expression`                    | the rule's `expression`, else empty                                    |
| `dataqualitytype`               | the rule's `ruleType`, else empty                                      |
| `dataqualityruledescription`    | the rule's `ruleDescription`, else empty                               |
| `dataqualityruledimension`      | the rule's `qualityDimension`, else its kind's dimension in lower case |
| `noncompliant_message`          | the rule's own message for a miss, else its kind's reason (GQ-06)      |
| `usedattributes`                | the rule's attribute, the one its check reads first                    |
| `dataqualityruletypename`       | the entity's type                                                      |
| `entity_guid`                   | the entity's GUID                                                      |
| `compliant`                     | `"1"` when the entity meets the rule, `"0"` when not                   |
| `result_id`, `business_rule_id` | `"0"` and `"1"`                                                        |
| `result`, `doc_guid`            | none: the legacy engine's schema has them and no document filled them  |

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ASG-01 | `POST /api/as/v1/engines/atlas-dev-gov-quality/search` and `.../search.json` answer as `atlas-dev`'s do (ASE-01, ASE-02): the user needs `ENTITY_READ`. Another engine name answers 404                                                                                                                                                                                                                      |
| ASG-02 | A rule without `dqcheckkind` reads from its `expression` when it is one part or several joined by `\|`, each `completeness('<name>')` or each `length('<name>', 1)`: `ATTRIBUTE_PRESENT` or `ATTRIBUTE_NOT_EMPTY`, the first part's name its attribute and the others' its `anyOf`. The expression is matched as text, never evaluated; any other one leaves the rule unread, as GQ-07 does (DD-533, DV-146) |
| ASG-03 | `atlas-dev-gov-quality` holds one document per rule and entity it judges, with the fields of the table above. A rule that is unread, inactive or deleted, or is for a type without such an entity, has none                                                                                                                                                                                                  |
| ASG-04 | The verdict is the rule's check (GQ-04 to GQ-06) over the entity as its read answers it: a name its type has as a relationship attribute reads the other ends of the entity's active relationships under it, a list or one end; any other name reads its attribute (DD-536)                                                                                                                                  |
| ASG-05 | `atlas-dev-gov-quality` answers its requests as `atlas-dev` does (ASE-04 to ASE-11), over its own fields, with `meta.engine.name` and `_meta.engine` its name. Its fields are all text, as the legacy schema's                                                                                                                                                                                               |
| ASG-06 | Each round of the App Search worker, after the documents and the quality round, judges again each entity whose attributes or relationships changed, or whose type's rules did, since it was judged, and writes its verdicts in place of those it had. An entity no longer judged loses its verdicts, a purged entity among them (DD-535)                                                                     |
| ASG-07 | No answer of Apache Atlas's API changes                                                                                                                                                                                                                                                                                                                                                                      |

ASG-02 amends GQ-07: 12.7's `validate-entity` and the 7.29 governance box read these rules too, and list in
`unreadRules` only the rules of another expression.

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389:

- `libs/m4i-flink-tasks/m4i_flink_tasks/operations/get_rules/get_rules.py`: a verdict per rule for each entity
  of the rule's type, its document's fields, `usedattributes` the first quoted name (ASG-03, ASG-04).
- `libs/m4i-data-management/.../core/quality/rules/completeness/` and `.../rules/length/`: the two forms, not
  null and at least one element or character (ASG-02, 12.6's GQ-04).
- `backend/m4i-atlas-post-install/m4i_atlas_post_install/app_search_engine_setup.py`: the engine's schema, every
  field text (ASG-05).
- `libs/atlas/api/src/lib/elastic/engines/gov-quality-search.service.ts` and the webapp's requests:
  `apps/atlas/src/app/search/details/components/governance-quality-cards/`, `.../cards/components/
governance-quality-list/`, `.../editor/services/editor-gov-quality-search.service.ts` (filters on
  `entity_guid` and `compliant`, facets on `dataqualityruledimension`, `dataqualitytype` and `guid`, sorts by
  `name`, `dataqualityruledimension`, `compliant` and `dataqualitytype`), and `.../details/gov-quality/
{compliant,non-compliant}-cards/` (filters on the rule's `guid` and `compliant`, `entity_guid` read, pages of
  1,000) (ASG-05).
- `k8s/charts/reverse-proxy/conf.d/search-api.yaml`: `<base>/gov_quality` reaching `atlas-dev-gov-quality`
  (ASG-01).

## Deviations

None against Apache Atlas (ASG-07). Against the legacy engine,
[DV-160](../../../../docs/architecture/conversion/deviations.md): a verdict for every rule of the two forms or
of the vocabulary and every entity of its type, kept current, where the legacy job judged the rules of its
definition files as an entity was published and never again; the rules of another expression judge nothing.
Against 12.6, ASG-02 amends GQ-07 (DD-533) within DV-146's meaning: a closed set of forms read as data, as the
four legacy pairs of the quality rules are.

## Acceptance

- `libs/python/aurelius-atlas-quality/tests/test__atlas.py`: each form, the `|` pair, a mixed pair, another
  expression and a vocabulary rule beside an expression (ASG-02).
- `libs/python/aurelius-atlas-core/tests/test__app_search_governance.py`, on the fake client:
    - a verdict's fields from its rule and entity; both verdicts of each kind; a relationship attribute, a
      deleted relationship and an attribute; no verdict for an unread, inactive or deleted rule, an entity of
      a subtype, a deleted entity or one without a document (ASG-03, ASG-04);
    - a second round writes nothing; a changed attribute, a new relationship, a changed, deactivated or deleted
      rule, a deleted and a purged entity show after a round (ASG-06);
    - the sample catalogue imported and indexed: 47 rules read, 48 unread; 2,602 verdicts, 1,782 met and 820
      missed; every one of the 1,612 legacy documents of a read rule with the verdict it holds, and none of the
      16 of the rule whose expression is now `conditional_value(...)` (LAS-13, DV-160).
- `libs/python/aurelius-atlas-core/tests/test__app_search_engine.py`: the engine's fields, and the details
  cards', the list's and the rule page's requests (ASG-05).
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_app_search_engine.py`: both paths of the engine
  (ASG-01); `test__aurelius_atlas_server_app_search.py`: a worker round runs the governance round last (ASG-06).
- `libs/python/aurelius-atlas-core/e2e/test__app_search_governance_e2e.py`, on the dev Elasticsearch: a rule over
  a dataset written by the writer, a round, the details cards' and the rule page's requests, a relationship
  added and a round (ASG-03 to ASG-06).
