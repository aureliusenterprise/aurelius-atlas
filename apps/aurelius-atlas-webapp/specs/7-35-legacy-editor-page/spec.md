# 7.35 The legacy editor page

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-816 to DD-819 (here); supersedes 7.7a's drawer (EDT-01, DD-166's family for the editor) and
  EDT-03's field set; relies on 7.7a to 7.7c and 7.9 (EDT-01 to EDT-28), 12.7 (EDT-23/24's verdict lines),
  16.5c (VDE-01 to VDE-08), 18.2 (HCA-06), 18.3 (PME-10), 18.5 (DCP-05)
- **Legacy source:** `aureliusenterprise/aurelius` at `b057389828c10497dd52d9efd4c16547c282c005`,
  `apps/atlas/src/app/search/components/editor/` (cited below as `editor/`), and
  `apps/atlas/src/app/search/{create,edit}-entity/`

The editor today is a drawer beside the page, and its form lists every attribute of the type and its
supertypes, ordered by label. The legacy editor was a page of its own, with one hand-written form per type: a
few fields, in a fixed order, each with its governance verdicts beside it. This increment brings that back.
The editor becomes a full page again; each of the ten types the legacy edited with a form of its own gets its
legacy fields in their legacy order; and the verdicts sit next to their field, refreshed while the user types.

## Scope

- `aurelius-atlas-webapp`:
    - the editor as one routed page, `search/editor`, creating without a `guid` query parameter and editing
      with one, replacing the `drawer` outlet's `edit/:guid` and create routes;
    - the History tab beside the form: the entity's audit events from the server's entity audit answer;
    - one form definition per type (below), replacing EDT-03's every-attribute field set for those types;
    - the verdict column beside each field.
- The validate-entity service answering under tenancy, which the verdicts need on a tenancy stack: a separate
  increment (12.7b), see [the plan](./plan.md).

Not delivered:

- A form for the types the legacy had no form for: they keep today's generic form (EDT-03), see EDP-13.

## Semantics

### The page

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDP-01 | The editor is one page of its own in the main outlet, `search/editor`: without a `guid` query parameter it creates, with `?guid=<guid>` it edits that entity. It takes the page's full content width in a centered container, as the legacy's `<div class="container">` did; no drawer and no backdrop. The legacy had two routes, `create-entity` and `edit-entity`, around the same editor (`create-entity.component.html`, `edit-entity.component.html`; DD-816) |
| EDP-02 | The page's title is "Create new entity" when creating and "Edit entity" when editing (`search.createEntity.newEntity`, `search.editEntity.editEntity`), a level-3 title above the form                                                                                                                                                                                                                                                                              |
| EDP-03 | The details pencil and the "create" action navigate to the page; Save, Cancel and Delete return to where the user came from (the details screen of the entity, or the search for a create), as the drawer's close does today                                                                                                                                                                                                                                        |
| EDP-04 | When creating, the type select comes first and stays until the entity is saved; when editing there is none (`editor.component.html`, `editTypeAllowed$`)                                                                                                                                                                                                                                                                                                            |

