# Release Management

The system releases as one versioned whole ([ADR 019](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)): one version number across the workspace, one changelog, one release event.

## The flow

```
graph LR
    C[Commits] -->|version| V[Version + changelog]
    V --> B[Image + inventory]
    B -->|scan green| SG[Signed + published]
    SG -->|promote by declared path| P[Production]
```

The unit that passes validation is the unit that ships, and a deployment promotes the signed artifact along the declared path ([ADR 010](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>), [ADR 024](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>)).

1. **Version** — the release tool reads conventional commits and bumps the workspace as one: one version, the project versions, and the changelog. A candidate can be cut locally for testing without publishing anything.
2. **Build** — every part produces its wheel and its image; the validated unit is the unit that ships ([ADR 010](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>)).
3. **Inventory** — images carry a contents inventory ([ADR 033](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/033-shipped-artifacts-carry-a-contents-inventory/index.md>)) and a vulnerability scan runs over the affected images in CI.
4. **Sign and publish** — published artifacts are signed with provable origin ([ADR 029](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)); the publish pipeline promotes a validated release along the declared path ([ADR 024](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>)).
5. **Docs** — the site publishes per release tag ([publishing](<https://aureliusenterprise.github.io/feat-webapp-api-auth/contributor-guide/documentation/#publishing-the-documentation>)).

The commands — the candidate cut, the publish, the docs site mechanics — are the contributor guide's: [Releasing](<https://aureliusenterprise.github.io/feat-webapp-api-auth/contributor-guide/releasing/index.md>).

## Conventions that make one-version work

Conventional commit titles are required (the changelog is generated from them); template updates merge from the `template` remote without versioning pressure because the repo keeps its history (ADR 050's mergeability requirement). The runtime version window is declared, not floating ([ADR 031](<https://aureliusenterprise.github.io/feat-webapp-api-auth/architecture/adr/031-runtime-versions-have-a-declared-support-window/index.md>)).

> [!WARNING]
>
> **A non-conventional commit title poisons the changelog**
>
> The changelog is generated, so its entries are only as good as the titles: a commit titled "fixes" contributes "fixes". `feat:`/`fix:` also drive the version bump — a miscategorised title releases a minor where a patch was meant, and the one-version rule makes that number every part's number.
