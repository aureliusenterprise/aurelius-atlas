# How to Contribute

Aurelius Atlas is built one reviewed increment at a time (ADR 051). Start with the [Development Environment](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/development-environment/index.md>) to get a working machine, then the [Conversion roadmap](<https://aureliusenterprise.github.io/feat-app-edge-charts/architecture/conversion/index.md>) to see what is in flight and how an increment runs: spec, code, parity scenarios, traceability, two approvals.

| Guide | For |
| --- | --- |
| [Development Environment](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/development-environment/index.md>) | First setup: devcontainer, Docker Hub login, SOPS key, first run |
| [Secrets Management](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/secrets-management/index.md>) | The age key, `.env`/`.env.enc`, encrypting after edits |
| [Operations Ownership](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/operations-ownership/index.md>) | Who owns secret handling and incident response, and the written paths (ADRs 028/041/042) |
| [Version Control](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/version-control/index.md>) | Branches, conventional commits, the two-signature gate (ADR 044) |
| [AI-Assisted Development](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/ai-assisted-development/index.md>) | `AGENTS.md` files, agents as contributors (ADR 022) |
| [Documentation](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/documentation/index.md>) | Docs tooling, the stub and filling-map convention |
| [Writing Style](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/writing-style/index.md>) | The prose style: short sections, callouts, diagrams; the page pass rules |
| [Testing](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/testing/index.md>) | Running the gate locally, test conventions, the `covers` marker |
| [TLS Certificates](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/tls-certificates/index.md>) | `tls.json`, `nx certgen`, the local CA, cleanup, named relaxations |
| [Releasing](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/releasing/index.md>) | `prerelease`/`release`, the changelog rule, docs publishing |
| [Adopting the Template](<https://aureliusenterprise.github.io/feat-app-edge-charts/contributor-guide/adopting-the-template/index.md>) | For template forks: the rename and re-founding checklist |

Workspace-wide rules for humans and agents live in the root [`AGENTS.md`](<https://github.com/aureliusenterprise/aurelius-atlas/blob/main/AGENTS.md>); every project carries a colocated `AGENTS.md` and `README.md` with its own wiring (ADR 003).
