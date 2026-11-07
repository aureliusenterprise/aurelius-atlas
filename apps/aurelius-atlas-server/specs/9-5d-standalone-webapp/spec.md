# 9.5d The standalone stack's webapp

- **Status:** in review
- **Pull request:** [#284](https://github.com/aureliusenterprise/aurelius-atlas/pull/284)
- **Records:** DD-369; relies on DD-363 (the standalone stack behind nginx), DD-366 (its demo realm), DD-262
  (the webapp's nginx template resolved by the deployment) and DD-139 (the `/api` prefix passed intact)

The standalone stack serves the Aurelius Atlas webapp at the root of its one entry, beside the Atlas
dashboards under `/atlas2/`. Both sign in to the demo realm, so one sign-in serves both, and the webapp shows
each user's rights as the dashboards do.

## Scope

The standalone stack in `apps/aurelius-atlas-server/standalone/`: the services `webapp-config` and
`aurelius-atlas-webapp`, the volume `webapp-nginx-conf`, `webapp/resolve-nginx.sh`, `webapp/config.json`, the
proxy's routes for `/` and `/otel/`, and the demo realm's public client `aurelius` as the webapp's sign-in.

Not in scope: the webapp's image and its nginx template, which are used as they are; telemetry, which the
stack does not collect.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                       |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SWA-01 | The webapp runs in the proxy's network on the webapp image, reading its nginx config from the volume `webapp-nginx-conf`, its `config.json` from the stack, and its certificate from `apps/aurelius-atlas-webapp/certs/`; it starts once `webapp-config` filled the volume |
| SWA-02 | `webapp-config` fills every placeholder of the image's nginx template, and fails on one left: the API upstream is the server on `https://127.0.0.1:21000`, verified as `aurelius-atlas-server`                                                                             |
| SWA-03 | The proxy passes `/` and every path but `/atlas2/`, `/auth/` and `/otel/` to the webapp on `https://127.0.0.1:8080`, verified as `aurelius-atlas-webapp`, its redirects rewritten to port 9000; `/otel/` answers 204                                                       |
| SWA-04 | The webapp signs in to the realm `demo` at `https://localhost:9000/auth` through the public client `aurelius`, with PKCE, which returns to any page of `https://localhost:9000/`; its write affordances read the roles of `aurelius-atlas-server`                          |

## Java origin

None: the webapp is Aurelius's.

## Deviations

None.

## Acceptance

- `tests/test__standalone_webapp.py`: SWA-01 to SWA-04, read from the compose file, the proxy's config, the
  resolver against the webapp's template, `config.json` and the demo realm.
- By hand, the standalone stack: `https://localhost:9000/` leads to the demo realm's sign-in and back to
  `/en-US/`; as `steward` the header shows the create button and a search for `data` finds 125 entities of the
  sample through `/api/`; as `scientist` the create button is not shown; after the webapp's sign-in,
  `/atlas2/` opens the dashboards without signing in again.
