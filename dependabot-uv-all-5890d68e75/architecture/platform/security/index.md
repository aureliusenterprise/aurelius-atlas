# Security

How Aurelius Atlas protects identity, access, secrets, and data. The system's security decisions are in [ADRs 007–008, 013, 028, 039](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/adr/index.md>); the practitioner's guide is in the [Contributor Guide](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/contributor-guide/secrets-management/index.md>).

| Page | Scope | Written by |
| --- | --- | --- |
| [Access Management](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/platform/security/access-management/index.md>) | Authorizer policies on every endpoint, role model | 6.2 (ADR 038) |
| [Identity Management](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/platform/security/identity-management/index.md>) | Shared identity provider, sessions, the dashboard's identity | 6.1 (ADR 007) |
| [Secrets Management](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/platform/security/secrets-management/index.md>) | Production: env channel, ownership (ADR 028), boundaries; dev/CI rules after; how-to in the [Contributor Guide](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/contributor-guide/secrets-management/index.md>) | written (ADRs 008/028) |
| [Data Encryption](<https://aureliusenterprise.github.io/dependabot-uv-all-5890d68e75/architecture/platform/security/data-encryption/index.md>) | TLS in flight (production), at rest; dev certificates and named relaxations after | written (0.2/0.5) |
