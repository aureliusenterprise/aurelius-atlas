"""``IdentifierHelper``: how a DSL query's names and values are unquoted, and its patterns read (DSE-06 to DSE-09).

The static methods of Atlas's class; its ``Info``, a name resolved against the active type, is the composer's
(``dsl_query_composer``).
"""

import re

_QUOTED_IDENTIFIER = {
    "`": re.compile(r"`(\w[\w\d.\s]*)`", re.ASCII),
    "'": re.compile(r"'(\w[\w\d.\s]*)'", re.ASCII),
    '"': re.compile(r'"(\w[\w\d.\s]*)"', re.ASCII),
}
_ESCAPE_CHARACTERS = frozenset("@#&~/")
_QUOTES = str.maketrans("", "", "\"'`")


def get(quoted_identifier: str) -> str | None:
    """``get``: the name inside quotes when it is a word of letters, digits, dots and spaces; else as given."""
    if not quoted_identifier:
        return None
    pattern = _QUOTED_IDENTIFIER.get(quoted_identifier[0])
    found = pattern.search(quoted_identifier) if pattern else None
    return found.group(1) if found else quoted_identifier


def is_quoted(value: str) -> bool:
    """``isQuoted``: begins and ends with the same quote character."""
    return bool(value) and value[0] == value[-1] and value[0] in "'\"`"


def remove_quotes(value: str) -> str:
    """``removeQuotes``: every quote character taken out, wherever it is."""
    return value.translate(_QUOTES)


def is_true_or_false(value: str) -> bool:
    """``isTrueOrFalse``: ``true`` or ``false`` in any case."""
    return value.lower() in {"true", "false"}


def get_fixed_reg_ex(value: str) -> str:
    """``getFixedRegEx``: ``*`` as any characters, ``?`` as one."""
    return value.replace("*", ".*").replace("?", ".")


def escape_characters(value: str) -> str:
    """``escapeCharacters``: ``@ # & ~ /`` escaped with a backslash."""
    return "".join(f"\\{character}" if character in _ESCAPE_CHARACTERS else character for character in value)


def remove_wildcards(value: str) -> str:
    """``removeWildcards``: unquoted, without ``*`` and ``?``."""
    return remove_quotes(value).replace("*", "").replace("?", "")


def is_complete_value(value: str) -> bool:
    """``isCompleteValue``: empty, ``0`` or ``false`` in any case (DSE-09)."""
    return not value or value == "0" or value.lower() == "false"


def is_in_complete_value(value: str) -> bool:
    """``isInCompleteValue``: ``1`` or ``true`` in any case (DSE-09)."""
    return value == "1" or value.lower() == "true"
