"""A stand-in for ``AsyncElasticsearch`` for unit tests that need no server."""

import copy
import fnmatch
import json
import math
import re
from decimal import Decimal
from functools import cmp_to_key
from typing import Any

from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elasticsearch import ApiError, ConflictError, NotFoundError

NODE = NodeConfig("https", "localhost", 9200)


def response_meta(status: int) -> ApiResponseMeta:
    """Response metadata as the transport attaches it to an ``ApiError``."""
    return ApiResponseMeta(status=status, http_version="1.1", headers=HttpHeaders(), duration=0.0, node=NODE)


def _not_found() -> NotFoundError:
    return NotFoundError("document_missing", response_meta(404), {"found": False})


def _conflict() -> ConflictError:
    return ConflictError("version_conflict_engine_exception", response_meta(409), {"status": 409})


def already_exists() -> ApiError:
    """The answer of a create of an index that exists, as another server booting on the same store makes it."""
    return ApiError(
        "index already exists", response_meta(400), {"error": {"type": "resource_already_exists_exception"}}
    )


class FakeResponse(dict[str, Any]):
    """A response whose ``body`` is the response itself, as the client's ``ObjectApiResponse`` has one."""

    @property
    def body(self) -> dict[str, Any]:
        """The response's JSON."""
        return self


