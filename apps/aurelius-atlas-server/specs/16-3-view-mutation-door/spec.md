# 16.3 The view family: the mutation door

- **Status:** planned
- **Pull request:** #359
- **Records:** ADR 064; DD-589 to DD-593 (here); relies on 16.1 (AVS-01..09), 16.2 (AVR-10's read
  door), 2.4 (EWR), 3.3a (CLS), 5.2c (GTA), 5.3a (LBL), 2.2 (ENS optimistic versioning)

## Scope

The third door of ADR 064's family:

- `POST /api/aurelius/v1/entity` — create or update an entity in the view's shape, the whole
  change applied inside the server, the new live view out (`routes/view_entity.py`, with 16.2);
- `GET /api/aurelius/v1/types/for-type/{name}` — the type and its supertype closure an editor
  needs to render one entity type, in place of the whole typedefs document (`routes/view_types.py`).

The server takes the view's `attributes`, `classifications`, `labels`, `meanings` and `sections`
as the _desired state_, diffs it against the store, and applies the difference through the same
internal paths 2.4, 3.3a, 5.2c and 5.3a use. A create carries a client-chosen qualified name and
no GUID; the answer carries the server's GUID.

Not delivered, with the increment that will:

| Not delivered                                                               | Lands with                                                                                                    |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Delete through the door                                                     | none: the webapp's delete flow (7.7b, 7.9) rides the Atlas delete, a mutation and outside ADR 064's read rule |
| The editor switched to the door                                             | 16.5                                                                                                          |
| Bulk create/update                                                          | none now                                                                                                      |
| Relationship-edge types beyond `sections` (propagation flags kept as today) | –                                                                                                             |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                            |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AVW-01 | `POST /api/aurelius/v1/entity` needs a user with `ENTITY_CREATE` (create, no `guid`) or `ENTITY_UPDATE` (update, with `guid`), answered 403 in the Aurelius error shape without it                                                                                                                                                              |
| AVW-02 | The body is a view: the entity's `typeName` and `attributes` are required; `classifications`, `labels`, `meanings` and `sections` are the desired sets, each complete; `quality`, `stale` and the breadcrumb are ignored on the way in                                                                                                          |
| AVW-03 | The server validates the entity as 2.4 does (typesystem EVL): a bad value is answered with Atlas's validation error, one Aurelius door around the same checks                                                                                                                                                                                   |
| AVW-04 | An update compares the request's `updateTime` with the stored one; a stored entity changed since is answered 409 `{errorCode: "ENTITY_VERSION_CONFLICT"}` with the stored view, and the request applies nowhere                                                                                                                                 |
| AVW-05 | The door applies in one request: attributes through 2.4's create/update path, then each set as a replace — classifications, labels and meanings diffed to add/remove calls of 3.3a, 5.3a and 5.2c's internals, sections diffed to relationship create/delete of 3.1a's internals. A later step that fails rolls the whole request back (DD-590) |
| AVW-06 | A create without `guid` gets a server GUID; the answer's view carries it. The qualified name is the client's (the editor invents it as today, EDT/DD-325's reason), and a clash with a stored entity is answered 409 in the conflict shape                                                                                                      |
| AVW-07 | The answer to a create or update is the live view of the entity as 16.2's read door answers it: derived fresh, `stale` false, `updateTime` the new one (AVS-06)                                                                                                                                                                                 |
| AVW-08 | Propagated classifications are not desired-state inputs: a `classifications` set that names only the entity's own tags leaves what propagated in (DD-326's read rule made a server rule), and removing a propagated tag answers a refusal naming its source                                                                                     |
| AVW-09 | A `sections` entry names ends by GUID, ACTIVE or a delete intent; an unknown end or an end whose type breaks the relationship constraint is refused in the validation shape (AVW-03)                                                                                                                                                            |
| AVW-10 | The door writes the audit and history records the underlying paths write (3.5a's AUD): one update is one update audit per changed kind, as the Atlas paths produce for the same effect                                                                                                                                                          |
| AVW-11 | `GET /api/aurelius/v1/types/for-type/{name}` needs `TYPE_READ` and answers `{type, superTypes}`: the named entity type and its supertype chain with the attributes each declares, enough to build a form for one type (EDT-04's need). An unknown type is answered 404                                                                          |
| AVW-12 | No answer of Apache Atlas's API changes (AVS-09): the Atlas entity write, classification, label and term endpoints behave as before                                                                                                                                                                                                             |

## Aurelius origin

- ADR 064's mutation door; the editor as built today (7.7a's save sequence DD-326's classification
  diff, DD-325's temp-GUID and remap, `entity-saved.ts`'s refetch tick, 7.7c's picker remap
  DD-338..341) is the mechanism this door replaces, not a contract it keeps.
- The Atlas write semantics the door reuses unchanged: 2.4 (EWR), 3.1a (REL), 3.3a (CLS),
  5.2c (GTA), 5.3a (LBL).

## Deviations

Against Apache Atlas, added to [Deviations](../../../../docs/architecture/conversion/deviations.md)
with the increment: none on the Atlas paths themselves (AVW-12). The door is new surface; its
whole-request-all-or-nothing rule (AVW-05) has no Atlas twin — the Atlas sequence of calls has no
atomicity either, and the door's rule is stricter than the client sequence it replaces, recorded
as DV-NNN at implementation.

## Acceptance

- `apps/aurelius-atlas-server/tests/test__view_mutation.py`: create with a server GUID and
  qualified-name clash (AVW-06), the version conflict and its stored view (AVW-04), set diffs
  adding and removing classifications, labels, terms and section edges (AVW-05, AVW-08, AVW-09),
  the ignored read-only fields (AVW-02), the answer equalling the read door's view (AVW-07),
  refusals and the error shape (AVW-01, AVW-03, with 16.2's AVR-13).
- `apps/aurelius-atlas-server/tests/test__view_types.py`: the chain for a deep m4i type, an
  unknown type (AVW-11).
- The rollback of AVW-05 proven on the fake store: a failing section step leaves attributes,
  tags and labels at the request's start (the store gap ADR 047 names, applied here).
- `apps/aurelius-atlas-server/e2e/test__view_mutation_e2e.py` on the dev store: the editor's
  round trip — read door, edit, save, save again with a stale `updateTime` (409), audit rows
  present (AVW-10). One `@pytest.mark.critical` scenario (ADR 062).
