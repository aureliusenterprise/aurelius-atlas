# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design
log apply: an accepted entry is never edited except its status line, and a changed
decision is a new entry that supersedes the old one.

## Entries

### DD-844. The unread corpus rules retire instead of growing new kinds

- **Status:** Proposed
- **Increment:** 12.7g
- **Date:** 2026-11-23
- **Supersedes:** none; follows DD-635 (Proposed, 12.7b, the retirement as data)
  and DD-638 (Proposed, 12.7d, the retirement of unjudgeable rules)

**Decision.** The 34 governance rules of the sample corpus that the vocabulary
cannot read carry `active: false` in both shipped bundles (`sample_data.zip`,
`only_gov_quality.zip`): the 33 `conditional_value` rules and
`m4i_field--qualifiedName` (`uniqueness('qualifiedName')`). No code changes;
VEV-03 and ASG-03 take an inactive rule out of the verdicts, the editor, the
rule pages and the 14.6 read set exactly as DD-638's did, and the details box's
client filter (`isActive`) drops it from the section. The vocabulary stays at its
two kinds. The two expression forms it reads (`completeness('<name>')`,
`length('<name>', 1)`, ASG-02) stay as they are.

**Reason.** A `conditional_value('target_relationship_type',
'source_typename' | 'target_typename', {…})` rule asks what type a relationship
is, or what type the entity on its other end is. The vocabulary has no kind for a
type (GQ-01), and the verdict record cannot carry one: an entity's relationship
reads as its end GUIDs alone, never their type names (VEV-08, ASG-04). So the
rule is unread on every path (VEV-03, ASG-02) and paints an iconless row by
design (DV-155). The four the product owner saw on a dataset are two such pairs
(`fields`, `collections`, one source and one target each). They are 33 rules over
seven types, not four, so every type that ships one shows the same iconless rows.

A new kind cannot make them judgeable by editing the rules alone. It needs the
engine to carry the relationship type and the neighbour's type into the record it
checks, on both the draft path (validate-entity) and the stored path (14.6's
governance round), plus a way to author the kind in the rule editor. That is its
own increment, and these rules encode a metamodel guarantee the metamodel already
enforces — a field assignment joins a dataset to a field — so as a per-record
check they answer "yes" for every well-formed entity.

The `uniqueness` rule fails the same two ways for a third reason. Its dimension
(`uniqueness`) fits neither presence kind, so even a `dqcheckkind` on it raises
the dimension mismatch (GQ-02). And uniqueness is a statement about a set of
entities — one value appearing once across the type — while a governance verdict
answers over one record (DD-487). The store already gives the answer the rule
wants: an ACTIVE entity holds one reservation per unique attribute value, and a
write that needs a value another entity holds fails (ENS-05). A second `m4i_field`
cannot carry the qualified name of a first one, so the rule can only ever report
what the store refused at the write.

**Alternatives considered.**

A new `RELATIONSHIP_TYPE` check kind (refused as out of scope here: it is a new
engine capability, the engine carries no type data today, and the rules it would
serve are near-always true; open it as its own increment if the check ever earns
it). A new `VALUE_UNIQUE` check kind (refused for the same reason and a stronger
one: the check is not about the record the verdict answers over, and the store
already enforces the value's uniqueness at the write, ENS-05). Reword each to a
presence rule (refused: each collapses into a readable rule the corpus already
has — the dataset's `fields`/`collections` pairs — and loses the type intent, so
it adds a duplicate warning and still answers no type). Keep them iconless
(refused: 34 iconless rows across seven pages is what started this, and the owner
chose the clean box).

**Consequences.** The 14.6 read set and verdict balance do not move. The count
line `test__app_search_governance.py` pins (`28` read of `65`) counts rule
entities by their lifecycle state, not by the `active` attribute, and the 34
already read nothing and judged no verdict, so retiring them removes zero verdict
documents — unlike DV-173, which retired two rules that did judge 528 (DV-200
names the difference). The parity set is untouched: the frozen oracle judged none
of the 34, and the only legacy verdict documents any of them own are the 16 of
`3cb9ab0b-050c-40db-9f12-f136045a77a0`, which DV-160 already counts as the
missing-guid. The details box of the seven types loses its iconless rows and keeps
its green checks and amber warnings. The
`e2e/test__aurelius_atlas_webapp.py` scenario stops pinning the box's count,
because the count is the store's and this edit moves it (DD-223's rule, not
DD-844's).
