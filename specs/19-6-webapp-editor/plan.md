# Plan: 19.6 An editor that reports its own outcome

The rules are WFE-01 to WFE-06 of [the spec](./spec.md), the design DD-802 to DD-808.

## Analysis

- **The delete inference.** `entity-editor.component.ts:621-638` scans the alerts store for `deletingLine`
  text stamped after `deleteStartedAt`, so a reword flips success into refusal, and the spec asserts the
  current text.
- **The save precedent.** `entity-saved.ts` is the `EntitySaved` tick that already reaches the drawer after a
  save (DD-327). The delete path should use that shape.
- **The combobox.** About twenty classification members and five handlers live in the editor with no coupling.
- **PME-10.** The parent-choice blocking is decided in the component and proven by a DOM test, while PME-01
  and PME-03 already live in `form-fields.ts`.
- **The drift guard.** `attribute-labels.spec.ts` already fails when a client label drifts from the catalogue,
  the pattern WFE-05 extends to form rules.
- **The cross-import.** The editor imports `cardTypeAlias` from `details/shared/card`.

## Steps

1. A delete-outcome signal shaped like `EntitySaved`; the delete code sets it, and the alert-scan effect goes
   away (DD-802, DD-803). Its test rewords the line and checks the outcome holds.
2. The classification combobox to its own component and spec (DD-804).
3. PME-10 to `form-fields.ts` with a direct unit test (DD-806).
4. The rule-vocabulary fixture from the server tests, and the guard test (DD-805).
5. `cardTypeAlias` to a shared place; the editor's cross-feature import goes away (DD-807).

Commit 1 is the behaviour the finding is about, so it lands with its reword test. Commits 2 to 5 move code
without
changing what the editor sends (DD-808).

## Verification

Level 0: `npx nx test aurelius-atlas-webapp -c ci` (Vitest), ruff does not apply, `npx nx lint` and `npx nx
typecheck aurelius-atlas-webapp`. The WFE-01 reword test is the gate for the finding. Level 2: `npx nx
e2e aurelius-atlas-webapp` for the editor delete and save flow. No parity scenario runs, because the increment
sends nothing new to the server (DD-808).
