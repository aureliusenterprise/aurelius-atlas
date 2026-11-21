"""How a search field's ``.text`` sub-field reads words: the pattern a word matches, and a query word (DD-092).

The standard analyzer of a keyword field's analysed ``.text`` sub-field keeps runs of word characters, and a free-text
query word may end in ``*`` to match the words that begin with it. The store package owns these so the fake, which
stands in for a server we do not run, reads the words it matches exactly as the index that matched them does, and
core's free-text reading and the App Search engine read the same ones (DD-772).
"""

import re

WORD = re.compile(r"\w+")
"""A word of a stored value: a run of word characters, as the ``.text`` sub-field's analyzer keeps it."""

QUERY_WORD = re.compile(r"\w+\*?")
"""A word of a free-text query, which may end in ``*`` to match the words beginning with it."""


def words(value: str) -> list[str]:
    """The words of a value, lower-cased: the ``.text`` sub-field's reading of it (DD-092)."""
    return [word.lower() for word in WORD.findall(value)]


def term_matches(term: str, found: set[str]) -> bool:
    """Whether a query term is one of the ``found`` words, or -- ending in ``*`` -- the start of one of them."""
    if term.endswith("*"):
        return any(word.startswith(term[:-1]) for word in found)
    return term in found
