"""Spike 11.1 probes HGS-01..03 against the spike's HugeGraph server (spikes/hugegraph/docker-compose.yaml).

HGS-03: schema added while the server runs, and an index built over vertices written before it.
HGS-02: concurrent writers creating vertices that share one value of a UNIQUE index, through the REST vertex API and
through Gremlin ``addV``.
HGS-01: concurrent writers updating one vertex conditionally on its version, read-check-write in one Gremlin script.

Run: .venv/bin/python spikes/hugegraph/probe_writes.py [--rounds N] [--writers N] [--repeat N]
"""

import argparse
import asyncio
import json
import time
import uuid
from collections import Counter
from typing import Any

import httpx

URL = "http://127.0.0.1:18080"
GRAPH = f"{URL}/graphs/hugegraph"
OK = 200
CREATED = (200, 201, 202)
PRELOADED = 2000
"""Vertices written before the index of HGS-03 exists."""
ALIASES = {"graph": "DEFAULT-hugegraph", "g": "__g_DEFAULT-hugegraph"}
"""Graph spaces (1.7) bind the graph as DEFAULT-hugegraph; a wrong alias desyncs the endpoint (hugegraph#2284)."""


class ProbeError(RuntimeError):
    """A probe request failed."""


class DesyncedError(ProbeError):
    """The REST Gremlin endpoint answered with another request's result (apache/hugegraph#2284)."""


