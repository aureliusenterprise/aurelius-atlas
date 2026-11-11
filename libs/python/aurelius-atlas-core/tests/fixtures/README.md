# Fixtures

`0010-base_model.json` is copied unchanged from `addons/models/0000-Area0/` of the Apache Atlas
`release-2.4.0` tag (commit 4787b75), under the Apache License 2.0. The 1.4 tests store and reload it.

`glossary_import/` holds `template_1.csv`, `incorrectFile.csv`, `template_with_circular_relationship.csv` and
`empty.csv` from `repository/src/test/resources/csvFiles/`, and `template_1.xlsx` and `invalid_xls.xls` from
`repository/src/test/resources/excelFiles/` of the same tag, unchanged, under the Apache License 2.0. The 5.2d
tests import them as `GlossaryServiceTest` does.

`legacy-app-search-atlas-dev.json`, `legacy-app-search-atlas-dev-quality.json` and
`legacy-app-search-atlas-dev-gov-quality.json` are the original Aurelius Atlas's App Search engine documents
for the sample catalogue, copied unchanged from `backend/m4i-atlas-post-install/data/atlas-dev.json`,
`atlas-dev-quality.json` and `atlas-dev-gov-quality.json` of `aureliusenterprise/aurelius` (commit b057389).
They are what the legacy pipeline produced from the catalogue of `data/atlas-sample/sample_data.zip`: all 684
entity documents' GUIDs are entities of that import. The series 14 tests derive the same documents from the
store and compare them with these (14.1, DD-484).
