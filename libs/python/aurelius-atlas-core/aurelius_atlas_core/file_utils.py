"""``FileUtils``: the rows of an uploaded CSV or Excel file, below its header row (GIM-01).

A CSV file is read as text, rows of one value left out (opencsv's ``CSVReader`` as Atlas reads it); an Excel
file's first sheet as strings, trimmed, empty rows left out (Apache POI). A value Atlas cannot read is read as its
text, and a backslash is no escape character (DV-104).
"""

import csv
import io
from collections.abc import Iterable

import openpyxl
import xlrd
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

PIPE_CHARACTER = "|"
COLON_CHARACTER = ":"

type Row = list[str | None]


def read_file_data(file_name: str | None, content: bytes) -> list[Row]:
    """``readFileData``: by the file name's extension, ``csv``, ``xls`` or ``xlsx`` in any case (GIM-01).

    Raises:
        AtlasError: ``INVALID_FILE_TYPE`` for another extension, ``NOT_VALID_FILE`` for a file that cannot be read,
            ``NO_DATA_FOUND`` for one without rows below its header.
    """
    extension = (file_name or "").rpartition(".")[2].lower() if "." in (file_name or "") else ""
    if extension == "csv":
        rows = read_csv(content)
    elif extension in {"xls", "xlsx"}:
        rows = read_excel(content, extension)
    else:
        raise AtlasError(AtlasErrorCode.INVALID_FILE_TYPE, file_name)
    if not rows:
        raise AtlasError(AtlasErrorCode.NO_DATA_FOUND)
    return rows


def read_csv(content: bytes) -> list[Row]:
    """``readCSV``: the rows after the header of more than one value; none without a header.

    Raises:
        AtlasError: ``NOT_VALID_FILE`` for text that is no CSV.
    """
    text = content.decode("utf-8", errors="replace")
    try:
        lines = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as error:
        raise AtlasError(AtlasErrorCode.NOT_VALID_FILE, "CSV") from error
    if not lines or not lines[0]:
        return []
    return [list(line) for line in lines[1:] if len(line) > 1]


def read_excel(content: bytes, extension: str) -> list[Row]:
    """``readExcel``: the first sheet's rows after the header, up to each row's last cell, trimmed; none for an
    empty header.

    Raises:
        AtlasError: ``NOT_VALID_FILE`` (``XLS``, as Atlas names both) for a file that is no workbook (DV-104).
    """  # noqa: D205 - one sentence
    try:
        rows = _xls_rows(content) if extension == "xls" else _xlsx_rows(content)
    except Exception as error:  # any failure to read the workbook
        raise AtlasError(AtlasErrorCode.NOT_VALID_FILE, "XLS") from error
    if not rows or _is_row_empty(rows[0]):
        return []
    return [[None if value is None else value.strip() for value in row] for row in rows[1:] if not _is_row_empty(row)]


def java_split(text: str, separator: str) -> list[str]:
    """``String.split`` by a literal separator: the text itself without one, else trailing empty strings removed."""
    if separator not in text:
        return [text]
    parts = text.split(separator)
    while parts and not parts[-1]:
        parts.pop()
    return parts


def _xlsx_rows(content: bytes) -> list[Row]:
    workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        return [_trimmed(_text(value) for value in row) for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def _xls_rows(content: bytes) -> list[Row]:
    workbook = xlrd.open_workbook(file_contents=content, ragged_rows=True)
    sheet = workbook.sheet_by_index(0)
    return [
        _trimmed(None if cell.ctype == xlrd.XL_CELL_EMPTY else _text(cell.value) for cell in sheet.row(index))
        for index in range(sheet.nrows)
    ]


def _text(value: object) -> str | None:
    """``getStringCellValue``: a string as it is, another value as its text (DV-104)."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _trimmed(values: Iterable[str | None]) -> Row:
    """The row up to its last cell with a value (``getLastCellNum``)."""
    row = list(values)
    while row and row[-1] is None:
        row.pop()
    return row


def _is_row_empty(row: Row) -> bool:
    """``isRowEmpty``: no cell with a value."""
    return all(value is None or value == "" for value in row)
