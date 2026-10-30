# Architecture Roadmap

The plan of record is the [conversion roadmap](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/conversion/index.md>) — increments 0.1 through 6.4, each with a semantics spec, status, and Java origin. This page is the theme-level view: what people can do with the catalogue at each phase.

| Phase | Theme | What becomes possible |
| --- | --- | --- |
| 0.x | Foundations | The platform runs: one store, dev infrastructure, the dashboard served, quality harnesses in place |
| 1.x | The type system | The catalogue's dictionary exists: the vocabulary describing your data assets, its hierarchies, and its built-in models |
| 2.x | Entities | Assets get catalogued: register data assets, read and update them, retire them cleanly |
| 3.x | Relationships and classification | Context appears: assets connect to each other, sensitive data is classified, every change is on the audit record |
| 4.x | Search | People find things themselves: quick search, suggestions, the Atlas query language, saved searches |
| 5.x | Semantics | Understanding deepens: lineage shows where data comes from, the glossary records business meaning and quality signals |
| 6.x | Governance and hardening | Governance goes live: sign-in through the corporate identity provider, role-based access, migration of an existing Atlas |

> [!NOTE]
>
> **What must be true before a phase starts?**
>
> The phase below it is done: the type system (1.x) is what entities (2.x) reference, entities are what search (4.x) finds, and authentication (6.1) arrives last because the contract is proven anonymous first. Each increment is specified before it is built ([ADR 051](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)), so the order is a dependency chain, not a schedule.

Each increment is specified before it is built and lands as one pull request; the roadmap table is the single status record. After increment 6.4, the template's examples leave ([DD-019](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/conversion/design-log/#dd-019-the-template-examples-stay-until-the-plan-is-done>)).

> [!NOTE]
>
> **Why do the template's examples stay until the very end?**
>
> They are load-bearing while the plan is being executed: the API and frontend example apps are the demonstrations that the template's wiring (secrets, TLS, CI, serve-with-infra) works for a real app, and the catalogue's own apps ride the same wiring. Removing the proof before the thing it proves is finished would leave the last increments unverifiable — so they leave in one slice, after 6.4.
