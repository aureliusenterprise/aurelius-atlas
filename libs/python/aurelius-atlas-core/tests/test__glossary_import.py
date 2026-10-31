"""Glossary import (GIM-01 to GIM-06) on the in-memory documents.

Read from ``GlossaryService#importGlossaryData``, ``GlossaryTermUtils`` and ``FileUtils`` of Apache Atlas 2.4.0, with
``GlossaryServiceTest``'s import tests and their files (``tests/fixtures/glossary_import``).
"""

import io
import json
from pathlib import Path

import openpyxl
import pytest
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.file_utils import java_split, read_csv, read_file_data
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder
from aurelius_atlas_core.glossary_term_utils import glossary_term_headers
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.bulk_import import BulkImportResponse, ImportStatus
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import AtlasGlossaryTerm
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.glossary_service.GlossaryService"
T = "aurelius_atlas_core.glossary_term_utils"
F = "aurelius_atlas_core.file_utils"
FILES = Path(__file__).parent / "fixtures" / "glossary_import"
MODELS = BUILTIN_MODELS_DIR / "0000-Area0"
HEADER = glossary_term_headers()


@pytest.fixture
def service() -> GlossaryService:
    """A service on a store with the base and glossary models."""
    registry = TypeRegistry()
    with registry.update() as transient:
        for name in ("0010-base_model.json", "0011-glossary_model.json"):
            transient.add_types(AtlasTypesDef.model_validate(json.loads((MODELS / name).read_text(encoding="utf-8"))))
    return GlossaryService(EntityStore(registry, MemoryEntityDocuments()))


async def imported(service: GlossaryService, name: str) -> BulkImportResponse:
    """The answer to importing one of Atlas's test files."""
    return await service.import_glossary_data(name, (FILES / name).read_bytes())


def csv_file(*rows: str) -> bytes:
    """A CSV file of the template's header and these rows."""
    return "\n".join([HEADER, *rows]).encode()


async def failure(awaitable: object) -> tuple[AtlasErrorCode, str]:
    """The code and message of the error the awaitable raises."""
    with pytest.raises(AtlasError) as raised:
        await awaitable  # type: ignore[misc]
    return raised.value.code, raised.value.message


async def term_named(service: GlossaryService, glossary: str, name: str) -> AtlasGlossaryTerm:
    """The term of the name in the glossary of the name."""
    found = next(g for g in await service.get_glossaries(-1, 0, SortOrder.ASCENDING) if g.name == glossary)
    header = next(h for h in (await service.get_glossary(found.guid)).terms or [] if h.display_text == name)
    return await service.get_term(str(header.term_guid))


@pytest.mark.covers(f"{T}.glossary_term_headers", rules=["GIM-06"])
def test__the_template_is_the_header_line() -> None:
    """``testGetTemplate``."""
    assert glossary_term_headers() == (
        "GlossaryName, TermName, ShortDescription, LongDescription, Examples, Abbreviation, Usage, "
        "AdditionalAttributes, TranslationTerms, ValidValuesFor, Synonyms, ReplacedBy, ValidValues, "
        "ReplacementTerms, SeeAlso, TranslatedTerms, IsA, Antonyms, Classifies, PreferredToTerms, PreferredTerms"
    )


@pytest.mark.covers(f"{F}.read_file_data", f"{F}.read_csv", f"{F}.read_excel", f"{F}.java_split", rules=["GIM-01"])
def test__a_file_is_read_by_its_extension() -> None:
    """``testEmptyFileException``, ``testInvalidFileException``, ``testFileExtension``; rows of one value dropped."""
    assert read_file_data("t.CSV", b"h1,h2\nx\n\na,b\n") == [["a", "b"]]
    assert read_csv(b"") == []
    sheet = openpyxl.Workbook()
    sheet.active.append(["GlossaryName", "TermName"])  # type: ignore[union-attr]
    sheet.active.append([" g ", 3.0, None])  # type: ignore[union-attr]
    sheet.active.append([None, None])  # type: ignore[union-attr]
    content = io.BytesIO()
    sheet.save(content)
    assert read_file_data("t.xlsx", content.getvalue()) == [["g", "3"]]
    for name, content, message in (
        ("empty.csv", (FILES / "empty.csv").read_bytes(), "No data found in the uploaded file"),
        ("invalid_xls.xls", (FILES / "invalid_xls.xls").read_bytes(), "Invalid XLS file"),
        ("x.xlsx", b"no workbook", "Invalid XLS file"),
        (
            "incorrectEXT.py",
            b"",
            "The provided file type: incorrectEXT.py is not supported. Expected file formats are .csv and .xls.",
        ),
    ):
        with pytest.raises(AtlasError) as raised:
            read_file_data(name, content)
        assert raised.value.message == message
    assert (java_split("a|b|", "|"), java_split("", ":"), java_split(":x", ":")) == (["a", "b"], [""], ["", "x"])


