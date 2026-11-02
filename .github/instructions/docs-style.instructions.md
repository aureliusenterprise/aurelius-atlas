---
applyTo: "**/*.md"
description: >-
    Plain-English writing style (ASD-STE100 adapted), document shape, and
    per-type rules (architecture, design records, implementation) for all
    Markdown documentation.
---

# Documentation style

Write plain English that a smart reader outside the field understands on one read. The sentence rules come
from ASD-STE100, the controlled language that aerospace uses for maintenance manuals. They are adapted from
the MIT-licensed [SimpleEnglish skill](https://github.com/AminBlg/SimpleEnglish). The shape and structure
rules below come from `docs/contributor-guide/writing-style.md`, which stays canonical with worked
examples; read that guide and its reference page `docs/contributor-guide/development-environment.md`
before you write a new page.

When you edit an existing page, write new and changed text with these rules. Do not rewrite text that your
change does not affect.

## The three document types

| Type                      | Lives in                                                                                                                           | Its job                                           |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Architecture              | `docs/architecture/` (except `adr/` and `conversion/`)                                                                             | The shape of the system, in role terms            |
| Design records            | ADRs in `docs/architecture/adr/`; `DD-NNN` entries in a spec's `design.md` (archive: `docs/architecture/conversion/design-log.md`) | Why a decision was made, kept comparable          |
| Implementation (as-built) | Project `README.md` and `AGENTS.md` files; pages in `docs/api-reference/`                                                          | How the thing is today: commands, paths, settings |

The rules under "Document shape", "Callouts", "Diagrams", "Voice", and "Mechanics" apply to all three.
The "Structure rules" and "Design records" sections apply only to the type named there.

## Rules

1. **Classify each passage.** Procedural text tells the reader what to do: imperative mood, 20 words per
   sentence at most, one instruction per sentence. Descriptive text explains: simple tenses, 25 words per
   sentence at most, one topic per paragraph, six sentences per paragraph at most.
2. **Never touch** code, identifiers, commands, flags, file paths, quoted errors, product names, or facts. If
   the source gives no number or cause, keep the general statement. Never invent a fact to sound precise.
3. **Condition before command, with a comma.** "If the build fails, read the log."
4. **Use simple tenses and active voice.** No present perfect ("has completed" becomes "completed"). No "-ing"
   verb after a comma (", making it easy" becomes a new sentence). Name the actor: "You run the migration."
5. **Modals:** use can, will, must. Never use should, would, may, might, or could. A required "should" becomes
   "must". An optional one is deleted.
6. **Use complete grammar.** No contractions. Keep articles. Keep "that". Write short sentences, not telegraph
   style.
7. **No semicolons and no em-dashes.** Write two sentences, or name the relation.
8. **One word, one meaning,** for the whole document. Use `make sure that` for check, verify, confirm,
   validate, and ensure. Use `configuration` for config, settings, and options. Break noun chains of more than
   three words with a preposition ("the timeout value for the connection pool").
9. **Give the reader each term and fact before the step that needs it.** Define a concept term at its first
   use, in under ten words, one definition per sentence. Do not define product names, standard names
   (Postgres, S3, HTTP), or the tool that the document is about. Also name the host, the flag, or the earlier
   step that a command depends on. "Restart the service" becomes "Restart the `sync` service on the host that
   runs the job."
10. **State the fact, not its importance.** Delete words that carry no fact (see the word list below). No "not
    just X, it is Y". No decorative triplets. No "in conclusion".
11. **Use formatting only where it carries structure.** No bold as emphasis and no emoji. Bold lead-ins are
    allowed only inside design records, where the record template asks for one (see "Design records"). Use a
    vertical list for three or more parallel items or steps: colon on the lead-in, uppercase start, one
    instruction per item.
12. **Warnings:** the command or condition first, then the risk. "Do not run this against production. The
    command deletes rows."

Use American spelling. If the repo has a Markdown lint config (for example `.markdownlint.json`), follow its
line length and list indent.

Before:

> **Connection timeouts.** If the service hangs or fails with `dial tcp: i/o timeout`, check that the host can
> reach the Postgres port (usually 5432) — this is often a firewall rule blocking the connection.

After:

> ## Connection timeouts
>
> The service stops with `dial tcp: i/o timeout` when it cannot connect to the Postgres port (5432 by
> default).
>
> 1. Make sure that the host that runs the service can connect to the Postgres port. A firewall usually blocks
>    it.

## Document shape

Short sections that each do one job; callouts for the important and the anticipated; tables for
enumerations. That is the target shape of every page.

1. **Lead**: open a page with one paragraph, two to four sentences. What it covers and why the reader needs
   it, in the reader's terms, before any mechanism.
2. **One job per `##` section**, named for that job. A reader who scans the headings gets the page's
   outline; a reader who opens one section does not need its neighbours.
3. **The point first**: every section and paragraph states its conclusion first, then supports it.

**No block of prose longer than about seven lines.** When a block grows past it, the content is one of
these instead: a list (parallel items), a table (items with two or more attributes each), a callout (a
warning, prerequisite, example, or anticipated question), a subsection (the block holds two jobs), or a
diagram (a flow between parts).

## Callouts

Callouts carry what the prose must not: risk, prerequisites, the expected question. Use the type for its
meaning, not for colour. Keep a callout's own text to one paragraph.

| Callout         | Use for                                                     |
| --------------- | ----------------------------------------------------------- |
| `!!! NOTE`      | A prerequisite the reader must have met before steps work   |
| `!!! TIP`       | Advice that saves time; the better path, not a requirement  |
| `!!! WARNING`   | A failure the reader will hit, with the reason and the fix  |
| `!!! IMPORTANT` | A rule whose violation damages data, security, or the build |
| `??? QUESTION`  | The question the reader is forming right now                |
| `??? INFO`      | Background for the curious; collapsible                     |

Name expected failures as expected: "this is expected, not a broken setup."

## Diagrams

Draw when the content is a sequence across parts, a decision, or a lifecycle; keep prose for declarations
and enumerations. Use `mermaid` fenced blocks, at most about eight nodes, and label the edges: a bare
arrow states a connection, a labelled arrow states the contract. Put one sentence after the diagram that
states what it proves, never "the following diagram shows".

## Voice

- Present tense, active voice. "The server reads its settings at start-up", not "settings will have been
  read".
- Guides address the reader ("run", "open", "your key") and name the thing: "`nx certgen` issues the
  certificates", not "a tool generates material". Architecture pages state facts about the system.
- Plain words over compressed epigrams. Say the thing straight. A sentence that needs a second reading to
  decode is rewritten, not kept for its rhythm. Compression is allowed in table cells, never in prose.
- No noun stacking or bumper-sticker clauses. If a clause fits on a bumper sticker, expand it.
- Define shorthand on first use, once per page: "the gate (the shared rule set of checks in ADR 014)";
  after that the short name is fine.
- Sentence case headings, proper nouns aside.
- Cite, do not restate. An ADR, spec, or code path owns the detail; the page links it once. Keep ADR
  references parenthetical at the sentence that needs them.
- No marketing in technical pages. Benefit framing belongs in the lead; the sections are facts.

## Structure rules

- **The litmus test** decides what an architecture page may say: would this detail still matter if we
  replaced every technology in the stack? If yes, it is architecture. If no, it belongs in the component's
  `docs/api-reference/` page or the project README.
- **Role-first naming** on architecture pages: parts appear by role ("the search store", "the identity
  provider"). Name the current implementation once, as a labelled anchor line. Ports, env-var names, file
  paths, version numbers, and commands do not appear in architecture prose.
- **Production first** on architecture pages: the production arrangement is the subject; the development
  arrangement appears only as a labelled short section that points to guides for mechanics.
- **Implementation docs carry the mechanics.** Commands, file paths, flags, env-var names, and version
  numbers live in project `README.md` and `AGENTS.md` files and in `docs/api-reference/` pages, which
  double as a component's design documentation. Every extraction from an architecture page leaves a
  pointer sentence behind.
- **Page = one increment's material**; unwritten pages carry the `Planned` marker. Status language is
  exact: `written (0.2)`, `Planned`, increment numbers as written. No "soon", no "we plan to".

## Design records

- The skeleton is fixed so records stay comparable. ADRs: `Decision`, `Context`, `Requirements`,
  `Alternatives`, and `Tradeoffs`, in that order. Design entries (`DD-NNN`, in the increment's
  `design.md` next to its spec): a `### DD-NNN.` heading with a Status/Increment/Date line, then bold
  **Decision**, **Reason**, and **Alternatives** paragraphs. `docs/architecture/conversion/design-log.md`
  is the read-only archive of entries written before per-increment design files existed.
- **Lifecycle:** a record's status moves Proposed, then Accepted, then optionally Superseded or Deprecated.
  A new record always enters as `Proposed`. Only a person moves it to `Accepted`. An agent that writes a
  record never writes that status, and never confirms on a person's behalf.
- Never edit the body of an accepted record, only its status line. A changed decision is a new record that
  supersedes the old one: the new record links the old, and the old record's status line gains
  `Superseded by [NNN](./NNN-slug.md)`. A supersede is a decision of the same weight as a new record, so
  it needs its own human confirmation.
- The shape and sentence rules work inside the sections, never on the skeleton. Lead each section with its
  answer in plain words; bold lead-ins are right here. Long uniform blocks become numbered requirements,
  alternative tables, and one-line consequences. Name sharp edges in `Decision`, not discovered in
  `Tradeoffs`. A record earns one or two callouts, not one per paragraph. Diagrams do not go in
  records; a flow that needs one belongs in the architecture page the record constrains.

## Mechanics

| Rule        | Setting                                                           |
| ----------- | ----------------------------------------------------------------- |
| Line length | 110 (markdownlint MD013); wrap prose at ~100                      |
| Formatting  | Prettier, `proseWrap: preserve`. Run it, do not hand-align tables |
| Links       | Relative paths; anchors lowercase-hyphen; no link rot (strict)    |
| Code        | Commands in fenced `bash` blocks; paths and flags in backticks    |
| Tables      | Short cells; long text goes in prose, not a cell                  |

Validate with the three gates, in order:

```bash
npx prettier --check "docs/**/*.md" mkdocs.yaml
uv run zensical build --strict
uv run pre-commit run markdownlint --files <changed files>
```

## Word list

If a word carries no fact, delete it. Otherwise swap it:

| Do not write                                                      | Write                                    |
| ----------------------------------------------------------------- | ---------------------------------------- |
| leverage, utilize, harness                                        | use                                      |
| in order to                                                       | to                                       |
| prior to                                                          | before                                   |
| ensure                                                            | make sure that                           |
| enables you to, allows you to                                     | you can                                  |
| in the event that                                                 | if                                       |
| due to the fact that                                              | because                                  |
| functionality                                                     | function, feature                        |
| and/or                                                            | one of them, or "X, or Y, or both"       |
| e.g., i.e., etc.                                                  | for example, that is, or name the items  |
| out of the box                                                    | by default                               |
| under the hood                                                    | internally                               |
| furthermore, moreover                                             | also                                     |
| gracefully handles                                                | say what it does ("retries three times") |
| as needed, as necessary                                           | state the condition                      |
| simply, just, easily, seamlessly, robust, powerful, comprehensive | delete, or give the measurable property  |
| it is worth noting, in conclusion, at the end of the day          | delete                                   |

## Self-check before you finish

1. Count the words in your three longest sentences. If a procedural sentence has over 20 words or a descriptive
   one has over 25, split it.
2. Search your new text for: `'`, `has been`, `should`, `may`, `;`, `—`, `, making`, `**`, `check`, `verify`,
   `config`. Fix each hit that is not code, a quote, or a name. A `**` is right only inside a design record
   whose template asks for it.
3. Check the shape: each section does one job, the page has a lead, and no prose block runs past about
   seven lines.
4. Read each step. If it relies on a host, a flag, or an earlier step that the reader must already have, name
   it or link to it.
