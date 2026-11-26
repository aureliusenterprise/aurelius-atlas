# Change data

This page covers the five things you can do to a record: create it, edit it, tag it, relate it, and delete it. Every one of them is a change, so every one of them is checked — by your rights first, and by the server when the change lands. To read a record instead, see [Understand data](<https://aureliusenterprise.github.io/feat-webapp-versioned-docs-link/user-guide/understand-data/index.md>). The examples run on the imported sample catalogue, signed in as `demo_steward`.

## Who can change data

Your rights decide what you see. Two matter here:

| Your rights | What you can do |
| --- | --- |
| Read | Read everything. No change controls appear at all. |
| Write | Create, edit, tag, relate and delete records. |

With read rights only, the plus button and the pencil button are absent, and a record's foot has no **Save** and no **Delete**. The screens are otherwise the same. Two further rights exist, for type definitions and for the whole catalogue, but the webapp has no screens for them yet.

## Create a record

1. Click the plus button, **Create new entity**.
2. Choose an **Entity type**. The picker lists only types the webapp has screens for.
3. Fill the form. The **Name** field carries a red star and is the one required value.
4. Click **Save**.

The new record's address is decided for it, so you never type one. After a save the page opens on the record itself, and the record appears in search and in the browse tree.

The drawer below sits open on step 2, waiting for an entity type.

![The Create new entity drawer.](<https://aureliusenterprise.github.io/feat-webapp-versioned-docs-link/assets/user-guide/create-entity.png>)

## Edit a record

Open the record and click the pencil, **Edit entity**. The form opens over the page you were reading, so the record stays in view behind it. Change the values and click **Save**. The button says **Saving the entity** while it works, then **Entity saved**. Cancel discards your edits.

Some values you cannot set by typing them. Where a value names another record, a picker lists records of the allowed types instead of a box for text, so you cannot point at a record that does not exist.

## Tag a record

Under **Classifications**, type to filter the list and pick a tag to add it. To remove one, click the small cross on its chip. The catalogue holds five tags today: **Has PII**, **Is key**, **High risk**, **Medium risk**, and **Low risk**. With none set, the row reads **No classifications available**.

A tag can travel. Some tags are set to carry down the records attached to the one you tagged, so a column inherits a tag put on its table. You can tell an inherited tag from one set here: hover it and a note names where it came from. An inherited tag is not yours to remove here — remove it from the record it came from.

> [!WARNING]
>
> **Tags are not business terms**
>
> A tag marks a record. It does not link a record to a business definition. The catalogue holds business terms, and a record can carry them, but the webapp has no screen for that link yet. A save never touches the terms already set on a record.

## Relate records

Use **Add a relationship...** to choose a relationship, then a picker to choose the record on the other end. To break one, click the small cross on it.

The webapp stops you from making the shapes the catalogue refuses. Where a relationship can hold only one record, a record already in that slot dims the others. Where two parent relationships exclude each other, choosing one dims the types of the other:

- A data entity sits under a data domain or a parent data entity.
- A field sits under a dataset or a parent field.
- A dataset sits under a collection or a parent dataset.

> [!NOTE]
>
> **The parent rules are newer than the sample**
>
> The sample catalogue was imported before these three rules were enforced. It holds a few older records that break them. A new save that would add another one is refused.

## Read the history

The record's page has no history. Click the pencil to open the editor and switch its tabs to **History**. It lists every change to the record, newest first, with who made it and when: when the record was created, when an attribute changed, when a tag arrived or was removed.

The list below is the History tab of the sample dataset. An entry that changed stored values carries a **Changes** button.

![The History tab of the entity editor.](<https://aureliusenterprise.github.io/feat-webapp-versioned-docs-link/assets/user-guide/history-tab.png>)

Each entry names what changed. Turn on **Changes** to expand the entries into tables of before and after. Sort the tables by clicking a column heading. Where a long piece of text changed, the entry shows the words that left out rather than the whole paragraph.

## Restore a value

Alongside a changed text, number, or yes-or-no value, there is a **Restore** button. It puts the previous value back as a new change; it does not roll the record back. The history keeps both the change and the restore, so you can see what happened.

Restore covers single values. It will not undo a relationship or a tag, and not every old value can be put back — if the value has since become invalid, the save is refused like any other.

## When a save is refused

A save can fail. Each refusal tells you what to do:

| Refusal | What you see |
| --- | --- |
| Someone else saved | A note: **This entity changed since you opened it. Your edits are kept — save again to write them over the stored version.** |
| The name is taken | A notice: **That name is already held by another entity.** |
| A parent is refused | A notice naming the record and the rule it breaks. |
| Something else | A notice: **Saving the entity**. The form stays open with your edits. |

A refusal never saves part of a change. The record is either written whole or not at all, so you can correct the form and try again.

## Delete a record

Click the record to open it, click the pencil, **Edit entity**, then hold the **Delete** button in the foot for three seconds. The hold is deliberate: releasing early cancels. When it completes, the record is deleted and you land back on the browse screen. The record leaves the catalogue; it is not moved to a bin.

> [!WARNING]
>
> **Deleting does not tidy up around the record**
>
> Deleting a record takes it out of the catalogue, but the records around it keep their links to what used to be there. Check the record's lineage and the rules that measure it first, and consider editing the record instead. The record's history stays after a delete.

## Try it on the sample

1. Sign in as `demo_steward` and click the plus button.
2. Choose the type **Dataset** and name the record something you will recognise, then **Save**.
3. Pick **Is key** from the tag list, and relate it to a collection from the sample.
4. Open the record with the pencil and switch to **History**; turn on **Changes**.
5. Edit a value, then **Restore** it from the history.
6. Delete the record to clean up: pencil, then hold **Delete** for three seconds.

Running the import script again brings the catalogue back whole, so nothing you do here can break the sample.
