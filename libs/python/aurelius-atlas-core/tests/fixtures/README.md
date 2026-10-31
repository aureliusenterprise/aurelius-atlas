# Fixtures

`0010-base_model.json` is copied unchanged from `addons/models/0000-Area0/` of the Apache Atlas
`release-2.4.0` tag (commit 4787b75), under the Apache License 2.0. The 1.4 tests store and reload it.

`glossary_import/` holds `template_1.csv`, `incorrectFile.csv`, `template_with_circular_relationship.csv` and
`empty.csv` from `repository/src/test/resources/csvFiles/`, and `template_1.xlsx` and `invalid_xls.xls` from
`repository/src/test/resources/excelFiles/` of the same tag, unchanged, under the Apache License 2.0. The 5.2d
tests import them as `GlossaryServiceTest` does.
