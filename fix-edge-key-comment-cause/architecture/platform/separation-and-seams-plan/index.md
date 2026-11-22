# Separation and Seams Plan

> [!NOTE]
>
> **Plan for approval, not yet the as-built**
>
> This page turns the 2026-11-21 architecture audit into a sequence of pull requests. Nothing here is implemented. On approval, each increment lands on its own branch with its own spec, plan, and review. No page below describes behaviour that ships today.

The audit read the server composition root, the entity write path, the search and index path, and the Angular front end. It found nineteen findings. Fifteen are structural: a missing seam, a rule written four times, or a file that does six jobs. Four are code hygiene. This plan groups eighteen of them into seven increments, one per pull request, and orders them so each one pays for the next. None of the seven changes an answer that leaves the server. Finding 13 was checked when its increment was being written and closed without code, for the reason the findings map gives.

The goal is not tidiness. The 18.x metamodel series and the 16.x view series both land in the same three places (the write path, the store, and the editor), and all three are where the seams are missing today. That is where the next feature will cost the most.

## Scope

This plan covers production code in `libs/python/aurelius-atlas-core`, `libs/python/aurelius-atlas-store-es`, `apps/aurelius-atlas-server`, `apps/aurelius-atlas-webapp`, and `libs/angular/aurelius-atlas-data-access`.

| Out of scope | Why | It lands in |
| --- | --- | --- |
| New Atlas routes | This plan changes no externally visible answer | Any later series |
| The scanner apps | The audit read them only for duplication, and found none worth a PR | Later |
| `helm/`, `docker/` | Untouched by every finding | Not planned |
| Java parity fixes | No finding here changes Atlas behaviour, so `java-map.md` gains no row | Not needed |

## Findings mapped to increments

The audit numbered its findings 1 to 19. Finding 13 read: the read doors do not scrub each result, so they show data the classic path hides. Verification disproved it. No per-entity read grant exists, so the doors' one check and the classic scrub are the same answer in two shapes, and [DV-02](<https://aureliusenterprise.github.io/fix-edge-key-comment-cause/architecture/conversion/deviations/index.md>) and [DV-114](<https://aureliusenterprise.github.io/fix-edge-key-comment-cause/architecture/conversion/deviations/index.md>) already record the simple authorizer Apache Atlas's per-type authorizer became. Finding 13 closes with this note and no increment. The remaining eighteen findings map below.

| Increment | Delivers | Audit findings | Home |
| --- | --- | --- | --- |
| 19.1 | One query semantics for the store and its fakes | 8, 9 | `store-es`, `core` |
| 19.2 | A store the write path can be tested against | 1, 2, 3 | `core` |
| 19.3 | One owner for the shared classification and parent rules | 6 | `core` |
| 19.4 | One document module set, one narrow engine seam | 7, 12, 10 | `core` |
| 19.5 | A server whose routes state their dependencies | 4, 5, 11, 17 | `server` |
| 19.6 | An editor that reports its own outcome | 14, 15, 19 | `webapp` |
| 19.7 | Small deletions | 16, 18 | `core` |

## Sequencing

```
flowchart LR
  A["19.1 Query semantics"] --> C["19.4 Documents split"]
  B["19.2 Write seams"] --> D["19.3 Shared rules"]
  D --> C
  B --> E["19.7 Small deletions"]
  A --> F["19.5 Server routes"]
  C --> F
  F --> G["19.6 Webapp editor"]
```

Read the arrows as build order, not need. Only two pairs truly block each other. 19.2 and 19.3 both touch the write path, so they must not run in parallel. 19.4 both splits and shrinks the same file, so 19.1 must land first to keep the diff readable. 19.6 is independent of every Python increment and can start whenever the front end has capacity.

## The increments

### 19.1 Store and fake query semantics

**Delivers:** one module that turns a query into an Elasticsearch clause, called by both the store documents and the App Search engine, and one home for the free-text word rules. The transport fake shares the word rules and keeps reading the emitted query JSON itself. Today four places build or read query semantics (audit 8, 9).

**The concrete case this closes.** Production emits `minimum_should_match` in ten places. The transport fake evaluates `should` as plain `any(...)`, so it agrees only because production always passes `1`. A query that needs `2` passes every unit test and fails in production.

**Design notes.** These settle the plan's first open decision (D1).

- One `es_clauses` module owns filter, free-text, kNN, and facet construction (DD-767). The store and the engine both call it, so a clause kind is written once.
- The fake keeps its own reading of the Elasticsearch query JSON, and gains an honest `minimum_should_match` (DD-768, DD-769). If it called the builder, a wrong builder and a wrong fake agree with each other silently.
- One differential test runs a saved matrix of basic searches through the in-memory store and the fake, and fails when the hit sets or facet counts differ (DD-771).
- The engines are typed on a narrow `SearchDocuments` contract, which removes the 28 `# type: ignore[arg-type]` comments (DD-770). The in-memory store keeps answering the basic and terms searches and does not gain an App Search search. An honest App Search answer there is a third query engine.