### The fields

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDP-05 | Each of the ten types below shows exactly the fields its table lists, in that order, and no other field. The label is the legacy dictionary's key (`search.components.editor.<form>.<field>`); the placeholder its `…Placeholder` key where the legacy had one                                                                                                                                  |
| EDP-06 | `typeAlias` is never shown: every legacy form carries it under `*ngIf="false"` (`editor/*/…-editor.component.html`). A value already stored is kept on save                                                                                                                                                                                                                                     |
| EDP-07 | A field's label sits above it. Below the label, on a desktop-wide page, the control takes two thirds of the row and the field's verdicts the third beside it; narrower, the verdicts sit under the control (`entity-editor.component.scss`'s `.grid`, `2fr 1fr`, `gap: 2rem`)                                                                                                                   |
| EDP-08 | `name` is required on every form; `email` is required and must be an email address on the person form; `expression` is required on the rule form. A save with a missing required field is refused in the browser: the field turns red with its `…Required` message, and the red notice `search.components.editor.<form>.notification` shows at the foot of the form                             |
| EDP-09 | A `name` or `definition` holding `’` (U+2019) shows the warning `…nameWarning` or `…definitionWarning` under it; the save is not refused                                                                                                                                                                                                                                                        |
| EDP-10 | A single-pick field holds at most one related entity (18.2, HCA-06). Of the two parents of a data entity (`dataDomain`, `parentEntity`), a field (`datasets`, `parentField`) and a dataset (`collections`, `parentDataset`), the picker of one is disabled while the other holds a pick (18.3 PME-10, 18.5 DCP-05). This keeps today's rule; the legacy cleared the other pick instead (DD-818) |
| EDP-11 | The classifications field is today's tag box (7.21a), shown only where the legacy form had it: data entity, data attribute, data domain                                                                                                                                                                                                                                                         |
| EDP-12 | The governance rule form serves `m4i_gov_data_quality`; `qualityDimension` and `ruleType` are free-text inputs, as in the legacy. `m4i_data_quality` keeps 7.27's quality mode, whose closed check vocabulary (DQ-01, DV-146) the legacy's free-text form would bypass; the legacy served both types with one form (`editors-by-type.ts`, DD-819)                                               |
| EDP-13 | A type without a table below keeps today's generic form (EDT-03) on the page. The create type select lists the ten types first, then the others; the legacy listed every `m4i_referenceable` subtype but `m4i_referenceable` and `m4i_source`, and showed an empty form for the ones it had no form for (DD-819)                                                                                |

### The history

| Id     | Rule                                                                                                                                                                                                                                                                       |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDP-19 | When editing, two tabs head the page: "Entity", the form, and "History" (`search.components.editor.entityPlaceholder`, `…historyPlaceholder`). The page opens on Entity. When creating there is no History tab: an entity not yet saved has none (`editor.component.html`) |
| EDP-20 | History lists the entity's audit events from `GET /api/atlas/v2/entity/{guid}/audit`, newest first (`sortOrder=DESC`), read 100 at a time until a page comes back short, all of them shown (`entity-audit.service.ts`, `retrieveAuditsPaged`)                              |
| EDP-21 | Each event is one entry: the action in bold, translated by its dictionary key (`ENTITY_CREATE` "Entity created", `ENTITY_UPDATE` "Entity updated", …), and under it, small, the user and the time as `yyyy-MM-dd HH:mm:ss` in the browser's time zone, joined by `·`       |
| EDP-22 | The history is read each time the History tab opens; a save leaves the page for the entity's details (EDP-03), so no list goes stale. A failed read shows an empty list; the form is unaffected. With tenancy on the server answers the tenant's audit index alone (15.2)  |
| EDP-23 | Save and Delete show under the Entity tab only, as in the legacy (`*ngIf="currentTab === 'entity'"`)                                                                                                                                                                       |

### The verdicts

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDP-14 | The form validates the draft on opening and again 200 ms after the user stops changing it (EDT-23, unchanged)                                                                                                                                                                                                                                                          |
| EDP-15 | Beside each field, one line per verdict whose attribute is the field's attribute: a yellow warning triangle and the message when the rule fails, a green check and the message when it passes (`gov-quality-display.component.html`). The rules `<type>--<attribute>--source` and `--target`, which check a relationship's ends, show beside that relationship's field |
| EDP-16 | The `definition` box (the rule description on the rule form) turns yellow while a rule on it fails (`[class.is-warning]="rules?.definition?.isNonCompliant"`)                                                                                                                                                                                                          |
| EDP-17 | A verdict on an attribute the form doesn't show, such as `m4i_field--qualifiedName` or `m4i_data_attribute--attributeType`, shows in no field; the legacy showed none of them either                                                                                                                                                                                   |
| EDP-18 | While the validator gives no answer, or a refusal, the verdict column is empty and the form stays usable (EDT-23's quiet swallow)                                                                                                                                                                                                                                      |

### The forms

Each table is one type's form, top to bottom. **Attribute** is the attribute the field writes: plain for an
entity attribute, `rel:` for a relationship attribute. **Pick** names the type the picker searches, and
whether it holds one entity or several. **Rules (sample)** names the governance rules the shipped sample
(`data/atlas-sample/sample_data.zip`) defines on that attribute, by their qualified name without the type
prefix; `±` marks the `--source` and `--target` pair. The rules a deployment holds are its own: these are what
the demo shows.

#### Data entity (`m4i_data_entity`, `editor/entity/`)

| #   | Label (en / nl)                           | Attribute           | Input          | Pick                       | Rules (sample)                              |
| --- | ----------------------------------------- | ------------------- | -------------- | -------------------------- | ------------------------------------------- |
| 1   | Name\* / Naam\*                           | `name`              | text, required |                            | `name`                                      |
| 2   | Definition / Definitie                    | `definition`        | text area      |                            | `definition`                                |
| 3   | Classifications / Classificaties          | classifications     | tag box        |                            |                                             |
| 4   | Data domain / Data Domein                 | `rel:dataDomain`    | picker         | `m4i_data_domain`, one     | `dataDomain` ±: a domain or a parent entity |
| 5   | Parent entity / Bovenliggende Entiteit    | `rel:parentEntity`  | picker         | `m4i_data_entity`, one     |                                             |
| 6   | Child entities / Onderliggende Entiteiten | `rel:childEntity`   | picker         | `m4i_data_entity`, many    |                                             |
| 7   | Data attributes / Data Attributen         | `rel:attributes`    | picker         | `m4i_data_attribute`, many | `attributes`: attributes or child entities  |
| 8   | Data owners / Data Eigenaren              | `rel:businessOwner` | picker         | `m4i_person`, many         | `businessOwner` ±                           |
| 9   | Data stewards / Data Stewards             | `rel:steward`       | picker         | `m4i_person`, many         | `steward` ±                                 |

#### Data attribute (`m4i_data_attribute`, `editor/attribute/`)

| #   | Label (en / nl)                  | Attribute           | Input          | Pick                   | Rules (sample)    |
| --- | -------------------------------- | ------------------- | -------------- | ---------------------- | ----------------- |
| 1   | Name\* / Naam\*                  | `name`              | text, required |                        | `name`            |
| 2   | Definition / Definitie           | `definition`        | text area      |                        | `definition`      |
| 3   | Classifications / Classificaties | classifications     | tag box        |                        |                   |
| 4   | Data entity / Data Entiteit      | `rel:dataEntity`    | picker         | `m4i_data_entity`, one | `dataEntity` ±    |
| 5   | Fields / Datavelden              | `rel:fields`        | picker         | `m4i_field`, many      |                   |
| 6   | Data owners / Data Eigenaren     | `rel:businessOwner` | picker         | `m4i_person`, many     | `businessOwner` ± |
| 7   | Data stewards / Data Stewards    | `rel:steward`       | picker         | `m4i_person`, many     | `steward` ±       |

Not shown: `attributeType`, which the sample's rule `attributeType` measures (EDP-17).

#### Dataset (`m4i_dataset`, `editor/dataset/`)

| #   | Label (en / nl)                         | Attribute                 | Input          | Pick                        | Rules (sample)                                    |
| --- | --------------------------------------- | ------------------------- | -------------- | --------------------------- | ------------------------------------------------- |
| 1   | Name\* / Naam\*                         | `name`                    | text, required |                             | `name`                                            |
| 2   | Definition / Definitie                  | `definition`              | text area      |                             |                                                   |
| 3   | Collection / Collectie                  | `rel:collections`         | picker         | `m4i_collection`, one       | `collections` ±: a collection or a parent dataset |
| 4   | Parent dataset / Bovenliggende Dataset  | `rel:parentDataset`       | picker         | `m4i_dataset`, one          | (`parentDataset`, inactive)                       |
| 5   | Child datasets / Onderliggende Datasets | `rel:childDataset`        | picker         | `m4i_dataset`, many         | (`childDataset`, inactive)                        |
| 6   | Fields / Datavelden                     | `rel:fields`              | picker         | `m4i_field`, many           | `fields` ±: fields or child datasets              |
| 7   | Producers / Producenten                 | `rel:outputFromProcesses` | picker         | `m4i_generic_process`, many |                                                   |
| 8   | Consumers / Afnemers                    | `rel:inputToProcesses`    | picker         | `m4i_generic_process`, many |                                                   |

#### Field (`m4i_field`, `editor/field/`)

| #   | Label (en / nl)                         | Attribute         | Input          | Pick                      | Rules (sample)                            |
| --- | --------------------------------------- | ----------------- | -------------- | ------------------------- | ----------------------------------------- |
| 1   | Name\* / Naam\*                         | `name`            | text, required |                           | `name`                                    |
| 2   | Definition / Definitie                  | `definition`      | text area      |                           |                                           |
| 3   | Dataset / Dataset                       | `rel:datasets`    | picker         | `m4i_dataset`, one        | `datasets` ±: a dataset or a parent field |
| 4   | Parent field / Bovenliggende Dataveld   | `rel:parentField` | picker         | `m4i_field`, one          |                                           |
| 5   | Child fields / Onderliggende Datavelden | `rel:childField`  | picker         | `m4i_field`, many         |                                           |
| 6   | Data attribute / Data Attribuut         | `rel:attributes`  | picker         | `m4i_data_attribute`, one | `attributes` ± (relationship ends only)   |

Not shown: `qualifiedName` (`qualifiedName`, a uniqueness rule), `hasContent` and `optionalField` (both inactive),
`dataQuality` (`dataQuality--source`) (EDP-17).

#### Collection (`m4i_collection`, `editor/collection/`)

| #   | Label (en / nl)        | Attribute      | Input          | Pick                | Rules (sample) |
| --- | ---------------------- | -------------- | -------------- | ------------------- | -------------- |
| 1   | Name\* / Naam\*        | `name`         | text, required |                     | `name`         |
| 2   | Definition / Definitie | `definition`   | text area      |                     |                |
| 3   | System / Systeem       | `rel:systems`  | picker         | `m4i_system`, one   | `systems` ±    |
| 4   | Datasets / Datasets    | `rel:datasets` | picker         | `m4i_dataset`, many | `datasets` ±   |

#### Data domain (`m4i_data_domain`, `editor/domain/`)

| #   | Label (en / nl)                          | Attribute        | Input          | Pick                    | Rules (sample) |
| --- | ---------------------------------------- | ---------------- | -------------- | ----------------------- | -------------- |
| 1   | Name\* / Naam\*                          | `name`           | text, required |                         | `name`         |
| 2   | Definition / Definitie                   | `definition`     | text area      |                         | `definition`   |
| 3   | Classifications / Classificaties         | classifications  | tag box        |                         |                |
| 4   | Data entities / Data Entiteiten          | `rel:dataEntity` | picker         | `m4i_data_entity`, many | `dataEntity` ± |
| 5   | Domain leads / Domein Verantwoordelijken | `rel:domainLead` | picker         | `m4i_person`, many      | `domainLead` ± |

#### System (`m4i_system`, `editor/system/`)

| #   | Label (en / nl)                       | Attribute          | Input          | Pick                   | Rules (sample)                                |
| --- | ------------------------------------- | ------------------ | -------------- | ---------------------- | --------------------------------------------- |
| 1   | Name\* / Naam\*                       | `name`             | text, required |                        | `name`                                        |
| 2   | Definition / Definitie                | `definition`       | text area      |                        |                                               |
| 3   | Parent system / Bovenliggende Systeem | `rel:parentSystem` | picker         | `m4i_system`, one      |                                               |
| 4   | Subsystems / Subsystemen              | `rel:childSystem`  | picker         | `m4i_system`, many     |                                               |
| 5   | Collections / Collecties              | `rel:collections`  | picker         | `m4i_collection`, many | `collections` ±: collections or child systems |

Not shown: `kibanaSpace` (`kibanaSpace` ±) (EDP-17).

#### Process (`m4i_generic_process`, `editor/process/`)

| #   | Label (en / nl)        | Attribute     | Input          | Pick                | Rules (sample) |
| --- | ---------------------- | ------------- | -------------- | ------------------- | -------------- |
| 1   | Name\* / Naam\*        | `name`        | text, required |                     |                |
| 2   | Definition / Definitie | `definition`  | text area      |                     |                |
| 3   | System / Systeem       | `rel:system`  | picker         | `m4i_system`, one   |                |
| 4   | Inputs / Invoer        | `rel:inputs`  | picker         | `m4i_dataset`, many |                |
| 5   | Outputs / Uitvoer      | `rel:outputs` | picker         | `m4i_dataset`, many |                |

The legacy process form has no `typeAlias` at all; the sample defines no rule for processes.

#### Person (`m4i_person`, `editor/person/`)

| #   | Label (en / nl)                                   | Attribute                    | Input           | Pick                       | Rules (sample) |
| --- | ------------------------------------------------- | ---------------------------- | --------------- | -------------------------- | -------------- |
| 1   | Name\* / Naam\*                                   | `name`                       | text, required  |                            | `name`         |
| 2   | Email\* / Email\*                                 | `email`                      | email, required |                            | `email`        |
| 3   | Domain lead / Domein Verantwoordelijke            | `rel:domainLead`             | picker          | `m4i_data_domain`, many    |                |
| 4   | Data owner entities / Data Eigenaar Entiteiten    | `rel:businessOwnerEntity`    | picker          | `m4i_data_entity`, many    |                |
| 5   | Data owner attributes / Data Eigenaar Attributen  | `rel:businessOwnerAttribute` | picker          | `m4i_data_attribute`, many |                |
| 6   | Data steward entities / Data Steward Entiteiten   | `rel:stewardEntity`          | picker          | `m4i_data_entity`, many    |                |
| 7   | Data steward attributes / Data Steward Attributen | `rel:stewardAttribute`       | picker          | `m4i_data_attribute`, many |                |

The person form has no definition.

#### Governance rule (`m4i_gov_data_quality`, `editor/gov-quality/`)

| #   | Label (en / nl)                             | Attribute             | Input               | Rules (sample) |
| --- | ------------------------------------------- | --------------------- | ------------------- | -------------- |
| 1   | Name\* / Naam\*                             | `name`                | text, required      |                |
| 2   | Rule description / Regelbeschrijving        | `ruleDescription`     | text area           |                |
| 3   | Dimension / Dimensie                        | `qualityDimension`    | text                |                |
| 4   | Rule type / Regeltype                       | `ruleType`            | text                |                |
| 5   | Compliant message / Conformbericht          | `compliantMessage`    | text area           |                |
| 6   | Non-compliant message / Niet-conformbericht | `nonCompliantMessage` | text area           |                |
| 7   | Expression\* / Expressie\*                  | `expression`          | text area, required |                |

The rule form has no pickers. `expression` is a plain text area, as in the legacy; the validate service reads
the expression forms 14.6 lists (ASG-02).

## Java origin

None: the editor is the legacy Aurelius webapp's, not Apache Atlas's.

## Deviations

From the legacy, each with its decision: one page for create and edit, where the legacy had two routes (EDP-01,
DD-816); the parents' mutual exclusion disables instead of clearing (EDP-10, DD-818); the generic form for the
types the legacy had none for, and 7.27's quality mode for `m4i_data_quality` (EDP-12, EDP-13, DD-819). None from
Apache Atlas.

## Acceptance

- The webapp's unit tests: EDP-01 to EDP-23, one form definition test per table naming each field in order.
- The webapp's e2e: create a data entity on the page, the name rule's verdict turning from warning to check
  while typing, and the save returning to the details screen; edit it again and find "Entity created" and
  "Entity updated" in its History.
- By hand on the standalone stack (with 12.7b): each of the ten forms against the tables above.
