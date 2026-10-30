# API Management

The API Aurelius Atlas exposes is Apache Atlas 2.4.0's REST API — the product's public contract, kept while its implementation is replaced ([ADR 046](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)).

## The contract

- **Base path** `/api/atlas/v2/...`, same resource families as Atlas (`admin`, `types`, `entity`, …), added increment by increment per the [roadmap](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/conversion/index.md>).
- **Wire format** is Atlas's, including its normalisations: the server's default response class is the Atlas JSON media type, and error bodies follow Atlas's `AtlasErrorCode` (status, code, message template) via `AtlasError` — the enum members are copied from Java Atlas, not invented.
- **No OpenAPI surface** is served: the contract is the wire format itself, specified by parity scenarios whose expectations are read from the Atlas 2.4.0 source and its own tests, each citing where ([ADR 052](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)).

> [!NOTE]
>
> **Why is there no OpenAPI / Swagger UI?**
>
> Atlas ships a Swagger description and integrators expect one. The description would be a second, hand-maintained statement of a contract that parity scenarios already pin byte-for-byte — and the two drifting apart is the failure ADR 030 exists to prevent. The scenarios, not a schema, are the authority ([ADR 030](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/030-interfaces-between-parts-are-verified-not-assumed/index.md>)).

## Change policy

> [!IMPORTANT]
>
> **A REST-visible difference is a decision, not an edit**
>
> Code that answers differently than Atlas 2.4.0 without a deviation entry is a defect, not a simplification: the parity report links every tolerated difference to its entry, and the client-facing contract is [ADR 046](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)'s to keep.

A difference that is kept is recorded in [deviations](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/conversion/deviations/index.md>) with the rule id that changed, and the parity scenario carries a `deviations` entry naming it. Shared concepts change only compatibly ([ADR 017](<https://aureliusenterprise.github.io/dependabot-uv-types-boto3-full--gte-1.43.119/architecture/adr/017-shared-concepts-change-only-compatibly/index.md>)); the version number of the contract stays Atlas 2.4.0's for the life of the conversion.
