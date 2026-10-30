# Resilience

How Aurelius Atlas fails, recovers, and is kept recoverable. The system promises nothing about staying up (ADR 037) but promises a rehearsed path back (ADRs 026, 041).

> [!NOTE]
>
> **Planned**
>
> To be written by increment 6.4 (hardening); see [Architecture](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/index.md>).

| Page | Scope | Written by |
| --- | --- | --- |
| [High Availability](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/platform/resilience/high-availability/index.md>) | Single-node posture, what fails together, the store as the critical dependency | 6.4 |
| [Incident Management](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/platform/resilience/incident-management/index.md>) | Owner and rehearsed path per failure (ADR 041) | 6.4 |
| [Backup &amp; Restore](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/platform/resilience/backup-and-restore/index.md>) | Store snapshots, restore drill (ADR 026) | 6.4 |
| [Disaster Recovery](<https://aureliusenterprise.github.io/dependabot-github_actions-dot-github-workflows-actions-cache-6/architecture/platform/resilience/disaster-recovery/index.md>) | Rebuild from image + snapshot, objectives | 6.4 |
