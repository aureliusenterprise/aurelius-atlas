# Security

How Aurelius Atlas protects identity, access, secrets, and data. The system's security decisions are
in [ADRs 007–008, 013, 028, 039](../../adr/index.md); the practitioner's guide is in the
[Contributor Guide](../../../contributor-guide/secrets-management.md).

| Page                                          | Scope                                                                                                                                                             | Written by             |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| [Access Management](access-management.md)     | Authorizer policies on every endpoint, role model                                                                                                                 | 6.2 (ADR 038)          |
| [Identity Management](identity-management.md) | Shared identity provider, sessions, the dashboard's identity                                                                                                      | 6.1 (ADR 007)          |
| [Secrets Management](secrets-management.md)   | Production: env channel, ownership (ADR 028), boundaries; dev/CI rules after; how-to in the [Contributor Guide](../../../contributor-guide/secrets-management.md) | written (ADRs 008/028) |
| [Data Encryption](data-encryption.md)         | TLS in flight (production), at rest; dev certificates and named relaxations after                                                                                 | written (0.2/0.5)      |
