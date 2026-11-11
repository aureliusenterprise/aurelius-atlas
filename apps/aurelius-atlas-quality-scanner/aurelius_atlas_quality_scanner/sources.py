"""The dataset reader seam, the file reader, and the source router (12.2 DQS-04/DQS-05, DD-459; 12.4a DQS-18).

A reader answers a polars frame for one dataset. The file reader reads the extract a ``file``
source names; a dataset the map does not name, or whose path is not a readable file of a known
extension, is skipped with its reason (DD-459: the qualified name is never used as a path, so a
name can never reach outside the map). The router sends each dataset to the reader of its source's
kind (DQS-18); the scan reads through the router and knows no kinds (DQS-11).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import polars as pl

from aurelius_atlas_quality_scanner.settings import SourceEntry

READABLE_EXTENSIONS: dict[str, str] = {
    ".parquet": "parquet",
    ".csv": "csv",
    ".ndjson": "ndjson",
    ".json": "json",
}
"""The extensions the file reader reads, by extension (DQS-04): polars' own formats, no others."""

NO_SOURCE = "no source configured"
"""The dataset's qualified name is not in the ``sources`` map."""

NO_FILE = "no readable file"
"""The mapped path is not a readable regular file."""

UNKNOWN_FORMAT = "format not readable"
"""The mapped path's extension is none of :data:`READABLE_EXTENSIONS`."""

TRUNCATED = "truncated"
"""The extract holds more rows than the budget; the frame was cut at it (DQS-05)."""


@dataclass(frozen=True)
class Read:
    """One dataset's rows, and what the reader noticed: at most one of :data:`TRUNCATED`."""

    frame: pl.DataFrame
    notice: str | None = None


class DatasetReader(Protocol):
    """The seam the scan reads through (DQS-04): a frame for one dataset, or the reason there is none."""

    def read(self, qualified_name: str, guid: str) -> Read | None:
        """The rows of the dataset, or ``None`` when there are none (DQS-04)."""
        ...

    def skip_reason(self, qualified_name: str, guid: str) -> str | None:
        """Why the dataset has no readable extract, or ``None`` when :meth:`read` answers a frame.

        The scan asks this only after a refused read, to say the reason out loud (DQS-04). The
        guid rides with the name so a guid-keyed source can answer too (DQS-20).
        """
        ...


class FileReader:
    """Reads each dataset's extract from the ``sources`` map (DQS-04, DD-459).

    Args:
        sources: The map from a dataset's qualified name to its extract path.
        max_rows: The most rows one read returns (DQS-05).
    """

    def __init__(self, sources: dict[str, str], max_rows: int) -> None:
        self._sources = sources
        self._max_rows = max_rows

    def skip_reason(self, qualified_name: str, guid: str) -> str | None:
        """Why the dataset has no readable extract, or ``None`` when it has one (DQS-04).

        The reasons, in the order they are checked: no entry in the map, a path that is not a
        readable regular file, and an extension the reader does not read. The guid is the seam's
        (DQS-20); the file map keys by name, so this reader discards it.
        """
        del guid  # the seam names it (DQS-20); the file map keys by name.
        path = self._sources.get(qualified_name)
        if path is None:
            return NO_SOURCE
        candidate = Path(path)
        if not candidate.is_file():
            return NO_FILE
        if candidate.suffix.lower() not in READABLE_EXTENSIONS:
            return UNKNOWN_FORMAT
        return None

    def read(self, qualified_name: str, guid: str) -> Read | None:
        """The dataset's frame, cut at the row budget; ``None`` when :meth:`skip_reason` names a reason.

        The budget is passed to the reader of each format where polars supports it (one row past
        it, to see that the extract is longer); the JSON reader has no row limit, so its frame is
        sliced after the read.
        """
        reason = self.skip_reason(qualified_name, guid)
        if reason is not None:
            return None
        path = Path(self._sources[qualified_name])
        format_ = READABLE_EXTENSIONS[path.suffix.lower()]
        frame = self._read_format(path, format_)
        if frame.height > self._max_rows:
            return Read(frame.head(self._max_rows), TRUNCATED)
        return Read(frame)

    def _read_format(self, path: Path, format_: str) -> pl.DataFrame:
        """Read ``path`` with the polars reader of ``format_``, one row past the budget where it has one."""
        budget = self._max_rows + 1
        if format_ == "parquet":
            return pl.read_parquet(path, n_rows=budget)
        if format_ == "csv":
            return pl.read_csv(path, n_rows=budget)
        if format_ == "ndjson":
            return pl.read_ndjson(path, n_rows=budget)
        return pl.read_json(path).head(budget)


FILE_KIND = "file"
"""The one reader kind this job answers. A later source adds its kind to the router (DQS-18)."""

KIND_NOT_AVAILABLE = "kind not available"
"""The dataset's source names a kind this job's router has no reader for (DQS-18): a skip, not a failure."""


class SourceRouter:
    """Sends each dataset to the reader of its source's kind (DQS-18, DQS-11, DQS-20, DD-463, DD-464).

    The scan reads through this seam and knows no kinds. The router answers every source; a kind
    it has no reader for is a skip with its reason, so a configuration for a newer job still
    scans the datasets this job can read (DQS-13). A dataset is matched by guid first, then by
    qualified name: the stable identity answers before the name its owner can change (DQS-20).

    Args:
        sources: The sources, each naming its dataset by qualified name or guid.
        max_rows: The row budget each reader enforces (DQS-05).
    """

    def __init__(self, sources: list[SourceEntry], max_rows: int) -> None:
        self._by_guid = {entry.dataset.guid: entry for entry in sources if entry.dataset.guid is not None}
        self._by_name = {entry.dataset.qualified_name: entry for entry in sources if entry.dataset.qualified_name}
        self._readers: dict[str, DatasetReader] = {FILE_KIND: FileReader(self._paths_of_kind(FILE_KIND), max_rows)}

    def _paths_of_kind(self, kind: str) -> dict[str, str]:
        """The ``path`` of every ``file`` source, keyed by its dataset name, for the file reader (DD-463).

        A guid-keyed file source rides under the guid: the scan reads the dataset it matched, and
        it calls the file reader with the key the source was built under (DQS-20).
        """
        return {
            entry.dataset.key(): str(entry.config["path"])
            for entry in [*self._by_guid.values(), *self._by_name.values()]
            if entry.kind == kind and isinstance(entry.config.get("path"), str)
        }

    def _entry_for(self, qualified_name: str, guid: str) -> SourceEntry | None:
        """The source of the dataset: its guid's source first, then its name's (DQS-20)."""
        return self._by_guid.get(guid) or self._by_name.get(qualified_name)

    def skip_reason(self, qualified_name: str, guid: str) -> str | None:
        """Why the dataset has no readable source, or ``None`` when it does (DQS-18, DQS-20).

        The reasons, in order: no source names the dataset (the file reader's own reason), a kind
        with no reader, and the kind's reader's own reason — asked with the key the source was
        built under.
        """
        entry = self._entry_for(qualified_name, guid)
        if entry is None:
            return NO_SOURCE
        reader = self._readers.get(entry.kind)
        if reader is None:
            return KIND_NOT_AVAILABLE
        return reader.skip_reason(entry.dataset.key(), guid)

    def read(self, qualified_name: str, guid: str) -> Read | None:
        """The dataset's frame from its kind's reader; ``None`` when :meth:`skip_reason` names a reason."""
        entry = self._entry_for(qualified_name, guid)
        if entry is None:
            return None
        reader = self._readers.get(entry.kind)
        if reader is None:
            return None
        return reader.read(entry.dataset.key(), guid)