**Rule ids:** `QRY-01` up to `QRY-06`. **DD:** 767 to 772.

### 19.2 Write-path seams

**Delivers:** a store interface the write path is typed against, a rewind wrapper built on the documents contract, and a per-attempt transaction object. This is the highest-value increment in the plan, and the three findings inside it share one root cause.

**The concrete case this closes.** `apps/aurelius-atlas-server/tests/test__view_mutation.py` is 680 lines of HTTP fixtures because the write door cannot be driven on its own. The store's internals are reached from a subclass (`view_mutation.py:110-124`), and a rolled-back write already woke the index workers, a fact pinned by a 26-line test instead of fixed.

**Design notes.**

- `EntityWriter` calls eight store members, and `ViewMutationDoor` calls six plus `undo`. A contract of that size is a day's work, and `EntityStore` stays the only implementation.
- The rewind wrapper is built from the documents contract rather than by subclassing, so it cannot inherit the real store's listener lists by accident.
- The 12-step transaction becomes a `WriteTransaction` object that steps share, so a wrong order is a type error and not a silent wrong write (DD-779).
- Import semantics leave `EntityWriter` for a small `ImportWriter` that shares the transaction object (DD-780). This settles the plan's second open decision (D2): the five mutable fields that only the import path reads are the main source of the order-dependency, so removing them from the shared writer is the cheapest fix.

**Rule ids:** `WRS-01` up to `WRS-09`. **DD:** 773 to 781.

### 19.3 Shared rule owners

**Delivers:** one function each for "which classifications did the user set" and "which end of this relationship is the parent". Today the first has four copies and the second has two plus a client copy.

**The concrete case this closes.** Increments 18.2, 18.3, and 18.5 each changed one copy of a parent-side rule and left the others. The RPS-02 exception exists in one of two write paths, so the view door answers a request the classic path refuses. That gap is only visible because the audit compared the two.

**Design notes.**

- Owner modules stay in `core`, next to `graph_helper`, which already hosts two of these primitives.
- Every copy is replaced by a call in the same pull request, so no half-migrated state ships.
- The RPS-02 gap is written up first, and either closed or recorded as a deviation. It must not ride along silently in a refactor.
- The webapp copy of the parent-side rule is found by 19.6's guard, not fixed here.

**Rule ids:** `RUL-01` up to `RUL-06`. **DD:** 782 to 787. **Deviations:** one row if RPS-02 stays a gap.

### 19.4 Documents and engine split

**Delivers:** `index_setup`, `documents_es`, and `es_query` in place of the 1,343-line `aurelius_atlas_core/entity_documents.py`, and `app_search_engine.py` split into schema, query, and answer.

**The concrete case this closes.** Adding one filter type means editing the contract, the Elasticsearch class, and both fakes together, and 64 files import the module. The engines are typed against the concrete class because `search_app_search` is missing from the contract, which is what 19.1 fixes first.

**Design notes.**

- The first commit is a pure move with no behaviour change, which makes review a file-existence check.
- The second commit narrows the contracts to what each indexer actually calls (six methods, not 34).
- The engine's hand-written highlighter joins the shared text module. That removes the third word definition in the repository.

**Rule ids:** `EDS-01` up to `EDS-05`. **DD:** 788 to 792.

### 19.5 Server routes

**Delivers:** store lookups that answer an Atlas error, dependency providers, a routes package with no hub, and one owner each for body validation and the export lock.

**The concrete case this closes.** A tenant whose store set is closed answers FastAPI's default 500 with no `errorCode`, because only `AtlasError` has a handler. And five test files change behaviour by writing `app.state.settings`, because a route's real dependency list is invisible from its signature.

**Design notes.**

- `stores(request)` raises `AtlasError`. One line plus a test, and it can ship alone as the first commit.
- Providers for settings, stores, and authorizer. `create_app` stays the composition root, so the change is mechanical and the diff stays readable.
- The ten service factories and the Java numeric coercion leave `routes/entity.py`, which removes a hub that seven route files import from.
- The four hand-written body-validation blocks collapse into `bodies.py`, and the export lock protocol collapses from two copies to one.
- The module-level model list in `openapi.py` becomes per-app, which removes cross-test pollution.

**Rule ids:** `SVC-01` up to `SVC-08`. **DD:** 793 to 801.

### 19.6 Webapp editor

**Delivers:** an editor that states its own outcome, one owner for the form rules, and a guard that fails when a client rule drifts from its Python original.

**The concrete case this closes.** The editor decides whether a delete succeeded by scanning the alerts store for its own message text stamped after a local clock (`entity-editor.component.ts:621-638`). A reword or a localization change flips "deleted" into "refused", and the unit tests keep passing because they assert the current text.

**Design notes.**

