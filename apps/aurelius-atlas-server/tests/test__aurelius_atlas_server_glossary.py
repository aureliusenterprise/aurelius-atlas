"""The glossary, category and term endpoints of ``GlossaryREST`` (GLS-01 to GTM-07), on the fake Elasticsearch.

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


@pytest.mark.covers(
    f"{R}.create_glossary_term",
    f"{R}.create_glossary_terms",
    f"{R}.get_glossary_term",
    f"{R}.update_glossary_term",
    f"{R}.partial_update_glossary_term",
    f"{R}.get_related_terms",
    f"{R}.get_category_terms",
    f"{R}.get_glossary_terms",
    f"{R}.get_glossary_term_headers",
    f"{R}.delete_glossary_term",
    rules=["GTM-01", "GTM-02", "GTM-03", "GTM-04", "GTM-05", "GTM-06", "GTM-07"],
)
async def test__terms_are_created_related_updated_and_deleted(client: httpx.AsyncClient) -> None:
    """The term endpoints in turn, with Atlas's failures and its swapped partial update message."""
    _, glossary = await send(client, "POST", GLOSSARY, json={"name": "bank"})
    anchor = {"glossaryGuid": glossary["guid"]}
    _, category = await send(client, "POST", f"{GLOSSARY}/category", json={"name": "accounts", "anchor": anchor})
    _, checking = await send(
        client,
        "POST",
        f"{GLOSSARY}/term",
        json={"name": "checking", "anchor": anchor, "categories": [{"categoryGuid": category["guid"]}]},
    )
    assert (checking["qualifiedName"], checking["categories"][0]["displayText"]) == ("checking@bank", "accounts")
    _, (savings,) = await send(
        client,
        "POST",
        f"{GLOSSARY}/terms",
        json=[{"name": "savings", "anchor": anchor, "seeAlso": [{"termGuid": checking["guid"], "status": "DRAFT"}]}],
    )
    assert [(h["termGuid"], h["qualifiedName"], h["status"]) for h in savings["seeAlso"]] == [
        (checking["guid"], "checking@bank", "DRAFT")
    ]
    _, related = await send(client, "GET", f"{GLOSSARY}/terms/{checking['guid']}/related")
    assert [header["termGuid"] for header in related["seeAlso"]] == [savings["guid"]]
    _, headers = await send(client, "GET", f"{GLOSSARY}/{glossary['guid']}/terms/headers", params={"sort": "DESC"})
    assert [header["displayText"] for header in headers] == ["savings", "checking"]
    _, terms = await send(client, "GET", f"{GLOSSARY}/{glossary['guid']}/terms", params={"limit": "1"})
    assert [found["name"] for found in terms] == ["checking"]
    _, in_category = await send(client, "GET", f"{GLOSSARY}/category/{category['guid']}/terms")
    assert [header["termGuid"] for header in in_category] == [checking["guid"]]
    _, detailed = await send(client, "GET", f"{GLOSSARY}/{glossary['guid']}/detailed")
    assert set(detailed["termInfo"]) == {checking["guid"], savings["guid"]}
    _, partial = await send(client, "PUT", f"{GLOSSARY}/term/{savings['guid']}/partial", json={"abbreviation": "SAV"})
    assert (partial["abbreviation"], partial["seeAlso"][0]["termGuid"]) == ("SAV", checking["guid"])
    _, bad = await send(client, "PUT", f"{GLOSSARY}/term/{savings['guid']}/partial", json={"language": "x"})
    assert bad["errorMessage"] == "Invalid attribute Glossary Term for partial update of language"
    full = (await send(client, "GET", f"{GLOSSARY}/term/{savings['guid']}"))[1]
    full["seeAlso"], full["usage"] = [], "u"
    _, updated = await send(client, "PUT", f"{GLOSSARY}/term/{savings['guid']}", json=full)
    assert (updated["guid"], updated["usage"], "seeAlso" in updated) == (savings["guid"], "u", False)
    _, unrelated = await send(client, "GET", f"{GLOSSARY}/terms/{checking['guid']}/related")
    assert unrelated == {}
    failures = [
        ("POST", f"{GLOSSARY}/term", {"json": {"name": "x"}}, 400, "ATLAS-400-00-072"),
        ("POST", f"{GLOSSARY}/terms", {"json": [{"name": "x"}]}, 400, "ATLAS-400-00-072"),
        ("POST", f"{GLOSSARY}/term", {"json": {"anchor": anchor}}, 400, "ATLAS-400-00-07A"),
        ("POST", f"{GLOSSARY}/term", {"json": {"name": "checking", "anchor": anchor}}, 409, "ATLAS-409-00-009"),
        ("GET", f"{GLOSSARY}/terms/{checking['guid']}/related", {"params": {"offset": "x"}}, 400, "ATLAS-400-00-029"),
        ("GET", f"{GLOSSARY}/term/nope", {}, 404, "ATLAS-404-00-005"),
    ]
    for method, url, kwargs, expected, code in failures:
        status, body = await send(client, method, url, **kwargs)
        assert (status, body["errorCode"]) == (expected, code), (method, url, body)
    assert (await send(client, "DELETE", f"{GLOSSARY}/term/{savings['guid']}"))[0] == 204
    assert (await send(client, "GET", f"{GLOSSARY}/term/{savings['guid']}"))[0] == 404


