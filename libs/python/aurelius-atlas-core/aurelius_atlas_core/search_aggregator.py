"""``SearchAggregatorImpl``: the facets of a quick search (QSR-03, QSR-04, DD-093).

Atlas's ``SearchAggregatorImpl`` with its ``ServiceTypeAggregator`` and ``EntityDiscoveryService``'s
``getAggregationFields`` and ``getAggregationAtlasAttributes``: the counts come from the entity documents'
aggregations of the search query.
"""

from collections.abc import Mapping, Sequence

from aurelius_atlas_model.discovery import AtlasAggregationEntry
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.search_fields import field_name
from aurelius_atlas_core.search_query import STATE_FIELD, TYPE_NAME_FIELD

ASSET_ENTITY_TYPE = "Asset"
OWNER_ATTRIBUTE = "owner"
ASSET_OWNER = f"{ASSET_ENTITY_TYPE}.{OWNER_ATTRIBUTE}"
SERVICE_TYPE = "ServiceType"


class SearchAggregator:
    """The facets of a search over the types of ``registry``."""

    def __init__(self, registry: TypeRegistry) -> None:
        self._registry = registry
        self.fields: dict[str, str] = {"__typeName": TYPE_NAME_FIELD, "__state": STATE_FIELD}
        """Each facet's name and the search field it counts: ``__typeName``, ``__state`` and ``Asset.owner``."""
        asset = registry.entity_type(ASSET_ENTITY_TYPE)
        owner = None if asset is None else asset.attribute(OWNER_ATTRIBUTE)
        owner_field = None if owner is None else field_name(owner)
        if owner is not None and owner_field is not None:
            self.fields[owner.qualified_name] = owner_field

    def aggregated_metrics(
        self, counts: Mapping[str, Sequence[tuple[str, int]]]
    ) -> dict[str, list[AtlasAggregationEntry]]:
        """``getAggregatedMetrics``: each facet's values and counts, and the ``ServiceType`` counts (QSR-03, QSR-04).

        ``counts`` holds the values of each search field of ``fields``, as the entity documents count them.
        """
        metrics = {
            name: [AtlasAggregationEntry(name=value, count=count) for value, count in counts.get(field, [])]
            for name, field in self.fields.items()
        }
        metrics.setdefault(ASSET_OWNER, [])  # Atlas fails without Asset.owner; a registry without it counts none
        services = self._service_types(metrics["__typeName"])
        if services:
            metrics[SERVICE_TYPE] = services
        return metrics

    def _service_types(self, type_counts: list[AtlasAggregationEntry]) -> list[AtlasAggregationEntry]:
        """``ServiceTypeAggregator``: the type counts added up by service type, those counted none left out."""
        totals = dict.fromkeys(self._registry.all_service_types(), 0)
        for entry in type_counts:
            entity_type = self._registry.entity_type(entry.name)
            service = None if entity_type is None else entity_type.service_type
            if service in totals:
                totals[service] += entry.count
        found = [(service, count) for service, count in totals.items() if count]
        return [
            AtlasAggregationEntry(name=service, count=count)
            for service, count in sorted(found, key=lambda item: (-item[1], item[0]))
        ]
