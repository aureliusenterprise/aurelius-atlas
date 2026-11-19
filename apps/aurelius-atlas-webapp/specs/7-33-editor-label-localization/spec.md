# 7.33 The editor's field labels are all localized

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-722, DD-723, DD-724 (here); DD-356 (the star, kept); amends
  EDT-03 (7-7a) and EDT-13 (7-7c, incl. its DD-379 bracket clause) in place;
  relies on SHL-08 (the dictionary bridge), DD-341, and DV-181 (the dictionary typos)

## Scope

Every label the entity editor shows for a field. Today a field's label is the
attribute's typedef `displayName`, or its raw camelCase name when the typedef
carries none. The shipped metamodel leaves many labels raw: `processOwner`,
`source`, `hasPII`, `isKeyData`, and every relationship name (`inputToProcesses
(Process)`). The base model names no attribute at all, and the vendored Area0
file cannot be edited. This increment makes the catalogue the first label
source for every attribute the editor can render, in both locales.

Delivered here:

- the editor passes one localized string per attribute to both field builders
  (EDT-33): the Aurelius dictionary key
  `search.components.editor.attribute.<name>` in `en-US` and `nl-NL`
- the relationship pickers share the same map (EDT-34): the catalogue string,
  then the `displayName`, then the name — the same precedence EDT-03 states
- 124 new catalogue keys in both catalogues, the fixtures, and the `$localize`
  bridge, so the completeness spec and the extractor both prove them
- the dictionary's two legacy typos fixed at the source (DV-181):
  `compliantMessage` ("Complaint Message") and `nonCompliantMessage`
  ("Non-complaint Message"), in the m4i dictionary and the three sample bundles

Not delivered here:

| Deferred                                  | Lands with | Why                                                                                    |
| ----------------------------------------- | ---------- | -------------------------------------------------------------------------------------- |
| Labels for a type an admin installs later | —          | A name with no catalogue key keeps today's behaviour: displayName, else name (DD-723)  |
| The details screens' labels               | —          | They already ride catalogue keys per section (DET-04); this is the editor's field form |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                             |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDT-33 | A plain field's label is the catalogue string `search.components.editor.attribute.<name>` where one exists, else the attribute's `displayName`, else its name (EDT-03 as amended here). Every attribute the shipped metamodel renders has a catalogue string, in both locales.   |
| EDT-34 | A relationship picker's label is the same catalogue string, else the `displayName`, else the name — with no `(Target Type)` bracket (DD-724): the chips already lead with the type (DD-341). The pickers share the editor's label map, and EDT-13's bracket clause is withdrawn. |

## Java origin

The legacy dashboard resolves every editor field label through its catalogue
(`search.components.editor.attribute.*` in its own `en-US.json`/`nl-NL.json`
files) before the typedef `displayName`, per type in its `editors-by-type`
components. Aurelius serves one def-driven form (DD-323) and carried only
`name`, `definition`, `classifications` and `typeAlias` from those keys; the
rest fell through to `displayName` or the raw name.

## Deviations

| Id     | Deviation                                                                      |
| ------ | ------------------------------------------------------------------------------ |
| DV-181 | The m4i dictionary's two legacy typo displayNames are corrected at the source. |

## Acceptance

Run with `npx nx test aurelius-atlas-webapp -c ci`.

- `i18n-completeness.spec.ts` (SHL-08): every new key present in both
  catalogues with the Aurelius text, no extras.
- `attribute-labels.spec.ts` (EDT-33): the map names only catalogue keys, its
  fallbacks match the English fixture, and the names the typedefs never
  humanize carry readable strings; the two typo keys carry the fixed text.
- `form-fields.spec.ts` (EDT-34): a relationship field labels from the catalogue
  string alone, with no target-type bracket (DD-724).
- `entity-editor.component.spec.ts` (EDT-33/EDT-34): a raw `displayName` loses
  to the catalogue string, a picker labels from the map and carries no bracket.
- `test__aurelius_atlas_webapp.py`: an ad-hoc type's relationship label stays the
  raw name and carries no bracket (EDT-33's last fallback, DD-724).
