# 9.5 The server under a path prefix

- **Status:** in review
- **Pull request:** to follow
- **Records:** DD-363, DV-140; relies on AUT-01 to AUT-07 (the sign-in), SRV-08 (the security headers)
  and SRV-10 (the proxy's trust)

A proxy can serve the server under a path, such as `https://localhost:9000/atlas2/`, beside other services
under theirs. The server is told the path as `root_path`; its redirects and its sign-in then lead there. The
standalone stack serves it that way behind nginx, with Keycloak under `/auth/`.

## Scope

In `aurelius-atlas-server`: the setting `root_path` (`AURELIUS_ATLAS_SERVER_ROOT_PATH`, empty by default),
passed to uvicorn; `root_path.site_path` and `under_root`; the authentication middleware, the login and logout
routes and the security headers reading paths through them. The standalone stack: an nginx entry on port 9000,
its own Keycloak under `/auth/`, and the server under `/atlas2/`.

Not in scope: the chart, whose gateway serves the server at the root of its host.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                      |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PFX-01 | `root_path` is empty, or segments each `/` and at least one character with no `/` or space, without a trailing `/`. Uvicorn takes it: every request's path starts with it, and the request's base URL ends with it. Empty serves the server at the root, as before                        |
| PFX-02 | What a path is, for the paths open without a user (AUT-01), for an API call being answered 401 instead of a redirect to sign in (AUT-04), and for the API's security headers (SRV-08), is read within `root_path`: `/atlas2/api/atlas/admin/status` is open, `/atlas2/api/...` is the API |
| PFX-03 | The redirect to sign in leads to `login.jsp` under `root_path`; the page remembered is the one asked, with its prefix; after sign-in a page that is no local path returns to `root_path`'s `/`                                                                                            |
| PFX-04 | The provider's return address is `login.jsp` under the base URL, so with `root_path` (`https://localhost:9000/atlas2/login.jsp`), and sign-out returns to the base URL. The session cookie stays on the whole host (`Path=/`)                                                             |

## Java origin

Apache Atlas `release-2.4.0`: `webapp/.../web/service/EmbeddedServer.java` serves the web application at `/`
(`new WebAppContext(path, "/")`); `AtlasAuthenticationEntryPoint` redirects to the login path from there. The
dashboards build their URLs from the page's location (`Utils.getBaseUrl`), so they work under a prefix as they
are.

## Deviations

- **DV-140:** the server can be served under a path prefix; Atlas serves only at the root of its host.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_root_path.py`: PFX-01 to PFX-04. The setting
  and uvicorn's option; paths within and under the prefix; the probes, a 401 and the API headers under
  `/atlas2`; a sign-in and sign-out under it against the fake provider.
- By hand, the standalone stack: `https://localhost:9000/` to `/atlas2/`, sign-in at `/auth/` and back, the
  session, a search and the sign-out; the sample import through the proxy.
