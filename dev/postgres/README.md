# aurelius-atlas-dev-postgres

Local development Postgres — the workspace's general-purpose relational store.

Part of the template **spine**.

## Services

| Service  | Image                           | Host port                 |
| -------- | ------------------------------- | ------------------------- |
| postgres | `dhi.io/postgres:18-alpine3.23` | `${DATABASE_PORT}` (5432) |

- Database: `aurelius`, user/password `postgres` (dev defaults in `.env`),
  `scram-sha-256` authentication
- Attached to the `aurelius-atlas-dev-postgres-network` Docker network for
  consumers that attach to it. Atlas itself persists in Elasticsearch; the
  template's example apps and JDBC sink that used this database are gone
  (DD-284). `dev/keycloak`'s compose borrows this slice's `pg_hba.conf`.

## Running

```bash
nx serve aurelius-atlas-dev-postgres   # docker compose up (foreground)
nx up aurelius-atlas-dev-postgres      # detached, waits for healthy
```

The slice keeps a blank database — schema belongs to the applications, not to
compose init scripts. There are no migration files here.
