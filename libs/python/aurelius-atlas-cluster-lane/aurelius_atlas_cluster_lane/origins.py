"""The realm's browser origins for the install's edge hostnames (CHT-107).

Keycloak's ``--import-realm`` lands the realm asset's browser origins and
never updates a live realm afterwards, and the master asset (the install's
realm, CHT-78) carries only the dev localhost origins. A browser on the
cluster's edge hostname is therefore refused at the sign-in redirect until
someone registers the edge origin on the client. Registering browser origins
is deployment topology, not credentials (CHT-77's own rule for the prod
asset's host tokens), and the cluster installer is the component that owns
the install's domain — so ``tools/cluster/install.sh`` calls this to converge
the live realm after every install, the same way the fenced hosts block
converges the browser leg's DNS (CHT-106).

The client is a plain argument: the caller owns the authenticated admin
transport (a ``httpx.Client`` with the base URL and the authorization header,
however it reached the issuer — a :class:`~aurelius_atlas_cluster_lane.forward.ServiceForward`
in the installer). That keeps this module free of kubectl and cluster shapes,
like the rest of the read/merge code here.
"""

import contextlib
from collections.abc import Iterator

import httpx2 as httpx

_MISSING_CLIENT_ERROR = "realm {realm!r} has no client {client_id!r} for its browser origins ({status})"

_OK = 200
_NO_CONTENT = (200, 204)


def ensure_browser_origins(client: httpx.Client, *, realm: str, client_id: str, host: str) -> tuple[str, ...]:
    """Make ``client_id``'s browser origins in ``realm`` cover ``https://host``; return what was added.

    The read-modify-write is on the admin REST client resource: the redirect
    and post-logout lists gain ``https://host/*``, the web origins gain
    ``https://host``. An already-covered client is a no-op (nothing is PUT,
    the tuple is empty), so the installer can re-run it on every ``up``
    without churn.
    """
    found = client.get(f"/admin/realms/{realm}/clients", params={"clientId": client_id})
    assert found.status_code == _OK, _MISSING_CLIENT_ERROR.format(
        realm=realm, client_id=client_id, status=found.status_code
    )
    matches = [entry for entry in found.json() if entry["clientId"] == client_id]
    assert len(matches) == 1, _MISSING_CLIENT_ERROR.format(realm=realm, client_id=client_id, status=len(matches))
    entry = matches[0]

    redirect_uris: list[str] = entry.setdefault("redirectUris", [])
    web_origins: list[str] = entry.setdefault("webOrigins", [])
    attributes: dict[str, str] = entry.setdefault("attributes", {})
    post_logout = attributes.get("post.logout.redirect.uris", "").split()

    def covered(entries: list[str], *, uri_pattern: bool) -> bool:
        # Keycloak's own wildcard entry covers every host — and appending to a
        # list that carries it is rejected as invalid input by the admin REST.
        # Redirect lists are URI patterns ("<host>/*"); web origins are bare.
        wanted = f"https://{host}/*" if uri_pattern else f"https://{host}"
        return "*" in entries or wanted in entries

    added: list[str] = []
    if not covered(redirect_uris, uri_pattern=True):
        redirect_uris.append(f"https://{host}/*")
        added.append("redirectUris")
    if not covered(web_origins, uri_pattern=False):
        web_origins.append(f"https://{host}")
        added.append("webOrigins")
    if not covered(post_logout, uri_pattern=True):
        post_logout.append(f"https://{host}/*")
        attributes["post.logout.redirect.uris"] = "\n".join(post_logout)
        added.append("post.logout.redirect.uris")

    if added:
        updated = client.put(f"/admin/realms/{realm}/clients/{entry['id']}", json=entry)
        assert updated.status_code in _NO_CONTENT, (
            f"the admin REST rejected the origin update for {client_id!r} ({updated.status_code}): {updated.text}"
        )
    return tuple(added)


@contextlib.contextmanager
def admin_client(
    issuer_base_url: str,
    *,
    token: str,
    verify: str | bool = True,
) -> Iterator[httpx.Client]:
    """An authenticated admin REST transport at ``issuer_base_url`` (the Bearer ``token``)."""
    with httpx.Client(
        base_url=issuer_base_url,
        verify=verify,
        headers={"authorization": f"Bearer {token}"},
    ) as client:
        yield client
