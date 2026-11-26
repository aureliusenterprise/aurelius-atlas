# User Documentation Plan

The User Guide documents installation and nothing else. A person who signs in to the catalogue
finds no page that explains what to do. This plan gives the guide its task pages for catalogue
users, on the Aurelius webapp, and drops the current posture that sends readers to the Apache
Atlas 2.4.0 documentation. It plans the work only. It writes no guide prose.

The audience is the catalogue user: the data steward, the data scientist, the analyst. The
installer and the operator keep the three pages they have. The integrator keeps the
[API Reference](../api-reference/index.md).

## Why the posture changes

[docs/README.md](../README.md) states that the User Guide "is intentionally short" because the
Apache Atlas documentation describes the behaviour this system reproduces. That was true while the
guide held only installation steps. It stops being true now, for two reasons:

- The Aurelius webapp is not the Atlas dashboard. It has its own screens, its own search modes, and
  its own quality surfaces, and no upstream page describes them.
- The catalogue's behaviour is now documented here: [Deviations from Apache Atlas](../architecture/conversion/deviations.md)
  holds every intended difference, and the specs hold the rules. A guide that sends the reader
  elsewhere duplicates nothing and helps nobody.

The change removes the deferral paragraph from `docs/README.md` and from
[user-guide/index.md](../user-guide/index.md). Nothing else in either file changes.

## Where the guide stands today

| Page                                                         | Job                                             | Task content for a catalogue user |
| ------------------------------------------------------------ | ----------------------------------------------- | --------------------------------- |
| [user-guide/index.md](../user-guide/index.md)                | Five capability bullets, then links to installs | None                              |
| [standalone-server.md](../user-guide/standalone-server.md)   | Includes `docker/README.md`                     | None                              |
| [standalone-tenants.md](../user-guide/standalone-tenants.md) | Add a tenant with `docker/bin/tenant.sh`        | None                              |
| [deployment.md](../user-guide/deployment.md)                 | Install on Kubernetes                           | None                              |

The guide is therefore an install guide with the title "User Guide". Its index borrows the five
capability statements from the product page, which is the right lead and the wrong body.

