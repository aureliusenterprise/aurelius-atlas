# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-359. Each alert links its section of one runbook page

- **Status:** Proposed
- **Increment:** 6.4f
- **Date:** 2026-11-05

**Decision.** The steps for every alert live on one page, Incident Management, one section per rule anchored
by the rule's uid. Each rule carries `runbook_url` to its section on the published docs. A test fails when a
rule has no section.

**Reason.** A responder starts from the alert, so the alert must say where the steps are. Grafana's
`runbook_url` is the annotation its UI and notifications show as a link. One page keeps the steps of related
alerts beside each other, such as the store, the collector and the snapshots, and in one review. The test
keeps a new rule from arriving without its steps (ADR 041 R2).

**Alternatives.** The steps in each rule's `description`: Grafana shows it, but a rule's text is no place for
numbered steps and commands, and the dev and chart copies would carry them twice. A page per alert: eight
small pages whose steps refer to each other.

**Consequences.** The link points at the published site, which shows the main branch: a change to a rule and
its steps lands together, and a deployment of an older release reads the newer steps. A renamed uid changes
the anchor, so the test checks both together.

### DD-360. An incident's record is a docs page beside the runbook

- **Status:** Proposed
- **Increment:** 6.4f
- **Date:** 2026-11-05

**Decision.** Each incident and each rehearsal leaves one page in `resilience/incidents/`, named by its date
and a slug, with five sections: Summary, Timeline, Actions, Cause, Follow-ups. A test checks the sections and
that the page is listed.

**Reason.** ADR 041 R5 asks for a record a future responder and the next audit can read. A page in the docs is
reviewed like any change, versioned with the system it describes, and found from the runbook it used. The five
sections are the ones the incident path already names.

**Alternatives.** An issue per incident: searchable, but outside the reviewed tree, and its fields drift. A
log file of incidents: one growing file whose structure nobody checks.

**Consequences.** A record that names customers' data or people's addresses does not belong in the public
docs; it keeps the facts and leaves the names out. A rehearsal's follow-ups land in the same pull request when
they are small, as this increment's do.
