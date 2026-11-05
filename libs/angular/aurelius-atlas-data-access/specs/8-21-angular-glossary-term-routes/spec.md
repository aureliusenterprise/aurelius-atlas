# 8.21 Angular glossary twin (2/3) — the terms

- **Status:** done
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), 8.18 (the DELETE-with-body idiom), 8.20 (AGL,
  the service and `GlossaryPage`), and the server's rules GTM-01..GTM-06,
  GTA-01..GTA-03.

8.20 took the thirteen glossary routes of `routes/glossary.py`; this
increment takes the eleven term routes and grows `GlossaryService`.
Categories (8.22) finish the family.

## Scope

In scope: `GET /term/{glossary_term_guid}`, `POST /term`, `POST /terms`,
`PUT /term/{glossary_term_guid}`, `PUT /term/{glossary_term_guid}/partial`,
`DELETE /term/{glossary_term_guid}`, `GET /terms/{glossary_term_guid}/related`,
and the four `/terms/{glossary_term_guid}/assignedEntities` routes (GET,
POST, DELETE, PUT) — on `GlossaryService` — plus their Vitest specs.

Out of scope: the eight category routes (8.22); any screen that calls the new
methods.

## Semantics

The methods land on 8.20's `GlossaryService`, named after the twin's
(`client.glossary.term()` → `getTerm`, …). None collides with AGL's names.
A 204 answer is a `void` answer; a DELETE with a body rides
`HttpClient.request("DELETE", …)` — the typed `HttpClient.delete` takes none.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AGT-01 | `getTerm(termGuid)` answers `GET /term/{guid}` with an `AtlasGlossaryTerm` (GTM-01). `createTerm(term)` and `createTerms(terms)` answer `POST /term` and `POST /terms` with the bare term or array of terms and answer it back (GTM-02). The anchor is not checked here — a term without one is the server's `MISSING_MANDATORY_ANCHOR` answer, as in the twin (CLG-05).                                                                                                                                         |
| AGT-02 | `updateTerm(termGuid, term)` answers `PUT /term/{guid}` with the bare `AtlasGlossaryTerm`; the body guid is not rewritten — the server grafts the path GUID (GTM-04, CLG-08). `partialUpdateTerm(termGuid, fields)` answers `PUT /term/{guid}/partial` with the bare attribute map (name, descriptions, abbreviation, usage — GTM-04) and answers the whole updated term; an empty map is refused client-side, mirroring the twin's `_no_fields` raise (CLG-03), and an unknown field stays the server's answer. |
| AGT-03 | `deleteTerm(termGuid)` answers `DELETE /term/{guid}`; the route answers 204, so the method is `Observable<void>` (GTM-05, CLG-09).                                                                                                                                                                                                                                                                                                                                                                               |
| AGT-04 | `getRelatedTerms(termGuid)` answers `GET /terms/{guid}/related` with a `Record<string, AtlasRelatedTermHeader[]>` keyed by the relation's JSON name (`seeAlso`, `synonyms`, …) — the keyed map, as the twin returns it (GTM-06, CLG-07). The page parameters the server reads and ignores, the client does not send.                                                                                                                                                                                             |
| AGT-05 | `getAssignedEntities(termGuid, page?)` answers `GET /terms/{guid}/assignedEntities` with an `AtlasRelatedObjectId[]` (GTA-01). The paging is 8.20's `GlossaryPage` (CLG-02): a default travels as absence, an explicit `-1` travels.                                                                                                                                                                                                                                                                             |
| AGT-06 | The assignment trio — `assignTerm` (POST), `removeTermAssignment` (DELETE, the body through `request`), and `disassociateTermAssignment` (PUT, kept so a caller states its intent) — take an `AtlasRelatedObjectId[]` and send it as a bare JSON array; each answers 204 → `void` (GTA-02, GTA-03, CLG-04). The `AtlasRelatedObjectId` of `atlas-glossary.ts` is reused unchanged; the client checks nothing about the ends or the relationship — the server answers.                                            |

### The coverage matrix (`routes/glossary.py`, the term routes)

| Method and path                      | Server function                              | Client method                          | Rule   |
| ------------------------------------ | -------------------------------------------- | -------------------------------------- | ------ |
| `GET /term/{t}`                      | `get_glossary_term`                          | `getTerm` (covered)                    | AGT-01 |
| `POST /term`                         | `create_glossary_term`                       | `createTerm` (covered)                 | AGT-01 |
| `POST /terms`                        | `create_glossary_terms`                      | `createTerms` (covered)                | AGT-01 |
| `PUT /term/{t}`                      | `update_glossary_term`                       | `updateTerm` (covered)                 | AGT-02 |
| `PUT /term/{t}/partial`              | `partial_update_glossary_term`               | `partialUpdateTerm` (covered)          | AGT-02 |
| `DELETE /term/{t}`                   | `delete_glossary_term`                       | `deleteTerm` (covered)                 | AGT-03 |
| `GET /terms/{t}/related`             | `get_related_terms`                          | `getRelatedTerms` (covered)            | AGT-04 |
| `GET /terms/{t}/assignedEntities`    | `get_entities_assigned_with_term`            | `getAssignedEntities` (covered)        | AGT-05 |
| `POST /terms/{t}/assignedEntities`   | `assign_term_to_entities`                    | `assignTerm` (covered)                 | AGT-06 |
| `DELETE /terms/{t}/assignedEntities` | `remove_term_assignment_from_entities`       | `removeTermAssignment` (covered)       | AGT-06 |
| `PUT /terms/{t}/assignedEntities`    | `disassociate_term_assignment_from_entities` | `disassociateTermAssignment` (covered) | AGT-06 |

The eight category routes stay open for 8.22; 8.20's thirteen stay closed.

## Aurelius origin

- Apache Atlas 2.4.0 `GlossaryREST` (the eleven term routes).
- This workspace: `routes/glossary.py` (the anchor check, the keyed related
  map, the assignment bodies) and the server's rules GTM and GTA, cited, not
  restated. `AtlasClient.glossary` (CLG-01..CLG-09, in
  `libs/python/aurelius-atlas-server-client/specs/8-10-client-glossary-routes/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing) and
8.18's idiom (a DELETE with a body rides `HttpClient.request`). No new
decision. As in 8.20, the empty-partial-update refusal raises synchronously
out of the method call rather than out of an `await`.

## Acceptance

- Unit: `glossary.service.spec.ts` grows one `it()` per method naming its
  URL, its parameters or body, and the rule ids (APC-10's pattern).
- Unit: AGT-02's empty map raises with no request; AGT-05's paging reuses
  8.20's pin (a default travels as absence); AGT-06 pins all three verbs on
  the one URL in one `it()`.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
