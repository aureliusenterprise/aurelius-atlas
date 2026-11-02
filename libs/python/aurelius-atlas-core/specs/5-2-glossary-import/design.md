# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-249. Uploaded files are read with python-multipart, openpyxl and xlrd

- **Status:** Proposed
- **Increment:** 5.2d
- **Date:** 2026-10-31

**Decision.** The server reads a multipart upload with `python-multipart`, which FastAPI's form parsing
requires. The core reads an `xlsx` workbook with `openpyxl` (read-only, cached values) and an `xls` workbook
with `xlrd` 2, which reads only that format; a CSV file with the standard library's `csv` module. All three are
pure Python.

**Reason.** Atlas reads CSV with opencsv and both Excel formats with Apache POI. Python has no single library
for both Excel formats: openpyxl reads only the XML format, xlrd 2 only the binary one, and each is the
maintained reader of its format.

**Alternatives.** pandas: reads both, but through these same engines and with numpy behind it. Dropping `xls`:
Atlas's clients may upload it, and its error message names it.

**Consequences.** Three new runtime dependencies, in the SBOM. A value is read as Python gives it; DV-104 records
where that differs from Atlas.
