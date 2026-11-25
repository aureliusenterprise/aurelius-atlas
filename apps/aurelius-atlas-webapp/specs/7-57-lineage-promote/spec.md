# 7.57 The Lineage Model leaves `search/details/` and gets a barrel

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-884 (here). No new rule ids. Cites LDG-09 (the `#lineage-model`
  box sits between the card boxes and owns its own fetch), LDG-10 (its three
  states), LDG-25 (the routed quickview in the `drawer` outlet), DD-415 (the root
  `LineageModelState` and the selection the screen reads), DD-388 (the box's
  place in the dataset and process layouts), and DD-869/DD-870 (the layer rule
  this increment extends with a named boundary).

## Scope

The Lineage Model lived at `search/details/lineage/` — a folder inside the
details feature — even though its module reaches into `shell/` and `tokens` (the
session, the version stamp, the app config): app-level services that no `search/`
feature should own. This increment promotes the folder to `src/app/lineage/`,
gives it a public `index.ts`, and adds a mechanical guard so `search/` can only
reach it through that barrel.

The change (no behaviour, template text, or string change):

- `git mv search/details/lineage → src/app/lineage` (31 files, history
  preserved). The folder is now a top-level feature beside `search/`, `settings/`
  and `shell/`, which is where its dependencies already put it.
- A new `src/app/lineage/index.ts` exports exactly two names — `LineageModel`
  (the box the details screen mounts) and `LineageModelState` (the root store it
  injects). Nothing else is public.
- The escaping imports change depth only. The folder moved from four levels below
  `src/app` to two, so each path up is recomputed, not just shortened:
  `../../../tokens` → `../tokens`, `../../../shell/*` → `../shell/*`,
  `../../meta/type-icons` → `../search/meta/type-icons` (meta stayed under
  `search/`), and the test fixture `../../../../../tests/*` → `../../../tests/*`.
  No import was added, removed, or retargeted to a different module.
- Three consumers repoint: the details screen reads `../../lineage`; the drawer
  route and its spec load `./lineage/model-browser.component` directly (kept
  direct on purpose, below).
- `check-webapp-purity.sh` grows one guard: nothing under `search/` may import a
  file inside `lineage/` — the only allowed form is the barrel (`../lineage`). It
  fails the build on a deep import, the way DD-870 made DD-869's layer rule
  enforceable.

It does **not** deliver: any change to the box, the diagram, the tabs, the AR3
parsers, or the quickview (the move is byte-for-byte in their contents); a
barrel for any other folder (the plan names only `lineage/` and `search/shared/`,
and this does `lineage/`; `search/shared/` already reads as a shared layer and its
consumers name files directly); a re-export of the routed quickview (kept out for
the code-split, DD-884); or a change to `java-map.md` and `deviations.md` (the
box, its fetch, and its states are already ported and specced — moving the folder
adds nothing a parity test can see).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The box, the store, and the quickview behave exactly as before.** No file's
  logic, template, or style changes — only the import paths that reach outside the
  folder, which resolve to the same modules at the new depth (build, 1,047 tests,
  and e2e all green).
- **`LineageModelBrowser` keeps its own lazy chunk.** The drawer route
  (`LDG-25`) still imports the component file directly, and the barrel does not
  re-export it, so the build emits it as its own chunk (verified: the AOT build
  still lists a `model-browser-component` lazy chunk). Folding it through the
  barrel would merge that route's code into every eager importer of the barrel.
- **`search/` reaches lineage only through `index.ts`.** The new purity guard
  fails if any file under `search/` writes `…/lineage/<file>`; the only legal
  form is `…/lineage` (the barrel). This names the boundary the architect review
  asked for, mechanically, in the gate that already holds the other layer rules.
- **The other layer rules hold.** Lineage no longer sits inside `search/`, so the
  sibling-feature checks are unaffected; `search/shared` and `search/meta` still
  import no feature. Lineage's own outward imports (`shell/`, `tokens`,
  `search/meta`) are unchanged in target.
- **1,047 tests stay green** across 85 files, unchanged: the specs moved with
  their files and their fixture import depth was fixed with them.
- **The string catalogue is unchanged.** No `$localize` site moved or was
  retargeted, so both locale fixtures stay byte-equal (SHL-08).

## Java origin

Apache Atlas 2.4.0 has no Aurelius lineage folder. The box, its fetch and three
states (LDG-09/LDG-10), the diagram and tabs, and the routed quickview (LDG-25)
are already ported and specced (7.22 series). Moving Aurelius files between
Aurelius directories adds nothing a parity test can see, so this increment adds no
row to `java-map.md`.
