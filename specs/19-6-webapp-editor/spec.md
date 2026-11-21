# 19.6 An editor that reports its own outcome

- **Status:** in review
- **Pull request:** #432
- **Records:** DD-802 to DD-808, plan in [plan.md](./plan.md), design in [design.md](./design.md)

## Scope

This increment gives the entity editor a way to state what its own delete did, moves the parent-choice rule
and
the classification combobox out of the component to places with direct tests, and adds one guard that fails
when a
client form rule drifts from the Python rule it copies. It changes no answer that leaves the server. The
editor
answers the same on screen; only how it knows the outcome changes.

This increment changes no answer that leaves the server. It touches Angular and the client's own form rules.
The
parity scenarios are a server concern and do not run on this increment. The webapp's own unit and e2e suites
are
the gate, and that is below.

This increment does not deliver:

| Not delivered                               | It lands in |
| ------------------------------------------- | ----------- |
| The server's parent-end rule owner          | 19.3        |
| The store contract and the write-path seams | 19.2        |
| Any change to a server route or answer      | 19.5        |

## Semantics

The editor today decides whether a delete succeeded by searching the alerts store for its own message text,
stamped
after a local clock. A reword or a localization change flips "deleted" into "refused", and the unit tests keep
passing because they assert the current text. The rules below make the editor state the outcome where it
performs
the action.

| Id     | Rule                                                                                                                                                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| WFE-01 | The editor sets the result of its own delete on a signal in the code that performs the delete. It does not read the alerts store to infer the outcome.                                      |
| WFE-02 | The delete-outcome signal follows the save-outcome signal. The save path uses the `EntitySaved` tick to reach the drawer; the delete path uses the same kind of signal, not alert text.     |
| WFE-03 | The classification combobox is its own component, with the members, the handlers, and the tests that belong to it. It keeps no coupling to the rest of the editor class.                    |
| WFE-04 | The parent-choice blocking rule (PME-10) lives in `form-fields.ts` beside PME-01 and PME-03, and has a direct unit test. It is no longer decided in the component and proven by a DOM test. |
| WFE-05 | One guard test asserts that the client's form-rule vocabulary matches a fixture that the server's own tests produce. A client rule that drifts from its Python original fails this test.    |
| WFE-06 | The editor stops importing a details-screen helper (`cardTypeAlias`). The helper moves to a place both screens own, so the editor does not reach into the details feature.                  |

## Java origin

This ports nothing. The Atlas 2.4.0 dashboard's entity editor is a different application, and the webapp is a
slice-by-slice Angular rewrite of its behaviour (ADR 053). The delete inference, the combobox, and the PME-10
client rule are Aurelius Angular code, so this increment adds no row to
[Java map](../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas. The editor answers the same on screen, so the increment adds no row to
[Deviations](../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                          | Command                                                                          | Level |
| ---------------------------------------------- | -------------------------------------------------------------------------------- | ----- |
| Every WFE rule has a test that names it        | the webapp test names carry the rule ids                                         | 0     |
| The delete outcome is a signal, not alert text | `npx nx test aurelius-atlas-webapp -c ci` with the WFE-01 and WFE-02 tests       | 0     |
| A reword does not change the outcome           | a test rewords the delete line and the outcome stays the same                    | 0     |
| The combobox is its own component              | the combobox has its own component file and its own spec                         | 0     |
| PME-10 has a direct unit test                  | `form-fields.spec.ts` carries the PME-10 test, no DOM test                       | 0     |
| The rule-vocabulary guard fails on drift       | the WFE-05 guard test, run against a deliberately edited fixture                 | 0     |
| The live editor flow still works               | `npx nx e2e aurelius-atlas-webapp` for the editor delete and save flow           | 2     |
| Lint and types                                 | `npx nx lint aurelius-atlas-webapp` and `npx nx typecheck aurelius-atlas-webapp` | 0     |

## Design decisions

The reasoning for each rule above lives in [design.md](./design.md) as DD-802 to DD-808. The two worth reading
before the rest are DD-802, which records why the editor states its own outcome, and DD-805, which records the
guard that keeps the client form rules honest against the Python originals.
