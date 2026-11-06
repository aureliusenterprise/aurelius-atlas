# 9.6 The server's e2e suites clean up after themselves

- **Status:** in review
- **Pull request:** [#283](https://github.com/aureliusenterprise/aurelius-atlas/pull/283)
- **Records:** DD-368; relies on DD-223 (the e2e suites share the dev stores, their writes namespaced and
  self-cleaned), EDL-02 to EDL-08 (delete and purge) and TDS-09 (type deletion)

The server's e2e suites write to the shared dev store: the parity scenarios and the export, import and
replication tests create types and entities named by their run. They deleted some and purged few, and removed
almost none of their types, so every run left a share behind. A session now removes what it created.

## Scope

In `apps/aurelius-atlas-server/e2e/`: `cleanup.py` (`Created`, `remove`, `warn_left`), the session fixture
`created`, and the `client` and `api` fixtures recording into it. The replication test registers the
`AtlasServer` its export creates.

Not in scope: what earlier runs left on the dev store; the server's admin audits and entity audits of the
removed entities, which Atlas keeps as well; the suites of other projects, which keep their own indices or
data.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ECU-01 | Every answer to a successful `POST` or `PUT` of the writer's clients is read for what it created: the guids of `mutatedEntities.CREATE`, an import's `processedEntities`, the `guid` of a glossary, term, category or saved search, and every definition a `POST` of typedefs answers. A test registers an entity the server creates without naming it in an answer |
| ECU-02 | At the session's end, the recorded entities are deleted and purged, 100 guids a request                                                                                                                                                                                                                                                                             |
| ECU-03 | Then the recorded types still stored are deleted in one request, each in its category's list. When the server refuses that request, they are deleted one by one, the later created first, pass by pass while a pass deletes one                                                                                                                                     |
| ECU-04 | What cannot be removed is reported as a warning of the session, which does not fail it. Only what the session recorded is removed, never by a name, so the writes of a parallel run stay                                                                                                                                                                            |

## Java origin

None: the suites are Aurelius's.

## Deviations

None.

## Acceptance

- `e2e/test__aurelius_atlas_server_cleanup_e2e.py`: ECU-01 to ECU-04 against a recording fake of the server.
- By hand, `nx e2e aurelius-atlas-server` on the dev store: the store holds no more entities or test types
  after the run than before it.
