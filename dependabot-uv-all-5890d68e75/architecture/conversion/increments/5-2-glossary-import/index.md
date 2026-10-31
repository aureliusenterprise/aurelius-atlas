# 5.2d Glossary import

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-249, DV-104; relies on DD-246

The last part of increment 5.2: glossary terms imported from a CSV or Excel file, and the template of its columns. Each row names a glossary, created when there is none, a term of it with its attributes, and the terms it relates to. The rows are read twice: first every term is created, then the relations are written, so a row may relate to a term of a later row.

## Scope

| Endpoint | Answers |
| --- | --- |
| `GET /api/atlas/v2/glossary/import/template` | the template's header line, as a download |
| `POST /api/atlas/v2/glossary/import` | `BulkImportResponse`, from the form's `file` |

In `aurelius-atlas-core`, `file_utils` (`FileUtils`), the import of `GlossaryTermUtils` and `GlossaryService`; in `aurelius-atlas-model`, `bulk_import` (`BulkImportResponse`, `ImportInfo`) and the error codes.

## Semantics

| Id | Rule |
| --- | --- |
| GIM-01 | A file is read by its name's extension, in any case: `csv` as text, its rows of more than one value; `xls` and `xlsx` from the first sheet, each row up to its last cell, values trimmed, empty rows left out. The first row is the header. Another extension, or a blank name, fails with `INVALID_FILE_TYPE`; a file that cannot be read with `NOT_VALID_FILE` (`CSV`, or `XLS` for both Excel kinds); one without rows below its header with `NO_DATA_FOUND` |
| GIM-02 | The answer lists the rows that failed and the terms created, each with its glossary's and term's names, status and remarks; an empty list is left out, and so is the row number |
| GIM-03 | The first pass makes a term of each row: a blank glossary name or term name fails the row, the glossary is found by qualified name or created with the name, unless the name is invalid; examples are joined by `\\|`, additional attributes are `key:value` pairs joined by `\\|`. Each term is then created as `createTerm` does, a failure reported with its message; the term's header is a success's remarks. None created fails the import with `GLOSSARY_IMPORT_FAILED` |
| GIM-04 | The second pass reads the thirteen relation columns, in the template's order, as `glossary:term` pairs joined by `\\|`, each the qualified name of an existing term; a pair of another form, the term itself or a term there is not fails the row with its message. A term with relations is updated as `updateTerm` does, without the check for a term listed twice, a failure reported |
| GIM-05 | A term that an earlier row relates to keeps the relations it has: they are added to its row's before the update |
| GIM-06 | The template is the columns `GlossaryName` to `PreferredTerms` each but the last followed by a comma and a space |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/GlossaryREST.java`: `produceTemplate`, `importGlossaryData`
- `repository/.../glossary/GlossaryService.java`: `importGlossaryData`, `createGlossaryTerms`, `updateGlossaryTermsRelation`, `getGlossaryName`, `checkForSuccessImports`
- `repository/.../glossary/GlossaryTermUtils.java`: `getGlossaryTermDataWithoutRelations`, `getGlossaryTermDataWithRelations`, `getGlossaryTermHeaders`, `updateGlossaryTermRelations`, `getMapValue`, `getListValue`, `getAtlasRelatedTermHeaderSet`, `populateGlossaryTermObject`, `createGlossary`, `cacheRelatedTermQNameGuid`, `copyRelations`
- `repository/.../util/FileUtils.java`: `readFileData`, `readCSV`, `readExcel`
- `intg/.../bulkimport/BulkImportResponse.java`
- Tests: `repository/.../glossary/GlossaryServiceTest.java` (`testGetTemplate`, `testImportGlossaryData`, `testEmptyFileException`, `testInvalidFileException`, `testFileExtension`, `testIncorrectFileException`) and their files, copied to `libs/python/aurelius-atlas-core/tests/fixtures/glossary_import/`

## Deviations

- **DV-104:** where Atlas fails with an internal error, the import answers a client error or reads on: a request without a file part, an unreadable `xlsx` file and an empty sheet are refused as `INVALID_FILE_TYPE`, `NOT_VALID_FILE` and `NO_DATA_FOUND`; an Excel cell that is not text is read as its text. A backslash in a CSV file is kept, where opencsv takes it as an escape character.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — GIM-01 to GIM-06 on the in-memory documents, with Atlas's test files.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/glossary/` — the endpoints over HTTP.
- `uv run aurelius-atlas-trace check`.
