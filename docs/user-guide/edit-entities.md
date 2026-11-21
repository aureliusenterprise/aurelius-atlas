# Edit Entities

Create and edit catalogue entities in the webapp, and see whether each one meets your governance rules while you
type. This page needs a user with the `atlas` or `steward` role in its tenant: only they see the pencil and the
`+`.

## Open the editor

- To create an entity, select **+** next to the search box. The **Create new entity** page opens.
- To edit an entity, open it and select the pencil next to its title. The **Edit entity** page opens.

The editor is one page, `search/editor`. When it edits an entity, its address names the entity
(`search/editor?guid=<guid>`), so you can bookmark or share it.

## Choose the type

When you create an entity, choose its type first. The types with a form of their own come first in the list:
data entity, data attribute, dataset, field, collection, data domain, system, process, person and governance
rule. Choosing another type clears the form.

## Fill in the form

Each of those types shows only the fields that matter for it, in a fixed order. A data entity, for example,
shows its name, definition, classifications, data domain, parent entity, child entities, data attributes, data
owners and data stewards. Every other type shows all its attributes.

- **Name** is required on every form, **email** on a person, and **expression** on a governance rule.
- A data entity has one parent: a data domain or a parent entity. While one holds a choice, the other is
  disabled. The same holds for a field (dataset or parent field) and a dataset (collection or parent dataset).
- A name or definition that holds the typographic apostrophe `’` gets a warning under it. Replace it with `'`
  if the text is going to be imported elsewhere; you can still save.

## Check the governance rules while you type

Next to each field, the editor lists the result of every governance rule on that field: a green check when the
rule is met, a yellow warning when it is not. The results refresh shortly after you stop typing, and the
definition turns yellow while one of its rules fails. The rules are your tenant's own `m4i_gov_data_quality`
entities, so a change to a rule shows here at the next minute.

A failing rule doesn't stop you saving. A missing required field does: the field turns red, and a notice
next to **Save** says what is missing.

## Save, cancel or delete

- **Save** stores the entity and opens its details.
- **Cancel** discards your changes and returns to the entity's details, or to the search when you were creating
  one.
- **Delete**, on an existing entity, needs to be held for three seconds, and is shown only to users who may
  delete.

## See the history

When you edit an entity, the **History** tab next to **Entity** lists every change to it, newest first: what
happened, who did it, and when.
