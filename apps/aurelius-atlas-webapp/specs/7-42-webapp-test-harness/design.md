# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-868. The webapp's shared test world lives in `src/testing/`, behind relative imports

- **Status:** Proposed
- **Increment:** 7.42
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The webapp's test-only world lives in `apps/aurelius-atlas-webapp/src/testing/`,
in six files by job (`api.ts` for the door URLs, `auth.ts` for the Keycloak
double, `config.ts` for the runtime config and tenancy, `providers.ts` for the
provider set, `view-fixtures.ts` for the entity builders, `dom.ts` for the two
markup helpers) plus a barrel and a spec of its own. Specs reach it by relative
import (`../../../testing/api`). The directory is excluded in
`tsconfig.app.json`, so the spec program type-checks it and the application
bundle never carries it. No new Nx project, no new Angular library, no
`tsconfig.base.json` path.

**Why.** Fourteen specs rebuilt the same five providers, the same door URLs, and
the same entity literal, and the copies had already drifted apart: an inline
config carried no `atlasClientId`, so the write gate read its default instead of
the deployed value, and ten specs kept their own whitespace collapse that no test
could keep in step with the others. The fix has to be importable by a spec and
invisible to a bundle, which is what an excluded folder inside the same project
gives. A separate library was rejected because it would add an Nx project whose
whole content is test code, and the webapp's purity gate (WBP-02, the `dependsOn`
of `test`) constrains imports by project: a new library would need its own
boundaries and its own story to carry nothing but fakes. A `tsconfig.base.json`
alias was rejected because the root `package.json` declares no workspaces, so the
alias needs a second resolver entry in the Vitest config to survive — two places
to keep in step for the same path. The relative ladder is one line per spec and
cannot drift.

**Considered and rejected.** _A `package.json` self-reference_
(`aurelius-atlas-webapp/testing` resolves through the project's own `name`) — the
Vitest builder resolves through Vite, not Node's self-reference rules, so it
either breaks under `nx test` or needs an alias anyway; _`src/app/testing/`_ —
the purity gate (WBP-02) greps the whole of `src`, so a fake there is as covered
as one beside `src/app/`, but it sits inside the tree production code imports
from, where a fake path reads like an intra-app import; _Global test setup in the
Vitest config_ — a provider set is not global, since
several specs need a router with a real drawer outlet and none need the write
grant.

**Consequences.** The exclusion cuts both ways: the harness never reaches the
bundle, and the build target never type-checks it either. `nx test` covers that
half — a screen spec's import pulls `src/testing/` into the spec program, so a
harness change that breaks a caller's types fails the test target. Specs
keep a small literal where they pin something of their own: the header spec
overrides the Keycloak realm because it asserts the account-console URL
(`SHC-05`), and the editor's store spec layers its own view defaults on the
builder because the store parses `updateTime`, the tags, and one section
(`VDE-01`, `VDE-03`). Both build the harness value rather than writing a parallel
one, so the drift the increment removes cannot return. The header spec keeps its
own Keycloak literal: its Logout tests hand the provider a `vi.fn()` and then
assert on that same object, so the spec needs the spy rather than a double that
only answers calls.
