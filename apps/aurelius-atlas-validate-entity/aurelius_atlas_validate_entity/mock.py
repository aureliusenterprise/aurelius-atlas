"""The fixed governance-quality mock document (VE-02, DV-50, DD-112).

The legacy ``m4i-validate-entity`` service is a mock: it accepts the entity,
never reads it, and answers this constant (ADR 055, DV-50). The document is
the webapp's editor contract — the ``AppSearchResult<GovQualitySearchObject>``
cards its governance panel renders (``libs/atlas/api::GovQualityApi``) — so it
is ported verbatim, as data: the legacy's ``doc-…`` ids, ``raw`` strings,
``Attribute - <key>`` names, string ``compliant`` flags, and
``_meta.engine = atlas-dev-gov-quality`` are part of the browser contract.
"""

from typing import Any

MOCK_VALIDATION: dict[str, Any] = {
    "dataEntity": {
        "items": [
            {
                "result": {"raw": "This entity is missing a dataEntity"},
                "dataqualitytype": {"raw": "attribute"},
                "usedattributes": {"raw": ["dataEntity"]},
                "name": {"raw": "Attribute - dataEntity"},
                "compliant": {"raw": "0"},
                "_meta": {"engine": "atlas-dev-gov-quality", "score": 1, "id": "doc-6290d9e0dd895e02b897451f"},
                "id": {"raw": "doc-6290d9e0dd895e02b897451f"},
            }
        ],
        "isNonCompliant": True,
    },
    "definition": {
        "items": [
            {
                "result": {"raw": "This entity has a definition"},
                "dataqualitytype": {"raw": "attribute"},
                "usedattributes": {"raw": ["definition"]},
                "name": {"raw": "Attribute - definition"},
                "compliant": {"raw": "1"},
                "_meta": {"engine": "atlas-dev-gov-quality", "score": 1, "id": "doc-6290d9dedd895e197b974510"},
                "id": {"raw": "doc-6290d9dedd895e197b974510"},
            }
        ],
        "isNonCompliant": False,
    },
    "domainLead": {
        "items": [
            {
                "result": {"raw": "This entity is missing a domainLead"},
                "dataqualitytype": {"raw": "attribute"},
                "usedattributes": {"raw": ["domainLead"]},
                "name": {"raw": "Attribute - domainLead"},
                "compliant": {"raw": "0"},
                "_meta": {"engine": "atlas-dev-gov-quality", "score": 1, "id": "doc-6290d9e0dd895e02b8974528"},
                "id": {"raw": "doc-6290d9e0dd895e02b8974528"},
            }
        ],
        "isNonCompliant": True,
    },
    "name": {
        "items": [
            {
                "result": {"raw": "This entity has a name"},
                "dataqualitytype": {"raw": "attribute"},
                "usedattributes": {"raw": ["name"]},
                "name": {"raw": "Attribute - name"},
                "compliant": {"raw": "1"},
                "_meta": {"engine": "atlas-dev-gov-quality", "score": 1, "id": "doc-6290d9dedd895e197b974507"},
                "id": {"raw": "doc-6290d9dedd895e197b974507"},
            }
        ],
        "isNonCompliant": False,
    },
}
"""The legacy ``output`` dict verbatim: the four governance cards the mock answers."""
