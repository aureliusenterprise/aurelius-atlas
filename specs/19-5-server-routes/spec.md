# 19.5 A server whose routes state their dependencies

- **Status:** in review
- **Pull request:** [#431](https://github.com/aureliusenterprise/aurelius-atlas/pull/431)
- **Records:** DD-793 to DD-801, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

This increment makes a route's dependencies visible in its signature, fixes the one store-lookup error that
answers a bare 500, removes the hub that eight sibling route files import from, and gives body validation and
the
export lock one owner each. It changes no answer for a request that succeeds or that answers a known Atlas
error.
The one answer it changes is a closed tenant store, which today answers a bare 500 and starts answering the
Atlas
error body (SVC-01).

This increment changes no answer that leaves the server except SVC-01, which moves an unspecified 500 to the
Atlas error shape the rest of the API already uses. The parity scenarios and the frozen 14.6 corpus answer
byte-identical, because no scenario targets a closed tenant store.

This increment does not deliver:

| Not delivered                                 | It lands in |
| --------------------------------------------- | ----------- |
| The store contract the write path is typed on | 19.2        |
| The owner for the shared parent-side rule     | 19.3        |

## Semantics

A route that reads `request.app.state` or calls a factory inline hides what it needs, so its tests reach
through
`app.state` to change behaviour. The rules below move those needs into the signature as dependencies.

| Id     | Rule                                                                                                                                                                                               |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SVC-01 | A request for a tenant whose store set is closed answers the Atlas error body with an `errorCode`, the same shape every other refusal uses. It does not answer FastAPI's default 500 with no body. |
| SVC-02 | Settings, the store set, and the authorizer reach a route through a dependency, not through `request.app.state` read inside the body. `create_app` stays the composition root that wires them.     |
| SVC-03 | The service factories that build the per-request services leave `routes/entity.py` to a services module, so `routes/entity.py` holds handlers and nothing else.                                    |
| SVC-04 | The Java numeric coercion that some handlers apply leaves `routes/entity.py` to the module that owns the coercion rule. The sibling route files stop importing from the entity hub.                |
| SVC-05 | The four hand-written request-body validation blocks call one owner, so a body rule written wrong is wrong in one place, not four.                                                                 |
| SVC-06 | The export lock protocol exists once. The two places that take and release the export lock call the same owner.                                                                                    |
| SVC-07 | The model list that builds the OpenAPI schema is per app, not a module-level list appended at import, so two apps' tests do not pollute each other's schema.                                       |
| SVC-08 | No answer for a request that succeeds or that answers a known Atlas error changes. The parity scenarios and the 14.6 governance corpus answer identical to the base commit.                        |

## Java origin

This ports nothing new. Apache Atlas 2.4.0 wires its JAX-RS resources through Spring injection, and its store
lookup failure surfaces as `AtlasExceptionMapper` output. Aurelius Atlas already maps `AtlasError` to that
shape
at `app.py:257`, and SVC-01 routes the one uncovered lookup through the same mapper. The route files and the
OpenAPI builder this increment touches are Aurelius code, so it adds no row to
[Java map](../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas. SVC-01 aligns a bare 500 with the Atlas error shape the reference already answers for
a
closed store, so it removes a difference rather than adding one. The increment adds no row to
[Deviations](../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                       | Command                                                                        | Level |
| ------------------------------------------- | ------------------------------------------------------------------------------ | ----- |
| Every SVC rule has a test that names it     | `uv run aurelius-atlas-trace check` scoped to this increment                   | 0     |
| A closed store answers the Atlas error body | `uv run pytest apps/aurelius-atlas-server/tests` for the SVC-01 test           | 0     |
| The routes take their needs as dependencies | `nx test aurelius-atlas-server -c ci`, and no test writes `app.state.settings` | 1     |
| The entity hub holds handlers only          | `routes/entity.py` imports no service factory and no coercion helper           | 0     |
| No wire answer moved except SVC-01          | The parity scenarios and `test__app_search_governance.py` answer identical     | 1     |
| Lint and types                              | `nx lint aurelius-atlas-server` and `nx typecheck aurelius-atlas-server`       | 0     |
| One live proof that the routes still answer | `nx e2e aurelius-atlas-server -c ci`                                           | 2     |

## Design decisions

The reasoning for each rule above lives in [design.md](./design.md) as DD-793 to DD-801. The two worth reading
before the rest are DD-793, which records the one-line store-lookup fix that can ship alone, and DD-795, which
records why the entity hub is split by removing its non-handler contents.