@pytest.mark.covers(
    f"{S}.import_glossary_data",
    f"{T}.GlossaryTermUtils.glossary_term_data_without_relations",
    rules=["GIM-02", "GIM-03"],
)
async def test__a_file_creates_its_glossary_and_terms(service: GlossaryService) -> None:
    """``testImportGlossaryData``: one term each from the CSV and the Excel file; the same file again fails."""
    first = await imported(service, "template_1.csv")
    assert [(i.parent_object_name, i.child_object_name, i.import_status) for i in first.success_import_info_list] == [
        ("testBankingGlossary", "BankBranch", ImportStatus.SUCCESS)
    ]
    branch = await term_named(service, "testBankingGlossary", "BankBranch")
    assert json.loads(str(first.success_import_info_list[0].remarks)) == {
        "termGuid": branch.guid,
        "qualifiedName": "BankBranch@testBankingGlossary",
    }
    assert (branch.short_description, branch.examples, branch.abbreviation, branch.usage) == (
        "SD4",
        ["EXAMPLE"],
        "ABBREVIATION",
        "USAGE",
    )
    assert len((await imported(service, "template_1.xlsx")).success_import_info_list) == 1
    assert await failure(imported(service, "template_1.csv")) == (
        AtlasErrorCode.GLOSSARY_IMPORT_FAILED,
        "Glossary import failed",
    )
    assert (await failure(service.import_glossary_data(" ", b"")))[0] is AtlasErrorCode.INVALID_FILE_TYPE


@pytest.mark.covers(
    f"{S}.import_glossary_data",
    f"{T}.GlossaryTermUtils.glossary_term_data_with_relations",
    f"{T}.GlossaryTermUtils.update_glossary_term_relations",
    f"{S}.update_term",
    rules=["GIM-04", "GIM-05"],
)
async def test__relations_are_written_after_every_term(service: GlossaryService) -> None:
    """``testImportGlossaryData`` with circular relations: each term keeps the relations earlier rows gave it."""
    response = await imported(service, "template_with_circular_relationship.csv")
    assert (len(response.success_import_info_list), response.failed_import_info_list) == (3, [])
    related = {}
    for name in ("Fact", "Vertical", "Horizontal"):
        found = await term_named(service, "Industry", name)
        related[name] = sorted(str(header.display_text) for header in found.see_also or [])
    assert related == {"Fact": ["Horizontal", "Vertical"], "Vertical": ["Fact"], "Horizontal": ["Fact"]}


@pytest.mark.covers(f"{S}.import_glossary_data", rules=["GIM-03", "GIM-04"])
async def test__rows_that_fail_are_reported(service: GlossaryService) -> None:
    """``testIncorrectFileException`` and the messages of each kind of failing row."""
    response = await imported(service, "incorrectFile.csv")
    assert len(response.success_import_info_list) == 1
    missing = (
        "The provided Reference GentsFootwear@ does not exist at Atlas referred at record with TermName  : "
        "BankBranch1 and GlossaryName : testBankingGlossary"
    )
    assert [info.remarks for info in response.failed_import_info_list] == [missing]
    response = await service.import_glossary_data(
        "rows.csv",
        csv_file(
            "g,a,,,x|y,,,k:v|bad,,,,,,,,,,,,,",
            ",b,c",
            "g,,c",
            "g.x,c,,",
            "g,d,,,,,,,,,,,,,g:d|g|g:e,,,,,,",
            "g,a,,,,,,,,,,,,,,,,,,,",
        ),
    )
    pair = "AdditionalAttributes needs to be a key:value pair"
    invalid = "name cannot contain following special chars (@, ., <, >)"
    relations = (
        "Invalid relationship specified for Term. Term cannot have a relationship with self\n"
        "Incorrect relation data specified for the term : d@g\n"
        "The provided Reference e@g does not exist at Atlas referred at record with TermName  : d and GlossaryName : g"
    )
    assert [(i.parent_object_name, i.child_object_name, i.remarks) for i in response.failed_import_info_list] == [
        ("g", "a", f"The Data in the uploaded file is incorrectly specified  : k:v|bad\n{pair}"),
        ("", None, "The GlossaryName is blank for the record : [, b, c]"),
        ("g", "", "The TermName is blank for provided record: [g, , c]"),
        ("g.x", None, f"The provided Glossary Name {{g.x}} is invalid : {invalid}"),
        ("g", "", "Mandatory anchor attribute is missing"),
        ("g", "a", "Glossary term with qualifiedName a@g already exists"),
        ("g", "d", relations),
    ]
    created = await term_named(service, "g", "a")
    assert (created.examples, created.additional_attributes) == (["x", "y"], {"k": "v"})
