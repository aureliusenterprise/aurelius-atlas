# Resilience

How Aurelius Atlas fails, recovers, and is kept recoverable. The system promises nothing about
staying up (ADR 037) but promises a rehearsed path back (ADRs 026, 041).

| Page                                          | Scope                                                                          | Written by     |
| --------------------------------------------- | ------------------------------------------------------------------------------ | -------------- |
| [High Availability](high-availability.md)     | Single-node posture, what fails together, the store as the critical dependency | written (6.4f) |
| [Incident Management](incident-management.md) | Owner and rehearsed path per failure (ADR 041)                                 | written (6.4f) |
| [Backup & Restore](backup-and-restore.md)     | Store snapshots, restore drill (ADR 026)                                       | written (6.4e) |
| [Disaster Recovery](disaster-recovery.md)     | Rebuild from image + snapshot, objectives                                      | written (6.4e) |
| [Incidents](incidents/index.md)               | The record of every incident and rehearsal (ADR 041 R5)                        | written (6.4f) |
