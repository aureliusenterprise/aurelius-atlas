# Business Objectives

What the organisation gets from Aurelius Atlas, the commitment behind each benefit, and how it is measured.

| Objective (what the business gets) | Commitment | Measured by |
| --- | --- | --- |
| No disruption to the way people work | The Atlas 2.4.0 REST API and dashboard behave as the reference does (ADR 046) | Parity scenarios per increment, expectations cited from Atlas source (ADR 052) |
| Governance you can afford | One store, one service, one dashboard (ADR 047, ADR 050); no Kafka/HBase/Solr assembly to run | Dependency and service count stay at the spine; ADR 050's removal map |
| Confidence in every delivery | Every increment is specified before built, proven before accepted (ADR 051, ADR 052) | Definition of Done in the [roadmap](<https://aureliusenterprise.github.io/feat-cluster-validation-10-5/architecture/conversion/index.md>); green tests per change |
| Quality you can audit | Behaviour lives in executed tests; every rule and function is named by one (ADR 056) | The CI suites: unit, parity scenarios, end-to-end; the SonarQube coverage gate |
| Fast, dependable development | The whole system runs locally; defects reproduce (ADR 006) | One command brings the system and its infrastructure up (ADR 005) |
| What ships is what was tested | E2E tests run the built image against real services (ADR 010, ADR 012) | The e2e stage: the built image, real services, over TLS |
| Trustworthy supply chain | Signed artifacts, SBOMs, verified origins (ADR 029, ADR 033) | CI scan and publish pipelines |

> [!NOTE]
>
> **Who measures these?**
>
> The pipeline, mostly: every measurement in the right-hand column is an automated artifact — a parity scenario, a trace check, an e2e run, a signed build — produced on the change that claims it, not a survey answered after the fact. The reviewer reads the evidence ([ADR 014](<https://aureliusenterprise.github.io/feat-cluster-validation-10-5/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)); the organisation audits the reports, not the promises.
