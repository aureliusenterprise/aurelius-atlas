# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-884. Lineage is a top-level feature reached through a barrel; the routed quickview stays a direct import

- **Status:** Proposed
- **Increment:** 7.57
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** `search/details/lineage/` moves to `src/app/lineage/` (git mv,
history kept) and becomes a top-level feature. Its `index.ts` re-exports exactly
`LineageModel` and `LineageModelState` — the box the details screen mounts and the
root store it injects. Every other module in the folder (the diagram, the browse/
model/view tabs, the entity and property tables, the AR3 parser and index helpers,
the PNG metadata, and the routed quickview `LineageModelBrowser`) is internal. A
new guard in `check-webapp-purity.sh` fails the build if any file under `search/`
imports a file inside `lineage/` rather than the barrel. The drawer route and its
spec keep a **direct** import of `lineage/model-browser.component`.

**Why.** The folder sat inside the details feature but its module depends on
`shell/session.service`, `shell/version.service`, and `tokens` — app-level
services, not details' business (the architect review's item 7: "it reaches into
shell/* and tokens, so it is a feature, not a sub-folder"). Promoting it stops a
`search/` feature from owning dependencies that belong above `search/`, and puts
it beside the other top-level features. A barrel, not per-file imports, is what
makes the boundary nameable: the plan says "Add one only for `lineage/` and
`search/shared/`, where the boundary needs a name", and a two-name surface is the
whole contract another feature needs. The guard goes in `check-webapp-purity.sh`
rather than an Nx tag because the script is the gate that already enforces the
neighbouring layer rules (DD-869/DD-870) and greps relative imports — an Nx tag
would need tags on every folder and a rewrite of the open `depConstraints`, which
item 3 does separately; the guard here is the specific rule, added where the
other specific rules live.

The quickview stays a direct file import because Angular splits a route on the
imported module: routing it through the barrel would pull `LineageModelBrowser` —
and through it the diagram, tabs, and AR3 parsers — into whatever chunk imports
the barrel, undoing the lazy chunk the `drawer` route exists to get. So the
eager consumer (the details screen) uses the barrel and the lazy consumer (the
route) uses the file, and the guard's scope is exactly `search/`, which lets the
route's direct path through because `routes.ts` is outside `search/`.

**Alternatives considered.** _Re-export the whole folder._ Defeats the boundary —
every internal name becomes fair game, and it folds the lazy route into the
eager barrel graph. _Add Nx tags for all of `src/app` here too._ That is plan item
3 (the workspace-wide mechanical boundary); bundling it would mix a 31-file
rename with a lint-config change touching every project, against the one-slice
rule. It follows in its own increment. _Leave the folder in place and only add the
guard._ The boundary would still be real, but the folder's dependency on
`shell/`/`tokens` would keep `search/` pointing at app services — the exact
inversion the move removes. _Re-point the route through the barrel and accept the
bundle cost._ Measured against keeping a 39 kB route chunk lazy, the cost is the
whole lineage feature loading on first paint of any screen that imports the
barrel; not accepted.
