from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import bearer_headers


@pytest.fixture
def dashboard_dir(tmp_path: Path) -> Path:
    """A dashboard directory laid out as the build writes it: v2 at the root, v3 in ``n/``."""
    root = tmp_path / "dashboard"
    (root / "n" / "js").mkdir(parents=True)
    (root / "js").mkdir()
    (root / "index.html").write_text("<title>dashboardv2</title>")
    (root / "js" / "main.js").write_text("// v2")
    (root / "n" / "index.html").write_text("<title>dashboardv3</title>")
    (root / "n" / "js" / "main.js").write_text("// v3")
    (root / "api").mkdir()
    (root / "api" / "atlas").mkdir()
    (root / "api" / "atlas" / "admin").mkdir()
    (root / "api" / "atlas" / "admin" / "status").write_text("a file the API must hide")
    return root


async def get(settings: ServerSettings, path: str) -> httpx.Response:
    """Start the application, ask one path, stop it."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://aurelius-atlas", headers=bearer_headers()
        ) as client:
            return await client.get(path)


@pytest.mark.covers("aurelius_atlas_server.app.mount_dashboards", rules=["DSH-01", "DSH-02"])
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/", "<title>dashboardv2</title>"),
        ("/index.html", "<title>dashboardv2</title>"),
        ("/js/main.js", "// v2"),
        ("/n/", "<title>dashboardv3</title>"),
        ("/n/js/main.js", "// v3"),
    ],
)
async def test__dashboards_are_served_where_atlas_serves_them(
    settings: ServerSettings, fake_es: FakeClient, dashboard_dir: Path, path: str, body: str
) -> None:
    """dashboardv2 is at the root and dashboardv3 under ``/n/``."""
    _ = fake_es
    response = await get(settings.model_copy(update={"dashboard_dir": dashboard_dir}), path)

    assert response.status_code == 200
    assert response.text == body


@pytest.mark.covers("aurelius_atlas_server.app.mount_dashboards", rules=["DSH-02"])
async def test__dashboardv3_without_a_slash_redirects(
    settings: ServerSettings, fake_es: FakeClient, dashboard_dir: Path
) -> None:
    """``/n`` leads to ``/n/``, as a browser expects of a directory."""
    _ = fake_es
    response = await get(settings.model_copy(update={"dashboard_dir": dashboard_dir}), "/n")

    assert response.status_code in {307, 308}
    assert response.headers["location"].endswith("/n/")


@pytest.mark.covers("aurelius_atlas_server.app.mount_dashboards", rules=["DSH-03"])
@pytest.mark.parametrize(
    ("path", "status"), [("/api/atlas/admin/status", 200), ("/missing.js", 404), ("/n/missing.js", 404)]
)
async def test__the_api_takes_precedence_over_dashboard_files(
    settings: ServerSettings, fake_es: FakeClient, dashboard_dir: Path, path: str, status: int
) -> None:
    """An API path is answered by the API even when a file has its name; other unknown paths are 404."""
    _ = fake_es
    response = await get(settings.model_copy(update={"dashboard_dir": dashboard_dir}), path)

    assert response.status_code == status
    if status == 200:
        assert response.json() == {"Status": "ACTIVE"}


@pytest.mark.covers("aurelius_atlas_server.app.create_app", rules=["DSH-04"])
async def test__without_a_dashboard_directory_only_the_api_is_served(
    settings: ServerSettings, fake_es: FakeClient
) -> None:
    """No dashboard directory: ``/`` is 404 and the API still answers."""
    _ = fake_es

    assert (await get(settings, "/")).status_code == 404
    assert (await get(settings, "/api/atlas/admin/status")).status_code == 200
