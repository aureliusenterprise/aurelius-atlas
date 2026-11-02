# 5.3c Business metadata import

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DV-119; relies on DD-302, DV-104 (the file reading of 5.2d), DV-117

The last part of 5.3 imports business attribute values from a CSV or Excel file. Each row names an entity by type
and unique value, a business attribute as `<business metadata>.<attribute>`, and a value. A template gives the
header line. The file is read as the glossary import reads it (5.2d). The values are applied through 5.3b's
add-or-update with overwrite, so they are validated, audited and checked as there.

## Scope

| Endpoint                                                    | Atlas method         |
| ----------------------------------------------------------- | -------------------- |
| `GET /api/atlas/v2/entity/businessmetadata/import/template` | `produceTemplate`    |
| `POST /api/atlas/v2/entity/businessmetadata/import`         | `importBMAttributes` |

In `aurelius-atlas-core`, `EntityBusinessMetadata.bulk_create_or_update_business_attributes` and
`business_metadata_headers`. In `aurelius-atlas-model`, `FILE_NAME_NOT_FOUND`. In `aurelius-atlas-server`,
the two routes in `routes/entity`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BMI-01 | The template is the line `EntityType,EntityUniqueAttributeValue,BusinessAttributeName,BusinessAttributeValue,EntityUniqueAttributeName[optional]`, an `application/octet-stream` download named `template_business_metadata`                                                                                                                                                                                                                                                                                                                 |
| BMI-02 | The import takes the form's `file`; a blank file name is `FILE_NAME_NOT_FOUND` (404), and the file is read as GIM-01 reads it. Each row below the header, numbered from 2, fails with a reason when it misses a type, unique value, business attribute or value (`Line #<n>: missing fields. [<cells>]`), names no entity type, names an attribute the type does not have or one that is not unique (the fifth cell, else `qualifiedName`), names no entity of exactly that type with that value, or names no business attribute of the type |
| BMI-03 | A value of an array attribute is split at `\|`. Each element is parsed by the element type: `int`, `long`, `short` and `date` as whole numbers in range, `float` and `double` as Java parses them, `boolean` as `true` in any case, an enum as one of its values; any other as text. An element that fails is left out and reported with Atlas's text (`Provided value <v> is Integer of Long type at line #<n-1>`, and the like). A value of any other attribute is the cell's text                                                         |
| BMI-04 | Each entity named is given its stored business attributes with the rows' values set, and overwritten with them (BMD-04). The response lists the rows that failed, then each entity that failed, its GUID and its business attributes as Java's map text (`{bm={attr=value}}`), with the error's message; it lists each entity that succeeded the same way with `SUCCESS`                                                                                                                                                                     |
| BMI-05 | An entity's overwrite is checked as BMD-04's (AUZ-17); a refusal is that entity's failure, not the import's                                                                                                                                                                                                                                                                                                                                                                                                                                  |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: `produceTemplate`, `importBMAttributes`
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `bulkCreateOrUpdateBusinessAttributes`,
  `getBusinessMetadataDefList`, `assignMultipleValues`
- `repository/.../store/graph/v2/AtlasGraphUtilsV2.java`: `assignEnumValues`, the number and boolean parsers
- `repository/.../util/FileUtils.java`: `getBusinessMetadataHeaders`, the column indexes
- `intg/.../bulkimport/BulkImportResponse.java`: `ImportInfo`

## Deviations

- **DV-119:** the entities are applied, and listed, in the order the file first names them, where Atlas's map
  gives hash order. An import without a file part is `FILE_NAME_NOT_FOUND`, where Atlas fails on the missing
  part. Each entity's business attributes are listed in its type's order (DV-117).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_business_metadata.py` — BMI-01 to BMI-05 on the in-memory
  documents.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_business_metadata.py` — the template and the
  upload, with a reader refused.
- `apps/aurelius-atlas-server/scenarios/entity/entity-business-metadata-import.scenario.yaml` — the parity
  scenario.
- `uv run aurelius-atlas-trace check`.
