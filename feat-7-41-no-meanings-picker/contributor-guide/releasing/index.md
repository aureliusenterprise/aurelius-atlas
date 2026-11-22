# Releasing

How to cut, publish, and document a release. The architecture rules — one versioned whole, promoted by a declared path — are [Release Management](<https://aureliusenterprise.github.io/feat-7-41-no-meanings-picker/architecture/platform/delivery/release-management/index.md>) and [ADRs 019/024/029](<https://aureliusenterprise.github.io/feat-7-41-no-meanings-picker/architecture/adr/index.md>); this page is the mechanics.

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
> A commit titled "fixes" contributes "fixes". Because the system releases as one versioned whole ([ADR 019](<https://aureliusenterprise.github.io/feat-7-41-no-meanings-picker/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)), a miscategorised title releases a minor where a patch was meant — and the one-version rule makes that number every part's number.

`npm run prerelease` runs `nx release --preid=rc --skip-publish`: it versions, writes the changelog, and cuts an `rc` tag locally, publishing nothing. The tag is for pulling a release candidate and testing it as an artifact; `npm run release` is the step that publishes and signs ([ADR 029](<https://aureliusenterprise.github.io/feat-7-41-no-meanings-picker/architecture/adr/029-shipped-artifacts-are-signed-and-their-origin-is-provable/index.md>)).

> [!NOTE]
>
> **The first release names its version**
>
> Before the first `v*` tag exists, Nx cannot read the current version or the previous release ref from git. The version falls back to the disk (`fallbackCurrentVersionResolver: "disk"`); the changelog needs `--first-release`, which starts it at the first commit. The conventional-commits bump also moves past `0.1.0`. To make `v0.1.0` the first tag, name the version once: `npx nx release 0.1.0 --first-release --skip-publish`. An exact version ignores `--preid`, so to iterate release candidates after it, use `npm run prerelease` (it cuts `0.1.1-rc.0`, `0.1.1-rc.1`, and so on). After the first tag, `nx release` reads both from git as usual.

## What publishing runs

Per project, `docker-build` produces the wheel (workspace libraries bundled) and the image; the publish pipeline attaches a CycloneDX SBOM ([ADR 033](<https://aureliusenterprise.github.io/feat-7-41-no-meanings-picker/architecture/adr/033-shipped-artifacts-carry-a-contents-inventory/index.md>)) and the signed artifacts are published so a deployment can promote the validated release along its declared path ([ADR 024](<https://aureliusenterprise.github.io/feat-7-41-no-meanings-picker/architecture/adr/024-a-validated-release-is-promoted-by-a-declared-path/index.md>)).

## Publishing the documentation

The site publishes per tag via mike; `main` is aliased `latest` — details in [Documentation](<https://aureliusenterprise.github.io/feat-7-41-no-meanings-picker/contributor-guide/documentation/#publishing-the-documentation>).
