# aurelius-atlas-server

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-server)

The Aurelius Atlas server: the Apache Atlas 2.4.0 REST API on Elasticsearch.

## Usage

```bash
npx nx serve aurelius-atlas-server
```

This starts the dev Elasticsearch store and the observability stack, then the server at
[https://localhost:21000](https://localhost:21000), the port Apache Atlas uses.

## Deployment

Deploy the image built from the provided Dockerfile. It listens on port 21000 and needs the
Elasticsearch settings; it does not start without its store.

## Configuration

??? INFO "Settings"

    ::: aurelius_atlas_server.settings.ServerSettings

## Design

The technology-specific detail of how the server runs. The properties it must keep are in the
architecture: [Configuration Management](../../architecture/platform/delivery/configuration-management.md)
(ADR 018), [Components & Interfaces](../../architecture/platform/components-and-interfaces.md).

**Settings.** Read once at start-up into a frozen `ServerSettings`; a validation failure (missing
key, bad scheme, missing TLS material) stops start-up with a message naming the variable (SRV-01,
SRV-02, SRV-06). All names carry the `AURELIUS_ATLAS_SERVER_` prefix. What a deployment must supply,
with no defaults:

| Variable                                 | Purpose                                                                                        |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `..._ELASTICSEARCH_HOSTS`                | JSON list of store node URLs, e.g. `["https://es-0:9200"]` — `https` only                      |
| `..._ELASTICSEARCH_PASSWORD`             | Store password — a `SecretStr`, never shown in logs                                            |
| `..._ELASTICSEARCH_CA_CERTS`             | PEM CA of the store certificate; the store link is https-only (ADR 039)                        |
| `..._TLS_CERT_FILE` + `..._TLS_KEY_FILE` | PEM pair for serving HTTPS: both required — the server never serves plaintext (SRV-06, DD-234) |

With defaults: `HOST` (`0.0.0.0` in the image), `PORT` (21000, Atlas's port — kept so existing
clients find the catalogue where Atlas was, ADR 046), `LOG_LEVEL`, `REVISION` (reported by
`admin/version`, ADM-01), `HSTS_ENABLED` (true — the dev arrangement sets it false, SRV-08/DD-236),
`DASHBOARD_DIR` (None serves the API only, DSH-04), `MODELS_DIR`
(default: the vendored Atlas 2.4.0 `addons/models`, MDL-16/DD-032),
`TYPEDEF_REFRESH_SECONDS` (5.0 — how long the server answers from its type registry before
checking for another process's type change, TDS-13/DD-029).

!!! WARNING "The server does not start without TLS material"

    `TLS_CERT_FILE` and `TLS_KEY_FILE` are required settings — there is no plaintext mode
    (SRV-06, DD-234, superseding the both-or-neither rule of SRV-03). A container that mounts
    no material exits with a message naming the missing variable; this is the design working,
    not a broken image. The image's `ENV` names where the pair lives (`/certs/server.pem`,
    `/certs/server-key.pem` — DD-216's stack-owned mount).

**The image** (`apps/aurelius-atlas-server/Dockerfile`: hardened base, runs as `nonroot`) bakes in
the production defaults — listen on `0.0.0.0:21000`, dashboards served from
`/application/dashboard` — and a liveness healthcheck against `/api/atlas/admin/liveness` over
HTTPS, verifying the served certificate (SRV-06). Liveness is the probe a restart decision
uses; readiness also fails while the store is away (DD-016).

**Security headers.** Every answer carries them (SRV-08, DD-236): `security_headers.py` stamps
the JSON API with no-store/nosniff/framing-closed headers and a documents-free CSP, the
dashboards with a same-origin CSP (DV-86) and immutable caching on bust-versioned assets,
and HSTS when `HSTS_ENABLED`.

**Parity scenarios.** `scenarios/<resource>/*.scenario.yaml` state each expectation as Atlas's own
answer — e.g. `scenarios/admin/version.scenario.yaml` expects `Version: "2.4.0"`,
`Name: apache-atlas`, the exact content type — each cited to the Java source that produces it.
Build-varying fields are marked volatile; the two places Aurelius Atlas must answer differently
(name, description) carry a `deviations: DV-03` entry. Anything else that differs fails the
scenario (ADR 052).

## Documentation

::: aurelius_atlas_server.app

::: aurelius_atlas_server.errors

::: aurelius_atlas_server.routes.admin
