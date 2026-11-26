# Write quality rules

A quality rule is data you author, not a setting. You write one here and read its result on the quality screens. This page holds the shape of a rule and the fixed list of checks behind it. For what a score means once the rule runs, see [Check data quality](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/user-guide/check-data-quality/index.md>). The examples run on the imported sample catalogue, signed in as `demo_steward`, who can write.

## A rule is data

A rule stores a small set of values. The editor collects them:

| Value | What it is |
| --- | --- |
| Name | The rule's own name. Required. |
| Rule description | A sentence about what the rule checks. |
| Check kind | The one check the rule performs, from the fixed list below. |
| Dimension | The dimension the check belongs to. You do not set it; the kind fixes it. |
| Parameters | The few values the chosen kind needs, such as a column or a pattern. |
| Threshold | The score the rule must reach to pass, a share from 0 to 1. |
| Active | A switch. Off retires the rule without deleting it. |
| Fields | The records the rule measures, chosen in a picker. |

The dimension line is read-only on purpose. Each kind belongs to exactly one dimension, so picking the kind picks the dimension for you.

## Where the editor is

There is no separate rules screen. The editor is a special form inside the same drawer you use to create any record. You open it two ways:

1. **Create a rule.** Click the plus button, **Create new entity**, and choose **Data Quality** in the type picker. The drawer opens with the rule form.
2. **Edit a rule.** Open the rule's own page and click the pencil, **Edit entity**. The drawer opens with the same form.

The drawer title reads **Create new entity** or **Edit entity**, and the foot button reads **Save**.

## The ten check kinds

The webapp offers ten kinds, grouped by the dimension each belongs to. Pick a kind and the form shows only the parameters that kind uses.

| Kind | Dimension | What it checks | Parameters |
| --- | --- | --- | --- |
| Not empty | Completeness | One column carries a value in at least a share | Column |
| Row filled | Completeness | Every row holds all of the chosen columns | Columns, at least N |
| No duplicates | Uniqueness | One column's values repeat no more than a share | Column |
| Composite unique | Uniqueness | The chosen columns together never repeat | Columns |
| Matches a pattern | Validity | Every value follows a text pattern | Column, Pattern |
| Values from a set | Validity | Every value comes from a list you set | Column, Values |
| Convertible type | Validity | Every value converts to a type you set | Column, Type |
| Columns match | Accuracy | Two columns hold the same value in a set share | Column, Other column |
| Within a range | Accuracy | Every value sits between a minimum and maximum | Column, Min, Max |
| Fresh rows | Timeliness | Rows were written no longer ago than an age | Column, Max age |

Each kind also has a threshold, which is the share that lets the rule pass. The threshold field takes a percentage. Typing a number outside 0 to 100 snaps it to the nearer end.

## Author a rule

1. Open the rule form, as above.
2. Give it a name and a description.
3. Pick a check kind. The form clears any parameters from a previous kind and shows only this kind's own.
4. Fill the parameters that kind asks for.
5. Set the threshold.
6. Choose the fields the rule measures, in the **Fields** picker.
7. Click **Save**.

A threshold and a verdict are not the same thing. The threshold is the bar this scored rule must clear when it measures a set of rows. A verdict is a yes or no about one record, made by the other kind of rule (governance rules, below), and it has no threshold.

## The save is checked on the server

A rule never saves unchecked. On **Save**, the webapp sends the rule to the server's own checker first. Only a rule the server can read proceeds. If the shape is wrong, the checker answers with a reason, the drawer stays open, and your edits are kept. The reason names what is wrong, for example a missing parameter or a threshold outside the range.

The webapp catches the obvious cases before it even asks the server. With no name, the field shows **Name is required.** With a missing parameter, a notice reads **This entity can't be saved because one or more required fields are missing.**

## Two governance kinds you can read but not edit

The catalogue also holds two governance kinds, **Attribute present** and **Attribute not empty**, which judge one record and answer yes or no. Each accepts an extra **Any Of** value, which lets a second attribute satisfy the check. That pair stands in for an OR: the rule passes if either attribute is there.

The rule form above does not edit these two kinds today. You can read a governance rule on its page, in [Check data quality](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/user-guide/check-data-quality/index.md>), but you cannot author one in the webapp yet. An operator can import them.

## Retire a rule by switching it off

To stand a rule down, clear its **Active** switch. The rule stops being scored, disappears from verdicts and rule lists, and keeps its score history and its link to the fields. Switch it back on to bring it back.

The drawer also carries a **Delete** for every record, including a rule: a danger button you hold for three seconds. Reach for **Active** off first, because it keeps the history and is easy to undo. Use **Delete** only when the rule should not exist at all.

> [!WARNING]
>
> **The sample rules cannot demo this form**
>
> The sample catalogue's 50 quality rules come from an older system and store their check as a free-text expression, not as one of the ten kinds. None of them opens in the rule form; they open in the plain attribute form instead. So there is no sample rule to inspect here. Author a fresh rule as `demo_steward` to see the form, then clear its **Active** switch or **Delete** it.

## Try it on the sample

1. Sign in as `demo_steward` and click the plus button, **Create new entity**.
2. Choose the type **Data Quality**.
3. Name the rule, pick the kind **Not empty**, and set a threshold.
4. Save. The rule page opens at its new address. Its scores come when the governance worker runs.
5. To tidy up, open the rule, clear **Active**, and save.

To read what that rule will report once it runs, go to [Check data quality](<https://aureliusenterprise.github.io/feat-21-2-mcp-deployment/user-guide/check-data-quality/index.md>).
