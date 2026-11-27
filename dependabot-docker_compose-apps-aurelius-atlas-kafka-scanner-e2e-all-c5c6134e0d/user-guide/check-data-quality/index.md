# Check data quality

This page covers the trust question: can you believe a record, and what makes it stronger or weaker. It shows the score you see on a record, the reasons behind it, and the two different rule screens. The examples run on the imported sample catalogue, signed in as `demo_scientist`.

## The five dimensions

A quality score is never one number for everything. It splits into five dimensions, and every screen uses the same five words in the same order:

| Dimension | The question it answers |
| --- | --- |
| Accuracy | Do the values look right? |
| Completeness | Are the values present? |
| Timeliness | Are the values fresh enough? |
| Uniqueness | Do the values repeat too often? |
| Validity | Do the values follow the form? |

The webapp also keeps a sixth entry, **Overall**, which pools every measurement of the five into one figure, weighing each rule equally. The Overall figure is the score shown in a record's stats bar. The five dimensions are the rows under it.

## The score on a record

Seven kinds of record page carry a **Data Quality** box and one score in their stats bar: a dataset, a field, an attribute, a data entity, a domain, a collection, or a system. The score in the stats bar is the Overall figure. The box lists one row per measured dimension.

A row reads like `81.4% Accuracy (1)`: the score, the dimension, and how many rules were measured for it in brackets. The sample field `HIER_ORGANIZATION` shows two rows, `81.4% Accuracy (1)` and `100% Completeness (1)`, and its stats bar reads `90.7%`.

> [!NOTE]
>
> **No score is not a bad score**
>
> A record the governance worker never scored shows no rows, and its stats bar reads **Unavailable** instead of `0%`. That is the honest answer. A zero would claim a measurement that never happened.

## Why one record sits lower than another

A lower score comes from one dimension, not from everything. Open the record's **Data Quality** box and read across the rows. A dimension with a low figure is where the record is weakest, and the rule behind it names the reason.

A dimension you do not see at all is not a failure. The box prints a row only when at least one rule measured that dimension. If a record has no Timeliness row, no rule measured its timeliness. The record is not failing timeliness. Nothing looked at it.

## The rules behind a score

On a field page, the **Data Quality Rules** box holds one card per rule attached to the field. Each card carries the rule's own score row, such as `81.4% accuracy`, so you can see which rule pulled a dimension down.

A card always appears when a rule is attached to the field. A rule that the worker never scored keeps its card and prints no score row. The card is the promise that the rule exists. The score row only appears when a measurement exists.

On the sample field `HIER_ORGANIZATION` the box holds three cards. Two carry a score row, and the third, an inactive rule, shows none. That third card is the expected case, not a missing number.

## Two kinds of rule, two kinds of page

The catalogue holds two kinds of quality rule, and they read on different pages. Do not look for one on the other's screen.

A **scored rule** (type **Data Quality**) measures a whole set of rows and answers with a score from 0 to 1. It shows a score row wherever it is attached. You reach it from a field's **Data Quality Rules** box.

A **governance rule** (type **Governance Data Quality**) judges one record and answers yes or no, with no score. Its own page is where the compliance material lives.

## A governance rule's page

Open a governance rule and its page shows three parts:

- A **Compliance Chart**, a simple pie of compliant against non-compliant records, with the legend words **Non-compliant** and **Compliant**.
- A **Non-compliant** box, one card per record the rule refused.
- A **Compliant** box, one card per record the rule passed.

This is the screen to open when a record is refused and you want to know how many others share the problem. The scored rule has no such chart, because it measures a set instead of judging one record.

## The verdict lines while you edit

When a person with the write right opens the editor, a line can appear under a field or a relationship picker. A green check means a governance rule passed for that field. A warning triangle means it was refused. The line states the rule's own verdict text.

These lines advise. They do not block the save for an ordinary record. A person can still save over a warning, because the verdict is the reader's to weigh, not a wall.

One verdict can appear under two different fields at once. This is not a mistake and not one sentence about two fields. Some governance rules accept more than one field that can satisfy them, so the same verdict is painted under each field the rule names. The rule below passes if either of its two fields is filled, so both fields carry the same line:

```
length('fields', 1) | length('childDataset', 1)
```

## Try it on the sample

The sample field `HIER_ORGANIZATION` is a clean walk-through of every case:

1. Sign in as `demo_scientist` and search for `NL1-HR-001`. Open it. Its **Data Quality** box scores Accuracy and Completeness, and its stats bar reads `98.2%`.
2. Open the **Fields** box and choose `HIER_ORGANIZATION`. Its **Data Quality** box shows `81.4% Accuracy (1)` and `100% Completeness (1)`, with no Timeliness, Uniqueness, or Validity row, because nothing measured those.
3. Read the **Data Quality Rules** box. Three cards appear. Two carry a score row. The third carries none, which is the unscored rule.
4. Its stats bar reads `90.7%`, the pooled figure across the two measurements.

The screen below holds both boxes: the two scored dimensions, and the three rule cards, one of which scores nothing.

![The Data Quality and Data Quality Rules boxes of HIER\_ORGANIZATION.](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/assets/user-guide/data-quality-box.png>)

The next step, to change a rule or write a new one, is [Write quality rules](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/user-guide/write-quality-rules/index.md>). To change a record itself, see [Change data](<https://aureliusenterprise.github.io/dependabot-docker_compose-apps-aurelius-atlas-kafka-scanner-e2e-all-c5c6134e0d/user-guide/change-data/index.md>).
