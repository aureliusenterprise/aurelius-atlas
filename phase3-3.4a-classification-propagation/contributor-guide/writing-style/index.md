# Writing Style

The style this documentation is written in, and the rules the page-by-page style pass applies. The reference implementation is the [Development Environment](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/contributor-guide/development-environment/index.md>) guide: short sections that each do one job, callouts for the important and the anticipated, tables for enumerations. Every page aims for that shape.

## The shape of a page

1. **Lead**: one paragraph, two to four sentences. What the page covers and why a reader needs it — in the reader's terms, before any mechanism.
2. **Sections**: one job per `##`, named for that job. A reader scanning the headings should get the page's outline; a reader opening one section should not need the neighbours.
3. **The point first**: every section and paragraph states its conclusion first, then supports it. Build-ups bury the answer.

The size rule: **no block of prose longer than about seven lines.** When a section grows past it, the content is one of these instead:

- a **list** — the block is a set of parallel items
- a **table** — the items have two or more attributes each
- a **callout** — the content is a warning, prerequisite, example, or anticipated question
- a **subsection** — the block contains two jobs
- a **diagram** — the block describes a flow between parts

## Callouts

Callouts carry what the prose must not: risk, prerequisites, the expected question. Use the type for its meaning, not for colour.

| Callout | Use for |
| --- | --- |
| `!!! NOTE` | A prerequisite the reader must have met before the steps work |
| `!!! TIP` | Advice that saves the reader time; the better path, not a requirement |
| `!!! WARNING` | A failure the reader *will* hit, with the reason and the fix |
| `!!! IMPORTANT` | A rule whose violation damages data, security, or the build |
| `??? QUESTION` | The question the reader is forming right now |
| `??? INFO` | Background that rewards the curious and clutters everyone else (collapsible) |
| `??? EXAMPLE` | A worked example or deep dive |

Two habits from the dev-environment guide worth copying everywhere:

- Name expected failures as expected: *"this is expected, not a broken setup."*
- Keep the callout's own text short — it is a paragraph, not a section.

```
!!! WARNING "Your first tests may fail until your key is registered"

    Almost every `serve`, `test`, and `e2e` target first runs a `decrypt` step. Decryption only
    succeeds once your public key is listed in `.sops.yaml`. Until then, commands fail with a
    SOPS/age decryption error — this is expected, not a broken setup.
```

## Diagrams

A flow that takes a paragraph to describe is usually one diagram and one sentence. Draw when the content is a **sequence across parts**, a **decision**, or a **lifecycle**; keep prose for declarations and enumerations.

Rules: `mermaid` fenced blocks only; at most about eight nodes; label the edges — a bare arrow states a connection, a labelled arrow states the contract; one sentence after the diagram stating what it proves (never "the following diagram shows…").

```
graph LR
    P[Pull request] -->|two signatures| M[main]
    M -->|nx release| R[Signed release]
    R -->|promote| D[Deployment]
```

Merge requires two signatures; the release is the unit a deployment promotes ([ADR 024](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>)).

## Voice

