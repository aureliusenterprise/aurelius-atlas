"""Route-level tests for the write-role authorization gate on mutating endpoints.

The fixtures override only ``user_info`` (the token decode) and pin
``auth_write_role`` on the settings, so ``require_write_access`` runs exactly as
in production: valid caller, missing role → 403; role present → allowed. The
401-on-missing-token path is covered by the ``unauthenticated_client`` tests in
the collection/item specs (auth runs before authorization).
"""

import uuid

from aurelius_atlas_example import Entity


def test__create_denied_without_write_role(write_role_client) -> None:  # noqa: ANN001
    """A valid, authenticated token without the write role must not be able to write."""
    entity = Entity(name="No Role", description="caller lacks the role")

    with write_role_client({"sub": "u", "realm_access": {"roles": ["viewer"]}}) as client:
        response = client.put("/entities/", json=entity.model_dump(mode="json"))

    assert response.status_code == 403


def test__delete_denied_without_write_role(write_role_client) -> None:  # noqa: ANN001
    """A valid, authenticated token without the write role must not be able to delete."""
    with write_role_client({"sub": "u"}) as client:
        response = client.delete(f"/entities/{uuid.uuid4()}")

    assert response.status_code == 403


def test__create_allowed_with_realm_role(write_role_client) -> None:  # noqa: ANN001
    """A token with the write role in realm_access can write."""
    entity = Entity(name="Realm Role", description="caller has the realm role")

    claims = {"sub": "u", "realm_access": {"roles": ["aurelius-write"]}}
    with write_role_client(claims) as client:
        response = client.put("/entities/", json=entity.model_dump(mode="json"))

    assert response.status_code == 200


def test__create_allowed_with_client_role(write_role_client) -> None:  # noqa: ANN001
    """A token with the write role in resource_access (client-scoped) can write."""
    entity = Entity(name="Client Role", description="caller has the client role")

    claims = {"sub": "u", "resource_access": {"aurelius": {"roles": ["aurelius-write"]}}}
    with write_role_client(claims) as client:
        response = client.put("/entities/", json=entity.model_dump(mode="json"))

    assert response.status_code == 200


def test__create_denied_with_role_on_other_client(write_role_client) -> None:  # noqa: ANN001
    """Keycloak namespaces client roles: a same-named role under another client is not ours."""
    entity = Entity(name="Foreign Role", description="role granted on a different client")

    claims = {
        "sub": "u",
        "azp": "aurelius",
        "resource_access": {"other-client": {"roles": ["aurelius-write"]}},
    }
    with write_role_client(claims) as client:
        response = client.put("/entities/", json=entity.model_dump(mode="json"))

    assert response.status_code == 403


def test__reads_allowed_without_write_role(write_role_client) -> None:  # noqa: ANN001
    """Reads stay authenticated-only: the write role gates mutations, not reads."""
    with write_role_client({"sub": "u"}) as client:
        response = client.get("/entities/")

    assert response.status_code == 200
