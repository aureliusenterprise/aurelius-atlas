"""Register the pipeline and lineage edges declared in a project's openlineage.yaml.

It uses the version-pinned ``metadata.sdk`` client (``openmetadata-ingestion``,
a dev-group dependency), so its API calls are typed models rather than
hand-rolled JSON, and the client refuses cross-major talks with the server —
the same guard the ``openmetadata-ingest`` targets run with. The package is
kept in lockstep with the server image version (``om_version.py``).

The YAML contract (see docs/architecture/data-governance/data-lineage/) is
unchanged:

    version: 1
    openmetadata:
        host: http://localhost:8585   # UI root; /api is appended internally
        tokenEnv: OPENLINEAGE_JWT_TOKEN
    pipeline:
        service: <pipeline service name>
        serviceType: <optional; creates/refreshes the owning service>
        serviceDisplayName: <optional label for the Service Lineage box>
        name: <pipeline name>
        description: <optional>
        state: Active
    edges:
        - from: {entity, service, name}
          to: {entity, service, name}
          source: Manual          # pruning only touches edges with this source
          description: <optional>

Beyond upserting the pipeline and PUTting every declared edge, registration
PRUNES stale edges anchored on this pipeline: an edge touching the pipeline
whose ``source`` matches this file's edges but that no longer appears in the
file is deleted (renames used to leave orphans forever). Edges from other
sources — notably the OpenLineage events the ingestion connector merges into
the same pipeline — are never touched.

Authentication mirrors the ingestion targets: the bearer token comes from the
environment (``tokenEnv``); when unset it is minted from the Keycloak
service-account client (kc_token.py) so no PAT is ever stored.
"""

import argparse
import logging
import os
import sys
import urllib.parse
from enum import Enum
from pathlib import Path
from typing import Any, Literal, NoReturn, NotRequired, Required, TypedDict, cast
from uuid import UUID

import yaml
from metadata.generated.schema.api.data.createPipeline import CreatePipelineRequest
from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest
from metadata.generated.schema.api.services.createPipelineService import CreatePipelineServiceRequest
from metadata.generated.schema.entity.data.pipeline import Pipeline, PipelineState
from metadata.generated.schema.entity.services.pipelineService import PipelineService, PipelineServiceType
from metadata.generated.schema.type import basic as basic_types
from metadata.generated.schema.type.entityLineage import EntitiesEdge, LineageDetails, Source
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.ingestion.ometa.client import APIError
from metadata.sdk import OpenMetadata, OpenMetadataConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kc_token import _config as _kc_config
from kc_token import fetch_id_token

VALID_ENTITY_TYPES = {"topic", "table", "pipeline", "apiEndpoint"}
EntityType = Literal["topic", "table", "pipeline", "apiEndpoint"]

# A parsed YAML mapping whose values are validated as they are read.
_YamlMap = dict[str, object]