- **Present tense, active voice.** "The server reads its settings at start-up", not "settings will have been read".
- **Guides address the reader** ("run", "open", "your key"); **architecture pages state facts about the system** ("the server reads", "every path is TLS").
- **Name the thing** in guides: "`nx certgen` issues the certificates", not "a tool generates material". Architecture pages reverse this: parts by role, product names only in the anchor line (see [Structure rules](<#structure-rules>)).
- **Plain words over compressed epigrams.** Say the thing straight: "being up to date is the default", not "the default is currency"; "we chase every update the day it appears", not "every update is chased the day it publishes". A sentence that needs a second reading to decode is rewritten, not kept for its rhythm. Compression is allowed in table cells, never in prose.
- **Define shorthand on first use.** "The gate (the shared rule set of checks in ADR 014)", once per page; after that, the short name is fine. Team-internal shorthand — "spine", "slice", "the gate", "the ladder" — is defined where it first appears, per the glossary in [Architecture Decisions](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/#terms-used-in-these-records>).
- **No noun-stacking or bumper-sticker clauses.** "Age by choice is policy; age by forgetting is drift" becomes "keeping a dependency old on purpose is a recorded decision; getting old by forgetting is drift". If a clause fits on a bumper sticker, expand it.
- **Sentence case headings**, proper nouns aside — "The CI gate", "Configure your SOPS key".
- **Cite, don't restate.** An ADR, spec, or code path owns the detail; the page links it once. ADR references stay parenthetical at the sentence that needs them.
- **No marketing in technical pages.** Benefit framing belongs in the lead; the sections are facts.

## Structure rules

- **The litmus test** decides what an architecture page may say: *would this detail still matter if we replaced every technology in the stack?* If yes, it is architecture. If no, it is design detail and belongs in the component's own documentation. The same test governs ADRs ([Architecture Decisions](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/#keep-decisions-business-focused>)).
- **Role-first naming** on architecture pages: parts appear by role ("the search store", "the identity provider", "the collector"). A page names the current implementation **once**, as a labelled anchor line — evidence, not contract. Ports, env-var names, file paths, version numbers, and commands do not appear in architecture prose.
- **Where extracted detail goes**: component detail (settings, storage layout, protocol mechanics) → that component's [API Reference](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/api-reference/index.md>) page, which doubles as its design documentation; cross-cutting how-tos (testing commands, certificates, releasing, setup) → a Contributor Guide page; development topology → [Dev Topology](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/contributor-guide/development-environment/#dev-topology>) and the `dev/` slice READMEs. Every extraction leaves a pointer sentence behind in the architecture page.
- **Production first** on architecture pages: the production arrangement is the subject; the development arrangement appears only as a labelled short section stating rules, pointing to the design documentation and guides for mechanics ([example](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/platform/delivery/configuration-management/index.md>)).
- **Page = one increment's material**, per the [filling maps](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/index.md>); unwritten pages carry the `Planned` marker.
- **Status language is exact**: `written (0.2)`, `Planned`, increment numbers as written. No "soon", no "we plan to" — the increment's status line says it.

## ADRs and the design log

The record skeleton is fixed — `Decision`, `Context`, `Requirements`, `Alternatives`, `Tradeoffs`, `Consequences`, in that order — so records stay comparable ([template](<https://aureliusenterprise.github.io/phase3-3.4a-classification-propagation/architecture/adr/template/index.md>)). The style pass works **inside** sections, never on the skeleton:

- Lead every section with its answer: the decision in one sentence, the requirement as a gradeable "must", the tradeoff as what was given up. The bold lead-in names the rule in plain words ("**Being up to date is the default.**"), not in a compressed phrase.
- Long uniform blocks become numbered requirements, alternative tables, and one-line consequences.
- Sharp edges stay named, in the `Decision` section, not discovered in `Consequences`.
- Callouts apply as everywhere, inside the sections: `??? QUESTION` for the objection a reader forms at that sentence ("why not automate the majors too?"), `!!! WARNING` for a named decay mode the record accepts. A record earns one or two, not one per paragraph.
- Diagrams do not go in records; a flow that needs one belongs in the architecture page the record constrains.

## Mechanics

| Rule | Setting |
| --- | --- |
| Line length | 110 (markdownlint MD013); wrap prose at \~100 |
| Formatting | Prettier, `proseWrap: preserve` — run it, don't hand-align tables |
| Links | Relative paths; anchors lowercase-hyphen; no link rot (strict) |
| Code | Commands in fenced `bash` blocks; paths and flags in backticks |
| Tables | Short cells; long text goes in prose, not a cell |

Validate with the three gates, in order:

```
npx prettier --check "docs/**/*.md" mkdocs.yaml
uv run zensical build --strict
uv run pre-commit run markdownlint --files <changed files>
```