@pytest.mark.covers(
    f"{R}.assign_term_to_entities",
    f"{R}.get_entities_assigned_with_term",
    f"{R}.remove_term_assignment_from_entities",
    f"{R}.disassociate_term_assignment_from_entities",
    rules=["GTA-01", "GTA-02", "GTA-03", "GTA-04", "GTA-05", "GTA-06", "GTA-07"],
)
async def test__a_term_is_assigned_audited_searched_and_removed(client: httpx.AsyncClient) -> None:
    """The assignment endpoints, the entity's meanings and audit, and the searches by term."""
    _, glossary = await send(client, "POST", GLOSSARY, json={"name": "bank"})
    _, term = await send(
        client, "POST", f"{GLOSSARY}/term", json={"name": "loan", "anchor": {"glossaryGuid": glossary["guid"]}}
    )
    _, created = await send(
        client,
        "POST",
        "/api/atlas/v2/entity",
        json={"entity": {"typeName": "Asset", "attributes": {"qualifiedName": "a", "name": "a"}}},
    )
    entity = created["mutatedEntities"]["CREATE"][0]["guid"]
    assigned_url = f"{GLOSSARY}/terms/{term['guid']}/assignedEntities"
    status, _ = await send(client, "POST", assigned_url, json=[{"guid": entity, "typeName": "Asset"}])
    assert status == 204
    _, (assigned,) = await send(client, "GET", assigned_url)
    assert (assigned["guid"], assigned["displayText"], assigned["relationshipStatus"]) == (entity, "a", "ACTIVE")
    _, header = await send(client, "GET", f"/api/atlas/v2/entity/guid/{entity}/header")
    assert (header["meaningNames"], header["meanings"][0]["qualifiedName"]) == (["loan"], "loan@bank")
    _, events = await send(client, "GET", f"/api/atlas/v2/entity/{entity}/audit", params={"auditAction": "TERM_ADD"})
    assert [event["details"][:12] for event in events] == ["Added term: "]
    _, basic = await send(client, "POST", "/api/atlas/v2/search/basic", json={"termName": "loan@bank"})
    assert [found["guid"] for found in basic["entities"]] == [entity]
    _, dsl = await send(client, "GET", "/api/atlas/v2/search/dsl", params={"query": "Asset hasTerm loan"})
    assert [found["guid"] for found in dsl["entities"]] == [entity]
    status, unknown = await send(client, "POST", "/api/atlas/v2/search/basic", json={"termName": "loan"})
    assert (status, unknown["errorCode"]) == (400, "ATLAS-400-00-06E")
    no_guid = [{"guid": entity, "typeName": "Asset"}]
    status, missing = await send(client, "PUT", assigned_url, json=no_guid)
    assert (status, missing["errorCode"]) == (400, "ATLAS-400-00-078")
    wrong = [{"guid": entity, "relationshipGuid": "other"}]
    status, invalid = await send(client, "DELETE", assigned_url, json=wrong)
    assert (status, invalid["errorCode"]) == (400, "ATLAS-400-00-080")
    status, _ = await send(client, "DELETE", assigned_url, json=[assigned])
    assert status == 204
    assert (await send(client, "GET", assigned_url))[1] == []


@pytest.mark.covers(f"{R}.produce_template", f"{R}.import_glossary_data", rules=["GIM-01", "GIM-02", "GIM-06"])
async def test__a_file_of_terms_is_imported(client: httpx.AsyncClient) -> None:
    """The template downloads; a CSV upload creates its glossary and terms; no file is no file type (DV-104)."""
    template = await client.get(f"{GLOSSARY}/import/template")
    assert (template.status_code, template.headers["content-type"]) == (200, "application/octet-stream")
    assert template.text.startswith("GlossaryName, TermName, ShortDescription")
    content = f"{template.text}\nimported,first,,,,,,,,,,,,,,,,,,,\nimported,second,,,,,,,,,,,,,imported:first,,,,,,\n"
    status, answer = await send(
        client, "POST", f"{GLOSSARY}/import", files={"file": ("terms.csv", content.encode(), "text/csv")}
    )
    assert status == 200, answer
    assert [info["childObjectName"] for info in answer["successImportInfoList"]] == ["first", "second"]
    assert "failedImportInfoList" not in answer
    _, headers = await send(client, "GET", f"{GLOSSARY}", params={"limit": "1"})
    _, terms = await send(client, "GET", f"{GLOSSARY}/{headers[0]['guid']}/terms")
    assert {term["name"]: [h["displayText"] for h in term.get("seeAlso", [])] for term in terms} == {
        "first": ["second"],
        "second": ["first"],
    }
    status, again = await send(
        client, "POST", f"{GLOSSARY}/import", files={"file": ("terms.csv", content.encode(), "text/csv")}
    )
    assert (status, again["errorCode"]) == (409, "ATLAS-409-00-011")
    status, no_file = await send(client, "POST", f"{GLOSSARY}/import", files={"other": ("x.csv", b"x")})
    assert (status, no_file["errorCode"]) == (400, "ATLAS-400-00-098")
