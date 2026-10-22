"""The client's JSON: floats read as decimals with their digits, bodies given as bytes passed through (DD-039, DD-043).

Catalogue values keep their digits from request to store and back: the application writes documents as the bytes of
its JSON codec, and every response is read with ``Decimal`` for numbers with a fraction or exponent.
"""

import json
from decimal import Decimal
from typing import Any

from elastic_transport import JsonSerializer

JSON_MIMETYPES = ("application/json", "application/vnd.elasticsearch+json")
"""The media types Elasticsearch 9 answers JSON with, which the serializer reads."""


class DecimalJsonSerializer(JsonSerializer):
    """``JsonSerializer`` that reads every float as a ``Decimal``; bytes and strings are sent as they are."""

    def loads(self, data: bytes) -> Any:  # noqa: ANN401 - any JSON value
        """The JSON value of ``data``, floats as decimals."""
        return json.loads(data, parse_float=Decimal)


def serializers() -> dict[str, JsonSerializer]:
    """The serializers the store's client uses, by media type."""
    serializer = DecimalJsonSerializer()
    return dict.fromkeys(JSON_MIMETYPES, serializer)