class FakeCluster:
    """The ``cluster`` namespace of the fake client."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        """Answer like ``GET _cluster/health``, or raise the configured error."""
        if self._client.health_error is not None:
            raise self._client.health_error
        return {"cluster_name": self._client.cluster_name, "status": self._client.cluster_status}


class FakeIndices:
    """The ``indices`` namespace of the fake client: aliases and index creation."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    async def exists_alias(self, *, name: str) -> bool:
        """Whether ``name`` is an alias of a created index."""
        return name in self._client.aliases

    async def create(
        self,
        *,
        index: str,
        aliases: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        **_mappings: object,
    ) -> dict[str, Any]:
        """Create ``index`` with ``aliases``; its settings and mappings are kept as given, not applied.

        The index named by ``race_lost`` answers like a create that lost to another server booting on the same
        store: the other server's index stands (it appears, alias and all) and this call is refused.
        """
        if self._client.create_error is not None:
            raise self._client.create_error
        if self._client.race_lost == index:
            self._client.race_lost = None
            self._make(index, aliases, settings, _mappings)
            raise already_exists()
        self._make(index, aliases, settings, _mappings)
        return {"acknowledged": True, "index": index}

    def _make(
        self, index: str, aliases: dict[str, Any] | None, settings: dict[str, Any] | None, _mappings: object
    ) -> None:
        """Put the index in the cluster with its alias, settings and mappings, as a create leaves them."""
        self._client.documents.setdefault(index, {})
        self._client.index_settings[index] = dict(settings or {})
        self._client.index_mappings[index] = dict(_mappings.get("mappings") or {})  # type: ignore[call-overload]
        for alias in aliases or {}:
            self._client.aliases[alias] = index

    async def put_mapping(self, *, index: str, **_mapping: object) -> dict[str, Any]:
        """Count the call; the fake keeps no mappings."""
        self._client.mapping_updates.append(index)
        return {"acknowledged": True}

    async def put_settings(self, *, index: str, settings: dict[str, Any]) -> dict[str, Any]:
        """Count the call and merge the settings into the index behind ``index``."""
        self._client.settings_updates.append(index)
        self._client.index_settings.setdefault(self._client.aliases.get(index, index), {}).update(settings)
        return {"acknowledged": True}

    async def refresh(self, *, index: str) -> dict[str, Any]:
        """Count the call; the fake's documents are always visible."""
        self._client.refreshes.append(index)
        return {"_shards": {"failed": 0}}

    async def get(self, *, index: str, **_options: object) -> FakeResponse:
        """The created indices matching ``index`` (comma-separated, wildcards, or an alias), by name, with their
        aliases and the settings and mappings they were created with.
        """  # noqa: D205 - one sentence
        names = [self._client.aliases[index]] if index in self._client.aliases else self._client.matching(index)
        return FakeResponse(
            {
                name: {
                    "aliases": {alias: {} for alias, target in self._client.aliases.items() if target == name},
                    "settings": self._client.index_settings.get(name, {}),
                    "mappings": self._client.index_mappings.get(name, {}),
                }
                for name in names
            }
        )

    async def update_aliases(self, *, actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Apply ``remove`` and ``add`` actions in order, as one change."""
        for action in actions:
            ((kind, target),) = action.items()
            if kind == "remove":
                self._client.aliases.pop(target["alias"], None)
            else:
                self._client.aliases[target["alias"]] = target["index"]
        return {"acknowledged": True}

    async def delete(self, *, index: str) -> dict[str, Any]:
        """Delete the named indices, their documents, settings and aliases; Elasticsearch refuses wildcards here."""
        for name in index.split(","):
            if "*" in name or name not in self._client.documents:
                raise _not_found()
            self._client.drop_index(name)
        return {"acknowledged": True}


class FakeSnapshot:
    """The ``snapshot`` namespace: repositories, and snapshots that copy the indices they hold (SNP-01, SNP-05)."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    async def create_repository(self, *, name: str, repository: dict[str, Any]) -> dict[str, Any]:
        """Register ``name``; it keeps the snapshots it already holds."""
        self._client.repositories[name] = repository
        self._client.snapshots.setdefault(name, {})
        return {"acknowledged": True}

    def _held(self, repository: str) -> dict[str, dict[str, Any]]:
        if repository not in self._client.repositories:
            raise _not_found()
        return self._client.snapshots[repository]

    async def get(self, *, repository: str, snapshot: str, **_options: object) -> dict[str, Any]:
        """Answer like ``GET _snapshot/repository/snapshot``, ``_all`` in the order they were taken."""
        held = self._held(repository)
        if snapshot != "_all" and snapshot not in held:
            raise _not_found()
        names = list(held) if snapshot == "_all" else [snapshot]
        return {"snapshots": [held[name]["info"] for name in names]}

    async def restore(
        self,
        *,
        repository: str,
        snapshot: str,
        indices: str,
        include_aliases: bool = True,
        **_options: object,
    ) -> dict[str, Any]:
        """Bring back the snapshot's indices matching ``indices``; an index that exists fails the restore."""
        taken = self._held(repository).get(snapshot)
        if taken is None:
            raise _not_found()
        patterns = indices.split(",")
        names = [name for name in taken["indices"] if any(fnmatch.fnmatchcase(name, p) for p in patterns)]
        if any(name in self._client.documents for name in names):
            raise _conflict()
        for name in names:
            documents, settings, aliases = copy.deepcopy(taken["indices"][name])
            self._client.documents[name], self._client.index_settings[name] = documents, settings
            if include_aliases:
                self._client.aliases.update(dict.fromkeys(aliases, name))
        total = len(names)
        return {"snapshot": {"snapshot": snapshot, "indices": names, "shards": {"total": total, "failed": 0}}}


class FakeSlm:
    """The ``slm`` namespace: one lifecycle policy per id, run on request; the fake has no clock to schedule on."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    async def put_lifecycle(self, *, policy_id: str, **policy: Any) -> dict[str, Any]:  # noqa: ANN401 - the policy's body
        """Store the policy; its run history stays."""
        self._client.policies[policy_id] = {**self._client.policies.get(policy_id, {}), "policy": policy}
        return {"acknowledged": True}

    async def get_lifecycle(self, *, policy_id: str) -> dict[str, Any]:
        """Answer like ``GET _slm/policy/policy_id``."""
        if policy_id not in self._client.policies:
            raise _not_found()
        return {policy_id: self._client.policies[policy_id]}

    async def execute_lifecycle(self, *, policy_id: str) -> dict[str, Any]:
        """Take a snapshot of the policy's indices now, or record the configured failure."""
        policy = self._client.policies[policy_id]
        repository = policy["policy"]["repository"]
        name = f"snapshot-{len(self._client.snapshots[repository]) + 1}"
        now = self._client.now_millis
        if self._client.snapshot_error is not None:
            policy["last_failure"] = {"snapshot_name": name, "time": now, "details": self._client.snapshot_error}
            return {"snapshot_name": name}
        names = self._client.matching(",".join(policy["policy"]["config"]["indices"]))
        self._client.snapshots[repository][name] = {
            "info": {"snapshot": name, "state": "SUCCESS", "start_time_in_millis": now, "indices": names},
            "indices": {
                index: copy.deepcopy(
                    (
                        self._client.documents[index],
                        self._client.index_settings.get(index, {}),
                        [alias for alias, target in self._client.aliases.items() if target == index],
                    )
                )
                for index in names
            },
        }
        policy["last_success"] = {"snapshot_name": name, "time": now}
        return {"snapshot_name": name}


class FakeClient:
    """Records how it was built and closed; ``info`` and ``cluster.health`` return or raise as configured.

    Cast it to ``AsyncElasticsearch`` where a client is expected; it implements only what the store uses.
    """

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.version = "9.5.5"
        self.cluster_name = "aurelius-atlas"
        self.cluster_status = "green"
        self.info_error: BaseException | None = None
        self.health_error: BaseException | None = None
        self.close_calls = 0
        self.cluster = FakeCluster(self)
        self.indices = FakeIndices(self)
        self.snapshot = FakeSnapshot(self)
        self.slm = FakeSlm(self)
        self.repositories: dict[str, dict[str, Any]] = {}
        self.snapshots: dict[str, dict[str, dict[str, Any]]] = {}
        """Each repository's snapshots by name, in the order taken: their info, and a copy of each index."""
        self.policies: dict[str, dict[str, Any]] = {}
        """Each lifecycle policy by id: ``policy`` as put, and its ``last_success`` and ``last_failure``."""
        self.now_millis = 1_700_000_000_000
        """The time the fake's snapshots are taken at, in epoch milliseconds."""
        self.snapshot_error: str | None = None
        """When set, each policy run fails with these details instead of taking a snapshot."""
        self.aliases: dict[str, str] = {}
        self.create_error: Exception | None = None
        """When set, each index create raises it instead of answering (a failed create other than the race)."""
        self.race_lost: str | None = None
        """The index whose next create loses to another server's identical one (DD-508); see ``FakeIndices.create``."""
        self.documents: dict[str, dict[str, tuple[dict[str, Any], int]]] = {}
        self.primary_term = 1
        self.mapping_updates: list[str] = []
        self.settings_updates: list[str] = []
        self.index_settings: dict[str, dict[str, Any]] = {}
        self.index_mappings: dict[str, dict[str, Any]] = {}
        """The mappings each index was created with, by its name."""
        """The settings of each created index, by its name: those it was created with, then each update's."""
        self.seq_no = -1
        self.refreshes: list[str] = []
        self.write_refreshes: list[tuple[str, str]] = []
        """The ``refresh`` parameter of every write, as ``(index, refresh)`` in call order (ENS-11)."""

    def matching(self, pattern: str) -> list[str]:
        """The created indices matching ``pattern``: comma-separated names or wildcards, sorted."""
        patterns = pattern.split(",")
        return sorted(name for name in self.documents if any(fnmatch.fnmatchcase(name, p) for p in patterns))

    def drop_index(self, name: str) -> None:
        """Remove an index with its documents, settings and aliases."""
        del self.documents[name]
        self.index_settings.pop(name, None)
        self.index_mappings.pop(name, None)
        for alias in [alias for alias, target in self.aliases.items() if target == name]:
            del self.aliases[alias]

    def _index_of(self, name: str) -> dict[str, tuple[dict[str, Any], int]]:
        return self.documents.setdefault(self.aliases.get(name, name), {})

    def _record_write_refresh(self, index: str, *, refresh: bool | str | None) -> None:
        """Remember the ``(index, refresh)`` of a write; the parameter is a no-op in the fake.

        A bool is recorded as Elasticsearch's wire spelling (``True`` -> ``"true"``), the
        way the real client serialises it; the parameter's type mirrors that client's
        ``bool | str | None``.
        """
        if isinstance(refresh, bool):
            refresh = "true" if refresh else "false"
        if refresh is not None:
            self.write_refreshes.append((index, refresh))

    async def get(self, *, index: str, id: str, source: bool = True) -> dict[str, Any]:  # noqa: A002 - Elasticsearch's name
        """Answer like ``GET index/_doc/id``, raising ``NotFoundError`` for a missing document."""
        stored = self._index_of(index).get(id)
        if stored is None:
            raise _not_found()
        document, seq_no = stored
        response: dict[str, Any] = {"_id": id, "_seq_no": seq_no, "_primary_term": self.primary_term, "found": True}
        if source:
            response["_source"] = document
        return response

    async def index(  # noqa: PLR0913 - Elasticsearch's keyword arguments
        self,
        *,
        index: str,
        id: str,  # noqa: A002 - Elasticsearch's name
        document: dict[str, Any] | bytes,
        op_type: str | None = None,
        if_seq_no: int | None = None,
        if_primary_term: int | None = None,
        refresh: bool | str | None = None,
        **_options: object,
    ) -> dict[str, Any]:
        """Store ``document``, raising ``ConflictError`` like Elasticsearch for ``op_type=create`` or ``if_seq_no``.

        A body given as bytes is read as Elasticsearch reads it, its floats kept as decimals.
        """
        self._record_write_refresh(index, refresh=refresh)
        if isinstance(document, bytes):
            document = _read(document)
        documents = self._index_of(index)
        current = documents.get(id)
        if op_type == "create" and current is not None:
            raise _conflict()
        if if_seq_no is not None and (
            current is None or current[1] != if_seq_no or if_primary_term != self.primary_term
        ):
            raise _conflict()
        self.seq_no += 1
        seq_no = self.seq_no
        documents[id] = (document, seq_no)
        return {"_id": id, "_seq_no": seq_no, "_primary_term": self.primary_term, "result": "created"}

    async def mget(self, *, index: str, ids: list[str]) -> dict[str, Any]:
        """Answer like ``_mget``: one entry per id, ``found`` or not."""
        docs = []
        for document_id in ids:
            try:
                docs.append(await self.get(index=index, id=document_id))
            except NotFoundError:
                docs.append({"_id": document_id, "found": False})
        return {"docs": docs}

    async def bulk(self, *, operations: bytes, refresh: bool | str | None = None, **_options: object) -> dict[str, Any]:
        """Apply ``create``, ``index`` and ``delete`` actions of an NDJSON body, each with its own outcome."""
        lines = iter([line for line in operations.split(b"\n") if line.strip()])
        items = []
        for action_line in lines:
            ((kind, action),) = _read(action_line).items()
            self._record_write_refresh(action["_index"], refresh=refresh)
            versions = {"if_seq_no": action.get("if_seq_no"), "if_primary_term": action.get("if_primary_term")}
            try:
                if kind == "delete":
                    result = await self.delete(index=action["_index"], id=action["_id"], **versions)
                else:
                    result = await self.index(
                        index=action["_index"],
                        id=action["_id"],
                        document=_read(next(lines)),
                        op_type="create" if kind == "create" else None,
                        **versions,
                    )
                items.append({kind: {"_id": action["_id"], "status": 200 if kind == "delete" else 201, **result}})
            except ConflictError:
                items.append({kind: {"_id": action["_id"], "status": 409}})
            except NotFoundError:
                items.append({kind: {"_id": action["_id"], "status": 404}})
        return {"errors": any(next(iter(item.values()))["status"] >= 300 for item in items), "items": items}  # noqa: PLR2004

    async def delete(
        self,
        *,
        index: str,
        id: str,  # noqa: A002 - Elasticsearch's name
        if_seq_no: int | None = None,
        if_primary_term: int | None = None,
        refresh: bool | str | None = None,
        **_options: object,
    ) -> dict[str, Any]:
        """Delete a document, raising ``NotFoundError`` when missing and ``ConflictError`` on a stale version."""
        self._record_write_refresh(index, refresh=refresh)
        documents = self._index_of(index)
        current = documents.get(id)
        if current is None:
            raise _not_found()
        if if_seq_no is not None and (current[1] != if_seq_no or if_primary_term != self.primary_term):
            raise _conflict()
        del documents[id]
        return {"_id": id, "result": "deleted"}

    async def search(  # noqa: PLR0913 - Elasticsearch's keyword arguments
        self,
        *,
        index: str,
        size: int = 10,
        query: dict[str, Any] | None = None,
        sort: list[Any] | None = None,
        search_after: list[Any] | None = None,
        seq_no_primary_term: bool = False,
        from_: int = 0,
        track_total_hits: bool | None = None,
        track_scores: bool | None = None,
        aggs: dict[str, Any] | None = None,
        knn: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Answer like ``_search`` with the documents matching the query, ``size`` of them from ``from_``.

        With ``sort``, hits are ordered by the sort fields (``_score`` among them) and carry their sort values; a
        plain direction stands a document without the field in with its id, an options object puts it last. Only
        hits after ``search_after`` are answered. The total counts every match; each hit has its ``_score``.
        ``terms`` and ``composite`` aggregations count the values of every match. A ``knn`` adds the ``k`` nearest
        documents its ``filter`` matches, scored ``(1 + cosine) / 2`` times its ``boost``, to the query's matches,
        the scores of both added; without a query only the nearest match.
        """
        _ = track_total_hits, track_scores
        order = [_sort_clause(clause) for clause in sort or []]
        nearest = _nearest(self._index_of(index), knn)
        hits = []
        for document_id, (source, seq_no) in self._index_of(index).items():
            matched = (knn is None or query is not None) and _matches(source, query, document_id)
            score = (_score(source, query) if matched else 0.0) + nearest.get(document_id, 0.0)
            values = [
                score if field == "_score" else _sort_value(source, field, document_id, options)
                for field, options in order
            ]
            if not (matched or document_id in nearest) or (
                search_after is not None and _compare(values, search_after, order) <= 0
            ):
                continue
            hit: dict[str, Any] = {"_id": document_id, "_source": source, "_score": score}
            if seq_no_primary_term:
                hit |= {"_seq_no": seq_no, "_primary_term": self.primary_term}
            if sort:
                hit["sort"] = values
            hits.append(hit)
        if sort:
            hits.sort(key=cmp_to_key(lambda a, b: _compare(a["sort"], b["sort"], order)))
        response: dict[str, Any] = {"hits": {"total": {"value": len(hits)}, "hits": hits[from_ : from_ + size]}}
        if aggs:
            sources = [hit["_source"] for hit in hits]
            response["aggregations"] = {
                name: _composite(sources, spec["composite"]) if "composite" in spec else _terms(sources, spec["terms"])
                for name, spec in aggs.items()
            }
        return response

    async def reindex(
        self, *, source: dict[str, Any], dest: dict[str, Any], refresh: bool | None = None, **_options: object
    ) -> dict[str, Any]:
        """Copy every document of ``source``'s index into ``dest``'s, its source as stored, with new versions."""
        del refresh
        copied = 0
        for document_id, (document, _) in self._index_of(source["index"]).items():
            await self.index(index=dest["index"], id=document_id, document=document, op_type=dest.get("op_type"))
            copied += 1
        return {"total": copied, "created": copied, "failures": []}

    async def count(self, *, index: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Answer like ``_count`` for a ``match_all`` or ``term`` query."""
        return {"count": sum(1 for source, _ in self._index_of(index).values() if _matches(source, query))}

    async def info(self) -> dict[str, Any]:
        """Answer like ``GET /``, or raise the configured error."""
        if self.info_error is not None:
            raise self.info_error
        return {"cluster_name": self.cluster_name, "version": {"number": self.version}}

    async def close(self) -> None:
        """Count the call."""
        self.close_calls += 1


def _read(body: bytes) -> dict[str, Any]:
    """A JSON body as Elasticsearch reads it, its floats as decimals."""
    return json.loads(body, parse_float=Decimal)


def _matches(source: dict[str, Any], query: dict[str, Any] | None, document_id: str | None = None) -> bool:
    """Whether ``source``, the document ``document_id``, matches a query: ``match_all``, ``match_none``, ``ids``,
    ``bool`` (``filter``, ``must``, ``must_not``, ``should``), ``simple_query_string``, and single-field ``term``,
    ``terms``, ``range``, ``prefix``, ``wildcard``, ``regexp`` (Python's, whole values or a ``.text`` sub-field's
    words) and ``exists``.
    """  # noqa: D205 - one sentence
    if query is None or "match_all" in query:
        return True
    if "match_none" in query or "ids" in query:
        return "ids" in query and document_id in query["ids"]["values"]
    if "bool" in query:
        clauses = query["bool"]
        should = clauses.get("should", [])
        return (
            all(_matches(source, clause, document_id) for clause in clauses.get("filter", []) + clauses.get("must", []))
            and not any(_matches(source, clause, document_id) for clause in clauses.get("must_not", []))
            and (not should or any(_matches(source, clause, document_id) for clause in should))
        )
    if "simple_query_string" in query:
        return _text_score(source, query["simple_query_string"]) > 0
    if "exists" in query:
        return _held(source, query["exists"]["field"]) != []
    ((kind, condition),) = query.items()
    ((field, operand),) = condition.items()
    return _field_matches(source, kind, field, operand)


def _field_matches(source: dict[str, Any], kind: str, field: str, operand: Any) -> bool:  # noqa: ANN401 - a query operand
    """A single-field query: ``term``, ``terms``, ``range``, ``prefix``, ``wildcard`` or ``regexp``."""
    if kind == "regexp":
        return _regexp(source, field, operand)
    held = _held(source, field)
    if kind == "range":
        return any(_in_range(value, operand) for value in held)
    if kind == "terms":
        return any(value in held for value in operand)
    if kind == "prefix":
        return any(isinstance(value, str) and value.startswith(operand) for value in held)
    if kind == "wildcard":
        options = operand if isinstance(operand, dict) else {"value": operand}
        pattern = _wildcard(options["value"], ignore_case=bool(options.get("case_insensitive")))
        return any(isinstance(value, str) and pattern.fullmatch(value) is not None for value in held)
    return operand in held


def _regexp(source: dict[str, Any], field: str, options: dict[str, Any]) -> bool:
    """A ``regexp``: a value, or for a ``.text`` sub-field a lower-cased word of one, matching whole."""
    pattern = re.compile(options["value"], re.IGNORECASE if options.get("case_insensitive") else 0)
    if field.endswith(".text"):
        values = [
            word.lower() for value in _held(source, field.removesuffix(".text")) for word in _WORD.findall(str(value))
        ]
    else:
        values = [value for value in _held(source, field) if isinstance(value, str)]
    return any(pattern.fullmatch(value) is not None for value in values)


def _nearest(documents: dict[str, tuple[dict[str, Any], int]], knn: dict[str, Any] | None) -> dict[str, float]:
    """The ``k`` documents nearest to a ``knn``'s vector among those its filter matches, by id, with their scores."""
    if knn is None:
        return {}
    target = knn["query_vector"]
    scored = []
    for document_id, (source, _) in documents.items():
        held = _held(source, knn["field"])
        if not held or not _matches(source, knn.get("filter"), document_id):
            continue
        vector = [float(value) for value in held]
        norms = math.sqrt(sum(a * a for a in vector)) * math.sqrt(sum(b * b for b in target))
        cosine = sum(a * b for a, b in zip(vector, target, strict=True)) / norms if norms else 0.0
        scored.append(((1 + cosine) / 2 * float(knn.get("boost", 1.0)), document_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return {document_id: score for score, document_id in scored[: knn["k"]]}


def _score(source: dict[str, Any], query: dict[str, Any] | None) -> float:
    """A document's score: what its ``simple_query_string`` clauses, alone or in a ``bool``'s ``must``, give it."""
    if query is None:
        return 0.0
    if "simple_query_string" in query:
        return _text_score(source, query["simple_query_string"])
    return sum((_score(source, clause) for clause in query.get("bool", {}).get("must", [])), 0.0)


def _text_score(source: dict[str, Any], options: dict[str, Any]) -> float:
    """A ``simple_query_string`` read word by word: each field (``.text`` sub-field, ``^`` boost) whose words, in
    any case, hold one of the query's, or one beginning with a word ending in ``*``, adds its boost.
    """  # noqa: D205 - one sentence
    terms = [term.lower() for term in _QUERY_WORD.findall(options["query"])]
    score = 0.0
    for spec in options["fields"]:
        name, _, boost = spec.partition("^")
        words = {
            word.lower() for value in _held(source, name.removesuffix(".text")) for word in _WORD.findall(str(value))
        }
        if any(_term_in(term, words) for term in terms):
            score += float(boost or 1)
    return score


def _terms(sources: list[dict[str, Any]], options: dict[str, Any]) -> dict[str, Any]:
    """A ``terms`` aggregation, by count then key: a ``.text`` sub-field's lowercased words, else the values;
    ``include`` a regular expression the whole term matches.
    """  # noqa: D205 - one sentence
    field: str = options["field"]
    text = field.endswith(".text")
    include = re.compile(options["include"]) if "include" in options else None
    counts: dict[Any, int] = {}
    for source in sources:
        held = _held(source, field.removesuffix(".text") if text else field)
        terms = {word.lower() for value in held for word in _WORD.findall(str(value))} if text else set(held)
        for term in terms:
            if include is None or include.fullmatch(str(term)):
                counts[term] = counts.get(term, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[: options.get("size", 10)]
    return {"buckets": [{"key": key, "doc_count": count} for key, count in ordered]}


def _composite(sources: list[dict[str, Any]], options: dict[str, Any]) -> dict[str, Any]:
    """A ``composite`` aggregation of ``terms`` sources, by key with a missing value first, ``size`` buckets after
    ``after``; a document without a value of a source is left out unless it has ``missing_bucket``.
    """  # noqa: D205 - one sentence
    names = [next(iter(source)) for source in options["sources"]]
    fields = [next(iter(source.values()))["terms"] for source in options["sources"]]
    counts: dict[tuple[Any, ...], int] = {}
    for source in sources:
        held = [_held(source, terms["field"]) for terms in fields]
        if any(not values and not terms.get("missing_bucket") for values, terms in zip(held, fields, strict=True)):
            continue
        key = tuple(values[0] if values else None for values in held)
        counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: [(value is not None, value) for value in item[0]])
    if "after" in options:
        after = [(options["after"][name] is not None, options["after"][name]) for name in names]
        ordered = [item for item in ordered if [(value is not None, value) for value in item[0]] > after]
    buckets = [
        {"key": dict(zip(names, key, strict=True)), "doc_count": count} for key, count in ordered[: options["size"]]
    ]
    return {"buckets": buckets, **({"after_key": buckets[-1]["key"]} if buckets else {})}


def _term_in(term: str, words: set[str]) -> bool:
    if term.endswith("*"):
        return any(word.startswith(term[:-1]) for word in words)
    return term in words


_WORD = re.compile(r"\w+")
_QUERY_WORD = re.compile(r"\w+\*?")


def _value(source: dict[str, Any], field: str) -> Any:  # noqa: ANN401 - any field value
    """A field's value: by its full name, or through objects, as a dotted path."""
    if field in source:
        return source[field]
    head, separator, rest = field.partition(".")
    while separator:
        inner = source.get(head)
        if isinstance(inner, dict):
            found = _value(inner, rest)
            if found is not None:
                return found
        step, separator, rest = rest.partition(".")
        head = f"{head}.{step}"
    return None


def _held(source: dict[str, Any], field: str) -> list[Any]:
    """The values a field holds: none, one, or an array's."""
    value = _value(source, field)
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _wildcard(pattern: str, *, ignore_case: bool = False) -> re.Pattern[str]:
    """An Elasticsearch wildcard pattern as a regular expression: ``*``, ``?``, and backslash escaping."""
    parts, escaped = [], False
    for character in pattern:
        if escaped:
            parts.append(re.escape(character))
            escaped = False
        elif character == "\\":
            escaped = True
        else:
            parts.append(_WILDCARDS.get(character) or re.escape(character))
    return re.compile("".join(parts), re.DOTALL | (re.IGNORECASE if ignore_case else 0))


_WILDCARDS = {"*": ".*", "?": "."}


def _sort_clause(clause: Any) -> tuple[str, dict[str, Any]]:  # noqa: ANN401 - a sort clause
    ((field, options),) = clause.items()
    return field, options if isinstance(options, dict) else {"order": options, "missing": "_id"}


def _sort_value(source: dict[str, Any], field: str, document_id: str, options: dict[str, Any]) -> Any:  # noqa: ANN401
    """A hit's value of a sort field: an array's least, or largest descending; the id or None when missing."""
    held = _held(source, field)
    if not held:
        return document_id if options.get("missing") == "_id" else None
    return max(held) if options.get("order") == "desc" else min(held)


_BOUNDS = {
    "gt": lambda value, bound: value > bound,
    "gte": lambda value, bound: value >= bound,
    "lt": lambda value, bound: value < bound,
    "lte": lambda value, bound: value <= bound,
}


def _in_range(value: Any, bounds: dict[str, Any]) -> bool:  # noqa: ANN401 - any field value
    """Whether a present value meets every bound of a ``range`` query."""
    return value is not None and all(_BOUNDS[name](value, bound) for name, bound in bounds.items())


def _compare(left: list[Any], right: list[Any], order: list[tuple[str, dict[str, Any]]]) -> int:
    """Compare two hits' sort values field by field, each ascending or descending, missing ones last."""
    for a, b, (_, options) in zip(left, right, order, strict=False):
        if a == b:
            continue
        if a is None or b is None:
            return 1 if a is None else -1
        smaller = -1 if a < b else 1
        return -smaller if options.get("order") == "desc" else smaller
    return 0
