# Delivery

How changes reach production: configuration, change control, testing, release, and deployment.
Parts of this tree are already written ([Change Management](change-management.md),
[Testing](testing.md)); the rest is filled per the map below.

| Page                                                    | Scope                                                                     | Written by    |
| ------------------------------------------------------- | ------------------------------------------------------------------------- | ------------- |
| [Configuration Management](configuration-management.md) | Production env-var contract (ADR 018); dev/CI secrets and prefixes        | written (0.5) |
| [Change Management](change-management.md)               | Release → acceptance/production hand-over (ADR 024); dev + pipeline after | —             |
| [Testing](testing.md)                                   | Layer map, CI gate (production bar); developer-side conventions after     | —             |
| [Release Management](release-management.md)             | One versioned whole (ADR 019): version, inventory, signing, promotion     | written (0.1) |
| [Deployment](deployment.md)                             | Image-per-service, compose layouts, promote-by-declared-path (ADR 024)    | 6.4           |
