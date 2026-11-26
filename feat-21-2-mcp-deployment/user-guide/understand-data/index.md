# Understand data

One record's page answers three things: what the record is, what relates to it, and who answers for it. Every record type uses the same shape, so a page you learn once works everywhere. The examples run on the imported sample catalogue, signed in as `demo_scientist`.

## What the page is made of

From the top:

| Part | What it holds |
| --- | --- |
| Header | The name, the type badge, the classification chips, and the breadcrumb |
| Description box | The record's description text, or "No description available." |
| People box | The named people, on the three types that carry them (see below) |
| Stats bar | A count for each section, which scrolls you to it |
| Card sections | One box per related group, each a grid of cards |
| Properties table | Two columns, Key and Value, of everything else the record stores |

The pencil at the top right opens the editor. It appears only for a person who can write, and [Change data](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/user-guide/change-data/index.md>) covers what it lets you do.

The dataset page below shows each part: the header, the Description box, and the stats bar with the record's counts.

![The page of the sample dataset NL1-HR-001.](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/assets/user-guide/entity-details.png>)

## The header

The header states what the record is. The name is the record's name, or its qualified name when it has none. Below it sits the type badge: an icon and a friendly type name such as **Dataset**, **Data Field**, or **Person**.

A badge can show an alias instead of the type name, when the record carries one. A record of the **System** type stored with the alias `Kafka Topic` shows a badge that reads **Kafka Topic**, and the header adds the friendly type in brackets, so it reads `Kafka Topic (System)`. The alias is stored on the record, not chosen by the screen. The sample catalogue stores no aliases, so its badges show plain type names.

Classification chips sit under the badge. Your own classifications and the ones propagated to the record share one row. A propagated chip carries a marker. Open it and the marker lists the source records under "originates from the following sources:", each a link. Click one to open the record the chip came from.

The breadcrumb shows the record's place in the hierarchy. It appears only for a record with a stored parent. A parentless record, which most datasets are, draws no trail at all, and that is normal.

## The sections

A **layout** decides which sections a type shows and in what order. Eleven types have their own layout, and an unknown type gets the plain shape: description and properties.

The dataset page shows **Fields**, **Child Datasets**, the **Lineage Model** box, **Producers**, **Consumers**, a **Data Quality** score box, **Governance Quality Rules**, and **Properties**. A field page shows **Data Attributes**, **Child Fields**, a **Data Quality** score box, **Data Quality Rules**, **Governance Quality Rules**, and **Properties**. Each box is searchable and filterable in the same way the results screen is, and each counts up in the stats bar above it.

Follow any card to leave this page for the record it names. That is the normal way to walk a catalogue: dataset to field, field to rule, record to person.

## The people

A record names the people who answer for it. Only three types carry the People box: **Data Domain**, **Data Entity**, and **Data Attribute**. Their rows are **Domain Lead(s)**, **Data Owner(s)**, and **Data Steward(s)**, and each name links to that person's own page. A dataset page holds no People box, which is why `NL1-HR-001` shows none.

Open a person's page and the picture inverts. A person shows one box, **Governance Responsibilities**, which merges everything they lead or own across five kinds of responsibility: as a domain lead, as the owner of an entity, as the owner of an attribute, as the steward of an entity, and as the steward of an attribute. Its stats bar groups the same material under **Domain Lead**, **Data Owner**, **Data Steward**, and **Other**.

To find who owns a subject, search for the domain, open it, and read the **Domain Lead(s)** row. Then open that person to see everything else they answer for.

## History

The page itself has no history view. The pencil opens the editor, and the editor has a **History** tab next to the **Entity** tab. It lists every change: what happened, by whom, and when, with words such as **Entity created**, **Classification added**, or **Entity updated by import**.

A line for a changed attribute carries a **Restore** button, which writes that one attribute back to its earlier value. Restore needs the write permission, and it restores one attribute at a time, not the whole record.

## The navigation control

A round button at the foot of the screen opens a menu of the page's sections, in page order. It lets you jump to **Properties** or **Data Quality** on a long page. The address bar records the jump, so the browser's Back button walks your jumps.

## Try it on the sample

1. Search for `NL1-HR-001` and open it. The header shows the name and the **Dataset** badge. No breadcrumb appears, because the dataset has no stored parent.
2. Open the **Fields** box and choose `HIER_ORGANIZATION`. The field page shows its own sections, and its **Data Quality Rules** box holds the rules scored against that field.
3. Search for `Finance` and open the domain. It carries the People box, and its **Domain Lead(s)** row names a person.
4. Open that person. The **Governance Responsibilities** box lists everything they lead or own.

Next, decide whether you can trust what you just read, in [Check data quality](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/user-guide/check-data-quality/index.md>), or see what a change affects, in [Follow lineage](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/user-guide/follow-lineage/index.md>).
