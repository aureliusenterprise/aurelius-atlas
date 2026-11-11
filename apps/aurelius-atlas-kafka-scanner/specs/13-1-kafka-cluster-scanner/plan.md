# Plan: 13.1 The Kafka cluster scanner

The rules are KSC-01 to KSC-10 of [the spec](./spec.md), the design DD-465 to DD-469.

## Analysis

- **The legacy scanner:** `aureliusenterprise/aurelius` `apps/m4i-data-dictionary-io`,
  `SOURCE=kafka` → `sources/kafka/` (630 lines). AdminClient lists external topics; one System,
  one Collection named by the cluster id, one Dataset per topic; the Schema Registry's
  `<topic>-value` subject parsed by type (Avro, JSON schema), else one consumed message sniffed
  (wire-format magic byte → schema by id, else JSON payload inference); per-entity create with a
  ten-try retry; password-grant auth through `m4i_atlas_core`'s ConfigStore singleton. The
  qualified-name rule is lower, whitespace to `-`, remove `&`–`-` characters, join with `--`.
- **Hard to use, concretely:** the `SOURCE` switch (the excel reader and the kafka reader in one
  app), username/password auth, no topic filter, five-second poll timeouts, one write per entity,
  a broker it cannot reach hangs on.
- **The libraries:** `confluent-kafka` has no musl wheel (the image base is alpine, the install is
  wheels-only) — verified against PyPI; `kafka-python-ng` and `avro` are pure Python and resolve
  for `x86_64-musllinux`/3.14. `kafka-python-ng`'s admin client answers `describe_cluster` (the
  metadata v2+ `cluster_id`) and `is_internal` per topic (DD-465).
- **The server write:** one `create_or_update_bulk` with request-local temp guids resolves ends
  inside the request (EWR-11, the webapp seeder idiom); a re-send resolves by unique
  `qualifiedName`; an unchanged entity is skipped (EWR-08). (DD-466.)
- **The dev broker:** the template's removed `dev/kafka` ran five listeners and a `kafka` realm;
  this scan needs one PLAINTEXT listener (DD-469). The images return as the template had them:
  `dhi.io/kafka:4.3-debian13`, `confluentinc/cp-schema-registry:8.2.1`.

## Chosen scope

The scanner app, its unit and e2e suites, and the dev Kafka stack. The Helm chart and the prod
realm join stay with 13.2. The m4i types need nothing: `m4i_system`, `m4i_collection`,
`m4i_dataset`, and `m4i_field` with their four relationship ends ship with 1.5b's model file.

## Steps

1. The app skeleton: `apps/aurelius-atlas-kafka-scanner` (pyproject under the uv workspace,
   project.json with the `scan` and `e2e` targets, Dockerfile, sonar properties, README, AGENTS,
   `certs/.gitignore`, `.env`/`.env.enc`), mirroring 12.2's shape (DD-458's identity pattern,
   DD-196's telemetry).
2. `settings.py`: the prefixed settings (broker list, Registry URL, system name, topic patterns,
   the sniff bound, the bounds and timeouts, the token and OTLP doors) — KSC-02's `TOPICS`,
   KSC-03's system name, KSC-05's bound, KSC-09/KSC-10's doors.
3. `cluster.py` (the broker door behind a small protocol: topics, cluster id, newest records) +
   `registry.py` (the Registry REST: latest subject, by id). Dead-broker failure names the
   bootstrap list (KSC-01, KSC-02, KSC-10).
4. `fields.py`: the three parsers to the `FieldSpec` tree — Avro (the `avro` package's schema
   objects), JSON schema (`$defs`, `anyOf`/`allOf`/`oneOf`), payload inference (KSC-04..06,
   DD-468).
5. `graph.py`: the qualified-name rule, and the topic tree + field trees to entities with temp
   guids and `relationshipAttributes` (KSC-03, KSC-07, DD-466).
6. `scan.py` + `__main__.py`: the five steps, the notices, `--dry-run`, `--topic`, the exit code
   (KSC-01, KSC-07..09).
7. `dev/kafka`: compose (KRaft broker + Registry, loopback-pinned 29092/28081, healthchecks),
   project.json, README/AGENTS, `.env`/`.env.enc`; the loopback guard extended to `dev/kafka`;
   the dev realm gains the scanner's client and service-account roles, the server's audience
   setting joins it (the 12.2 plumbing repeated: import/master.json, helm/files/master.json,
   compose passthrough, both `.env.enc` re-encrypted).
8. Unit suites per module with `@pytest.mark.covers` markers for every KSC id (the broker and
   Registry doors faked).
9. `e2e/`: the compose stack (the server on 21006 like 12.2's 21005), a producer helper that
   creates topics and publishes records through `kafka-python-ng`, the Registry's REST used to
   register an Avro subject; the proofs: the tree lands under the scanner's own identity, the
   Avro fields with nesting, the wire sniff, the payload inference, the field-less notice, and
   the idempotent re-scan (KSC-07). Namespaced `zz<run>` topics, deleted at the end (DD-223).
10. Records and wiring: the roadmap rows 13.1 (in review) and 13.2 (planned), the java-map line,
    root pyproject member, `uv lock`, the mkdocs nav entry for the app README page, the trace
    check.
11. Verify: ruff/pyright/pytest offline (level 0), then `nx e2e` on the dev stack (level 2),
    prettier/markdownlint/zensical, `nx lint`/`typecheck` for the two projects.
