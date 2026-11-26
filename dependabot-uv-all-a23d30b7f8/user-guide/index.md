# User Guide

Aurelius Atlas is a data catalogue. A catalogue answers four questions about the data your organisation holds: where a dataset lives, who is accountable for it, whether you can trust it, and what breaks if you change it. This guide shows a data steward, an analyst, or a data scientist how to answer those questions in the Aurelius Atlas webapp. It does not cover the Apache Atlas dashboard or the REST API.

## The four questions

Each question has a page. Start with [Quick Start](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/quick-start/index.md>), which signs you in and walks you to one dataset page in about twenty minutes.

| Your question | Page |
| --- | --- |
| Where is this data, and how do I find it? | [Find data](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/find-data/index.md>) |
| What does this record say, and who owns it? | [Understand data](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/understand-data/index.md>) |
| Can I trust this data, and why or why not? | [Check data quality](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/check-data-quality/index.md>) |
| What breaks if I change this data? | [Follow lineage](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/follow-lineage/index.md>) |

The guide also covers the jobs around those questions: [Write quality rules](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/write-quality-rules/index.md>) for the checks the scores come from, [Change data](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/change-data/index.md>) for creating, editing and deleting records, and [Settings and Alerts](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/settings-and-alerts/index.md>) for the choices on the header.

## The two ways in

You reach the catalogue one of two ways.

- Your own stack: [Standalone Server](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/standalone-server/index.md>) runs the whole system on your machine so you can try it by hand. To run it for several teams, add a tenant ([Add a Tenant to the Standalone Server](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/standalone-tenants/index.md>)).
- Your organisation's deployment: an operator installed the system for you, usually on Kubernetes ([Deploy to Kubernetes](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/deployment/index.md>) documents that install). Sign in at the address your operator gives you and start at [Quick Start](<https://aureliusenterprise.github.io/aurelius-atlas/dependabot-uv-all-a23d30b7f8/user-guide/quick-start/index.md>).

> [!NOTE]
>
> **The guide is in English**
>
> The webapp ships English and Dutch, so you can switch its language in the Settings panel. This guide ships in English only.
