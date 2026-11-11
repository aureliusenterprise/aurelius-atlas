# 11.5b The search mode in the settings, no Similar entities box

- **Status:** done
- **Pull request:** [#316](https://github.com/aureliusenterprise/aurelius-atlas/pull/316)
- **Records:** DD-473 and DD-474, superseding DD-478 and DD-480; amends 11.5 (SBW-02, SBW-05, SBW-06,
  SBW-07); relies on 7.10 (the settings panel, SPL-08 to SPL-13, DD-160)

A correction of 11.5. Users choose between Words, Meaning and Both in the settings panel, once, instead of
in a switch under the search field; the choice is stored as the page size is. The Similar entities box
leaves the details page. The searches by meaning, their paging and their errors stay as 11.5 made them.

## Scope

- the settings panel: a Search by section with Words, Meaning and Both;
- `SearchModeService`, the mode's stored owner, and the facade's `searchMode` and `setSearchMode`;
- the results store: reads the stored mode, and searches again when it changes;
- the search hero: the switch is removed;
- the details page: the Similar entities box and its four labels are removed;
- the header's gear and bell, and the settings and alerts panels' close: they keep the URL's query.

Not in scope: the endpoints of 11.4 and `SearchByMeaningService`, whose `similar` stays for a later screen.

## Semantics

| Id     | Rule                                                                                                                                                                                                        |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SBX-01 | The settings panel shows, after Language, a Search by section of three buttons: Words, the default, Meaning and Both, the stored one pressed. The choice is stored in the browser; a corrupt store is Words |
| SBX-02 | A new mode, chosen while a query is shown, restarts its search at the first page, the type selection kept; without a query it searches nothing; choosing the mode already stored is no change               |
| SBX-03 | The search hero has no mode switch, and the details page no Similar entities box                                                                                                                            |
| SBX-04 | Opening or closing the settings or the alerts drawer keeps the URL's query, so the search behind the drawer stays                                                                                           |

SBW-02 and SBW-07 of 11.5 are replaced by these rules. SBW-05 is SBX-02's case of a shown query. SBW-06's
fallback to Words now stores Words, so the panel shows it.

## Aurelius origin

None, as for 11.5 (ADR 059). The section is a Bulma `buttons has-addons` group, as 11.5's switch was.

## Deviations

None against Apache Atlas.

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/settings/search-mode.service.spec.ts`: SBX-01, SBX-02.
- `apps/aurelius-atlas-webapp/src/app/settings/settings-panel.component.spec.ts` and `settings.service.spec.ts`:
  SBX-01.
- `apps/aurelius-atlas-webapp/src/app/search/search-state.spec.ts`: SBX-02, and SBW-03 to SBW-06 unchanged.
- `apps/aurelius-atlas-webapp/src/app/search/search-layout.component.spec.ts` and
  `details/details.component.spec.ts`, back to their state before 11.5: SBX-03.
- `apps/aurelius-atlas-webapp/src/app/shell/header.component.spec.ts`, `settings-panel.component.spec.ts` and
  `alerts/alerts-panel.component.spec.ts`: SBX-04.
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts`: the four Similar entities keys leave both
  dictionaries and both catalogues.
- By hand, on the standalone stack: Meaning chosen in the panel searches the shown query by meaning, which
  stays when the panel closes; no box on a details page.
