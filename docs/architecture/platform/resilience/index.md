# Resilience

How Aurelius Atlas fails, recovers, and is kept recoverable. The system promises nothing about
staying up (ADR 037) but promises a rehearsed path back (ADRs 026, 041).

!!! INFO "Planned"

    To be written by increment 6.4 (hardening); see [Architecture](../../index.md).

| Page                                          | Scope                                                                          | Written by |
| --------------------------------------------- | ------------------------------------------------------------------------------ | ---------- |
| [High Availability](high-availability.md)     | Single-node posture, what fails together, the store as the critical dependency | 6.4        |
| [Incident Management](incident-management.md) | Owner and rehearsed path per failure (ADR 041)                                 | 6.4        |
| [Backup & Restore](backup-and-restore.md)     | Store snapshots, restore drill (ADR 026)                                       | 6.4        |
| [Disaster Recovery](disaster-recovery.md)     | Rebuild from image + snapshot, objectives                                      | 6.4        |
