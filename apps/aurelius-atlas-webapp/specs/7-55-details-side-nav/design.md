# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-882. The side navigation is one presentational component; the layout read stays in the screen

- **Status:** Proposed
- **Increment:** 7.55
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The side navigation (DET-25): the 7.16 sticky drop-up holding the
opened layout's anchors moves into one component, `DetailsSideNav`, in the
details feature. It takes two signal inputs — the layout's `NavDef` entries and
a `hasLayout` boolean — owns the shell's menu label and the `.aurelius-details-nav`
class as template constants, re-emits nothing, and paints nothing else. It holds
no `output`: the items are plain `routerLink` anchors, so there is no click to
relay. The screen keeps `layout()` (which resolves the type's row: the boxes, the
stats, and the nav set, DET-25) and its own scroll effect (DD-191). The
`DetailsNavigation` and `RouterLink` imports ride with the markup, which was
their only use on the screen. The part takes no stylesheet — the ui shell
carries the sticky drop-up and Bulma's `menu-list` carries the items — so the
child needs none, like the chips row (7.53) and the properties box (7.54).

**Why.** The navigation is the same clean leaf 7.50–7.54 set with the narrowest
contract yet: two inputs, zero outputs, no store, and no custom SCSS. The label
and the `.aurelius-details-nav` class are template constants, not inputs, for the
same reason 7.54 made the anchor and expanded default constants — no caller of
this screen changes them, so an input would be a knob nobody turns and a way to
silently drift the class the e2e selects. The one judgement call is the
`hasLayout` boolean instead of passing `layout()` itself: the part cannot ask
whether a layout was named from an empty entries list, because a named layout is
allowed to have entries and an unnamed one has the default's one entry, and the
two shapes mean different things (DET-02). Passing the boolean is the narrowest
fact that names that difference, and it is the exact read the screen already
makes for the card sections and the stats bar (7.52's `hasLayout`, same idiom).
Handing the whole `TypeLayout` to a painter would give it the sections, the
stats, and the fetch seeds it must not read (DET-05/DET-06).

**Alternatives considered.** _Pass `layout()` and let the part branch._ That
hands a painter a type layout: the sections, the stats, the seed keys, and the
`lineageAfter` anchor — everything the navigation must not know, and the widest
input any leaf here has taken (DD-880's wide-trap lesson, 7.49's narrowing).
_Keep the `<li>` items in the screen and project them._ The shell's contract is
that the caller owns the `ul.menu-list` (UIC-18), so the parent could project and
the child just mount the shell — but that leaves the loop, the branch, and the
default entry in the screen, which is the markup this increment set out to move;
the child would then be a one-line wrapper that buys nothing. _Move the scroll
effect too._ DD-191 places the scroll behaviour app-side and DET-06 places the
router with the screen; the part would then need the router, which every leaf
here keeps out.