There is no map of intended pages, so nobody can tell a missing page from a forgotten one. The
architecture trees solve this with a [filling map](../architecture/index.md) and a `Planned`
marker ([Documentation](documentation.md#architecture-pages)). The guide needs the same mechanism,
because the webapp is mid-conversion and many of its screens are still in flight.

## What the legacy documentation teaches

The legacy site ([aurelius-atlas-documentation](https://aureliusenterprise.github.io/aurelius-atlas-documentation/))
and the product page carry usable material and material that must not be ported.

Worth keeping:

- **The scenario spine.** Each User Story states a job, then walks it end to end on real sample
  data ("find where employee data is stored, then find who owns it"). That is the right shape for a
  catalogue guide, and it matches this repository's habit of proving one flow.
- **The five capability statements.** Discover, efficiency, lineage, compliance, quality. They
  already open both the product page and `user-guide/index.md`.
- **Scenarios with names.** `NL1-HR-001`, the Logistics domain. A named object makes a walkthrough
  checkable, which is the rule this plan adopts below.

Not portable:

| Legacy page or pattern                             | Problem                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Data Quality                                       | Describes the Flink-era design: 15 Python rule functions, "you can not enter this rule via the front end", a script to propagate results. The new engine has a closed vocabulary of ten check kinds and two governance kinds ([`rule.py`](../../libs/python/aurelius-atlas-quality/aurelius_atlas_quality/rule.py), [`governance.py`](../../libs/python/aurelius-atlas-quality/aurelius_atlas_quality/governance.py)). Only the five dimensions survive. |
| Conceptual, technical, and Python code in one page | Mixes three audiences. The technical and Python material belongs in the API Reference and the architecture pages.                                                                                                                                                                                                                                                                                                                                        |
| "Challenges" and "Benefits and Features" sections  | Marketing in the body. The house style puts benefit framing in the lead and facts in the sections ([Writing Style](writing-style.md#voice)).                                                                                                                                                                                                                                                                                                             |
| Annotated screenshots, "segment 5", "segment 6"    | Rotates out with the next layout change, and duplicates the interface in prose.                                                                                                                                                                                                                                                                                                                                                                          |
| Hand-kept numbering                                | The rule list numbers two items 12, lists "Check Unallowed Text" twice, and links a broken URL. Hand-copied enumerations drift here as everywhere.                                                                                                                                                                                                                                                                                                       |
| Hosted demo, "A Google account is required"        | This repository ships no hosted demo. The reader's path is the standalone stack.                                                                                                                                                                                                                                                                                                                                                                         |

## Target shape

The nav splits the guide into two groups, because the reader is either trying the product or using
it at work. Nested groups already work in this site (`navigation.indexes`, `navigation.sections`).

```yaml
- User Guide:
      - user-guide/index.md
      - Trying and running it:
            - user-guide/standalone-server.md
            - user-guide/standalone-tenants.md
            - user-guide/deployment.md
      - Using the catalogue:
            - user-guide/quick-start.md
            - user-guide/find-data.md
            - user-guide/understand-data.md
            - user-guide/follow-lineage.md
            - user-guide/check-data-quality.md
            - user-guide/write-quality-rules.md
            - user-guide/change-data.md
            - user-guide/settings-and-alerts.md
```

The page inventory names the job of each page and the increment that makes its screen true. That
column is the guide's filling map. On the day the page is written, confirm a screen against the
running stack or the merged commits, and never copy a status from this table or from the
[conversion roadmap](../architecture/conversion/index.md#roadmap): the roadmap's status column
still reads _in review_ for increments that merged weeks ago (see the gap note below).

| Page                     | Job                                                                       | Screen owner          | Write today?  |
| ------------------------ | ------------------------------------------------------------------------- | --------------------- | ------------- |
| `index.md`               | What the catalogue does, who the guide is for, which page answers what    | —                     | Yes (rewrite) |
| `quick-start.md`         | Sign in, import the sample, reach one dataset page                        | 9.5d, 15.7            | Yes           |
| `find-data.md`           | Hero search, Words/Meaning/Both, results, facets, sort, paging            | 7.4a, 7.4b, 11.5      | Yes           |
| `understand-data.md`     | The details page: header, chips, breadcrumb, properties, sections, People | 7.6, 7.20, 7.21a/c    | Yes           |
| `follow-lineage.md`      | Open the diagram, pan, zoom, select, quickview, save an image             | 7.22a–d               | Yes           |
| `check-data-quality.md`  | The five dimensions, a field's scores, the rules box, the banner          | 7.24–7.25e, 12.x      | Yes           |
| `write-quality-rules.md` | Author a rule from the vocabulary, the threshold, the verdict             | 7.27, 12.5            | Yes           |
| `change-data.md`         | Create, edit, tag, relate, delete, and the history tab                    | 7.7a, 7.7c, 7.35–7.40 | Yes           |
| `settings-and-alerts.md` | Language, search mode, theme, page size, telemetry, alerts, tenant        | 7.14, 7.15, 15.6      | Yes           |

There is no page for people arriving from the Atlas dashboard. The guide describes the one
interface it ships, and the differences from Apache Atlas stay in
[deviations.md](../architecture/conversion/deviations.md). Each page names the gap its own reader
meets, where they meet it: `find-data.md` says a search has no save button and the page URL is the
bookmark, and `change-data.md` says a term assignment builds no field and survives a save untouched
(7.41, DV-193).

## Storyboard

The pages in reading order, with what each one teaches and the data it walks through. Every scene
names a real object from a shipped sample, so a reviewer can repeat it at the running stack.

Every page walks through the `sample_data` bundle: 701 entities, with the `NL1-HR-001` dataset, the
`logistics` domain, real people, and the whole quality corpus. The `small` bundle is a 13-entity
structural fixture with placeholder names (`domain 1`, `dataset 1`) and an isolated domain, and the
`only_gov_quality` bundle holds governance rules alone. Neither tells a story, so no page uses
either. The import script names `sample_data.zip` when given no argument, which keeps one command
throughout the guide.

!!! NOTE "The identities below"

    `demo_atlas`, `demo_steward` and `demo_scientist` exist when the stack runs with tenancy. Without
    tenancy the reader makes their own person, and that person needs `atlas-read` or `atlas-write`.
    The stack's README owns the names and how to make them.

### index.md

What the catalogue answers, and which page answers it.

- The four questions: where is this data, who owns it, can I trust it, what breaks if I change it
- Which page answers which question, in one table
- The two ways in: a stack of your own, or your organisation's deployment
- Language: English, while the webapp ships English and Dutch

### quick-start.md

Twenty minutes from a running stack to one dataset page.

- Before you start: a running stack, one person, one password
- Import the sample: `docker/bin/import-sample.sh`
- Sign in to the webapp
- Reach the `NL1-HR-001` dataset, first by browse then by search
- Where to next, one line per page

Sample `sample_data`, which the command above imports by default. The page reaches one dataset page
and stops; quality comes later, so the reader who stops here learns that the scores are there and
what page explains them.

### find-data.md

The search screen, from a question to a short list.

- The landing page's three starting points: Business context, Technical context, and Data governance
  organization. The first two explore `m4i_data_domain` and `m4i_system`, which the sample holds
  (DV-84), and the third searches the signed-in user's e-mail.
- Words, Meaning and Both, which live in the Settings panel and not on the search screen, and which
  one to try first
- What a result card states, and what its score row means
- The facet column, and today's limit: only the Type facet filters, the other three are read-only
  counters (7.4b, DV-143)
- Order and paging: no sort control by design (7.4a), ten at a time behind a load link, and the
  header count, which a search by meaning words as "closest matches"
- No saved search: the page URL carries the query, so it is the bookmark
- Empty results: three causes, in the order a reader meets them

Sample `sample_data`, identity `demo_scientist`. The searches are `employee`, then `NL1-HR-001`.

### understand-data.md

One record's page, and how to leave it for a related record.

- What a page is made of: header, chips, breadcrumb, prose, stats bar, sections, side navigation
- The breadcrumb rule: the stored parent chain, and no trail at all for a parentless record (DD-630)
- Who answers for the record: the People box on the three types that carry it, and the five merged
  responsibilities on a person's own page (DET-23, DET-41)
- The sections of the eleven layouts, and how a card opens the record it names
- The badge under a name: the type alias, so a Kafka topic reads "Kafka Topic"
- Tags of a record, and the ones propagated to it
- History, read here and edited in `change-data.md`

Sample `sample_data`, identity `demo_scientist`. The records are the `NL1-HR-001` dataset, one of its
fields, and the `logistics` domain.

### follow-lineage.md

The lineage diagram around a dataset.

- Open the diagram, and the two states of the box
- Read the drawing: nodes, connections, labels
- Move: pan, zoom, reset
- Open a node in the quickview, and its three tabs
- Jump from a node to that record's page
- Save the view as an image
- When the diagram answers nothing: a record with no ends, and the aux API down

Sample `sample_data`, identity `demo_scientist`. The path is `NL1-HR-001` through the change-event
process into Kafka and Elasticsearch, which is the legacy cross-platform story and still runs.

### check-data-quality.md

Whether to trust a record, and why not.

- The five dimensions, in the words the screens use
- A dataset's score and its dimension rows
- A field's scores, and why one field sits lower than its neighbours
- The rules box on a field: each rule's own score, dimension and reason
- A rule's own page: the compliance chart, the compliant and the non-compliant records
- The governance banner during an edit: live verdicts, and why one line names two fields
- A dimension with no rows: no rule of that dimension, which is not a failure

Identity `demo_scientist`. The field is `NL1-HR-001.HIER_ORGANIZATION`, which holds three rules of
two dimensions, two of them scored. Every surface named above runs today: the score block (7.25d),
the rule scores on the field (7.25e), the governance rules box (7.25a) and a rule's own page (7.25b)
all merged, so the page carries no `Planned` marker. Two honest absences belong on the page: a
dimension with no rows
means no rule of that dimension, and a rule the scanner never scored keeps its card and prints no
score (DV-207). The reader who wants to change a rule goes to `write-quality-rules.md`.

### write-quality-rules.md

The rules editor, and the closed vocabulary behind it. A rule is written here and read on the
quality page, so the two pages link each other: this one holds the shape of a rule, that one holds
what a score means.

- A rule is data: kind, dimension, parameters, threshold
- The ten check kinds, in plain words, in a table generated from the vocabulary and never copied by
  hand
- The two governance kinds, and the pair that stands in for an OR
- Author a rule: the kind picker, only its own parameters, the threshold
- A save validates the shape through the server's parser before it posts
- The difference between a threshold and a verdict
- Retire a rule by setting it inactive, and why deletion is not the tool

Sample `sample_data`, identity `demo_steward`.

### change-data.md

The editor drawer, and what the reader's rights allow.

- What you may change, in one short table. Four roles exist (`atlas-read`, `atlas-write`, `atlas-types`,
  `atlas-admin`) and only the first two have a webapp screen. This is where an absent pencil is
  explained.
- Create a record: pick a type, fill the required fields, save
- Edit a record
- Tag a record, and what propagation means for the records below it
- Relate two records: one parent per child, and the three parent groups the model refuses (18.2, 18.3,
  18.5)
- No term assignment: the drawer builds no field for it, and a stored one survives a save (DV-193)
- See what changed, and restore one attribute
- When the save is refused: a version conflict, a name taken, a governance line
- Delete a record, which ships: hold **Delete** for three seconds (7.7c, #262)

Sample `sample_data`, identity `demo_steward`.

### settings-and-alerts.md

The two drawers on the header, and the choices they hold.

- Language, and what a change does to the screen
- The search mode setting, and why it reruns the shown query
- Theme, time zone, page size
- Telemetry: what leaves the browser, and its switch
- The alerts drawer: severity, grouping, what a person reads there
- Switch tenant: the account menu, sign in again, one tenant per session

Sample `sample_data`, any signed-in identity. Tenancy on for the tenant section.

## Rules that keep the guide honest

1. **A page documents a screen that runs.** A screen that is in progress or planned carries the
   `Planned` marker naming its increment, the same convention as the architecture pages. A page
   whose increment has merged loses the marker in that increment's pull request.
2. **Every walkthrough names its data and its identity.** "Open the `NL1-HR-001` dataset, signed in
   as `demo_steward`." A reader must be able to repeat it at the running stack. A walkthrough that
   cannot be repeated is deleted, not softened. The two samples are not interchangeable: `small`
   holds 13 entities and no quality data, so every quality scene runs in `sample_data`.
3. **One owner per fact.** The standalone stack's README owns the realm name, the user names, and
   the certificates; the guide links it. Sign-in identities are moving now (9.5b and 15.7 are open),
   so no page may restate them.
4. **Roles appear where the reader needs them.** The reason a pencil is missing belongs in
   `change-data.md`, in one short table. There is no roles page in the user guide; rights design is
   an architecture and admin topic.
5. **No numbered screenshots.** Where an image helps, use one full-screen image with a sentence
   that names what to look at. Keep the first pass to at most eight images, in
   `docs/assets/user-guide/`, captured from the standalone stack with the `small` sample.
   Images are the most expensive thing in the guide to keep true.
6. **The style gates are the review gates.** Prettier, `zensical build --strict`, markdownlint, in
   that order, per [Documentation](documentation.md). Documentation needs no SOPS key and no
   Docker, so the work is a level 0 change.

## Open decisions

!!! QUESTION "Does a hosted demo return?"

    The legacy docs and the product page send readers to a hosted demo. This repository offers the
    standalone stack. Either the guide points only at the stack, or someone runs a demo the guide
    can name. This decision changes `quick-start.md`.

!!! QUESTION "Who retires the legacy site?"

    The product page footer links five times into the legacy documentation, and the legacy site
    holds material that is now wrong. Replacing the posture leaves a public page describing a
    system that no longer exists. The retirement belongs outside this repository, so it needs an
    owner and a date. The guide can carry a one-line note until then.

!!! QUESTION "English only?"

    The webapp ships `en-US` and `nl-NL`. The documentation ships in English. State that in the
    guide's index, so a Dutch reader does not expect a translated guide.

## Gaps to name, not paper over

- **The webapp has no glossary screen.** The server has the whole glossary API (5.2a–5.2d) and the
  landing page can browse `AtlasGlossary`, but the Aurelius webapp builds no glossary editor and no
  term-assignment picker (7.41, DV-193). A guide that implies otherwise is wrong. `change-data.md`
  names the gap where a person reaches for a term.
- **The webapp has no saved searches.** The server has them (4.5). `find-data.md` names the gap where
  a person wants to keep a search, and points at the page URL instead.
- **The roadmap's status column lags the code in several places.** It lists 15.7 as planned while
  `docker/bin/tenant.sh` and its guide page are merged, and it still reads _in review_ for 7.25 and
  7.27, which merged as #462, #463 and #317. Verify a screen against the running stack or the merged
  commits before you write it. Do not trust the roadmap's word over the stack.

## Sequence

Three pull requests, each under the 1,500-line norm for an increment.

| PR  | Deliverable                                                                                                     | Rough size |
| --- | --------------------------------------------------------------------------------------------------------------- | ---------- |
| 1   | Foundation: rewrite `index.md`, add `quick-start.md`, group the nav, remove both deferrals, add the nav entries | ~350 lines |
| 2   | The four core pages: `find-data.md`, `understand-data.md`, `follow-lineage.md`, `settings-and-alerts.md`        | ~700 lines |
| 3   | Governance and change: `check-data-quality.md`, `change-data.md`, `write-quality-rules.md`                      | ~420 lines |

Each pull request carries its own page set, so a reviewer reads one job at a time. PR 1 is the
smallest slice that changes the posture, which makes the posture change the thing under review
first. All three pull requests delivered (PRs #484, #486, and this one), so every page in the
inventory above now exists and no user-guide page carries a `Planned` marker.

An optional guard test joins PR 3, in `tests/`: every `Planned` marker in the user guide names an
increment that exists in the roadmap table, every sample named in a walkthrough exists in
`data/atlas-sample/`, and every user-guide page appears in `mkdocs.yaml`. It is a small test, and
it is the kind of drift this repository already refuses elsewhere.

## Review

Read each page once on the built site, in one sitting, as a new reader. The test is the one from
the writing style: a smart reader outside the field understands it on one read.
