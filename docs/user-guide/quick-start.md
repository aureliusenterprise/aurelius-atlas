# Quick Start

This page takes you from a running Aurelius Atlas stack to one dataset page, in about twenty
minutes. You import a sample catalogue, sign in to the webapp, and read a real record. You change
nothing. When you reach the dataset page, the other pages of the guide explain what to do next.

!!! NOTE "Before you start"

    You need a running stack and one person who can read the catalogue. The
    [Standalone Server](standalone-server.md) page starts the stack on your machine and owns the
    addresses, the certificates, and how to make a person. If your organisation already runs Atlas,
    skip to [Sign in](#sign-in) and use the address your operator gives you.

## Import the sample

A new stack holds nothing. Import the sample catalogue, which adds 699 records: datasets, their
fields, systems, people, and the quality scores that later pages use.

1. Make sure that the stack is running, then run the import script from the repository root:

    ```bash
    docker/bin/import-sample.sh
    ```

    The script imports `data/atlas-sample/sample_data.zip`, its default. It logs the counts by type
    when the import ends, and exits non-zero on a failed import.

2. Wait until the webapp answers at <https://localhost:9000/>. A cold start takes about two minutes.

!!! TIP "Run it again when you want a clean start"

    An import updates the records it finds by GUID, so a second run is safe. It does not delete
    records you created by hand.

## Sign in

The webapp has no sign-in button. When you open it while signed out, it sends you to the stack's
Keycloak sign-in page and returns you to the page you asked for.

1. Open <https://localhost:9000/> in your browser. The certificate is the development CA's, so the
   browser asks you to accept it once for `localhost:9000`.
2. Sign in as a person who can read the catalogue:
    - With tenancy on, sign in as `demo_steward`. Its password is `DEMO_USER_STEWARD_PASSWORD` in
      `infra/keycloak/.env`. See [Add a Tenant to the Standalone Server](standalone-tenants.md).
    - Without tenancy, the stack ships only the platform operator, who cannot read the catalogue.
      Follow the bring-your-own-user steps in
      [Standalone Server](standalone-server.md) to add a person and give it the `atlas-read` role.
3. You arrive on the **Getting started** screen. It holds one search box at the top and three cards:
   **Business context**, **Technical context**, and **Data governance organization**. Each card asks
   for a keyword and has a green button that browses one type.

??? QUESTION "Do the three buttons find the sample?"

    Not yet on the sample catalogue. Each button filters on an Apache Atlas type
    (`AtlasGlossary`, `Infrastructure`, or a person's own e-mail), and the sample records use
    Aurelius's own types instead ([DV-84](../architecture/conversion/deviations.md)). So the buttons
    answer **No results found** here. Use the search box at the top instead, which is the normal path
    anyway.

## Find one dataset

The search box sits above every screen, so you never lose it. Type a name and press Enter.

1. Click in the search box, type `NL1-HR-001`, and press Enter.
2. The results screen lists the matches. The webapp searches by words by default, which looks for
   the exact words you typed.
3. Click **NL1-HR-001** in the list. Each result card shows the record's name and, on the right, its
   type badge.

If you see **No results found**, one of three things is true: the import did not finish, the search
mode looks for meaning and the sample's meaning index is not ready, or you typed a name the sample
does not hold. Make sure that the import logged its counts, then search again.

!!! TIP "Change how the search works in Settings, not on the screen"

    The gear icon opens **Settings**, and the **Search by** group chooses **Words**, **Meaning**, or
    **Both**. Words matches exact words and is the default. Meaning finds records about an idea even
    when they do not hold the word. Both runs the two together. The webapp reruns your search when
    you change it.

## Read one dataset

The record's page answers the four questions the guide is built around.

You land on the **NL1-HR-001** dataset page. Its header shows the name, and below it the badge
**Dataset**. Under the header you can see the description, the properties, and the sections of cards
that link to the record's fields, its people, and its systems. Two things to try here:

- Follow a card to a related record. Each card links to the record it names, and the breadcrumb at
  the top shows where you are.
- Look at the people named on the page. They answer for the record.

You are done with the quick start. The next pages of the guide take each of these jobs further.

## Where to next

| What you want to do                       | Page                            |
| ----------------------------------------- | ------------------------------- |
| Search well: words, meaning, both, facets | Find data (`Planned`)           |
| Read any record: layout, sections, people | Understand data (`Planned`)     |
| See what a change would affect            | Follow lineage (`Planned`)      |
| Trust a record, and see why not           | Check data quality (`Planned`)  |
| Change a record, or make a new one        | Change data (`Planned`)         |
| Choose language, search mode, theme       | Settings and alerts (`Planned`) |

The **Create new entity** button is the plus icon at the right end of the search band. It appears
only for a person who can write. Use `demo_steward`, or a person with the `atlas-write` role, to try
it.
