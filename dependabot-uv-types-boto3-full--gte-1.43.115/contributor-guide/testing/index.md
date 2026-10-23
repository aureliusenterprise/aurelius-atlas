# Testing

How to run the gate locally and how to write tests that satisfy it. The layer map and what each layer proves is the architecture page [Testing Strategy](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/architecture/platform/delivery/testing/index.md>); the gate's rules are [ADR 014](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>). This page is the commands and conventions.

## Running the gate locally

The same checks CI runs, available before you push:

```
npx nx test <project> -c ci
npx nx e2e <project> -c ci
npx nx affected -t test e2e -c ci
uv run aurelius-atlas-trace check
```

Always `-c ci` for test targets — the default is watch mode, which never exits.

> [!WARNING]
>
> **Without `-c ci`, tests run in watch mode and never exit**
>
> A bare `nx test <project>` starts Vitest in watch mode, keeps the process running, and blocks every later step that waits for it. The symptom — a "hung" build that is really an idle watcher — is expected, not a broken setup: add `-c ci` and it runs to completion with coverage.

The traceability check runs collection only, no tests, and prints the functions and rule ids that no test names. Fix a gap by writing the test, not by editing the check ([ADR 049](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/architecture/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>)).

## Writing tests

- **Python**: test files `test__*.py` under `tests/`, functions `test__<function_name>_<scenario>`. Async tests use `pytest-asyncio`; fixtures live in `conftest.py`; `pytest-cov` collects coverage. Unit tests of store code use the fake client from `aurelius_atlas_store_es.testing.fake`; containers come from `aurelius_atlas_store_es.testing.container`.
- **TypeScript**: `.spec.ts` co-located with source (analog pattern), Vitest via `@nx/vitest`.
- **Test data**: created through fixtures, never shared mutable state. TLS material comes from `nx certgen` (`tls.json` per project, ephemeral mkcert CA — see [TLS Certificates](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/contributor-guide/tls-certificates/index.md>)); E2E containers get per-run CAs, and compose health checks gate startup.

### Naming what a test proves

`@pytest.mark.covers("<dotted.path>", rules=["ENT-07"])` names the function under test and the specification rules it checks. CI fails on gaps; `uv run aurelius-atlas-trace check` shows them locally first.

- **Every new public function gets a test that names it** — the trace check enforces it, so writing the test is not optional bookkeeping.
- Every rule id in an increment's spec gets a test that names it the same way.

## Flaky tests

1. Record the recurring failure pattern from CI (the test report keeps the evidence per change).
2. Find the root cause — timing, isolation, shared environment — before any retry is considered.
3. Fix the test or the product; do not skip. A test that cannot be made deterministic is removed with a note naming why, not annotated away.

> [!IMPORTANT]
>
> **Flaky tests are fixed, never skipped**
>
> A skipped test silently deletes the evidence the gate is made of: the test report reads as green while the behaviour it stood for goes unproven. Retrying a flaky test hides its root cause — timing, isolation, shared environment — which is the bug worth fixing.

## Pointers

- What each layer proves: [Testing Strategy](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/architecture/platform/delivery/testing/index.md>)
- Realism rules: [ADR 010](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>), [ADR 012](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/architecture/adr/012-validation-runs-against-real-services/index.md>)
- Parity scenarios: [ADR 052](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>), the [parity library](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.115/api-reference/libs/python/aurelius-atlas-parity/index.md>)
- Per-project commands: each project's `AGENTS.md`
