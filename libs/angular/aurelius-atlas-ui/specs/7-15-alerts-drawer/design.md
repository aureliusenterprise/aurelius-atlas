# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-175. AlertList and Badge are ui-lib presentational components

- **Status:** Accepted (the `clearAll()` half of the contract superseded by DD-176)
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The feed and the dot live in `aurelius-atlas-ui` as
presentational components (ALR-10): `AlertList` renders a
caller-supplied `AlertGroup[]` (the model the lib exports — the row's
shape is presentation vocabulary) and emits `dismiss(id)`/`clearAll()`;
`Badge` wraps content, shows a severity dot on `visible`. Labels are
inputs with English defaults (the `Drawer.ariaLabel` pattern), so the
lib keeps no translation dependency and the app passes `@@shell.alerts.*`
strings (ALR-08). The store, the window, and the routing stay app-side.

**Reason.** The user: "let's ensure we make a reusable ui component
for alerts." The feed has a second consumer by the plan's own logic
(7.6+ feature slices push alerts through the same store, and the
drawer is the product's surface); the dot generalises to any nav item.
The lib's rule is the same one `Drawer` keeps (DD-157): Bulma-shaped
presentational markup, state in the caller. The lib's chrome-strings
lane (DD-136: legacy dictionary paths) has no alert keys to reuse —
these are Aurelius's own strings (DV-66) — so the inputs carry
defaults and the app's catalogue owns the translations; the XLIFF
gate (SHL-08) and the purity gate (DD-137) stay app-side, the lib
stays service-free (its AGENTS.md convention).

**Alternatives.** App-local components under `src/app/alerts` (not
reusable — the user's ask). A smart `AlertsDrawer` in the lib that
injects a store (the lib owns no app state, no xlf dependency).
`model()` for the alerts array (the list never edits rows; dismiss is
an event, not a two-way value).

**Consequences.** The `AlertGroup` type is public API of the lib
(`src/index.ts`). The stories ship per UIC-15's bar (visual regression
covers the feed and the dot). The badge's ring is Bulma-token ink
(`--bulma-navbar-item-color`, currentColor fallback) — a future non-
navbar host keeps a visible edge without a new input.

### DD-176. The chip's pinned pair; Clear all in the drawer head

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** Two live-review fixes to the alert feed (ALR-06, ALR-07):
the burst chip's pair is pinned — `#f5f5f5` plate, `#363636` ink — not
Bulma's `tag is-light`; and the "Clear all" button is a content action
in the drawer's head, not part of the feed. The Drawer grows a
`drawer-actions` projection slot between the title and the close button
and AlertList loses its `clearLabel`/`clearAll` — clearing a store the
list does not own was the list's borrowed business (DD-175's
presentational rule).

