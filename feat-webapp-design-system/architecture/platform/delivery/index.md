# Delivery

How changes reach production: configuration, change control, testing, release, and deployment. Parts of this tree are already written ([Change Management](<https://aureliusenterprise.github.io/feat-webapp-design-system/architecture/platform/delivery/change-management/index.md>), [Testing](<https://aureliusenterprise.github.io/feat-webapp-design-system/architecture/platform/delivery/testing/index.md>)); the rest is filled per the map below.

| Page | Scope | Written by |
| --- | --- | --- |
| [Configuration Management](<https://aureliusenterprise.github.io/feat-webapp-design-system/architecture/platform/delivery/configuration-management/index.md>) | Production env-var contract (ADR 018); dev/CI secrets and prefixes | written (0.5) |
| [Change Management](<https://aureliusenterprise.github.io/feat-webapp-design-system/architecture/platform/delivery/change-management/index.md>) | Release → acceptance/production hand-over (ADR 024); dev + pipeline after | — |
| [Testing](<https://aureliusenterprise.github.io/feat-webapp-design-system/architecture/platform/delivery/testing/index.md>) | Layer map, CI gate (production bar); developer-side conventions after | — |
| [Release Management](<https://aureliusenterprise.github.io/feat-webapp-design-system/architecture/platform/delivery/release-management/index.md>) | One versioned whole (ADR 019): version, inventory, signing, promotion | written (0.1) |
| [Deployment](<https://aureliusenterprise.github.io/feat-webapp-design-system/architecture/platform/delivery/deployment/index.md>) | Image-per-service, compose layouts, promote-by-declared-path (ADR 024) | 6.4 |