class Probe:
    """One run's labels and property keys, suffixed with its id so runs never meet."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Probe through ``client``."""
        self.client = client
        self.run = uuid.uuid4().hex[:8]

    def key(self, name: str) -> str:
        """``name`` as this run's property key or label."""
        return f"{name}_{self.run}"

    async def schema(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        """Create a schema element of ``kind``; waits for the index build an index label starts."""
        response = await self.client.post(f"{GRAPH}/schema/{kind}", json=body)
        if response.status_code not in CREATED:
            message = f"{kind} {body['name']}: {response.status_code} {response.text}"
            raise ProbeError(message)
        created = response.json()
        if created.get("task_id"):
            created["task"] = await self.wait_task(created["task_id"])
        return created

    async def wait_task(self, task_id: int) -> dict[str, Any]:
        """The server task ``task_id`` once it has ended."""
        while True:
            task = (await self.client.get(f"{GRAPH}/tasks/{task_id}")).json()
            if task.get("task_status") in ("success", "failed", "cancelled"):
                return task
            await asyncio.sleep(0.5)

    async def gremlin(self, script: str, bindings: dict[str, Any] | None = None, *, strict: bool = True) -> Any:  # noqa: ANN401 - Gremlin results
        """The result of ``script``, or None for a failed script unless ``strict``.

        The result travels with a nonce, so an answer that belongs to another request is caught.
        """
        nonce = uuid.uuid4().hex
        response = await self.client.post(
            f"{URL}/gremlin",
            json={
                "gremlin": f"r = {{ {script} }}.call(); [nonce, r instanceof Iterator ? r.toList() : r]",
                "bindings": {**(bindings or {}), "nonce": nonce},
                "language": "gremlin-groovy",
                "aliases": ALIASES,
            },
        )
        if response.status_code != OK:
            if strict:
                message = f"{script[:80]}: {response.status_code} {response.text[:300]}"
                raise ProbeError(message)
            return None
        answered, result = response.json()["result"]["data"]
        if answered != nonce:
            message = f"sent {nonce}, got {answered}"
            raise DesyncedError(message)
        return result

    async def entity_label(self) -> str:
        """A vertex label with a version, a writer and a qualified name, keyed by GUID."""
        label = self.key("entity")
        keys = {"guid": "TEXT", "version": "LONG", "writer": "INT", "qualifiedName": "TEXT"}
        for name, data_type in keys.items():
            await self.schema("propertykeys", {"name": self.key(name), "data_type": data_type, "cardinality": "SINGLE"})
        await self.schema(
            "vertexlabels",
            {
                "name": label,
                "id_strategy": "PRIMARY_KEY",
                "primary_keys": [self.key("guid")],
                "properties": [self.key(name) for name in keys],
                "nullable_keys": [self.key(name) for name in keys if name != "guid"],
            },
        )
        return label

    async def unique_label(self) -> str:
        """A vertex label whose qualified name has a UNIQUE index."""
        label = self.key("unique")
        for name in ("uguid", "uqualifiedName"):
            await self.schema("propertykeys", {"name": self.key(name), "data_type": "TEXT", "cardinality": "SINGLE"})
        await self.schema(
            "vertexlabels",
            {
                "name": label,
                "id_strategy": "PRIMARY_KEY",
                "primary_keys": [self.key("uguid")],
                "properties": [self.key("uguid"), self.key("uqualifiedName")],
            },
        )
        await self.schema(
            "indexlabels",
            {
                "name": self.key("uniqueQn"),
                "base_type": "VERTEX_LABEL",
                "base_value": label,
                "index_type": "UNIQUE",
                "fields": [self.key("uqualifiedName")],
            },
        )
        return label

    async def hgs_03(self) -> dict[str, Any]:
        """Vertices, then a property key, an attribute on the label and an index: Atlas types change at runtime."""
        label = await self.entity_label()
        started = time.perf_counter()
        for start in range(0, PRELOADED, 500):
            vertices = [
                {"label": label, "properties": {self.key("guid"): f"pre-{n}", self.key("qualifiedName"): f"qn-{n}"}}
                for n in range(start, start + 500)
            ]
            (await self.client.post(f"{GRAPH}/graph/vertices/batch", json=vertices)).raise_for_status()
        load = time.perf_counter() - started
        await self.schema(
            "propertykeys", {"name": self.key("description"), "data_type": "TEXT", "cardinality": "SINGLE"}
        )
        append = await self.client.put(
            f"{GRAPH}/schema/vertexlabels/{label}?action=append",
            json={"name": label, "properties": [self.key("description")], "nullable_keys": [self.key("description")]},
        )
        started = time.perf_counter()
        index = await self.schema(
            "indexlabels",
            {
                "name": self.key("byQn"),
                "base_type": "VERTEX_LABEL",
                "base_value": label,
                "index_type": "SECONDARY",
                "fields": [self.key("qualifiedName")],
            },
        )
        built = time.perf_counter() - started
        found = await self.gremlin(f"g.V().hasLabel('{label}').has('{self.key('qualifiedName')}', 'qn-1234').count()")
        return {
            "vertices_before_index": PRELOADED,
            "load_seconds": round(load, 2),
            "append_property_status": append.status_code,
            "index_task": index.get("task", {}).get("task_status"),
            "index_seconds": round(built, 2),
            "lookup_after_index": found,
        }

    async def duplicates(self, label: str, name: str) -> int:
        """How many vertices of ``label`` hold ``name``; a UNIQUE index answers no query, so the label is scanned."""
        values = f"g.V().hasLabel('{label}').values('{self.key('uqualifiedName')}').toList().count('{name}')"
        return await self.gremlin(values)

    async def hgs_02(self, rounds: int, writers: int) -> dict[str, Any]:
        """Per round, ``writers`` concurrent creates of one unique value, through REST and through Gremlin."""
        label = await self.unique_label()
        report = {}
        for via in ("rest", "gremlin"):
            accepted = rounds_with_duplicates = 0
            for round_ in range(rounds):
                name = f"{via}-shared-{round_}"
                created = await asyncio.gather(*(self.create_unique(via, label, name, w) for w in range(writers)))
                accepted += sum(created)
                rounds_with_duplicates += await self.duplicates(label, name) > 1
            report[via] = {"accepted_writes": accepted, "rounds_with_duplicates": rounds_with_duplicates}
        return {"rounds": rounds, "writers": writers, **report}

    async def create_unique(self, via: str, label: str, name: str, writer: int) -> bool:
        """Whether a create of ``name`` by ``writer`` was accepted."""
        guid, qualified = self.key("uguid"), self.key("uqualifiedName")
        if via == "rest":
            response = await self.client.post(
                f"{GRAPH}/graph/vertices",
                json={"label": label, "properties": {guid: f"{name}-{writer}", qualified: name}},
            )
            return response.status_code in CREATED
        created = await self.gremlin(
            "g.addV(lbl).property(gk, gid).property(qk, qn).id()",
            {"lbl": label, "gk": guid, "gid": f"{name}-{writer}", "qk": qualified, "qn": name},
            strict=False,
        )
        return created is not None

    async def hgs_01(self, rounds: int, writers: int) -> dict[str, Any]:
        """Per round, ``writers`` concurrent conditional writes of one vertex; two winners of one version lose one."""
        created = await self.client.post(
            f"{GRAPH}/graph/vertices",
            json={
                "label": self.key("entity"),
                "properties": {self.key("guid"): uuid.uuid4().hex, self.key("version"): 0},
            },
        )
        created.raise_for_status()
        vertex = created.json()["id"]
        # Read the version, then write version + 1 only if it is still the one read.
        script = (
            "v = g.V(vid).next(); seen = v.value(vkey); Thread.sleep(20);"
            "updated = g.V(vid).has(vkey, seen).property(vkey, seen + 1).property(wkey, writer).toList();"
            "[seen, updated.size()]"
        )
        bindings = {"vid": vertex, "vkey": self.key("version"), "wkey": self.key("writer")}
        claims = lost = 0
        for _ in range(rounds):
            results = await asyncio.gather(
                *(self.gremlin(script, {**bindings, "writer": w}, strict=False) for w in range(writers))
            )
            winners = Counter(result[0] for result in results if result and result[1] == 1)
            claims += sum(winners.values())
            lost += sum(count - 1 for count in winners.values() if count > 1)
        return {"rounds": rounds, "writers": writers, "successful_claims": claims, "lost_updates": lost}


async def main() -> None:
    """Run the probes and print their report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--writers", type=int, default=20)
    parser.add_argument("--repeat", type=int, default=1, help="runs of HGS-01")
    options = parser.parse_args()
    async with httpx.AsyncClient(timeout=120, limits=httpx.Limits(max_connections=100)) as client:
        probe = Probe(client)
        report = {
            "run": probe.run,
            "HGS-03": await probe.hgs_03(),
            "HGS-02": await probe.hgs_02(options.rounds, options.writers),
            "HGS-01": [await probe.hgs_01(options.rounds, options.writers) for _ in range(options.repeat)],
        }
    print(json.dumps(report, indent=2))  # noqa: T201 - the probe's report


if __name__ == "__main__":
    asyncio.run(main())
