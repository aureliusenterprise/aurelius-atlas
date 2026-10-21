# Releasing

How to cut, publish, and document a release. The architecture rules — one versioned whole, promoted by a declared path — are [Release Management](<https://aureliusenterprise.github.io/feat-webapp-ui-components-ii/architecture/platform/delivery/release-management/index.md>) and [ADRs 019/024/029](<https://aureliusenterprise.github.io/feat-webapp-ui-components-ii/architecture/adr/index.md>); this page is the mechanics.

## The release flow

```
npm run prerelease    # version + changelog + local rc tag; publishes nothing
npm run release       # publish: version, changelog, tag, signed artifacts
```

The version step is `nx release`: it reads conventional commits and bumps the workspace as one — the root `pyproject.toml` version, project versions, and the changelog. A non-conventional commit title poisons the changelog: entries are only as good as the titles, and `feat:`/`fix:` drive the version bump.

> [!WARNING]
>
> **A non-conventional commit title poisons the changelog**
>
> A commit titled "fixes" contributes "fixes". Because the system releases as one versioned whole ([ADR 019](<https://aureliusenterprise.github.io/feat-webapp-ui-components-ii/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)), a miscategorised title releases a minor where a patch was meant — and the one-version rule makes that number every part's number.

`npm run prerelease` runs `nx release --preid=rc --skip-publish`: it versions, writes the changelog, and cuts an `rc` tag locally, publishing nothing. The tag is for pulling a release candidate and testing it as an artifact; `npm run release` is the step that publishes and signs ([ADR 029](<https://aureliusenterprise.github.io/feat-webapp-ui-components-ii/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)).

## What publishing runs

Per project, `docker-build` produces the wheel (workspace libraries bundled) and the image; the publish pipeline attaches a CycloneDX SBOM ([ADR 033](<https://aureliusenterprise.github.io/feat-webapp-ui-components-ii/architecture/adr/033-shipped-artifacts-carry-a-contents-inventory/index.md>)) and the signed artifacts are published so a deployment can promote the validated release along its declared path ([ADR 024](<https://aureliusenterprise.github.io/feat-webapp-ui-components-ii/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>)).

## Publishing the documentation

The site publishes per tag via mike; `main` is aliased `latest` — details in [Documentation](<https://aureliusenterprise.github.io/feat-webapp-ui-components-ii/contributor-guide/documentation/#publishing-the-documentation>).