def _as_yaml_map(value: object, context: str) -> _YamlMap:
    """Validate that ``value`` is a string-keyed mapping and narrow its type."""
    if not isinstance(value, dict):
        _fail(f"{context} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        _fail(f"{context} keys must be strings")
    return cast("_YamlMap", value)


# Entity type -> REST collection suffix (leading slash, as OMeta.get_suffix).
# The same list route resolves every type: FQNs are inconsistent across
# types (topics quote dotted names, apiEndpoints carry an extra collection
# segment), while "?service=<svc>" + exact name match is uniform.
_ENTITY_ROUTES: dict[EntityType, str] = {
    "topic": "/topics",
    "table": "/tables",
    "pipeline": "/pipelines",
    "apiEndpoint": "/apiEndpoints",
}


class _OpenMetadataConfig(TypedDict):
    host: str
    tokenEnv: str


class _PipelineConfig(TypedDict):
    service: Required[str]
    name: Required[str]
    serviceType: NotRequired[str]
    serviceDisplayName: NotRequired[str]
    description: NotRequired[str]
    state: NotRequired[str]


class _EndpointConfig(TypedDict):
    entity: EntityType
    service: str
    name: str


EdgeConfig = TypedDict(
    "EdgeConfig",
    {
        "from": _EndpointConfig,
        "to": _EndpointConfig,
        "source": str,
        "description": str,
    },
)


class _RootConfig(TypedDict):
    version: Literal[1]
    openmetadata: _OpenMetadataConfig
    pipeline: _PipelineConfig
    edges: list[EdgeConfig]


def _fail(message: str) -> NoReturn:
    logging.error("openlineage registration error: %s", message)
    raise SystemExit(1)


def _enum[EnumT: Enum](enum_cls: type[EnumT], value: str, what: str) -> EnumT:
    """Coerce a YAML string into an OM enum, failing with the valid choices."""
    try:
        return enum_cls(value)
    except ValueError:
        _fail(f"{what} must be one of {[item.value for item in enum_cls]}, got {value!r}")


def _read_yaml(path: Path) -> _YamlMap:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = cast("object", yaml.safe_load(handle))
    except FileNotFoundError:
        _fail(f"config file not found: {path}")
    except yaml.YAMLError as exc:
        _fail(f"invalid yaml in {path}: {exc}")

    if not isinstance(data, dict):
        _fail("top-level YAML must be a mapping")

    return _as_yaml_map(data, "top-level YAML")


def _require_mapping(value: object, context: str) -> _YamlMap:
    return _as_yaml_map(value, context)


def _require_non_empty_string(mapping: _YamlMap, key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{context}.{key} must be a non-empty string")
    return value


def _optional_string(mapping: _YamlMap, key: str, default: str) -> str:
    value = mapping.get(key, default)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{key} must be a non-empty string when provided")
    return value


def _validate_endpoint(endpoint_raw: object, context: str) -> _EndpointConfig:
    endpoint_map = _require_mapping(endpoint_raw, context)
    entity_raw = endpoint_map.get("entity")
    if entity_raw not in VALID_ENTITY_TYPES:
        _fail(f"{context}.entity must be one of {sorted(VALID_ENTITY_TYPES)}")

    return {
        "entity": cast("EntityType", entity_raw),
        "service": _require_non_empty_string(endpoint_map, "service", context),
        "name": _require_non_empty_string(endpoint_map, "name", context),
    }


def _validate_edges(edges_raw: object) -> list[EdgeConfig]:
    if edges_raw is None:
        return []
    if not isinstance(edges_raw, list):
        _fail("edges must be a list when provided")

    edges: list[EdgeConfig] = []
    for idx, edge_raw in enumerate(edges_raw):
        edge_map = _require_mapping(edge_raw, f"edges[{idx}]")
        edge: EdgeConfig = {
            "from": _validate_endpoint(edge_map.get("from"), f"edges[{idx}].from"),
            "to": _validate_endpoint(edge_map.get("to"), f"edges[{idx}].to"),
            "source": _optional_string(edge_map, "source", "Manual"),
            "description": _optional_string(
                edge_map,
                "description",
                "Registered by Nx OpenLineage plugin",
            ),
        }
        edges.append(edge)

    return edges


def _validate(config: _YamlMap) -> _RootConfig:
    for key in ["version", "openmetadata", "pipeline"]:
        if key not in config:
            _fail(f"missing required top-level key '{key}'")

    if config["version"] != 1:
        _fail("only version: 1 is supported")

    metadata_map = _require_mapping(config["openmetadata"], "openmetadata")
    pipeline_map = _require_mapping(config["pipeline"], "pipeline")

    openmetadata_cfg: _OpenMetadataConfig = {
        "host": _require_non_empty_string(metadata_map, "host", "openmetadata"),
        "tokenEnv": _require_non_empty_string(metadata_map, "tokenEnv", "openmetadata"),
    }

    pipeline_cfg: _PipelineConfig = {
        "service": _require_non_empty_string(pipeline_map, "service", "pipeline"),
        "name": _require_non_empty_string(pipeline_map, "name", "pipeline"),
    }

    if "serviceType" in pipeline_map:
        pipeline_cfg["serviceType"] = _optional_string(pipeline_map, "serviceType", "")
    if "serviceDisplayName" in pipeline_map:
        pipeline_cfg["serviceDisplayName"] = _optional_string(pipeline_map, "serviceDisplayName", "")
    if "description" in pipeline_map:
        pipeline_cfg["description"] = _optional_string(pipeline_map, "description", "")
    if "state" in pipeline_map:
        pipeline_cfg["state"] = _optional_string(pipeline_map, "state", "Active")

    return {
        "version": 1,
        "openmetadata": openmetadata_cfg,
        "pipeline": pipeline_cfg,
        "edges": _validate_edges(config.get("edges")),
    }


def _build_client(host: str, token: str) -> OpenMetadata:
    parsed = urllib.parse.urlparse(host)
    if parsed.scheme not in {"http", "https"}:
        _fail("openmetadata.host must use http or https")
    # The SDK client addresses the API directly, so the YAML host (the UI
    # root) needs the /api suffix appended.
    return OpenMetadata(OpenMetadataConfig(server_url=f"{host.rstrip('/')}/api", jwt_token=token))


def _unwrap_uuid(value: object) -> str:
    """Unwrap a pydantic Uuid root model (or plain str) into a string."""
    root = getattr(value, "root", value)
    text = str(root)
    try:
        return str(UUID(text))
    except ValueError:
        _fail(f"server returned a non-UUID id: {text!r}")


def _resolve_entity_id(om: OpenMetadata, entity_type: EntityType, service: str, name: str) -> str:
    """Resolve an entity id by exact name within its service (list route)."""
    route = _ENTITY_ROUTES[entity_type]
    query = urllib.parse.urlencode({"service": service, "limit": 1000})
    try:
        response = _as_yaml_map(om.ometa.client.get(f"{route}?{query}") or {}, "entity list response")
    except APIError as exc:
        _fail(f"could not resolve {entity_type} id for {service}.{name}: {exc} (code {exc.code})")

    data = cast("list[object]", (response or {}).get("data") or [])
    for item in data:
        if isinstance(item, dict) and item.get("name") == name:
            item_id = item.get("id")
            if isinstance(item_id, str) and item_id:
                return item_id

    _fail(f"could not resolve {entity_type} id for {service}.{name}")


def _put_pipeline(om: OpenMetadata, pipeline_cfg: _PipelineConfig) -> str:
    request = CreatePipelineRequest(
        name=basic_types.EntityName(root=pipeline_cfg["name"]),
        service=basic_types.FullyQualifiedEntityName(root=pipeline_cfg["service"]),
        description=basic_types.Markdown(root=pipeline_cfg.get("description", "")),
        state=_enum(PipelineState, pipeline_cfg.get("state", "Active"), "pipeline.state"),
    )
    try:
        pipeline = cast("Pipeline", om.ometa.create_or_update(request))
    except APIError as exc:
        what = f"{pipeline_cfg['service']}.{pipeline_cfg['name']}"
        _fail(f"could not create/update pipeline {what}: {exc} (code {exc.code})")
    return _unwrap_uuid(pipeline.id)


def _ensure_pipeline_service(om: OpenMetadata, pipeline_cfg: _PipelineConfig) -> None:
    """Create or refresh the owning pipeline service when the project declares one.

    A project that names ``serviceType`` owns its own pipeline service, so
    its pipelines appear as a separate box in Service Lineage instead of
    piling into the shared OpenLineage service. ``serviceDisplayName`` sets
    the label shown for that box (the raw name collides with same-named
    services of other types, e.g. the FastAPI pipeline vs API services).
    Existing services are only re-written when the declared display name
    drifts. The OpenLineage event service is created by the ingestion
    connector, not here.
    """
    service_type = pipeline_cfg.get("serviceType")
    if not service_type:
        return
    service = pipeline_cfg["service"]
    display_name = pipeline_cfg.get("serviceDisplayName")

    try:
        existing = cast("PipelineService | None", om.ometa.get_by_name(PipelineService, fqn=service))
    except APIError as exc:
        _fail(f"could not read pipeline service {service}: {exc} (code {exc.code})")
    existing_display = str(existing.displayName) if existing is not None and existing.displayName is not None else None
    if existing is not None and existing_display == display_name:
        return

    logging.info("Creating or updating pipeline service %s (%s)...", service, service_type)
    request = CreatePipelineServiceRequest(
        name=basic_types.EntityName(root=service),
        serviceType=_enum(PipelineServiceType, service_type, "pipeline.serviceType"),
        displayName=display_name,
        description=basic_types.Markdown(root=pipeline_cfg.get("description", "")),
    )
    try:
        om.ometa.create_or_update(request)
    except APIError as exc:
        _fail(f"could not create/update pipeline service {service}: {exc} (code {exc.code})")


def _put_edge(
    om: OpenMetadata,
    from_ref: tuple[EntityType, str],
    to_ref: tuple[EntityType, str],
    *,
    source: str,
    description: str,
) -> None:
    from_type, from_id = from_ref
    to_type, to_id = to_ref
    request = AddLineageRequest(
        edge=EntitiesEdge(
            fromEntity=EntityReference(id=basic_types.Uuid(UUID(from_id)), type=from_type),
            toEntity=EntityReference(id=basic_types.Uuid(UUID(to_id)), type=to_type),
            lineageDetails=LineageDetails(source=Source(source), description=description),
        )
    )
    try:
        # return_lineage=False skips the expensive post-write graph GET we
        # do not need here (pruning reads the graph separately).
        om.ometa.add_lineage(request, return_lineage=False)
    except APIError as exc:
        _fail(f"could not register edge {from_type}:{from_id} -> {to_type}:{to_id}: {exc} (code {exc.code})")


def _collect_entity_types(lineage: Any, pipeline_id: str) -> dict[str, str]:  # noqa: ANN401 - raw lineage dict
    """Map entity id -> type for the delete requests.

    Edge endpoints come back as bare ids; the node list supplies each id's
    entity type. The centre entity is not in nodes[], so add it explicitly.
    """
    types: dict[str, str] = {}
    for node in lineage.get("nodes") or []:
        if isinstance(node, dict) and node.get("id"):
            types[str(node["id"])] = str(node.get("type", ""))
    centre = lineage.get("entity")
    if isinstance(centre, dict) and centre.get("id"):
        types.setdefault(str(centre["id"]), str(centre.get("type", "pipeline")))
    types[pipeline_id] = "pipeline"
    return types


def _is_stale_edge(edge: Any, pipeline_id: str, declared_pairs: set[tuple[str, str]], source: str) -> bool:  # noqa: ANN401 - raw lineage dict
    """True if this edge touches the pipeline, carries our source, and is undeclared."""
    from_id = str(edge.get("fromEntity", ""))
    to_id = str(edge.get("toEntity", ""))
    if pipeline_id not in (from_id, to_id) or (from_id, to_id) in declared_pairs:
        return False
    details = edge.get("lineageDetails")
    edge_source = details.get("source") if isinstance(details, dict) else None
    return edge_source == source


def _prune_stale_edges(om: OpenMetadata, pipeline_id: str, declared_pairs: set[tuple[str, str]], source: str) -> int:
    """Delete edges anchored on this pipeline that this file no longer declares.

    Reads the pipeline's lineage (depth 1) and removes every edge that
    (a) touches this pipeline, (b) carries the same ``source`` this file
    writes with, and (c) is not among the pairs just declared. Edges from
    other sources — in particular the OpenLineage events the ingestion
    connector merges into the same pipeline — are left alone.
    """
    try:
        lineage = om.ometa.get_lineage_by_id("pipeline", pipeline_id, up_depth=1, down_depth=1)
    except APIError as exc:
        _fail(f"could not read pipeline lineage for pruning: {exc} (code {exc.code})")

    if not lineage:
        return 0

    types = _collect_entity_types(lineage, pipeline_id)
    edges = [*(lineage.get("upstreamEdges") or []), *(lineage.get("downstreamEdges") or [])]
    pruned = 0
    for edge in edges:
        if not _is_stale_edge(edge, pipeline_id, declared_pairs, source):
            continue
        from_id = str(edge.get("fromEntity", ""))
        to_id = str(edge.get("toEntity", ""))
        delete_edge = EntitiesEdge(
            fromEntity=EntityReference(id=basic_types.Uuid(UUID(from_id)), type=types.get(from_id, "pipeline")),
            toEntity=EntityReference(id=basic_types.Uuid(UUID(to_id)), type=types.get(to_id, "pipeline")),
        )
        try:
            om.ometa.delete_lineage_edge(delete_edge)
        except APIError as exc:
            _fail(f"could not prune stale edge {from_id} -> {to_id}: {exc} (code {exc.code})")
        logging.info("Pruned stale edge %s -> %s", from_id, to_id)
        pruned += 1
    return pruned


def _resolve_token(metadata_cfg: _OpenMetadataConfig) -> str:
    token = os.environ.get(metadata_cfg["tokenEnv"], "")
    if token:
        return token
    # No pre-set bearer (the committed way): mint a short-lived token from
    # the Keycloak service-account client so no PAT needs to be stored.
    token_url, client_id, client_secret = _kc_config()
    if not (token_url and client_id and client_secret):
        _fail(
            f"environment variable {metadata_cfg['tokenEnv']} is required, or set "
            "KEYCLOAK_BOT_TOKEN_URL / OIDC_BOT_CLIENT_ID / OIDC_BOT_CLIENT_SECRET "
            "(dev/governance/.env provides them) for a client-credentials token"
        )
    return fetch_id_token(token_url, client_id, client_secret)


def _register(config_path: Path) -> int:
    config = _validate(_read_yaml(config_path))
    metadata_cfg = config["openmetadata"]
    pipeline_cfg = config["pipeline"]

    token = _resolve_token(metadata_cfg)
    client = _build_client(metadata_cfg["host"], token)

    _ensure_pipeline_service(client, pipeline_cfg)
    logging.info("Ensuring pipeline %s.%s exists...", pipeline_cfg["service"], pipeline_cfg["name"])
    pipeline_id = _put_pipeline(client, pipeline_cfg)

    edge_count = 0
    declared_pairs: set[tuple[str, str]] = set()
    edge_sources: set[str] = set()
    for edge in config["edges"]:
        edge_from = edge["from"]
        edge_to = edge["to"]

        from_type = edge_from["entity"]
        from_id = (
            pipeline_id
            if from_type == "pipeline"
            and edge_from["name"] == pipeline_cfg["name"]
            and edge_from["service"] == pipeline_cfg["service"]
            else _resolve_entity_id(client, from_type, edge_from["service"], edge_from["name"])
        )

        to_type = edge_to["entity"]
        to_id = (
            pipeline_id
            if to_type == "pipeline"
            and edge_to["name"] == pipeline_cfg["name"]
            and edge_to["service"] == pipeline_cfg["service"]
            else _resolve_entity_id(client, to_type, edge_to["service"], edge_to["name"])
        )

        source = edge["source"]
        description = edge["description"]

        logging.info(
            "Registering edge %s:%s.%s -> %s:%s.%s...",
            from_type,
            edge_from["service"],
            edge_from["name"],
            to_type,
            edge_to["service"],
            edge_to["name"],
        )
        _put_edge(client, (from_type, from_id), (to_type, to_id), source=source, description=description)
        declared_pairs.add((from_id, to_id))
        edge_sources.add(source)
        edge_count += 1

    # Prune only under the single source this file writes with; files mixing
    # sources skip pruning rather than guess which edges they own.
    pruned = 0
    if len(edge_sources) == 1:
        pruned = _prune_stale_edges(client, pipeline_id, declared_pairs, next(iter(edge_sources)))

    logging.info(
        "OpenLineage registration complete. Pipeline id: %s. Edges written: %s. Stale edges pruned: %s",
        pipeline_id,
        edge_count,
        pruned,
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register pipeline and optional lineage edges from openlineage.yaml")
    parser.add_argument("--config", required=True, help="Path to project openlineage.yaml")
    return parser.parse_args()


def _main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    args = _parse_args()
    return _register(Path(args.config))


if __name__ == "__main__":
    raise SystemExit(_main())
