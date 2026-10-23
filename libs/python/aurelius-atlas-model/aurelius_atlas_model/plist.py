"""``PList``: a page of a list, with its position and sort order, as Atlas answers lists (CLS-01).

Ported from Apache Atlas 2.4.0 ``org.apache.atlas.model.PList`` and ``SearchFilter.SortType``.
"""

from enum import StrEnum
from typing import Self

from aurelius_atlas_model.base import AtlasModel, JavaInt


class SortType(StrEnum):
    """``SearchFilter.SortType``: the order of a list."""

    NONE = "NONE"
    ASC = "ASC"
    DESC = "DESC"


type Elements[T] = list[T]
"""A list, under a name the ``list`` field does not hide."""


class PList[T](AtlasModel):
    """The elements, their start index, page size and total count, and how they are sorted."""

    list: Elements[T] | None = None
    start_index: JavaInt = 0
    page_size: JavaInt = 0
    total_count: JavaInt = 0
    sort_by: str | None = None
    sort_type: SortType | None = None

    @classmethod
    def of(cls, elements: Elements[T]) -> Self:
        """``PList(List)``: the whole list as one page, not sorted."""
        return cls(
            list=elements,
            start_index=0,
            page_size=len(elements),
            total_count=len(elements),
            sort_type=SortType.NONE,
        )
