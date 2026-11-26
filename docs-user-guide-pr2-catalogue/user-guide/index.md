# User Guide

Aurelius Atlas is a data catalogue. A catalogue answers four questions about the data your organisation holds: where a dataset lives, who is accountable for it, whether you can trust it, and what breaks if you change it. This guide shows a data steward, an analyst, or a data scientist how to answer those questions in the Aurelius Atlas webapp. It does not cover the Apache Atlas dashboard or the REST API. The [API Reference](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/api-reference/index.md>) covers the API, and the [Contributor Guide](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/contributor-guide/index.md>) covers building the system.

## The four questions

Each question has a page. Start with [Quick Start](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/quick-start/index.md>), which signs you in and walks you to one dataset page in about twenty minutes.

| Your question | Page |
| --- | --- |
| Where is this data, and how do I find it? | [Find data](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/find-data/index.md>) |
| What does this record say, and who owns it? | [Understand data](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/understand-data/index.md>) |
| Can I trust this data, and why or why not? | Check data quality (`Planned`) |
| What breaks if I change this data? | [Follow lineage](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/follow-lineage/index.md>) |

The guide also covers [Settings and Alerts](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/settings-and-alerts/index.md>), the choices on the header. Three catalogue jobs have pages that are not written yet: check data quality, write quality rules, and change data. The table links only the pages that exist today. As each page is written, it replaces its `Planned` marker here.

## The two ways in

You reach the catalogue one of two ways.

- Your own stack: [Standalone Server](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/standalone-server/index.md>) runs the whole system on your machine so you can try it by hand. To run it for several teams, add a tenant ([Add a Tenant to the Standalone Server](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/standalone-tenants/index.md>)).
- Your organisation's deployment: an operator installed the system for you, usually on Kubernetes ([Deploy to Kubernetes](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/deployment/index.md>) documents that install). Sign in at the address your operator gives you and start at [Quick Start](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/user-guide/quick-start/index.md>).

> [!NOTE]
>
> **The guide is in English**
>
> The webapp ships English and Dutch, so you can switch its language in the Settings panel. This guide ships in English only.

The catalogue's behaviour is documented here, in this repository. The [Deviations from Apache Atlas](<https://aureliusenterprise.github.io/docs-user-guide-pr2-catalogue/architecture/conversion/deviations/index.md>) ledger lists every intended difference from Apache Atlas 2.4.0, and it grows as the conversion proceeds.
