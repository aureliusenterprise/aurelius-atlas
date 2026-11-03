# 6.3c1 Import transforms

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DV-127 to DV-129; relies on IMS-01 to IMS-06 (6.3b2)

An import's `transforms` option rewrites each entity read from the ZIP before it is written: a text value
lowercased or with a part replaced, a classification added or removed, an attribute set, cleared or extended,
an entity marked deleted. A typical use is renaming a cluster suffix in qualified names when copying a
catalogue from one environment to another. This first part of 6.3c ports them. Replication bookkeeping and the
export, import and admin audits follow in 6.3c2. The newer `transformers` framework and the Hive-specific
incremental export are not ported (DV-127, DV-128).

## Scope

The `transforms` option of `POST /api/atlas/admin/import` and `admin/importfile`. In `aurelius-atlas-core`,
`import_transforms` (`ImportTransforms`, the transformers, `shape`), applied by `ZipSource` and set up by
`ImportService`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ITR-01 | The option is JSON of entity type name, then attribute name or `*`, then a list of transformer specifications; JSON that is no map gives no transforms, and an unknown or empty specification is passed over. Each entity read, and each it owns, of a type named goes through the `*` transformers, then each attribute's in order on the value it has, when it has the attribute                                                                                                                                                                                                              |
| ITR-02 | A specification is a name and its parameters apart by `:` (or a backslash), empty parameters dropped, as `StringUtils.split` splits                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ITR-03 | `lowercase`, `uppercase` and `replace:<find>:<with>` change a text value; `add:<name>=<value>` sets an attribute without a value, appends to a list (`list:<item>` is an item) or sets the text over another value; `clearAttrValue:<a>,<b>` nulls attributes; `setDeleted` marks the entity `DELETED`; `removeClassification:<name>` removes a classification; `addClassification:<name>[:topLevel]` adds one the entity lacks, with `topLevel` only to an entity an export item names by GUID, or by type and unique values. A transformer given what it does not change returns it unchanged |
| ITR-04 | Before the import, each `addClassification`'s type is created when the catalogue lacks it, and each named type's transforms are given to its sub types: a sub type without transforms takes its parent's, one with them gains the parent's for the attributes both name                                                                                                                                                                                                                                                                                                                         |
| ITR-05 | The transforms are set up before the types are merged, and apply to every entity the import writes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../impexp/ImportTransforms.java`, `ImportTransformer.java`, `ImportTransformsShaper.java`
- `repository/.../impexp/ImportService.java`: `setImportTransform`
- `repository/.../impexp/ZipSource.java`: `getEntityWithExtInfo`

## Deviations

- **DV-127:** the `transformers` option (`BaseEntityHandler`, `AtlasEntityTransformer` and the Hive and HDFS
  handlers) is not applied.
- **DV-128:** an incremental export of `hive_db` or `hive_table` follows the generic incremental fetch; Atlas's
  Hive-specific extraction (`IncrementalExportEntityProvider`) and the table replication on import
  (`TableReplicationRequestProcessor`) are not ported.

- **DV-129:** a `removeClassification` of an entity without classifications leaves it as it is; Atlas fails
  on the null list.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__import_transforms.py` — ITR-01 to ITR-05: each transformer, the
  specification's parsing, sub types and `topLevel`, and an import written transformed.
- `uv run aurelius-atlas-trace check`.