- `EditorState` gains a `deleteResult` signal, set by the code that performs the delete.
- The classification combobox (about ten members, five handlers, no coupling to the rest of the class) becomes its own component.
- PME-10 blocking moves from the component into `form-fields.ts`, where PME-01 and PME-03 already live, and gets a direct unit test instead of a DOM test.
- One guard test asserts the client's rule vocabulary matches a fixture the server tests already produce.
- The editor's cross-feature import of a details helper moves to a place both screens own. The Atlas-REST delete the editor calls stays where VDE-11 put it, because moving it to the view door changes a wire answer.
- `section-config.ts` needs nothing. The audit checked it and found pure data plus one lookup.

**Rule ids:** `WFE-01` up to `WFE-06`. **DD:** 802 to 808.

### 19.7 Small deletions

**Delivers:** one retry helper in place of six copies, and narrower derived blocks on the wide stored-entity record.

**Design notes.**

- The retry helper deletes about 60 lines. Each call site keeps its own error mapping through a parameter.
- The 91-field stored record is not rewritten. Its derived blocks (`app_search`, `quality_result`, `governed`) become nested frozen records, which gives readers narrower types without touching storage.

**Rule ids:** `PAR-01` up to `PAR-03`. **DD:** 809 to 811.

## Ledger reservation

Numbers are claimed at merge time, and parallel branches collide. Reserve a block, then re-check against `origin/main` immediately before each push.

| Ledger | Current max | This plan reserves |
| --- | --- | --- |
| DD | 766 | 767 to 811 |
| DV | 188 | 189, only if 19.3 records the RPS-02 gap as a deviation |
| ADR | 068 | none |
| Rule | none | `QRY`, `WRS`, `RUL`, `EDS`, `SVC`, `WFE`, `PAR` (all free) |

Roadmap rows go in `docs/architecture/conversion/index.md` as series 19, status `planned`. Rule-id rows go in `deviations.md` only where an increment changes behaviour a parity test can see. No increment here changes that behaviour, so expect zero `java-map.md` rows for the whole series.

## Verification

The acceptance gate is unchanged: CI runs commit checks, unit tests, and e2e on every pull request. Use the cheapest level that covers the increment, and say which you ran.

| Level | Covers | Command |
| --- | --- | --- |
| 0 | 19.3, 19.7, and the pure moves of 19.4 | `uv run pytest libs/python/aurelius-atlas-core/tests` |
| 1 | 19.1, 19.2, 19.5 unit suites | `nx test <project> -c ci` |
| 2 | 19.2 door behaviour, 19.5 routes, 19.6 flows | `nx e2e aurelius-atlas-server`, `nx e2e aurelius-atlas-webapp` |

Three standing checks apply to every increment in this plan.

1. Run the parity scenarios. Every increment must answer byte-identical to its base, or the difference is written into `deviations.md` in the same commit.
2. Run `uv run aurelius-atlas-trace check` scoped to your own rule ids. It exits 2 offline on main for two pre-existing collection errors, so compare against your base rather than reading the exit code alone.
3. Run the three docs gates on any page you touch: prettier, `zensical build --strict`, markdownlint.

## Risks

| Risk | Mitigation |
| --- | --- |
| 19.2 touches the retry and rollback path, where a mistake loses writes | Land the contract first with `EntityStore` as the only implementation and no behaviour change. Split the transaction object into its own commit. Prove the level-2 write suites green between the two. |
| 19.1 changes what the fakes accept, which can surface real bugs in production query code | That is the point of the increment. Triage each new failure on its own branch, and do not fix them inside 19.1. |
| 19.4's move is 1,300 lines across 64 importers, and reflows swamp the review | Pure-move commit, then a behaviour commit. Prove equality with `git diff -w` and a rename-detection review. |
| 19.5 changes route signatures in 13 files | Providers read `app.state` internally, so no route body changes semantics. One commit per route family. |
| 19.3 exposes a real behaviour difference between the two write paths | Write the RPS-02 finding up before the refactor. If it is a bug, it gets its own fix commit and its own test, and it is not folded into the refactor. |

## Rollback

Every increment is a squash-merged pull request on `main`, so rollback is a `git revert` of one SHA. Two need more than that.

1. **19.2:** if a write-path defect reaches `main`, revert and re-open. The store contract is additive, so the revert leaves no orphaned files.
2. **19.1:** the differential test fails on `main` when it uncovers a query bug that unit tests hid for a long time. Keep the shared builder, and mark the newly failing scenarios `xfail` with a link. That is the pattern 14.6 uses for frozen-oracle disagreements.

## Not checked

The audit did not read `libs/python/aurelius-atlas-quality`, the `aurelius-atlas-dsl` grammar internals (it read its boundary and found the layering clean), `helm/`, `docker/`, `tools/`, the three scanner apps past their settings modules, or the 6.3 import and export audit services. It ran no CI and no e2e. Every line reference came from reading source and tests on `main` at 91c0db622 on 2026-11-21.
