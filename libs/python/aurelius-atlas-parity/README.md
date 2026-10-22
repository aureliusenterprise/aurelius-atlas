# aurelius-atlas-parity

Parity scenarios for Aurelius Atlas
([ADR 052](../../../docs/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source.md)):
requests with the responses Apache Atlas 2.4.0 gives, read from its source and its own tests, run as
tests against Aurelius Atlas. No running Apache Atlas is involved.

Introduced by increment 0.4.

## A scenario

One `*.scenario.yaml` file per scenario. `source` says where in the `release-2.4.0` tag of Apache Atlas
the expected response was read; a scenario without it is refused.

```yaml
name: Create an entity and read it back
source:
    - webapp/src/main/java/org/apache/atlas/web/rest/EntityREST.java#createOrUpdate
    - webapp/src/main/java/org/apache/atlas/web/rest/EntityREST.java#getById
rules: [ENT-07]
stages:
    - name: create
      request:
          method: POST
          url: /api/atlas/v2/entity
          json: { entity: { typeName: hive_db, attributes: { qualifiedName: db1@cl1, name: db1 } } }
      response:
          status: 200
          json: { mutatedEntities: { CREATE: [{ guid: "", typeName: hive_db }] } }
          volatile: ["$.mutatedEntities.CREATE[*].guid"]
          save: { guid: "$.mutatedEntities.CREATE[0].guid" }
    - name: read
      request: { method: GET, url: "/api/atlas/v2/entity/guid/{guid}" }
      response:
          status: 200
          json: { entity: { guid: "{guid}", typeName: hive_db } }
          deviations:
              - { id: DV-03, path: $.entity.version, absent: true }
```

- **The body is compared exactly**: the same keys, arrays in order, `null` is not "absent", `true` is
  not `1`. Only `volatile` paths skip a value (the field must still be there).
- **`save`** keeps a value for later stages; `"{guid}"` takes it with its JSON type, `/x/{guid}` writes
  it into the text, also into an object key, `{{` and `}}` are literal braces.
- **`{run}`** is saved before the first stage: a value unique to each run, for names a scenario creates in a
  store that keeps them (DD-055).
- **`deviations`** turn the Atlas expectation into the Aurelius answer, each with its id from
  [Deviations](../../../docs/architecture/conversion/deviations.md).
- **Paths** are the JSONPath subset `$`, `.name`, `['name']`, `[n]` and `[*]`. Quote them in YAML
  flow style (`"$[*]"`).

## Running scenarios

A project keeps its scenarios in a directory and has one test module for them; its `client` fixture
decides whether the requests go to the application in-process or to a running server:

```python
from pathlib import Path

import httpx
import pytest
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario


@pytest.mark.parametrize("scenario", load_scenarios(Path(__file__).parent / "scenarios"))
async def test__scenario(scenario: Scenario, client: httpx.AsyncClient) -> None:
    await run_scenario(scenario, client)
```

Each scenario is one test, named by its path below the directory. Its `rules` and `covers` become a
`covers` marker, and the plugin records its endpoints and deviations, so the traceability check and the
test report of [aurelius-atlas-trace](../aurelius-atlas-trace/README.md) see it.
