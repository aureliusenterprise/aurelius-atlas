"""The glossary and category endpoints of ``GlossaryREST`` (GLS-01 to GCT-07), on the fake Elasticsearch.

Read from ``GlossaryREST`` of Apache Atlas 2.4.0; the service is tested on ``GlossaryService`` in
``aurelius-atlas-core``.
"""

import shutil
from pathlib import Path
from typing import Any

import httpx
import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR

R = "aurelius_atlas_server.routes.glossary"
GLOSSARY = "/api/atlas/v2/glossary"
MODELS = (Path("0000-Area0") / "0010-base_model.json", Path("0000-Area0") / "0011-glossary_model.json")


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base and glossary models alone (MDL-16)."""
    directory = tmp_path / "core-models"
    for model in MODELS:
        (directory / model.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy(BUILTIN_MODELS_DIR / model, directory / model)
    return directory


async def send(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and the JSON body, None without one."""
    response = await client.request(method, url, **kwargs)
    return response.status_code, response.json() if response.content else None


@pytest.mark.covers(
    f"{R}.create_glossary",
    f"{R}.get_glossary",
    f"{R}.get_glossaries",
    f"{R}.update_glossary",
    f"{R}.partial_update_glossary",
    f"{R}.get_detailed_glossary",
    f"{R}.delete_glossary",
    rules=["GLS-01", "GLS-02", "GLS-03", "GLS-04", "GLS-05", "GLS-06"],
)
async def test__a_glossary_is_created_read_updated_and_deleted(client: httpx.AsyncClient) -> None:
    """The glossary endpoints in turn, with Atlas's failures."""
    status, created = await send(client, "POST", GLOSSARY, json={"name": "bank", "shortDescription": "s"})
    guid = created["guid"]
    assert (status, created["qualifiedName"]) == (200, "bank")
    assert (await send(client, "GET", f"{GLOSSARY}/{guid}"))[1]["name"] == "bank"
    _, listed = await send(client, "GET", GLOSSARY, params={"limit": "1", "sort": "DESC"})
    assert [found["name"] for found in listed] == ["bank"]
    _, updated = await send(client, "PUT", f"{GLOSSARY}/{guid}", json={"name": "bank", "usage": "u"})
    assert (updated["guid"], updated["usage"]) == (guid, "u")
    _, partial = await send(client, "PUT", f"{GLOSSARY}/{guid}/partial", json={"language": "en"})
    assert (partial["language"], partial["usage"]) == ("en", "u")
    assert (await send(client, "GET", f"{GLOSSARY}/{guid}/detailed"))[1]["guid"] == guid
    failures = [
        ("POST", GLOSSARY, {"json": {"name": "bank"}}, 409, "ATLAS-409-00-007"),
        ("POST", GLOSSARY, {"json": {"name": "a.b"}}, 400, "ATLAS-400-00-083"),
        ("PUT", f"{GLOSSARY}/{guid}/partial", {"json": {"qualifiedName": "x"}}, 400, "ATLAS-400-00-074"),
        ("PUT", f"{GLOSSARY}/{guid}/partial", {"json": {}}, 400, "ATLAS-400-00-029"),
        ("GET", GLOSSARY, {"params": {"limit": "x"}}, 400, "ATLAS-400-00-029"),
        ("GET", f"{GLOSSARY}/nope", {}, 404, "ATLAS-404-00-005"),
    ]
    for method, url, kwargs, expected, code in failures:
        status, body = await send(client, method, url, **kwargs)
        assert (status, body["errorCode"]) == (expected, code), (method, url, body)
    _, bad_partial = await send(client, "PUT", f"{GLOSSARY}/{guid}/partial", json={"qualifiedName": "x"})
    assert bad_partial["errorMessage"] == "Invalid attribute qualifiedName for partial update of Glossary"
    assert (await send(client, "DELETE", f"{GLOSSARY}/{guid}"))[0] == 204
    assert (await send(client, "GET", f"{GLOSSARY}/{guid}"))[0] == 404


@pytest.mark.covers(
    f"{R}.create_glossary_category",
    f"{R}.create_glossary_categories",
    f"{R}.get_glossary_category",
    f"{R}.update_glossary_category",
    f"{R}.partial_update_glossary_category",
    f"{R}.get_related_categories",
    f"{R}.get_glossary_categories",
    f"{R}.get_glossary_categories_headers",
    f"{R}.delete_glossary_category",
    rules=["GCT-01", "GCT-02", "GCT-03", "GCT-04", "GCT-05", "GCT-06", "GCT-07", "GLS-05"],
)
async def test__categories_are_created_related_updated_and_deleted(client: httpx.AsyncClient) -> None:
    """The category endpoints in turn, with Atlas's failures and its swapped partial update message."""
    _, glossary = await send(client, "POST", GLOSSARY, json={"name": "g"})
    anchor = {"glossaryGuid": glossary["guid"]}
    _, parent = await send(client, "POST", f"{GLOSSARY}/category", json={"name": "p", "anchor": anchor})
    _, (child,) = await send(
        client,
        "POST",
        f"{GLOSSARY}/categories",
        json=[{"name": "c", "anchor": anchor, "parentCategory": {"categoryGuid": parent["guid"]}}],
    )
    assert (parent["qualifiedName"], child["qualifiedName"]) == ("p@g", "c.p@g")
    _, related = await send(client, "GET", f"{GLOSSARY}/category/{child['guid']}/related")
    assert [header["categoryGuid"] for header in related["parent"]] == [parent["guid"]]
    _, headers = await send(client, "GET", f"{GLOSSARY}/{glossary['guid']}/categories/headers")
    assert [header["displayText"] for header in headers] == ["c", "p"]
    _, categories = await send(client, "GET", f"{GLOSSARY}/{glossary['guid']}/categories", params={"limit": "1"})
    assert [found["name"] for found in categories] == ["c"]
    _, partial = await send(
        client, "PUT", f"{GLOSSARY}/category/{child['guid']}/partial", json={"longDescription": "l"}
    )
    assert partial["longDescription"] == "l"
    _, bad = await send(client, "PUT", f"{GLOSSARY}/category/{child['guid']}/partial", json={"language": "x"})
    assert bad["errorMessage"] == "Invalid attribute Glossary Category for partial update of language"
    full = (await send(client, "GET", f"{GLOSSARY}/category/{child['guid']}"))[1]
    full["shortDescription"] = "s"
    _, updated = await send(client, "PUT", f"{GLOSSARY}/category/{child['guid']}", json=full)
    assert (updated["guid"], updated["shortDescription"]) == (child["guid"], "s")
    status, missing = await send(client, "POST", f"{GLOSSARY}/category", json={"name": "x"})
    assert (status, missing["errorCode"]) == (400, "ATLAS-400-00-072")
    status, missing_many = await send(client, "POST", f"{GLOSSARY}/categories", json=[{"name": "x"}])
    assert (status, missing_many["errorCode"]) == (400, "ATLAS-400-00-072")
    assert (await send(client, "DELETE", f"{GLOSSARY}/category/{child['guid']}"))[0] == 204
    assert (await send(client, "GET", f"{GLOSSARY}/category/{child['guid']}"))[0] == 404