**Reason.** The user's review of the live drawer: "the counter text is
not visible on the white background" and the "clear all" button
"will become buried" on a long feed — "let's keep it above the
notifications". The chip's invisibility is a scheme trap, measured: the
brand pins the `light` colour pair at `:root`, outside Bulma's scheme
machinery (SHM-04, so the chrome colours survive), while Bulma 1's dark
theme re-pins `light`'s invert to a scheme-following ink — the
`is-light` tag composed the brand's white plate under dark-mode white
ink (white-on-white). The pinned `#f5f5f5`/`#363636` pair is the
footer's idiom (SHM-07): the same marker in either scheme, 9.3:1. The
first fix placed Clear all above the rows inside the scrolling body
(DD-176's first pass, unit-tested); on review the head is the stronger
answer — the body scrolls, so the hatch must ride the sticky head.

**Alternatives.** Pin `light-invert` in the brand's `dark-ink` ramp
(fixes the tag and every `is-light` surface app-wide — rejected as
wider than the bug: DD-156's ramp re-pins the ink chain Bulma itself
adapts; `light` is a colour pair SHM-04 pins deliberately, and
dark-adapting it reopens SHM-01's promise). A severity-coloured chip
(the row is already severity-coloured; the chip is metadata, not a
second signal). Clear all above the rows inside the body (the first
pass: on a long feed the drawer body scrolls, taking the hatch away —
rejected on review). A `clearLabel`/`clearAll` on AlertList kept "for
reusability": a feed that owns a store-clearing button presumes the
store's shape — the head slot keeps the list the rows.

**Consequences.** The chip is the third pinned pair in the product
(footer SHM-07, active locale DD-170, chip DD-176) — the growing list
of surfaces that read the same in both schemes. The Drawer's head
anatomy (DD-157's, shared with settings) gains an optional slot: the
settings panel projects nothing and is unchanged. The alerts drawer's
tab order is close, then Clear all (both in the head), then the rows.

### DD-180. The inbox bar: severity chips, read tracking, Clear all in the bar

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The drawer head's Clear all grows into a full-width inbox
bar (ALR-11): a new ui-lib `AlertInbox`, a Bulma `buttons has-addons`
group of one chip per severity (`is-expanded`, feed order, an empty
severity's chip included), each chip a filter toggle showing that
severity's **total** group count, a dot riding the DD-152 ramp while any
of its groups is unread, and the caller's Clear all projected into the
bar's end. The Drawer grows a second projection slot, `drawer-subhead`,
a strip between the head and the body; the bar rides it. Read tracking
lands with it (ALR-12): every `AlertGroup` carries `read`; an arrival —
or a merge bumping a read burst — marks unread, and the panel's effect
marks every group read while the drawer is open (visible-is-read). The
bell badge answers unread presence in the highest **unread** severity's
colour, superseding ALR-02's store-top reading.

**Reason.** The user's ask: a bar showing the count per severity, each
severity a show/hide button, Clear all kept, "keep track of whether
notifications have been read", and the question of totals vs unread on
the chips. Totals won: the chips are filters, and a filter's number is
what it covers — unread counts on filter chips make the bar flicker
under reading (the chips zero out as the drawer reads the feed, the
turn the user is mid-reading through vanishes). Unread stays where the
attention question is asked: the bell dot, the row, the chip's dot.
Visible-is-read won over a per-row read toggle: the drawer is 28rem of
rows the user came to read; a list that requires marking each row read
is a queue, not a feed, and the merge-re-unreads rule means a returning
burst re-asks for attention on its own. Filter state is the panel's,
not the store's: the store's counts and the bell must answer with the
whole store, and a view filter is not data.

**Alternatives.** Chips showing unread counts (rejected above — the
number changes under the user's eyes as the drawer reads). Filter state
in the store (rejected: the bell's badge and the chips' totals must see
everything, and persistence of a view toggle is scope the in-memory
store does not have). A per-group read button (a queue; rejected).
`markAllRead` on close (rejected: the badge would stay lit while the
user is reading, and the ring/dot answers "has this been seen" — seen
means seen). Clear all staying in the head beside the bar (two fixed
strips stacked, the head's action orphaned from the bar it serves; the
bar is the feed's command strip — the hatch belongs at its end).

**Consequences.** The Drawer has two content slots, actions (head) and
subhead (the strip); the settings panel uses neither. The alerts
drawer's tab order is close, the three chips, Clear all, then the
rows. `AlertGroup.read` joins the lib's model — the third field the
store owns and the list renders (ALR-10's vocabulary grows). The bell
badge goes quiet on open, which is the point: it asked for attention
and got it. DD-176's Clear all in the head is superseded in placement
(its "above the notifications" requirement keeps holding — the bar
never scrolls, DD-181); DD-176's chip-pair pinning stands.

### DD-181. The drawer's body is the scroll container

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The Drawer's panel clips (`overflow: hidden`) and its
body scrolls (`min-height: 0`, `overflow-y: auto`): the head and the
`drawer-subhead` strip are fixed, the content scrolls under them
(DD-180's inbox bar, ALR-06/ALR-11's escape hatch).

**Reason.** Found while answering the user's question about a long
feed: the panel carried `overflow-y: auto`, so the whole drawer
scrolled — the head, title, close button, and DD-176's Clear all slid
away with the feed, and the "head does not scroll" clause ALR-06 cited
was not true. A drawer whose chrome scrolls away is a page, not a
drawer: the close control and the command strip must be reachable at
any scroll depth, and the inbox bar (DD-180) only pays off fixed.

**Alternatives.** A sticky head inside the scrolling panel (`position:
sticky`: works, but the scrim/panel geometry makes it fragile with the
slide animation, and the head's border composes over scrolled content
under the rounded corners). Two scroll containers (rejected: nested
scrolling on a 28rem panel is a trap).

**Consequences.** The settings panel's long body (six sections) now
scrolls under a fixed head — the intended drawer reading, and the
settings drawer's head carries its accessible name, so the panel
reading it never loses it. jsdom runs no layout, so the scroll split is
pinned by the spec's slot-placement test (DD-180) and the dev-server
check, not by a unit assertion.

### DD-182. The inbox bar is one joined group, severity-coloured, ramp order

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** Three follow-ups to the inbox bar (ALR-11, DD-180), from
the user's review: every segment of the bar — the three chips, show
all, and the projected Clear all — is an `is-expanded` member of the
one `buttons has-addons` group (the actions join the joined bar, not
beside it); the chip order flips to the ramp ascending — `info`,
`warning`, `error`, calm to urgent (SEVERITIES, the countSeverities
output, and the chips all follow); and a shown chip rides its
severity's fill — the DD-152 pinned ramp (`#17a2b8`/`#ffc107`/`#dc3545`)
with the ramp's own inks (black on warning and info, white on danger),
not a single Aurelius blue. The unread dot rides the chip's ink
(currentColor) with a hairline ring in the chip's plate, and the fill
rides `is-sev-*` classes, not Bulma's `is-info`/`is-warning`/`is-danger`
button colours.

**Reason.** The user's review of the live bar. The ramp order reads a
bar the way the feed reads a stack — the urgent end lands beside the
feed's own newest-first errors, and a bar whose colour intensifies
left-to-right says "here is the dial". The severity fills carry the
bar's own information: a chip IS a severity, and one blue bar made the
chips interchangeable — the colours are the legend. Bulma's own
`.button.is-info`-family fills are scheme-following token tints, and
the brand pins `light` outside Bulma's scheme machinery (SHM-04): the
pinned ramp is the product's severity vocabulary (DD-152, DD-168) and
reads the same in both schemes, like the badge's dot and the footer's
pair. The dot flips to ink for the same reason DD-176 pinned the
count chip: a ramp-coloured dot on a ramp-coloured chip rides its own
colour and vanishes.

**Alternatives.** Bulma's `.button.is-info`/`.is-warning`/`.is-danger`
fills (scheme-following: the tints shift with the theme and collide
with the brand's pinned plates — DD-176's trap, measured once on this
very bar). Severity text ink on a plain chip, fill reserved (the user
asked for coloured buttons; an outline bar reads disabled, not
filtered). Ramp descending (error first, DD-180's first pass — kept
for the feed's rows, newest/urgest-first; the bar is a dial, not a
feed). The actions outside the group, flush right (DD-180's first
pass: two visual systems on one strip — the user asked for one joined
bar).

**Consequences.** `SEVERITIES` is the inbox's order and the bar is the
model's only consumer of it; the feed's order is the store's own
(newest first), untouched. The clear-all button's contract is "an
expanded member of the group" — the panel's button and the host test
carry `is-expanded`. The unread dot loses its severity classes
(`is-*`): the chip's face is the severity, the dot only marks news.
The bar's tab order is info, warning, error, [show all], clear all.

### DD-183. The inbox bar is one height: the count badge is compacted

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** The inbox bar's count badge sheds Bulma's `.tag` height:
`height: auto`, `line-height: 1`, `0.125em` vertical padding — the
badge is compacted to the small button's scale, so every member of the
group (chips, show all, Clear all) computes to the plain small-button
height (ALR-11, DD-182).

**Reason.** The user's review of the live bar: Show all and Clear all
sat a step shorter than the severity chips. The cause was the badge,
not the actions: Bulma's `.tag` is a 2em control, and at the small
button's font that is 1.5rem of content inside a chip whose own line
is 1.125rem — the badge stretched its chip, and the group's flex
stretch dragged Show all and Clear all up to match. DD-182's
"is-expanded everywhere" made the step visible: joined segments
expose each other's heights.

**Alternatives.** `align-items: flex-start` on the group (leaves the
tall chips and short actions as they are, the join shows the gap). A
plain `<span>` instead of a Bulma `.tag` (the tag's plate/rounding is
the chip vocabulary, DD-176's pinned pair; the height is the only
part to shed). `is-normal` on the tag (the size modifiers are font
sizes, the `2em` height rides them all).

**Consequences.** The badge reads as the button's own metadata (a
superscript plate) rather than a control sharing the row. The unit
test pins the compaction's two properties; the equal height across
segments is the group's stretch, verified on the dev server.

### DD-184. The void chip: an empty severity greys out

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** An inbox chip whose severity the feed holds no alerts of
is disabled (ALR-11): greyed by Bulma's disabled-button rule (the
scheme-main plate, 0.5 opacity), unpressed, and carrying no severity
fill. A chip with rows keeps DD-182's fills; a filtered-out chip keeps
DD-180's plain-button reading. The three states read: severity-coloured
= showing, plain = hidden by the user, grey = nothing to show.

**Reason.** The user's review: "grey out the buttons that have no
alerts". DD-182 made every chip severity-coloured, so a severity with
zero alerts kept its full-colour face — the bar shouted three
severities for a feed with one. The states now map to the chip's
truth: the fill answers "this severity is on the screen", plain answers
"you filtered it", grey answers "there is nothing of this". A disabled
chip is also inert, which is honest: toggling a filter with nothing to
filter changes nothing, and a chip whose click is a no-op should not
look clickable (the pointer cursor promises a state change).

**Alternatives.** Keep it clickable, greyed by class only (a click
that does nothing — the affordance lies). Hide the empty chips (DD-180
chose a fixed three-chip bar — the shape is the legend; hiding makes
the bar reshuffle as the feed churns). Strike the zero, keep the
colour (a coloured zero still reads "on").

**Consequences.** The `is-selected` fill gate moves from
"not hidden" to "has alerts and not shown hidden" — the `isOn`/`isVoid`
pair on the component. `allHidden` (DD-180) was already void-aware: an
empty severity's chip does not keep the show-all control away, and its
disabled chip cannot be clicked off, so the control cannot strand a
void-only bar. The panel hides the whole bar on an empty store, so the
all-void state shows only in isolation (the Empty story).

### DD-185. Show all is gone: the bar's shape never shifts

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** The inbox bar has no show-all control (ALR-11). The
`showAllLabel` input, the `showAll` output, the `allHidden` computed,
the conditional button, and the panel's `showAll()`/`showAllLabel` are
removed; the way back from a fully-filtered feed is a chip — a hidden
chip stays enabled (only a void chip is disabled, DD-184), and
clicking it shows its severity again. DD-182's "actions as group
members" stands for the projected clear-all; it no longer covers
show-all.

**Reason.** The user's review: appearing at full filtering, the control
joined the `buttons has-addons` group as a fourth `is-expanded`
segment — the three chips each jumped from a third to a quarter of the
row, every toggle into and out of the fully-hidden state. A bar whose
segments resize on state change reads as broken furniture; the escape
hatch was worth less than the jump. It was also redundant: the chips
were always clickable in that state (the hiding is per-severity and
independent), so show-all only ever did what three clicks — usually
one — already did.

**Alternatives.** A fixed-width reserved slot (a gap in the bar,
always sized for a button that is almost never there). Absolute
positioning outside the group (a floating control breaking the joined
bar, DD-182's shape). Auto-restoring the filter when the feed empties
(filtering to nothing is a legitimate state — the counts stay, the
user chose it; silently undoing it is worse than no control).

**Consequences.** The bar's segment count is constant while it shows
(chips + projected action), so the joined strip never reflows. The
fully-filtered state shows the feed's empty line under all-flat chips
— self-explanatory, and the counts on the chips say what is hidden.
The `shell.alerts.showAll` string leaves both fixture locales and both
catalogues (25 shell.alerts entries → 24). The AllHidden story and the
two bar tests carry the new contract: no control, three expanded
segments, a hidden chip toggles back on.
