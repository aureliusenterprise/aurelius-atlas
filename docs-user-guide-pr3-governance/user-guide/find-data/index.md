# Find data

This page covers the search screens: how to ask a question, what an answer card states, and how to narrow a long list. One search box sits at the top of every catalogue screen, so you can search from anywhere. The examples run on the imported sample catalogue, signed in as `demo_scientist`.

## The search box

The box is in the band at the top of the screen. Type a question and press Enter, or click the green search button beside it. The webapp searches only when you submit, not while you type. While the box holds text it shows a clear button, which empties the search and lists everything again.

The same box serves the landing screen, the results screen, and every record page. An empty search lists every record the server holds.

## The three starting points

The landing screen holds one box plus three cards, each with its own box and a green button:

| Card | Green button | The button lists |
| --- | --- | --- |
| Business context | Start browsing data domains | Records of the **Data Domain** type |
| Technical context | Start browsing systems | Records of the **System** type |
| Data governance organization | Start browsing people | Your own e-mail as a search |

The sample catalogue holds data domains and systems, so the first two buttons list them. The third button searches the signed-in account's e-mail address.

## Words, meaning, and both

The webapp searches in one of three modes. The mode is not a control on the search screen. Open Settings with the gear icon, and choose one under **Search by**:

| Mode | Finds | Needs |
| --- | --- | --- |
| Words | Records whose name, qualified name, or description holds your words | Nothing extra (the default) |
| Meaning | Records about your idea, even when they do not hold the word | The server's meaning index |
| Both | The two together, merged into one list | The server's meaning index |

Words is the default. A word may end in `*` to match words that begin with it, so `employ*` finds `employee`. Type names and identifiers match only as whole words.

Changing the mode while a search is on screen runs that search again from the first page. If the server has no meaning index, choosing Meaning or Both shows the alert "Search by meaning is not available on this server" and returns you to Words.

## What a result card states

The search below lists the sample dataset and the fields under it. Look at the filter column at the left, and at one card: it carries the type badge, a quality row, and a people row.

![Search results for NL1-HR-001.](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/assets/user-guide/search-results.png>)

Each result is a card. It shows:

- The record's name as the title. A record with no name shows its qualified name instead.
- The type badge at the right, with a friendly type name such as **Dataset** or **Data Field**.
- The classification chips of the record, and the chips propagated to it from a parent.
- A quality row, such as `70% Completeness (2)`, when the governance worker scored the record.
- The description, when the record has one.
- The people who answer for the record: **Domain Lead(s)**, **Data Owner(s)**, and **Data Steward(s)**, when the record names them.

A card drawn from search shows the governance mark, the warning triangle or the green check, only for a record the governance worker actually judged.

## Narrow a long list

The results screen puts a filter column beside the list. The column holds up to four menus, and an empty menu is hidden: **Type**, **State**, **Owner**, and **Service Type**. Each value shows its count in parentheses, and a menu with more than five values carries a **Show more** link.

Only the **Type** menu filters. Tick a type and the search runs again, narrowed to that type and its sub types. Untick it to widen again. A new search from the box clears your ticks. The other menus are read-only counters. Submitting a search whose facets all came back empty replaces the column with "No filters available."

## Order and paging

The results have no sort control, and that is deliberate. The server returns the best relevance matches first, and the webapp keeps that order.

The list holds ten records and grows as you scroll. Click **Load next page...** to add the next ten. The list never jumps to a random page and carries no "page 3 of 70" control. The header counts the whole answer, for example `25 results`. A search by meaning cannot know its total, so it counts the nearest records it found and says `25 closest matches`.

## Share a search

A search's text rides the page address as `?query=`. Copy the address from the browser bar to send the same search to a colleague, or to come back to it later. Opening the address runs the search again.

The search mode and your type ticks do not ride the address. The address opens in whatever mode your browser last used, with no ticks.

## When nothing comes back

**No results found** means the server answered with nothing. The usual causes, in the order to try them:

1. You typed a word the catalogue does not hold. Shorten it, or end it with `*`.
2. The webapp is in Meaning or Both mode and the meaning index is not ready. Switch to **Words** in Settings.

A failure looks different: an error appears in the Alerts drawer, and the list stays as it was. Open the bell icon to read it.

## Try it on the sample

1. Sign in as `demo_scientist` and type `employee` in the search box. Press Enter.
2. Look at the **Type** menu in the filter column. Tick **Data Field** and watch the list shrink to fields. Untick it.
3. Search for `NL1-HR-001` and open the result. The dataset page opens, and the address bar now holds `/search/details/` and the record's identifier, which you can copy to share or revisit.

The next step is the record page itself, in [Understand data](<https://aureliusenterprise.github.io/docs-user-guide-pr3-governance/user-guide/understand-data/index.md>).
