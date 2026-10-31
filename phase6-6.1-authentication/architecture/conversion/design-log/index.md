# Design Log

Technical decisions made during the conversion that are too implementation-specific for an ADR but must not be lost: storage layout, identifiers, query translation, test tooling. Business-level decisions are ADRs in [Architecture Decisions](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/index.md>).

## Rules

- Entries are numbered `DD-NNN`, consecutively; numbers are never reused.
- Statuses: **Proposed** → **Accepted**, then optionally **Superseded by DD-NNN**.
- An accepted entry is never edited except its status line. A changed decision is a new entry that supersedes the old one.
- Every entry names the increment that introduced it, so the reasoning can be found next to the code and the specification it belongs to.
- An increment that makes a decision adds its entry in the same pull request.

## Entry template

```
### DD-NNN. Decision as a statement

- **Status:** Proposed | Accepted | Superseded by DD-NNN
- **Increment:** N.N
- **Date:** YYYY-MM-DD

**Decision.** What we do, in one or two sentences.

**Reason.** Why, in terms of the requirements of the increment.

**Alternatives.** What else was considered and why it lost.

**Consequences.** What follows, including what must be revisited and when.
```

## Log

| \# | Decision | Increment | Status |
| --- | --- | --- | --- |
| [DD-001](<#dd-001-reference-is-apache-atlas-240-and-both-dashboards-are-served>) | Reference is Apache Atlas 2.4.0, and both dashboards are served | 0.1 | Accepted |
| [DD-002](<#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>) | Atlas code lives in aurelius-atlas projects split by layer | 0.1 | Accepted |
| [DD-003](<#dd-003-template-projects-are-renamed-to-the-aurelius-atlas-prefix>) | Template projects are renamed to the aurelius-atlas prefix | 0.1 | Accepted |
| [DD-004](<#dd-004-the-spa-keeps-tokens-in-memory-and-renews-them-silently>) | The SPA keeps tokens in memory and renews them silently | 0.1 | Accepted |
| [DD-005](<#dd-005-the-store-uses-the-official-async-elasticsearch-client>) | The store uses the official async Elasticsearch client | 0.2 | Proposed |
| [DD-006](<#dd-006-development-and-tests-run-elasticsearch-with-security-on>) | Development and tests run Elasticsearch with security on | 0.2 | Proposed |
| [DD-007](<#dd-007-the-elasticsearch-test-fixture-ships-with-the-store-library>) | The Elasticsearch test fixture ships with the store library | 0.2 | Proposed |
| [DD-008](<#dd-008-a-yellow-cluster-is-healthy>) | A yellow cluster is healthy | 0.2 | Proposed |
| [DD-009](<#dd-009-traceability-is-checked-from-collected-markers-not-from-a-test-run>) | Traceability is checked from collected markers, not from a test run | 0.3 | Proposed |
| [DD-010](<#dd-010-the-traceability-check-covers-atlas-code-from-increment-02-on>) | The traceability check covers Atlas code from increment 0.2 on | 0.3 | Proposed |
| [DD-011](<#dd-011-the-test-report-is-generated-from-junit-coverage-and-trace-files>) | The test report is generated from JUnit, coverage and trace files | 0.3 | Proposed |
| [DD-012](<#dd-012-parity-scenarios-are-yaml-files-run-as-parametrised-pytest-tests>) | Parity scenarios are YAML files run as parametrised pytest tests | 0.4 | Proposed |
| [DD-013](<#dd-013-a-scenario-response-is-compared-exactly-except-at-declared-paths>) | A scenario response is compared exactly, except at declared paths | 0.4 | Proposed |
| [DD-014](<#dd-014-scenario-facts-reach-the-report-as-test-properties>) | Scenario facts reach the report as test properties | 0.4 | Proposed |
| [DD-015](<#dd-015-the-server-is-a-fastapi-application-with-one-router-per-atlas-resource>) | The server is a FastAPI application with one router per Atlas resource | 0.5 | Proposed |
| [DD-016](<#dd-016-the-server-does-not-start-without-its-store>) | The server does not start without its store | 0.5 | Proposed |
| [DD-017](<#dd-017-the-dashboards-are-vendored-unchanged-and-built-with-dart-sass-on-node-24>) | The dashboards are vendored unchanged and built with dart-sass on Node 24 | 0.6 | Proposed |
| [DD-018](<#dd-018-the-server-serves-the-dashboards-from-the-apis-origin>) | The server serves the dashboards from the API's origin | 0.6 | Proposed |
| [DD-019](<#dd-019-the-template-examples-stay-until-the-plan-is-done>) | The template examples stay until the plan is done | 0.6 | Proposed |
| [DD-020](<#dd-020-typedef-models-are-pydantic-models-that-read-and-write-atlass-json>) | Typedef models are Pydantic models that read and write Atlas's JSON | 1.1 | Proposed |
| [DD-021](<#dd-021-set-valued-fields-keep-each-name-once-in-first-seen-order>) | Set-valued fields keep each name once, in first-seen order | 1.1 | Proposed |
| [DD-022](<#dd-022-typedef-timestamps-are-aware-datetimes-written-as-epoch-milliseconds>) | Typedef timestamps are aware datetimes, written as epoch milliseconds | 1.1 | Proposed |
| [DD-023](<#dd-023-atlas-errors-live-in-the-model-library>) | Atlas errors live in the model library | 1.2 | Proposed |
| [DD-024](<#dd-024-the-registry-is-updated-on-a-transient-copy-under-a-re-entrant-lock>) | The registry is updated on a transient copy under a re-entrant lock | 1.2 | Proposed |
| [DD-025](<#dd-025-the-type-system-ports-the-definition-side-only>) | The type system ports the definition side only | 1.2 | Proposed |
| [DD-026](<#dd-026-dynamic-attributes-and-search-lookups-wait-for-their-increments>) | Dynamic attributes and search lookups wait for their increments | 1.3 | Proposed |
| [DD-027](<#dd-027-derived-type-sets-keep-first-seen-order>) | Derived type sets keep first-seen order | 1.3 | Proposed |
| [DD-028](<#dd-028-the-type-definitions-are-one-elasticsearch-document>) | The type definitions are one Elasticsearch document | 1.4 | Proposed |
| [DD-029](<#dd-029-server-processes-share-the-type-definitions-through-the-documents-version>) | Server processes share the type definitions through the document's version | 1.4 | Proposed |
| [DD-030](<#dd-030-the-store-asks-the-entity-store-whether-a-type-is-in-use>) | The store asks the entity store whether a type is in use | 1.4 | Proposed |
| [DD-031](<#dd-031-the-patch-records-live-in-the-typedef-document>) | The patch records live in the typedef document | 1.5 | Proposed |
| [DD-032](<#dd-032-the-built-in-models-are-vendored-unchanged-and-read-from-a-directory>) | The built-in models are vendored unchanged and read from a directory | 1.5 | Proposed |
| [DD-033](<#dd-033-start-up-loading-is-one-change-per-model-file-and-per-patch>) | Start-up loading is one change per model file and per patch | 1.5 | Proposed |
| [DD-034](<#dd-034-lists-of-type-definitions-are-sorted-by-name>) | Lists of type definitions are sorted by name | 1.6 | Proposed |
| [DD-035](<#dd-035-type-scenarios-create-what-they-read-and-delete-it-at-their-end>) | Type scenarios create what they read and delete it at their end | 1.6 | Proposed |
| [DD-036](<#dd-036-start-up-loading-tries-a-raced-change-again>) | Start-up loading tries a raced change again | 1.6 | Proposed |
| [DD-037](<#dd-037-instance-models-are-one-module-per-java-class>) | Instance models are one module per Java class | 2.1 | Proposed |
| [DD-038](<#dd-038-attribute-values-stay-plain-json-values-until-their-types-read-them>) | Attribute values stay plain JSON values until their types read them | 2.1 | Proposed |
| [DD-039](<#dd-039-one-atlas-json-codec-reads-floats-as-decimals-and-writes-them-with-their-digits>) | One Atlas JSON codec reads floats as decimals and writes them with their digits | 2.1 | Proposed |
| [DD-040](<#dd-040-java-values-are-held-as-the-python-values-closest-to-them>) | Java values are held as the Python values closest to them | 2.1 | Proposed |
| [DD-041](<#dd-041-the-type-system-is-one-module-per-java-type-class-too>) | The type system is one module per Java type class too | 2.1 | Proposed |
| [DD-042](<#dd-042-a-validity-period-without-a-time-zone-is-in-utc>) | A validity period without a time zone is in UTC | 2.1 | Proposed |
| [DD-043](<#dd-043-entities-are-documents-of-one-index-their-attributes-under-qualified-names>) | Entities are documents of one index, their attributes under qualified names | 2.2 | Proposed |
| [DD-044](<#dd-044-a-guid-is-a-random-uuid>) | A GUID is a random UUID | 2.2 | Proposed |
| [DD-045](<#dd-045-unique-values-are-reserved-by-create-only-documents>) | Unique values are reserved by create-only documents | 2.2 | Proposed |
| [DD-046](<#dd-046-a-multi-entity-write-is-all-or-nothing-through-a-journal>) | A multi-entity write is all or nothing, through a journal | 2.2 | Proposed |
| [DD-047](<#dd-047-entities-are-written-conditionally-on-their-elasticsearch-version>) | Entities are written conditionally on their Elasticsearch version | 2.2 | Proposed |
| [DD-048](<#dd-048-a-type-is-in-use-while-the-entity-index-holds-one-of-it>) | A type is in use while the entity index holds one of it | 2.2 | Proposed |
| [DD-049](<#dd-049-attribute-values-are-stored-normalised-a-struct-inline-a-reference-as-a-guid>) | Attribute values are stored normalised; a struct inline, a reference as a GUID | 2.3 | Proposed |
| [DD-050](<#dd-050-relationship-attributes-read-empty-until-relationships-are-stored>) | Relationship attributes read empty until relationships are stored | 2.3 | Superseded by DD |
| [DD-051](<#dd-051-entity-reads-are-tested-on-entities-written-through-the-store-until-24>) | Entity reads are tested on entities written through the store until 2.4 | 2.3 | Proposed |
| [DD-052](<#dd-052-a-request-is-mapped-in-memory-and-written-once-a-lost-race-runs-it-again>) | A request is mapped in memory and written once; a lost race runs it again | 2.4 | Proposed |
| [DD-053](<#dd-053-relationship-attribute-values-are-resolved-but-stored-only-as-legacy-attributes-until-31>) | Relationship attribute values are resolved, but stored only as legacy attributes until 3.1 | 2.4 | Superseded by DD |
| [DD-054](<#dd-054-dynamic-attributes-are-evaluated-in-first-seen-dependency-order>) | Dynamic attributes are evaluated in first-seen dependency order | 2.4 | Proposed |
| [DD-055](<#dd-055-scenarios-name-what-they-create-with-a-per-run-value>) | Scenarios name what they create with a per-run value | 2.4 | Proposed |
| [DD-056](<#dd-056-an-entity-write-also-removes-documents-journaled-like-the-others>) | An entity write also removes documents, journaled like the others | 2.5 | Proposed |
| [DD-057](<#dd-057-entities-referring-to-one-are-found-through-an-indexed-field-of-guids>) | Entities referring to one are found through an indexed field of GUIDs | 2.5 | Proposed |
| [DD-058](<#dd-058-a-stored-reference-stands-for-an-edge-active-for-a-delete-deleted-for-a-purge>) | A stored reference stands for an edge: active for a delete, deleted for a purge | 2.5 | Proposed |
| [DD-059](<#dd-059-the-delete-type-and-its-override-are-server-settings>) | The delete type and its override are server settings | 2.5 | Proposed |
| [DD-060](<#dd-060-the-owned-reference-cascade-moves-from-32-to-25>) | The owned-reference cascade moves from 3.2 to 2.5 | 2.5 | Proposed |
| [DD-061](<#dd-061-relationships-are-documents-of-their-own-index-listed-by-both-ends>) | Relationships are documents of their own index, listed by both ends | 3.1 | Proposed |
| [DD-062](<#dd-062-an-entity-write-also-writes-relationships-all-or-nothing>) | An entity write also writes relationships, all or nothing | 3.1 | Proposed |
| [DD-063](<#dd-063-31-is-split-into-relationship-instances-and-relationship-attributes>) | 3.1 is split into relationship instances and relationship attributes | 3.1 | Proposed |
| [DD-064](<#dd-064-relationship-attribute-values-are-relationships>) | Relationship attribute values are relationships | 3.1 | Proposed |
| [DD-065](<#dd-065-a-relationship-keeps-one-array-index-the-last-writers>) | A relationship keeps one array index, the last writer's | 3.1 | Proposed |
| [DD-066](<#dd-066-relationship-attributes-are-mapped-in-memory-and-written-with-the-entities>) | Relationship attributes are mapped in memory and written with the entities | 3.1 | Proposed |
| [DD-067](<#dd-067-delete-cascades-follow-owned-relationships-from-31b>) | Delete cascades follow owned relationships from 3.1b | 3.1 | Proposed |
| [DD-068](<#dd-068-owned-entities-an-update-drops-are-deleted-through-a-view-of-the-request>) | Owned entities an update drops are deleted through a view of the request | 3.2 | Proposed |
| [DD-069](<#dd-069-a-reference-to-a-deleted-entity-stands-for-a-deleted-edge-when-reviving>) | A reference to a deleted entity stands for a deleted edge when reviving | 3.2 | Proposed |
| [DD-070](<#dd-070-classification-instances-are-documents-of-their-own-index-listed-by-their-entity>) | Classification instances are documents of their own index, listed by their entity | 3.3 | Proposed |
| [DD-071](<#dd-071-an-entity-write-also-writes-classification-instances-all-or-nothing>) | An entity write also writes classification instances, all or nothing | 3.3 | Proposed |
| [DD-072](<#dd-072-the-propagation-defaults-are-atlass-defaults>) | The propagation defaults are Atlas's defaults | 3.3 | Proposed |
| [DD-073](<#dd-073-33-is-split-into-direct-classifications-and-the-bulk-associator>) | 3.3 is split into direct classifications and the bulk associator | 3.3 | Proposed |
| [DD-074](<#dd-074-bulkheaders-moves-to-35>) | `bulk/headers` moves to 3.5 | 3.3 | Proposed |
| [DD-075](<#dd-075-a-propagated-classification-is-listed-by-the-entities-it-reaches>) | A propagated classification is listed by the entities it reaches | 3.4 | Proposed |
| [DD-076](<#dd-076-the-entities-a-classification-reached-are-found-through-an-indexed-field>) | The entities a classification reached are found through an indexed field | 3.4 | Proposed |
| [DD-077](<#dd-077-propagation-runs-within-the-request-until-34b>) | Propagation runs within the request until 3.4b | 3.4 | Proposed |
| [DD-078](<#dd-078-34-is-split-into-propagation-and-propagation-tasks>) | 3.4 is split into propagation and propagation tasks | 3.4 | Proposed |
| [DD-079](<#dd-079-tasks-are-documents-of-their-own-index-written-with-the-change-that-records-them>) | Tasks are documents of their own index, written with the change that records them | 3.4 | Proposed |
| [DD-080](<#dd-080-every-server-process-runs-tasks-each-claimed-with-a-lease>) | Every server process runs tasks, each claimed with a lease | 3.4 | Proposed |
| [DD-081](<#dd-081-tasks-are-enabled-by-a-server-setting-on-by-default>) | Tasks are enabled by a server setting, on by default | 3.4 | Proposed |
| [DD-082](<#dd-082-audit-events-are-documents-of-their-own-index-written-after-the-change>) | Audit events are documents of their own index, written after the change | 3.5 | Proposed |
| [DD-083](<#dd-083-audit-events-keep-atlass-event-keys-and-their-order>) | Audit events keep Atlas's event keys and their order | 3.5 | Proposed |
| [DD-084](<#dd-084-the-entity-writer-tells-a-change-notifier-what-it-changed>) | The entity writer tells a change notifier what it changed | 3.5 | Proposed |
| [DD-085](<#dd-085-classification-events-are-collected-in-the-request-and-recorded-after-its-write>) | Classification events are collected in the request and recorded after its write | 3.5 | Proposed |
| [DD-086](<#dd-086-tag-propagation-records-the-propagations-a-request-added-and-removed>) | Tag propagation records the propagations a request added and removed | 3.5 | Proposed |
| [DD-087](<#dd-087-basic-search-is-split-into-entity-and-classification-search>) | Basic search is split into entity and classification search | 4.1 | Proposed |
| [DD-088](<#dd-088-entity-attributes-are-searched-in-typed-search-fields-named-after-their-defining-type>) | Entity attributes are searched in typed search fields named after their defining type | 4.1 | Proposed |
| [DD-089](<#dd-089-a-search-is-a-query-of-the-entity-documents-ordered-by-creation-when-no-sort-is-given>) | A search is a query of the entity documents, ordered by creation when no sort is given | 4.1 | Proposed |
| [DD-090](<#dd-090-a-classification-search-finds-instances-first-then-the-entities-listing-them>) | A classification search finds instances first, then the entities listing them | 4.1 | Proposed |
| [DD-091](<#dd-091-free-text-is-split-from-quick-search>) | Free text is split from quick search | 4.2 | Proposed |
| [DD-092](<#dd-092-string-search-fields-carry-an-analysed-text-sub-field-searched-with-atlass-weights>) | String search fields carry an analysed text sub-field, searched with Atlas's weights | 4.2 | Proposed |
| [DD-093](<#dd-093-facets-are-aggregations-of-the-searchs-own-query>) | Facets are aggregations of the search's own query | 4.2 | Proposed |
| [DD-094](<#dd-094-suggestions-are-terms-aggregations-of-the-text-sub-fields>) | Suggestions are terms aggregations of the text sub-fields | 4.2 | Proposed |
| [DD-126](<#dd-126-the-webapp-is-a-new-project-not-the-aurelius-app-upgraded-in-place>) | The webapp is a new project, not the Aurelius app upgraded in place | 7.0 | Proposed |
| [DD-127](<#dd-127-signals-replace-the-custom-store-each-slice-owns-its-state>) | Signals replace the custom store; each slice owns its state | 7.0 | Proposed |
| [DD-128](<#dd-128-aurelius-dictionaries-become-xliff-migrated-whole-with-the-json-as-fixture>) | Aurelius dictionaries become XLIFF, migrated whole, with the JSON as fixture | 7.1 | Proposed |
| [DD-129](<#dd-129-google-analytics-and-clickstream-are-dropped-not-ported>) | Google Analytics and clickstream are dropped, not ported | 7.1 | Proposed |
| [DD-130](<#dd-130-the-webapps-config-is-a-typed-appconfig-and-environmentts-is-not-ported>) | The webapp's config is a typed AppConfig, and `environment.ts` is not ported | 7.1 | Proposed |
| [DD-131](<#dd-131-webapp-purity-is-a-checked-gate-not-a-review-convention>) | Webapp purity is a checked gate, not a review convention | 7.0 | Proposed |
| [DD-132](<#dd-132-the-wildcard-fallback-redirects-to-the-destination-not-through-the-root>) | The wildcard fallback redirects to the destination, not through the root | 7.1 | Proposed |
| [DD-133](<#dd-133-operational-telemetry-lands-with-71-the-auth-wiring-stays-with-73>) | Operational telemetry lands with 7.1; the auth wiring stays with 7.3 | 7.1 | Proposed |
| [DD-134](<#dd-134-the-design-system-slice-ports-the-in-use-components-not-the-library>) | The design-system slice ports the in-use components, not the library | 7.2 | Proposed |
| [DD-135](<#dd-135-component-services-dissolve-into-signal-state-nothing-is-ported-as-a-store>) | Component services dissolve into signal state; nothing is ported as a store | 7.2 | Proposed |
| [DD-136](<#dd-136-shared-chrome-strings-are-localisation-units-keyed-by-the-legacy-dictionary-paths>) | Shared chrome strings are localisation units keyed by the legacy dictionary paths | 7.2 | Proposed |
| [DD-137](<#dd-137-the-purity-gate-is-made-executable-over-libsangular>) | The purity gate is made executable over `libs/angular` | 7.2 | Proposed |
| [DD-138](<#dd-138-the-storybook-preview-loads-angularlocalizeinit>) | The Storybook preview loads `@angular/localize/init` | 7.2 | Proposed |
| [DD-139](<#dd-139-the-client-owns-the-base-url-the-proxy-forwards-the-prefix-untouched>) | The client owns the base URL; the proxy forwards the prefix untouched | 7.3 | Proposed |
| [DD-140](<#dd-140-the-rest-client-ports-the-live-surface-the-search-client-is-redesigned-in-74>) | The REST client ports the live surface; the search client is redesigned in 7.4 | 7.3 | Proposed |
| [DD-141](<#dd-141-auth-is-guarded-at-the-app-root-the-bearer-token-is-stated-inert-until-61>) | Auth is guarded at the app root; the bearer token is stated inert until 6.1 | 7.3 | Proposed |
| [DD-142](<#dd-142-the-webapp-e2e-stack-runs-the-real-atlas-server-behind-the-proxy>) | The webapp e2e stack runs the real Atlas server behind the proxy | 7.3 | Proposed |
| [DD-143](<#dd-143-the-landing-page-is-ported-statically-search-affordances-and-shell-chrome-join-the-search-slice>) | The landing page is ported statically; search affordances and Shell chrome join the search slice | 7.5 | Proposed |
| [DD-144](<#dd-144-i18n-ids-carry-no-description-suffix-the-bridge-key-must-equal-the-extracted-id>) | i18n ids carry no description suffix; the bridge key must equal the extracted id | 7.5 | Proposed |
| [DD-145](<#dd-145-the-shell-chrome-is-ported-search-free-the-root-composes-header-and-footer>) | The Shell chrome is ported search-free; the root composes header and footer | 7.11 | Proposed |
| [DD-146](<#dd-146-session-chrome-injects-the-keycloak-js-keycloak-instance-not-keycloak-angulars-keycloakservice>) | Session chrome injects the keycloak-js `Keycloak` instance, not keycloak-angular's `KeycloakService` | 7.11 | Accepted |
| [DD-147](<#dd-147-dev-keycloak-users-carry-default-roles-master-explicitly>) | Dev Keycloak users carry `default-roles-master` explicitly | 7.11 | Accepted |
| [DD-148](<#dd-148-the-aurelius-brand-lands-on-bulma-1-tokens-light-forced-legacy-metrics-pinned>) | The Aurelius brand lands on Bulma 1 tokens, light-forced, legacy metrics pinned | 7.12 | Accepted |
| [DD-149](<#dd-149-critical-css-inlining-is-off-the-zoneless-csr-app-never-swaps-the-print-sheet>) | Critical-CSS inlining is off: the zoneless CSR app never swaps the print sheet | 7.12 | Accepted |
| [DD-150](<#dd-150-the-sticky-footer-is-the-legacy-rule-verbatim-page-content-sits-on-bulmas-grid>) | The sticky footer is the legacy rule verbatim; page content sits on Bulma's grid | 7.12 | Accepted |
| [DD-151](<#dd-151-the-brand-re-emits-bulma-094s-text-ramp-not-just-the-body-metrics>) | The brand re-emits Bulma 0.9.4's text ramp, not just the body metrics | 7.12 | Accepted |
| [DD-152](<#dd-152-the-accent-ramp-primary-stays-bulma-teal-the-accents-take-the-bootstrap-map>) | The accent ramp: primary stays Bulma teal, the accents take the Bootstrap map | — | Proposed |
| [DD-153](<#dd-153-the-mobile-burger-chrome-grey-burger-blended-dropdowns-legacy-logout-anchor>) | The mobile burger chrome: grey burger, blended dropdowns, legacy logout anchor | — | Proposed |
| [DD-154](<#dd-154-the-entity-card-emits-entityclicked-the-caller-navigates>) | The entity card emits `entityClicked`; the caller navigates | — | Proposed |
| [DD-155](<#dd-155-the-select-is-one-field-with-a-searchrequested-output>) | The select is one field with a `searchRequested` output | — | Proposed |
| [DD-156](<#dd-156-the-brand-ships-a-dark-ink-ramp-on-bulmas-dark-hosts>) | The brand ships a dark ink ramp on Bulma's dark hosts | — | Proposed |
| [DD-157](<#dd-157-the-drawer-is-a-new-ui-lib-component-not-a-modal-or-a-dropdown>) | The drawer is a new ui-lib component, not a Modal or a dropdown | 7.14 | Accepted |
| [DD-158](<#dd-158-the-telemetry-switch-stops-exports-immediately-and-starts-them-on-reload>) | The telemetry switch stops exports immediately and starts them on reload | 7.14 | Accepted |
| [DD-159](<#dd-159-the-theme-choice-is-applied-pre-render-shm-01s-light-pin-is-superseded-by-a-light-default>) | The theme choice is applied pre-render; SHM-01's light pin is superseded by a light default | 7.14 | Accepted |
| [DD-160](<#dd-160-settings-are-a-facade-over-one-owner-service-per-category>) | Settings are a facade over one owner service per category | 7.14 | Accepted |
| [DD-161](<#dd-161-settings-are-browser-scoped-localstorage-server-side-persistence-is-the-follow-up-slice>) | Settings are browser-scoped localStorage; server-side persistence is the follow-up slice | 7.14 | Accepted |
| [DD-162](<#dd-162-the-drawer-animates-in-and-out-the-layers-life-is-the-exit-animations>) | The drawer animates in and out; the layer's life is the exit animation's | 7.14 | Accepted |
| [DD-163](<#dd-163-the-drawer-styles-itself-with-fallbacks-bulmas-modal-tokens-are-modal-scoped>) | The drawer styles itself with fallbacks; Bulma's modal tokens are `.modal`-scoped | 7.14 | Accepted |
| [DD-164](<#dd-164-the-appearance-picker-is-the-ui-lib-select-the-select-gains-searchvisible>) | The Appearance picker is the ui-lib Select; the Select gains `searchVisible` | 7.14 | Accepted |
| [DD-165](<#dd-165-about-shows-one-version-the-server-is-not-fetched>) | About shows one version; the server is not fetched | 7.14 | Accepted |
| [DD-166](<#dd-166-the-settings-panel-is-a-routed-overlay-in-the-drawer-aux-outlet>) | The settings panel is a routed overlay in the `drawer` aux outlet | 7.14 | Accepted |
| [DD-167](<#dd-167-settings-drawer-polish-lit-gear-scheme-following-band-browser-default-picker-label-headings>) | Settings-drawer polish: lit gear, scheme-following band, Browser-default picker, `.label` headings | 7.14 | Accepted |
| [DD-168](<#dd-168-the-navbar-follows-the-scheme-the-dark-slate-band>) | The navbar follows the scheme: the dark slate band | 7.14 | Accepted |
| [DD-169](<#dd-169-settings-headings-are-the-controls-accessible-names>) | Settings headings are the controls' accessible names | 7.14 | Accepted |
| [DD-170](<#dd-170-the-active-locale-is-filled-with-the-aurelius-blue>) | The active locale is filled with the Aurelius blue | 7.14 | Accepted |
| [DD-171](<#dd-171-the-alerts-store-groups-by-a-quiet-window>) | The alerts store groups by a quiet window | 7.15 | Accepted |
| [DD-172](<#dd-172-the-apps-errorhandler-chains-alert-then-trace>) | The app's ErrorHandler chains: alert, then trace | 7.15 | Accepted |
| [DD-173](<#dd-173-the-http-reporter-5xx-and-network-failures-on-api>) | The HTTP reporter: 5xx and network failures on /api | 7.15 | Accepted |
| [DD-174](<#dd-174-the-bell-severity-badge-and-ring-one-outlet>) | The bell: severity badge and ring, one outlet | 7.15 | Accepted |
| [DD-175](<#dd-175-alertlist-and-badge-are-ui-lib-presentational-components>) | AlertList and Badge are ui-lib presentational components | 7.15 | Accepted |
| [DD-176](<#dd-176-the-chips-pinned-pair-clear-all-in-the-drawer-head>) | The chip's pinned pair; Clear all in the drawer head | 7.15 | Accepted |
| [DD-177](<#dd-177-the-parallel-tracks-colliding-dddv-ids-renumber-to-the-7x8x-side>) | The parallel tracks' colliding DD/DV ids renumber to the 7.x/8.x side | — | Accepted |
| [DD-178](<#dd-178-the-merge-resolves-the-opentelemetry-version-split-to-the-1451066b1-set>) | The merge resolves the OpenTelemetry version split to the 1.45.1/0.66b1 set | — | Accepted |
| [DD-179](<#dd-179-the-branchs-second-collision-band-renumbers-above-mains-tail>) | The branch's second collision band renumbers above main's tail | — | Accepted |
| [DD-180](<#dd-180--the-inbox-bar-severity-chips-read-tracking-clear-all-in-the-bar>) | The inbox bar: severity chips, read tracking, Clear all in the bar | 7.15 | Accepted |
| [DD-181](<#dd-181--the-drawers-body-is-the-scroll-container>) | The drawer's body is the scroll container | 7.15 | Accepted |
| [DD-182](<#dd-182--the-inbox-bar-is-one-joined-group-severity-coloured-ramp-order>) | The inbox bar is one joined group, severity-coloured, ramp order | 7.15 | Accepted |
| [DD-183](<#dd-183--the-inbox-bar-is-one-height-the-count-badge-is-compacted>) | The inbox bar is one height: the count badge is compacted | 7.15 | Accepted |
| [DD-184](<#dd-184--the-void-chip-an-empty-severity-greys-out>) | The void chip: an empty severity greys out | 7.15 | Accepted |
| [DD-185](<#dd-185--show-all-is-gone-the-bars-shape-never-shifts>) | Show all is gone: the bar's shape never shifts | 7.15 | Accepted |
| [DD-186](<#dd-186--entity-details-arrives-as-a-routed-skeleton-its-data-spine-joins-23>) | Entity details arrives as a routed skeleton; its data spine joins 2.3 | 7.6 | Proposed |
| [DD-187](<#dd-187--the-entity-client-is-built-test-first-against-the-atlas-wire-format>) | The entity client is built test-first against the Atlas wire format | 7.6 | Proposed |
| [DD-188](<#dd-188--one-api-base-the-clients-urls-all-ride-the-api_base_url-token>) | One API base: the client's URLs all ride the API\_BASE\_URL token | 7.6 | Accepted |
| [DD-189](<#dd-189--the-details-chip-is-the-classification-chip-its-sources-project-in>) | The details chip is the classification chip; its sources project in | 7.16 | Proposed |
| [DD-190](<#dd-190--the-type-name-badge-is-extracted-from-entity-card>) | The type-name badge is extracted from entity-card | 7.16 | Proposed |
| [DD-191](<#dd-191--details-navigation-is-a-shell-the-scroll-directive-stays-app-side>) | Details navigation is a shell; the scroll directive stays app-side | 7.16 | Proposed |
| [DD-192](<#dd-192--the-count-bar-is-section-stats-one-component-two-call-sites>) | The count bar is section-stats: one component, two call sites | 7.16 | Proposed |
| [DD-193](<#dd-193--collector-ingest-is-authenticated-in-two-legs-user-jwts-for-browsers-a-shared-token-for-services>) | Collector ingest is authenticated in two legs: user JWTs for browsers, a shared token for services | 7.17 | Proposed |
| [DD-194](<#dd-194--the-collector-stamps-the-verified-user-onto-the-telemetry-enduserid>) | The collector stamps the verified user onto the telemetry: `enduser.id` | 7.17 | Accepted |
| [DD-195](<#dd-195--the-collector-rides-out-keycloaks-boot-bounded-restart-awaited-readiness>) | The collector rides out Keycloak's boot: bounded restart, awaited readiness | 7.17 | Accepted |
| [DD-196](<#dd-196--the-service-leg-graduates-to-per-service-identity-keycloak-client-credentials-jwts-azp-stamped>) | The service leg graduates to per-service identity: Keycloak client-credentials JWTs, azp-stamped | 7.18 | Proposed |
| [DD-197](<#dd-197--the-auxiliary-apis-share-one-foundation-the-otel-and-auth-libs>) | The auxiliary APIs share one foundation: the OTel and auth libs | 8.0 | Proposed |
| [DD-198](<#dd-198--the-8x-ports-are-pandas-free-pydantic-rule-models-plain-row-maps>) | The 8.x ports are pandas-free: pydantic rule models, plain row maps | 8.1 | Proposed |
| [DD-199](<#dd-199--app-unit-tests-clear-the-injected-env-prefix-in-an-autouse-fixture>) | App unit tests clear the injected `.env` prefix in an autouse fixture | 8.1 | Accepted |
| [DD-200](<#dd-200--the-82-proxy-app-injects-its-upstream-http-client-the-e2e-atlas-is-a-canned-file-server>) | The 8.2 proxy app injects its upstream HTTP client; the e2e Atlas is a canned-file server | 8.2 | Accepted |
| [DD-201](<#dd-201--the-83-mock-ships-as-module-data-the-verifier-is-injectable>) | The 8.3 mock ships as module data; the verifier is injectable | 8.3 | Accepted |
| [DD-202](<#dd-202--one-issuer-world-producers-mint-on-the-tls-listener-the-collector-validates-both>) | One issuer world: producers mint on the TLS listener, the collector validates both | 7.18 | Accepted |
| [DD-203](<#dd-203--the-wire-contract-lives-in-a-client-library-the-app-imports-it>) | The wire contract lives in a client library; the app imports it | 8.4 | Accepted |
| [DD-204](<#dd-204--clients-are-async-httpx-with-an-injectable-transport-and-read-no-env>) | Clients are async httpx with an injectable transport, and read no env | 8.4 | Accepted |
| [DD-205](<#dd-205--the-clients-httpxasyncclient-is-provided-externally>) | The client's `httpx.AsyncClient` is provided externally | 8.4 | Accepted |
| [DD-206](<#dd-206--the-lineage-models-upstream-breakers-live-in-the-app-on-pybreakers-calling-seam>) | The lineage-model's upstream breakers live in the app, on pybreaker's `calling()` seam | 8.5 | Accepted |
| [DD-207](<#dd-207--the-lineage-model-app-follows-the-example-apps-providerroute-layout>) | The lineage-model app follows the example app's provider/route layout | — | Proposed |
| [DD-208](<#dd-208--the-lineage-flow-lives-in-the-route-the-chain-class-is-dissolved>) | The lineage flow lives in the route; the chain class is dissolved | — | Proposed |
| [DD-209](<#dd-209--data2model-and-validate-entity-follow-the-example-apps-providerroute-layout>) | data2model and validate-entity follow the example app's provider/route layout | — | Proposed |
| [DD-210](<#dd-210--telemetry-goes-native-the-otel-sdk-replaces-the-logfire-shell>) | Telemetry goes native: the OTel SDK replaces the logfire shell | 8.5 | Proposed |
| [DD-211](<#dd-211--httpx2-replaces-httpx-across-the-http-surface>) | httpx2 replaces httpx across the HTTP surface | 8.5 | Proposed |
| [DD-212](<#dd-212--the-8x-apps-appscenario-test-modules-carry-their-package-name>) | The 8.x apps' app/scenario test modules carry their package name | 8.5 | Accepted |
| [DD-213](<#dd-213--the-lineage-guid-is-a-uuid-on-every-typed-surface>) | The lineage guid is a UUID on every typed surface | 8.5 | Accepted |
| [DD-214](<#dd-214--the-test-suite-review-of-2026-10-24-scopes-the-hardening-increments>) | The test suite review of 2026-10-24 scopes the hardening increments | cross-cutting | Accepted |
| [DD-215](<#dd-215--the-ci-pipeline-drops-the-traceability-check-and-report>) | The CI pipeline drops the traceability check and report; the tools stay as local aids | cross-cutting | Accepted |
| [DD-216](<#dd-216--stacks-own-the-tls-material-they-mount>) | Stacks own the TLS material they mount | cross-cutting | Accepted |
| [DD-217](<#dd-217--the-search-client-lands-on-both-sides-of-the-wire-ahead-of-74>) | The search client lands on both sides of the wire, ahead of 7.4 | cross-cutting | Accepted |
| [DD-226](<#dd-226--the-dev-stacks-restart-windows-are-unbounded>) | The dev stacks' restart windows are unbounded: an attempt budget burns out before Keycloak is up | cross-cutting | Accepted |
| [DD-227](<#dd-227--the-store-es-e2e-suite-is-removed-it-evaluated-the-dev-environment-not-production>) | The store-es e2e suite is removed: it evaluated the dev environment, not production | cross-cutting | Accepted |
| [DD-228](<#dd-228--dev-posture-tests-leave-the-suites-the-sweep-of-dd-223s-rule-applied>) | Six dev-posture e2e tests are removed: they asserted the dev box's deployment state, not shipped behaviour | cross-cutting | Accepted |
| [DD-229](<#dd-229--the-shape-a-tail-overlaps-the-test-graph-shares-its-daemon>) | Shape-A wall-time tuning: docker-build rides the test graph, sonar overlaps Storybook, cache save on miss | cross-cutting | Accepted |
| [DD-230](<#dd-230--parallelism-stays-at-the-default-the-scanner-cache-moves-to-the-pvc>) | Nx parallelism stays at the default (5 regressed); the SonarScanner download cache moves to the PVC; engine scoping measured away | cross-cutting | Accepted |
| [DD-231](<#dd-231--teardown-downs-the-compose-stacks-prune-only-sweeps-corpses>) | CI teardown downs every compose stack: prune only sweeps stopped containers, so the stacks rode through the tail | cross-cutting | Accepted |
| [DD-232](<#dd-232--the-ci-pipeline-is-a-fan-out-dag-the-pool-is-per-pod-emptydir>) | CI splits into validate then {e2e, scan-sonar, chromatic} on a 3-pod pool; the RWO cache PD retires for per-pod emptyDir | cross-cutting | Accepted |
| [DD-233](<#dd-233--the-toolchain-caches-bridge-pod-churn-through-the-cache-server>) | Fan-out pods churn: uv/pre-commit/sonar caches bridge across pods on the cache server (cold-pod tax measured away) | cross-cutting | Accepted |
| [DD-234](<#dd-234--tls-material-is-a-required-setting-the-server-never-serves-plaintext>) | TLS material is a required setting: the server never serves plaintext | 9.2 | Accepted |
| [DD-235](<#dd-235--a-5xx-answer-is-opaque-and-carries-the-trace-id-as-requestid>) | A 5xx answer is opaque and carries the trace id as `requestId` | 9.2 | Accepted |
| [DD-236](<#dd-236--security-response-headers-are-a-pure-asgi-middleware-split-on-api-path>) | Security response headers are a pure-ASGI middleware split on `/api` path | 9.2 | Accepted |
| [DD-237](<#dd-237--index-refresh-moves-from-reads-to-writes>) | Index refresh moves from reads to writes: writes carry `refresh=wait_for`, no read path refreshes | 9.3 | Accepted |
| [DD-238](<#dd-238--the-browser-rate-limit-lives-at-the-nginx-edge-not-in-the-server>) | The browser rate limit lives at the nginx edge, not in the server; private ranges are allowlisted | 9.3 | Accepted |
| [DD-239](<#dd-239--the-edge-exports-spans-on-the-legacy-leg-built-in-the-dev-image-stage>) | The webapp's nginx exports `/api/` spans on the collector's legacy leg; the module builds in the image's dev-stage | 9.4 | Accepted |
| [DD-240](<#dd-240-the-dsl-parser-is-generated-from-atlass-own-grammar>) | The DSL parser is generated from Atlas's own grammar | 4.3 | Proposed |
| [DD-241](<#dd-241-the-parse-tree-is-handed-on-as-typed-immutable-nodes>) | The parse tree is handed on as typed, immutable nodes | 4.3 | Proposed |
| [DD-242](<#dd-242-a-dsl-query-is-composed-into-the-basic-searchs-filter-tree>) | A DSL query is composed into the basic search's filter tree | 4.4 | Proposed |
| [DD-243](<#dd-243-dsl-traversals-and-projections-are-evaluated-in-steps>) | DSL traversals and projections are evaluated in steps | 4.4 | Proposed |
| [DD-244](<#dd-244-saved-searches-wait-for-authentication>) | Saved searches wait for authentication | 4.5 | Accepted |
| [DD-245](<#dd-245-lineage-walks-the-relationships-of-the-process-edges>) | Lineage walks the relationships of the process edges | 5.1 | Proposed |
| [DD-246](<#dd-246-glossary-objects-are-entities-written-through-the-entity-and-relationship-stores>) | Glossary objects are entities written through the entity and relationship stores | 5.2 | Proposed |
| [DD-247](<#dd-247-journal-writes-do-not-wait-for-a-refresh>) | Journal writes do not wait for a refresh | cross-cutting | Proposed |
| [DD-248](<#dd-248-an-entitys-meanings-are-read-from-its-listed-relationships>) | An entity's meanings are read from its listed relationships | 5.2 | Proposed |
| [DD-249](<#dd-249-uploaded-files-are-read-with-python-multipart-openpyxl-and-xlrd>) | Uploaded files are read with python-multipart, openpyxl and xlrd | 5.2 | Proposed |
| [DD-250](<#dd-250-the-server-authenticates-requests-itself-against-the-identity-provider>) | The server authenticates requests itself against the identity provider | 6.1 | Proposed |
| [DD-251](<#dd-251-browser-sessions-are-kept-in-the-servers-memory>) | Browser sessions are kept in the server's memory | 6.1 | Proposed |

### DD-001. Reference is Apache Atlas 2.4.0, and both dashboards are served

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** The behaviour to reproduce is that of the `release-2.4.0` tag of Apache Atlas. Both of its user interfaces are served unchanged at the paths Atlas uses: `dashboardv2` at `/` and `dashboardv3` at `/n/`. End-to-end tests cover `dashboardv3` in depth and `dashboardv2` with a smoke test.

**Reason.** Parity tests need one fixed reference ([ADR 048](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/048-behaviour-is-proven-against-the-reference-before-it-is-accepted/index.md>)), and 2.4.0 is the latest Apache Atlas release. Atlas 2.4.0 serves the classic interface at the root and the newer one under `/n/`, and each links to the other; serving both keeps every bookmark and link working at the cost of one more static build, whereas dropping one would be a visible deviation.

**Alternatives.** Track Atlas `master`: unstable fixtures, no released artefact to compare against. Serve only `dashboardv3` and redirect `/` to `/n/`: one build less, but breaks the switch-back link and existing bookmarks, and would need a deviation entry.

**Consequences.** A move to a later Atlas release is a new entry plus a re-recording of all fixtures. Features used only by `dashboardv2` still need backend support; they are found by its smoke test.

### DD-002. Atlas code lives in aurelius-atlas projects split by layer

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-09

**Decision.** Atlas code is split into workspace projects by layer, all prefixed `aurelius-atlas-` (Python packages `aurelius_atlas_*`): `-model` (data shapes, no I/O), `-typesystem` (type registry and validation), `-store-es` (Elasticsearch access), `-core` (stores and services), `-dsl` (query language), `apps/aurelius-atlas-server` (REST), `apps/aurelius-atlas-dashboard` (UI), `reports/aurelius-atlas-test-report`, plus `dev/elasticsearch` and `dev/atlas-reference`.

**Reason.** Layers that do not do I/O can be unit-tested without infrastructure; the dependency direction (model ← typesystem ← core → store-es; server → core) keeps each increment's change local, and each project follows an existing template recipe. The `aurelius` prefix keeps the organisation's naming convention.

**Alternatives.** One large package mirroring the Java module tree: simpler imports, but every change touches the same project and nothing can be tested in isolation. A package per Java module (`intg`, `repository`, `webapp`): mirrors history rather than the dependency structure we want.

**Consequences.** Projects are created by the increment that first needs them, not up front.

### DD-003. Template projects are renamed to the aurelius-atlas prefix

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-17

**Decision.** All workspace projects inherited from the template carry the `aurelius-atlas-` prefix (directories, Nx names, uv/npm package names, Python import packages, env-var prefixes, Sonar keys, compose project and network names, Grafana dashboards). The org handle `aureliusenterprise`, the npm scope `@aurelius`, the Keycloak client/realm ids (`aurelius`, `master`), and the DB name (`aurelius`) are identities of the organisation/Keycloak and stay unchanged.

**Reason.** DD-002 fixes the `aurelius-atlas-` prefix for the Atlas projects; renaming the template examples now, while they are the only content, avoids two naming generations in one repo and the churn of renaming them piecemeal once Atlas code lands beside them.

**Alternatives.** Rename only new Atlas projects: leaves `aurelius-*` and `aurelius-atlas-*` side by side, which reads as two projects with different ownership. Keep the template names entirely: makes the eventual atlas-vs-template distinction implicit rather than visible in the project graph.

**Consequences.** Docker image names change (`ghcr.io/aureliusenterprise/aurelius-atlas-*`); Sonar projects, Chromatic, and any external CI references must be created/renamed to match. `.env.enc` files were re-encrypted with the new prefixed keys. Old locally built images are stale and should be pruned (`docker image prune` / rebuild via `nx e2e`).

### DD-004. The SPA keeps tokens in memory and renews them silently

- **Status:** Accepted
- **Increment:** 0.1
- **Date:** 2026-10-17

**Decision.** The Angular SPA uses Keycloak's default in-memory token store (`tokenStore: "default"` in `provideKeycloak`, `apps/aurelius-atlas-frontend-example/src/app/app.config.ts`) with `onLoad: "check-sso"` and a silent-SSO redirect (`/silent-check-sso.html`). Access and refresh tokens never touch `localStorage` or any other persistent browser storage.

**Reason.** `localStorage` is readable by any script that achieves XSS on the origin, and is also exposed to browser extensions with host permissions; a stolen refresh token there is a durable session hijack. With the in-memory store, injected script can read the current access token but the attacker's code dies with the page, and a reload forces a fresh authentication check against Keycloak rather than replaying stored secrets.

**Alternatives.** `tokenStore: "sessionStorage"`: survives reload in the tab, but every XSS or extension read is still one `getItem` away — same theft surface, no meaningful gain. `tokenStore: "localStorage"`: survives tab close; strongest theft value, rejected. A confidential client with a BFF holding tokens server-side: the right answer at scale, deferred as its own increment — it changes the auth topology (new service, cookie session) rather than a setting.

**Consequences.** A page reload re-mints tokens via silent SSO; the user sees no login unless the Keycloak SSO session itself has ended. Silent SSO relies on a third-party-cookie-acceptable (or same-site) Keycloak deployment: where browsers block the framing cookie, `check-sso` degrades to a not-signed-in state and the app falls back to a full redirect login (`login()`), which still works. If per-tab token durability becomes a product requirement, supersede this entry by adding the BFF — not by moving the tokens to storage.

### DD-005. The store uses the official async Elasticsearch client

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-store-es` talks to Elasticsearch through `AsyncElasticsearch` from the official `elasticsearch` Python client, version 9.5 or later within major 9, matching the 9.5 server (`dhi.io/elasticsearch:9.5-debian13`; minor upgrades are deliberate, patch releases follow the tag). A store instance owns exactly one client, opened and closed with the store (`async with`).

**Reason.** The server is FastAPI and asynchronous; a blocking client would tie up the event loop or need a thread pool. The official client tracks the server's API and versioning, ships typed request helpers, and includes the query DSL module that search (4.x) will need.

**Alternatives.** `httpx` against the REST API directly: no extra dependency, but every API, retry and error type would be rebuilt by hand. `opensearch-py`: a different server; ADR 047 names Elasticsearch. One client per request: simple, but loses connection pooling.

**Consequences.** The client's major version moves with the server's (STO-04 guards it). Connection pooling and retries are the client's; tuning them is part of 6.4.

### DD-006. Development and tests run Elasticsearch with security on

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `dev/elasticsearch` and the test fixture run with `xpack.security` enabled: TLS on the HTTP layer with a certificate from the workspace CA (dev) or an ephemeral CA (tests), and basic authentication for the built-in `elastic` user. The store library has no option to skip certificate verification.

**Reason.** It is the posture production needs, and the one `dev/postgres` already has; a store that only ever ran without security would meet TLS and authentication for the first time in production.

**Alternatives.** Security disabled in development: faster start-up and simpler `curl`, but a different code path (plain HTTP, no credentials) from production, and a verification switch in the library that someone eventually leaves off.

**Consequences.** Dev tools need the CA file and the password (`curl --cacert dev/elasticsearch/certs/ca.pem -u elastic:…`). A dedicated application user with least privilege replaces `elastic` when authorization arrives (6.2).

### DD-007. The Elasticsearch test fixture ships with the store library

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The testcontainers helper that starts a TLS-enabled Elasticsearch lives in `aurelius_atlas_store_es.testing`, behind the library's `testing` extra, next to the code it serves.

**Reason.** Every later project with a store (`-core`, the server, the parity harness) needs the same container; the library that defines the settings is the one that knows how to build them for a test server, and keeping both together means a settings change cannot break the fixture unnoticed.

**Alternatives.** `aurelius-atlas-sdk.testing`, where the Postgres helper lives: would make the generic SDK depend on Elasticsearch. A copy per project: drifts.

**Consequences.** Test-only dependencies (`testcontainers`, `trustme`) stay out of the runtime install; consuming projects add `aurelius-atlas-store-es[testing]` to their dev dependencies.

### DD-008. A yellow cluster is healthy

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** The store's health check reports up for cluster status green or yellow and down for red (STO-05).

**Reason.** Yellow means every primary shard is assigned and all data is readable and writable; only replicas are missing. A single-node cluster, the development and small-installation case ([ADR 006](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/006-the-whole-system-runs-on-one-machine/index.md>)), is yellow as soon as an index has a replica. Reporting it down would make every single-node deployment permanently unready.

**Alternatives.** Green only: correct for multi-node clusters, unusable for single-node ones unless every index is created with zero replicas. A configurable threshold: one more setting nobody sets.

**Consequences.** Lost redundancy is not visible as a health failure; it is visible in the cluster metrics (ESD-06) and should be alerted on there.

### DD-009. Traceability is checked from collected markers, not from a test run

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace check` runs `pytest --collect-only` over the unit and end-to-end tests of every Atlas project and reads the `covers` markers from the collected items. Whether the naming tests pass is the test job's concern, not the check's.

**Reason.** CI runs `nx affected -t test e2e`, so the results of one run contain only the affected projects' tests; a check over them would report every unaffected function as uncovered (TRC-10). Collection imports the tests but starts no containers, so it is cheap enough to run on every change.

**Alternatives.** Merge the trace files of the run with those of the last run on `main`: needs artifact plumbing between workflows and still goes stale when a run on `main` fails. Run every test on every change: correct, but turns a one-minute check into the full end-to-end suite. Parse the test sources with `ast`: misses markers applied through `pytestmark`, classes and parametrisation.

**Consequences.** A test module that fails to import fails the check, which is the right answer: its markers are unknown. A test that names a function but is skipped still counts as naming it; the report shows it as skipped.

### DD-010. The traceability check covers Atlas code from increment 0.2 on

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** R1 applies to the public functions, methods and properties of every uv workspace member that the configuration does not exclude; the template projects (examples, SDK, reports) are excluded, and so are `testing` subpackages, which are test infrastructure. R2 applies to the rules of every specification from increment 0.2 on. The configuration is the `[tool.aurelius-atlas-trace]` table of the root `pyproject.toml`.

**Reason.** Template code is removed or replaced by the conversion (0.5 removes the examples), so markers on it would be written to be deleted. Excluding instead of listing makes a new Atlas project checked by default. Increment 0.1's rules (ADO-01 to ADO-03) describe the adoption of the template and were verified when it merged; 0.2 is the first increment with code, and its manual checks of ESD-01 to ESD-06 are replaced by tests in this increment.

**Alternatives.** Check every workspace member: retrofits markers onto code about to be deleted. List the Atlas projects explicitly: a new project is silently unchecked until someone adds it.

**Consequences.** A project that leaves the template set (the SDK, if it is kept) is removed from the exclusion list and gets its markers in the same change.

### DD-011. The test report is generated from JUnit, coverage and trace files

- **Status:** Proposed
- **Increment:** 0.3
- **Date:** 2026-10-17

**Decision.** `aurelius-atlas-trace report` turns JUnit XML (`pytest --junitxml`), Cobertura XML (`pytest-cov`) and the plugin's trace JSON into one static HTML page and a Markdown summary. CI uploads the page as the `test-report` artifact and appends the summary to the run page.

**Reason.** ADR 045's ladder: the input formats are the ecosystem's own, and no framework or community tool joins test results to specification rules and to a function inventory, which is the view ADR 049 R3 asks for. The generator is a few hundred lines with the standard library only.

**Alternatives.** Allure Report: a polished viewer, but it needs its Java CLI, and the per-rule and per-function gap view would still be ours to build as labels and post-processing. `pytest-html`: one page of test results, nothing about rules or functions. SonarCloud: shows coverage, not traceability.

**Consequences.** The page is an artifact of the CI run, not a published site; 0.4 adds the parity results to it. If a later need (history, trends) outgrows a static page, a viewer is chosen then.

### DD-012. Parity scenarios are YAML files run as parametrised pytest tests

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** A scenario is a `*.scenario.yaml` file in the stage shape of Tavern (`request`, `response`, `save`), validated with pydantic. A project's test module turns a directory of them into one parametrised test, `load_scenarios(directory)`, whose body is `await run_scenario(scenario, client)`; the project's fixture decides whether `client` talks to the application in-process (`httpx.ASGITransport`) or over HTTP to a running server.

**Reason.** ADR 045's ladder: the request/response/save stage is the community's shape for declarative API tests, so reviewers who know Tavern read our scenarios at once. Running scenarios as ordinary pytest parameters puts them in JUnit, in the trace file and under `covers` (SCN-04) with public pytest API only.

**Alternatives.** Tavern itself: speaks HTTP through `requests` only, so the in-process unit level is lost, and the exact comparison, volatile paths and deviations (DD-013) would be hooks around it. A custom collector for `*.scenario.yaml`: shorter test modules, but it needs pytest's private fixture API to give the items a client. Schemathesis: generates requests from an OpenAPI document, which Atlas 2.4.0 does not ship and which states types, not Atlas's answers.

**Consequences.** Every project with scenarios has one small test module and a `client` fixture. The scenario format is ours to keep stable; it is versioned by its rules SCN-01 to SCN-03.

### DD-013. A scenario response is compared exactly, except at declared paths

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The expected body must equal the actual body: the same keys, arrays in the same order, booleans and null distinct from numbers. Only `volatile` paths (generated GUIDs, timestamps) skip the value, and only `deviations` entries change the expectation, each naming its `DV-NN`.

**Reason.** The dashboard and existing clients read fields the scenarios might not think of; an extra, missing or `null` field is a visible difference ([ADR 046](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). Atlas serialises its models with Jackson `NON_NULL` inclusion, so "absent" and `null` differ there and must differ here.

**Alternatives.** Subset matching: short scenarios, but an extra or misnamed field passes. Snapshot files written from our own responses: exact, but the expectation would come from the implementation, not from Atlas (ADR 052 R1).

**Consequences.** Expectations for large responses are long; scenarios borrow Atlas's own test fixtures for request bodies to keep writing them cheap. Arrays whose order Atlas does not define get an explicit order-insensitive option when the first increment needs one.

### DD-014. Scenario facts reach the report as test properties

- **Status:** Proposed
- **Increment:** 0.4
- **Date:** 2026-10-17

**Decision.** The parity plugin adds each scenario's endpoints and deviation ids to the test item's `user_properties` at collection. The trace plugin writes every test's properties to the trace file, so `check` (unknown deviations) and `report` (one row per endpoint) read them from the collection they already do.

**Reason.** `user_properties` is pytest's own channel for facts about a test, and JUnit carries it too. Reading it at collection keeps the report's rule of DD-009: an endpoint whose scenarios did not run in this change is *not run*, not missing.

**Alternatives.** A separate `--parity-json` file: a second format next to the trace file for the same tests. Make the trace library know scenarios: couples the traceability tool to one kind of test.

**Consequences.** The trace file format gains a `properties` field per test; readers of version 1 files without it see no properties. Property names are prefixed with the plugin that sets them (`parity.`).

### DD-015. The server is a FastAPI application with one router per Atlas resource

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-server` is a FastAPI application built like the template's example service (settings, uvicorn entry point, logfire, hardened image), with one router module per Atlas REST resource class (`AdminResource` → `routes/admin.py`, later `EntityREST` → `routes/entity.py`). Atlas errors are raised as `AtlasError` and turned into the Atlas error body by one exception handler, as `AtlasBaseExceptionMapper` does; JSON goes out as `application/json; charset=UTF-8`.

**Reason.** ADR 045's ladder: FastAPI and the example's wiring are the workspace's convention, already gated, observed and packaged. Mirroring the Java resource classes keeps the Java map one row per class and lets a reviewer put a router next to its Java resource.

**Alternatives.** Starlette without FastAPI: no validation or OpenAPI for the request models later increments need. Routers per URL prefix rather than per Java class: `admin` would still be one, but `/v2/entity` and `/v2/entity/bulk` belong to one Java class and would split.

**Consequences.** The example service is no longer the only FastAPI app; it stays until the plan is done (DD-019). Later increments add routers and error codes; the error handler and media type stay.

### DD-016. The server does not start without its store

- **Status:** Proposed
- **Increment:** 0.5
- **Date:** 2026-10-17

**Decision.** The server opens the Elasticsearch store in its start-up and stops with an error when the store cannot be opened (unreachable, rejected, or not Elasticsearch 9). Once running, `readiness` reports the store's health on every call, and `liveness` and `status` do not depend on it.

**Reason.** The store is the only system of record ([ADR 047](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)); a server without it cannot answer anything but the admin endpoints. Failing at start-up shows a wrong setting at once ([ADR 018](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)) and lets an orchestrator restart the container, while readiness covers a store that goes away later.

**Alternatives.** Start without the store and retry in the background: a misconfigured server would run and only its readiness would say so. Make liveness depend on the store: an outage of Elasticsearch would make an orchestrator restart every server, which does not help.

**Consequences.** Start-up order matters: `nx serve` and the end-to-end tests start the dev store first.

### DD-017. The dashboards are vendored unchanged and built with dart-sass on Node 24

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** `apps/aurelius-atlas-dashboard/dashboardv2` and `dashboardv3` are copies of the `release-2.4.0` tag, byte for byte, with Atlas's `LICENSE` and `NOTICE`. Every change is a patch listed in `PATCHES.md` and made in its own commit. The first patch replaces `node-sass` with `sass` (dart-sass) in both `gruntfile.js` files and `package.json` files. Both dashboards are built with `grunt build-minify`, as Atlas's Maven build does, in the hardened Node 24 image; only the built files leave the build. The workspace's formatters, linters and hooks skip the vendored directories.

**Reason.** DD-001 asks for the dashboards unchanged; a vendored copy lets a reviewer prove that with a diff against the tag. `node-sass` 9 is a native module with builds for Node 16 to 20 only, and Node 20 is past its end of life; dart-sass is pure JavaScript, the maintained Sass compiler, and `grunt-sass` supports it. A trial build on Node 24 gave the same files as Atlas's toolchain on Node 20, with identical JavaScript; only the two compiled stylesheets differ.

**Alternatives.** Build unchanged on Node 20: no patch, but an unsupported Node and a native compile in every build. Download the tag at build time and apply patch files: a smaller repository, but the source the build uses is not in review. Commit the built files: no legacy toolchain at all, but the shipped files cannot be reviewed or rebuilt.

**Consequences.** The vendored `package-lock.json` files keep their 2020-era dependencies; they only run inside the build container and are not part of the server image, so Dependabot does not watch them. Moving to another Atlas release replaces both directories and re-applies `PATCHES.md`.

### DD-018. The server serves the dashboards from the API's origin

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** The server mounts the built `dashboardv3` at `/n/` and `dashboardv2` at `/` as static files, after the API routes, when `AURELIUS_ATLAS_SERVER_DASHBOARD_DIR` names their directory. The server image contains the built dashboards and sets that setting.

**Reason.** The dashboards call `api/atlas/...` with relative URLs and rely on the session cookie of the same origin, as in Atlas's web application. Serving them from the server keeps that without a proxy or cross-origin configuration, and one image is the whole product.

**Alternatives.** A separate static file server or the template's Angular serving: a second container and a proxy to keep one origin. Serving through a CDN: possible later in front of the server; nothing here prevents it.

**Consequences.** API paths must never collide with dashboard files; the API is matched first. Unit tests build their settings without the environment and serve no dashboards unless a test sets the directory; `nx serve` builds the dashboards first and its `.env` points at `dist/`.

### DD-019. The template examples stay until the plan is done

- **Status:** Proposed
- **Increment:** 0.6
- **Date:** 2026-10-17

**Decision.** The removal of the template's examples, planned as increment 0.7, moves to a to-do after 6.4. Until then, the FastAPI example service, the Angular example screen and its libraries, `aurelius-atlas-example`, `aurelius-atlas-sdk` and `dev/postgres` stay in the workspace. They remain the named deviation of ADR 050.

**Reason.** The project's second phase needs these components again. Removing them now and restoring them from the template later would cost more than keeping them.

**Alternatives.** Remove them now, as ADR 050 plans once the server and the dashboards replace them: this fulfils ADR 050's R1 sooner, but the components would have to be restored for the second phase.

**Consequences.** CI keeps building, testing and scanning the examples. 1.1 follows 0.6 directly. The to-do in the roadmap records the scope already agreed for the removal: everything the catalogue does not use, apart from `dev/keycloak`.

### DD-020. Typedef models are Pydantic models that read and write Atlas's JSON

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** Each Atlas typedef class is a Pydantic model in `aurelius_atlas_model.typedef` with snake\_case attributes and the Java getter names as aliases. `model_validate` reads a request body and `to_json` writes a response body: aliases, null fields left out, empty collections kept. Unknown fields are ignored. The Java setters' normalisations run as `_`-prefixed validators, so they apply when a body is read and when a model is built in code, as the Java constructors and setters do.

**Reason.** Pydantic is already the workspace's modelling library (settings, store) and FastAPI reads and writes it natively, so 1.6 needs no mapping layer. Atlas writes with Jackson `NON_NULL`, which is Pydantic's `exclude_none`; empty collections stay because Jackson keeps them (DD-013 compares exactly).

**Alternatives.** Dataclasses with a hand-written JSON codec: no dependency, but every rule of TDM-01 to TDM-15 would be custom code. Generating models from Atlas's JSON schema: Atlas publishes none, and the normalisations live in Java setters a schema cannot express.

**Consequences.** Response bodies must be written with `to_json` (or its `exclude_none`, `by_alias` dump), never with FastAPI's default response model serialisation. Later model packages (entities in 2.1) follow the same pattern.

### DD-021. Set-valued fields keep each name once, in first-seen order

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `superTypes`, `subTypes` and `entityTypes` are lists without duplicates, kept in the order the names were first given.

**Reason.** Java holds them in a `HashSet` and writes them in hash order, which Atlas does not define and no client can rely on. A Python `set` would make our order vary from run to run; first-seen order is stable and keeps what the client sent.

**Alternatives.** Reproduce Java's `HashSet` iteration order: possible from `String.hashCode` and the table size, but it would copy an accident of the implementation. Sorted order: stable, but reorders what clients send.

**Consequences.** The JSON order of these arrays can differ from Atlas's. Parity scenarios compare them without order, through the option DD-013 foresees, which 1.6 adds with the first scenario that needs it.

### DD-022. Typedef timestamps are aware datetimes, written as epoch milliseconds

- **Status:** Proposed
- **Increment:** 1.1
- **Date:** 2026-10-17

**Decision.** `createTime` and `updateTime` are timezone-aware UTC `datetime`s. They are written as integer milliseconds since the epoch and read from a number, a string of digits or an ISO-8601 date-time string.

**Reason.** Atlas's REST mapper has no date serialiser, so Jackson writes `java.util.Date` as epoch milliseconds and its `StdDateFormat` reads numbers, digit strings and ISO-8601. Pydantic would read a bare integer as seconds or milliseconds depending on its size, so the conversion is explicit.

**Alternatives.** Keep the raw integer: exact, but every caller would convert. Write ISO-8601 strings: readable, but a visible difference from Atlas.

**Consequences.** Jackson's RFC 1123 form (`Tue, 17 Oct 2026 10:00:00 GMT`) is not read. No Atlas client is known to send it; if one does, it becomes a deviation.

### DD-023. Atlas errors live in the model library

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `AtlasErrorCode` and `AtlasError` move from `aurelius_atlas_server.errors` to `aurelius_atlas_model.errors`. Each code keeps Atlas's HTTP status, error code and message template. The server keeps the error handler and the response class and imports the errors from there.

**Reason.** The type system (1.2) and the stores raise Atlas errors, and they may not depend on the server (DD-002: model ← typesystem ← core; server → core). In Java, too, `AtlasErrorCode` sits in `intg`, below everything else.

**Alternatives.** A separate errors library: one more project for two classes. Each layer with its own exception, mapped in the server: the mapping would repeat Atlas's error table.

**Consequences.** New error codes are added to `aurelius_atlas_model.errors` as each increment needs them, copied from `AtlasErrorCode`.

### DD-024. The registry is updated on a transient copy under a re-entrant lock

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** `TypeRegistry.lock_for_update(timeout)` returns a `TransientTypeRegistry` built from the registry's definitions, under a re-entrant `threading.RLock`. Changes resolve every type on the copy; `release(transient, commit=...)` swaps the copy's types into the registry or drops them. A context manager wraps the pair.

**Reason.** It is Atlas's `TypeRegistryUpdateSynchronizer`: readers never see a half-resolved registry, and a failed change leaves the registry as it was (TRG-05, TRG-09). A thread lock also protects FastAPI's thread-pool handlers; async handlers hold it only around synchronous code.

**Alternatives.** An `asyncio.Lock`: does not protect code run in threads. Copy-on-write without a lock: two concurrent updates would each start from the same registry and one would be lost.

**Consequences.** The lock is per process. Several server processes keep their registries in step through the store (1.4).

### DD-025. The type system ports the definition side only

- **Status:** Proposed
- **Increment:** 1.2
- **Date:** 2026-10-17

**Decision.** The ported types resolve definitions: names, attribute types, cardinalities, constraints and later the hierarchies (1.3). Their value side (`isValidValue`, `getNormalizedValue`, `validateValue`, `createDefaultValue`, `areEqualValues`) is ported with entity validation in 2.1. Their JanusGraph side (vertex property names, unique property names, index field names, index-query escaping) is not ported.

**Reason.** Types REST (1.6) needs only the definition side; values first matter for entities (2.1), which is where Atlas's tests for them can be run. The JanusGraph names have no meaning in Elasticsearch: the index mapping is designed in 2.2.

**Alternatives.** Port each class whole: one increment several times the size limit, with value code untested by any endpoint until 2.x.

**Consequences.** The type classes grow in 2.1. Atlas behaviour that depends on vertex property names is designed again for Elasticsearch in 2.2 and recorded there.

### DD-026. Dynamic attributes and search lookups wait for their increments

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** The entity type's dynamic attributes (`dynAttribute:` templates, their parsing and evaluation order) are ported with entity writes in 2.4. The root entity type's lookup of business attributes for search is ported with basic search in 4.1. Both resolve nothing a type definition is checked against.

**Reason.** They are used only when entities are written or searched, and can only be tested there; porting them now would leave them untested by any endpoint until then (as DD-025 argues for values).

**Alternatives.** Port them with the rest of `AtlasEntityType` now: a larger increment whose extra code no rule of 1.3 can exercise.

**Consequences.** 2.4 adds the template parsing to `EntityType`; 4.1 adds the lookup to the root type.

### DD-027. Derived type sets keep first-seen order

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** All super types are listed in the order the depth-first walk of the super types first reaches them; sub types and relationship attributes in the order the registry resolves its types, which is the order the definitions were added in.

**Reason.** Java keeps them in `HashSet`s and `HashMap`s, whose order Atlas does not define; first-seen order is stable, as for the definitions' own sets (DD-021). Where the order picks a winner, as for inherited relationship attributes, Java's winner is equally arbitrary.

**Alternatives.** Sort them by name: stable too, but unrelated to how the hierarchy was declared.

**Consequences.** `subTypes` in responses may be ordered differently from Atlas's; parity scenarios compare them without order (DD-021, from 1.6).

### DD-028. The type definitions are one Elasticsearch document

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** All stored type definitions are one document, `typedefs`, in the index `aurelius-atlas-typedefs` (through an alias, so a reindex can swap it). The document holds the definitions in their stored form (TDS-05, TDS-06), grouped by kind as in `AtlasTypesDef`. Every change replaces the whole document, guarded by `if_seq_no` and `if_primary_term`.

**Reason.** Atlas changes several definitions in one graph transaction: `createTypesDef` stores all of a request or none (TDS-10). Elasticsearch has no transaction across documents, but writes one document atomically, so one document makes every typedef change atomic and its sequence number a single version of all types (DD-029). The registry, not Elasticsearch, answers every query over types; the document is read whole at start-up and on change. Atlas's built-in models with all patches are about 1 MB of JSON, well inside Elasticsearch's limits.

**Alternatives.** One document per definition, keyed by name: queryable, and a create can use `op_type=create` for uniqueness, but a request touching several definitions needs a hand-written rollback when one write fails, and other processes see half a change. A changes log of operations, replayed at start-up: atomic per entry, but every process replays the whole history and compaction is extra work.

**Consequences.** The document's size grows with the number of types; a deployment with tens of thousands of custom types would revisit this. Type changes are serialised across the cluster, as Atlas serialises them with its update lock.

### DD-029. Server processes share the type definitions through the document's version

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** Each process remembers the `_seq_no` and `_primary_term` of the `typedefs` document its registry was built from. Before a type change it reloads when the stored document is newer; it then writes conditionally on what it read. A conflict means another process changed types first: the process reloads, applies the change again on the new definitions, and gives up with `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` after a second conflict. Readers reload when the document changed, checked at most every `AURELIUS_ATLAS_SERVER_TYPEDEF_REFRESH_SECONDS` (default 5).

**Reason.** Atlas runs one active server and keeps its registry in memory (DD-024 is per process). Several processes behind a load balancer must not lose each other's changes, and a change must reach the others without a restart. Optimistic concurrency on one document gives both with one cheap `GET` of the document's version.

**Alternatives.** A lock document: needs expiry and recovery when its holder dies. Change notification through a message bus: a component the system does not have (ADR 050).

**Consequences.** For up to the refresh interval, a process may answer from older types than another; a type change is visible at once only on the process that made it. 6.4 measures whether the interval needs tuning.

### DD-030. The store asks the entity store whether a type is in use

- **Status:** Proposed
- **Increment:** 1.4
- **Date:** 2026-10-18

**Decision.** The typedef store takes a `TypeUsage` callback that answers whether entities, classifications or relationships of a type exist; deleting a type that is in use fails with `TYPE_HAS_REFERENCES`. Until the entity store exists (2.2) the callback answers "not in use".

**Reason.** Atlas checks `typeHasInstanceVertex` before deleting a type. The instances live in the entity store, which the typedef store must not depend on; a callback keeps the dependency pointing from core's entity store to the typedef store.

**Alternatives.** Query the entity index from the typedef store: couples it to an index that does not exist yet.

**Consequences.** 2.2 passes its own check when it builds the stores.

### DD-031. The patch records live in the typedef document

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** The `typedefs` document of DD-028 holds, next to `typesDef`, a list `patches` of `AtlasPatch` records: one per typedef patch id, with its description, type, action, status and times. A patch's record is written in the same document write as the type change it makes.

**Reason.** Atlas keeps patch records as graph vertices and commits them after the type change, so a crash between the two applies a patch twice, which the `typeVersion` check mostly hides. One document makes the change and its record atomic, and gives both the single version of DD-029: a process that loses a race reloads the records with the types, and sees the patch as already applied (MDL-15).

**Alternatives.** A second document, or an index of patch records: queryable by `admin/patches`, but two writes per patch, and a race between processes needs its own conditional write.

**Consequences.** `admin/patches` (2.2) reads the records from the document. The Java patches of 2.2, which change entities rather than types, may keep their records elsewhere; 2.2 decides.

### DD-032. The built-in models are vendored unchanged and read from a directory

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** `addons/models` of Apache Atlas `release-2.4.0` is copied byte for byte into the package `aurelius_atlas_core.models`, and kept out of the formatting hooks. The server loads models from `AURELIUS_ATLAS_SERVER_MODELS_DIR`, which defaults to that package directory.

**Reason.** Atlas reads its models from `$ATLAS_HOME/models`, so operators add their own model files and patches there; a directory setting keeps that. Unchanged copies let a reviewer prove them unchanged with a diff against the tag, as for the dashboards (DD-017), and ship in the wheel without a build step. The line endings are kept too: one patch file has CRLF, so the directory is `-text` in `.gitattributes`.

**Alternatives.** Converting the models to Python data: no diff against Atlas, and no way to add models without a release. Reading them from a checkout of Atlas at build time: the build would depend on a second repository.

**Consequences.** A newer Atlas version's models are a new copy and a check of the new patches against the nine actions.

### DD-033. Start-up loading is one change per model file and per patch

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** Each model file and each patch is one change of the typedef store (DD-029): what to create, update or patch is decided inside the change, on the definitions and patch records just read, and decided again when a conditional write loses to another process.

**Reason.** Atlas loads models only on its one active server. Here every process starts the same way, possibly at the same moment; deciding inside the change makes a second process see the first one's types and records, so it creates, updates and patches nothing twice. One change per file and per patch keeps Atlas's isolation: a failing file or patch leaves the others applied (MDL-04, MDL-06).

**Alternatives.** All files and patches in one change: one write, but a failure would need the transient registry to roll back part of a change. A lock document held while loading: needs expiry when its holder dies (as in DD-029).

**Consequences.** The first start against an empty store writes the document once per model file and patch, a few hundred writes of the whole document; later starts write nothing unless a model or patch is new. Two processes starting together may each retry once per change.

### DD-034. Lists of type definitions are sorted by name

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** `GET /v2/types/typedefs` and `GET /v2/types/typedefs/headers` list the definitions of each kind sorted by name, compared as Java's `String.compareTo`.

**Reason.** Atlas lists them in the iteration order of the `ConcurrentHashMap`s of its registry: deterministic, but a function of Java's string hashes and the maps' resize history, which no client can rely on and no scenario can state without computing it. A sorted list is stable across restarts, processes and updates, which the order of the stored document is not: an update moves a definition to its end.

**Alternatives.** The order of the stored document: changes with every update. Emulating Java's hash order: costly, and still not something a client could use.

**Consequences.** DV-09. A scenario that lists several definitions of a kind states them sorted by name.

### DD-035. Type scenarios create what they read and delete it at their end

- **Status:** Proposed
- **Increment:** 1.6
- **Date:** 2026-10-18

**Decision.** Each types scenario creates the definitions it needs, all named `scenario_…`, and deletes them in its last stage. Before the server e2e runs its scenarios, it deletes any `scenario_…` definition left in the store by an earlier run that stopped half-way.

**Reason.** The in-process scenarios start each from an empty store, but the e2e runs them all against one server on the persistent dev store, which `nx serve` uses too. Self-contained scenarios pass on both, in any order, and a run never touches a developer's own types.

**Alternatives.** Deleting the typedef index before the e2e: also deletes the developer's types and makes the server load the models again. A separate index per e2e run: needs an index-name setting that nothing else needs.

**Consequences.** Scenario names must be unique across scenarios; a scenario's expectations cannot depend on types another scenario creates.

### DD-036. Start-up loading tries a raced change again

- **Status:** Proposed
- **Increment:** 1.6 (a fix to 1.5's MDL-15)
- **Date:** 2026-10-19

**Decision.** When the typedef store gives up on a model file or patch with `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` (two lost conditional writes, DD-029), the model loader makes the change again, up to ten times, before it treats the file as failed or the patch as `FAILED`. The REST endpoints keep DD-029's single retry.

**Reason.** DD-033 assumed a process starting next to another loses at most once per change. CI showed otherwise: two processes write a few hundred changes in near lockstep, and between one's reload and its retry the other may write its next file, so it loses twice and skipped a model file. Every lost race is another process's write, so trying again always makes progress, and a file or patch is never skipped for a race.

**Alternatives.** More retries in the store itself: also lengthens a REST request's wait under contention, where Atlas answers `FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK` at once. No limit: a store that never stops changing would hang start-up.

**Consequences.** DD-033's "may each retry once per change" becomes "until it wins, up to ten times". A process that loses ten times in a row still reports the file or patch as failed, as Atlas does on a lock failure.

### DD-037. Instance models are one module per Java class

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-20

**Decision.** The entity models live in the package `aurelius_atlas_model.instance`, one module per Java class, nested classes and enums included (`entity`, `entity_status`, `entity_with_ext_info`, …). The package re-exports every model. The JSON conventions all models share (`AtlasModel`, the timestamp, Java boolean, int and set types) move from `typedef` to `aurelius_atlas_model.base`; `typedef` imports them from there.

**Reason.** Atlas organises its models as one class per file; a reader who knows a Java class finds its port by name, and each module stays small enough to read whole. The typedef models were ported into one module (1.1); the instance models are more numerous and depend on each other in one direction only (struct, then entity, header, ext info), which modules make visible.

**Alternatives.** One `instance.py`, as `typedef.py`: about as long as all of `typedef.py` again, mixing seventeen classes. Importing the shared conventions from `typedef`: makes the instance models depend on the typedef module for reasons unrelated to type definitions.

**Consequences.** Tests follow the layout, one file per module under `tests/instance/`; the four enums, which have no behaviour of their own, share one. Splitting `typedef.py` the same way is possible later without changing its imports, through its re-exports.

### DD-038. Attribute values stay plain JSON values until their types read them

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-20

**Decision.** The models of 2.1a keep attribute values (`attributes`, `relationshipAttributes`, `uniqueAttributes`, business attributes) as the JSON values Python reads: objects, arrays, strings, integers, floats, booleans and null. Atlas's REST mapper reads floats as `BigDecimal` (`USE_BIG_DECIMAL_FOR_FLOATS`) and writes them back with their digits (`1.10`, `1E+3`); that is designed with the `bigdecimal`, `float` and `double` types in 2.1b.

**Reason.** An untyped value reaches a response only after its attribute's type normalised it (2.1b, then the stores), so the digits of a float matter only where a type keeps them. Keeping them in 2.1a would need a JSON reader and writer of its own for every model before any type needs it.

**Alternatives.** Read every float as `Decimal` now: Pydantic writes a `Decimal` as a JSON string, so every writer would need a custom encoder, designed without the type that motivates it.

**Consequences.** 2.1b decides how a `bigdecimal` value is read from a body and written back exactly, and applies it to these models.

### DD-039. One Atlas JSON codec reads floats as decimals and writes them with their digits

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** `aurelius_atlas_model.codec` holds Atlas's JSON reading and writing. `loads` reads every number with a fraction or exponent as a `Decimal`, as Jackson's `USE_BIG_DECIMAL_FOR_FLOATS` does. `dumps` writes a `Decimal` with its digits, a `datetime` as epoch milliseconds, NaN as the string `"NaN"`, and map keys as Java's text of the key. `AtlasModel.to_json` dumps in Pydantic's Python mode, so attribute values keep these types for the codec; typed timestamps are written as epoch milliseconds in both modes. The server's `AtlasJSONResponse` writes its content with `dumps`. This settles DD-038.

**Reason.** A `bigdecimal` attribute keeps the digits it was given (`1.10`), and normalised dates are Java `Date` values that Jackson writes as numbers, even inside untyped attribute maps. Python's `json` turns a `Decimal` into a float, and Pydantic's JSON mode turns it, and a `datetime`, into a string.

**Alternatives.** A custom Pydantic serializer per field: values inside `dict[str, Any]` have no field of their own. Converting decimals to floats: loses digits a client sent.

**Consequences.** A double is written with Python's shortest form (`10000000.0`), where Jackson writes `Double.toString` (`1.0E7`): the same number in another notation, equal for every JSON reader and for the parity comparison. Request bodies with entity values are read with `loads` from 2.3 on.

### DD-040. Java values are held as the Python values closest to them

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** A Java `Integer`, `Long`, `BigInteger`, `Byte` or `Short` is a Python `int`; which of them it was follows from its size, as Jackson chooses by size (`Integer` within 32 bits, `Long` within 64, `BigInteger` beyond). A `BigDecimal` is a `Decimal`, a `Double` a `float`, and a `Float` a `float` holding the shortest decimal of the 32-bit value. A `Boolean` is a `bool`, never a number. A `Date` is an aware UTC `datetime` with millisecond precision. The conversions Java applies between them (`longValue`, `intValue`, `floatValue`, `toBigInteger`, `BigDecimal.valueOf(double)`, `valueOf(String)`, `String.valueOf`) are functions of `aurelius_atlas_typesystem.java`, each named after its Java original.

**Reason.** The types branch on the Java class of a value (`instanceof Long`, `instanceof BigDecimal`), and their results depend on Java's arithmetic: truncation, saturation, 32-bit rounding. Values from a JSON body can only be integers, decimals, strings, booleans, lists and maps, so the Python types need only tell those apart; Java `Float` and `Double` arise from Atlas's own code and from Atlas's tests.

**Alternatives.** Wrapper classes for every Java number type: every value would need wrapping on reading and unwrapping on writing, for distinctions JSON cannot express.

**Consequences.** A `float` value written and read back is the same 32-bit value. An `Integer` and a `Long` of equal value cannot be told apart, and give the same result in every type. A `BigInteger` within 64 bits cannot be told apart from a `Long` either; `bigdecimal` treats them differently (`1` against `1.0`), but JSON never yields one, because Jackson reads such integers as `Integer` or `Long`.

### DD-041. The type system is one module per Java type class too

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-21

**Decision.** As DD-037 for the models: the types the value side adds or changes get one module each, `atlas_type`, `enum_type`, `array_type`, `map_type`, and `builtin/<name>_type` for each nested class of `AtlasBuiltInTypes`. `types.py` keeps the struct, classification, entity, relationship and business metadata types, which 2.1c moves the same way, and re-exports the moved classes.

**Reason.** The value side roughly doubles the type classes; one file of all of them would pass two thousand lines. A reader who knows Atlas's `AtlasArrayType` finds `array_type`.

**Alternatives.** Adding the value side to `types.py`: one module far beyond what anyone reads whole.

**Consequences.** `from aurelius_atlas_typesystem.types import ArrayType` keeps working; new code imports from the class's own module.

### DD-042. A validity period without a time zone is in UTC

- **Status:** Proposed
- **Increment:** 2.1
- **Date:** 2026-10-22

**Decision.** A classification's validity period without a `timeZone` is read in UTC, where Atlas reads it in its JVM's default time zone (`TimeZone.getDefault()`). Java's time zone ids are matched with Python's tz database (`zoneinfo`), Java's legacy three-letter ids (`ZoneId.SHORT_IDS`, such as `PST` and `IST`) and its custom `GMT±h[h][[:]mm]` offsets.

**Reason.** Atlas's default zone is whatever its host is set to; the server image runs in UTC, so UTC is the same answer for a container deployment, and it does not change with where the code happens to run. The tz database holds every zone Java's `TimeZone` resolves except the legacy short ids, which Java maps to tz ids.

**Alternatives.** The local zone of the Python process: makes validation depend on the developer's machine. A setting for the default zone: nothing asks for one yet.

**Consequences.** A validity period of `2026/01/01 00:00:00` without a zone means midnight UTC. The time zone list must stay in step with Java's; the tz database of the image (the `tzdata` package) supplies it.

### DD-043. Entities are documents of one index, their attributes under qualified names

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** Every entity, of every type, is one document of the index behind the alias `aurelius-atlas-entities`, with its GUID as the document id. The document holds the system properties Atlas keeps on a vertex (GUID, type name, super type names, state, times, users, version, labels, custom attributes) as top-level fields, mapped for exact lookup, and the attribute values in an `attributes` object keyed by each attribute's qualified name (`Referenceable.qualifiedName`, `hive_table.createTime`), as the vertex properties are named. The `attributes` object is stored but not indexed (`dynamic: false`) until 4.1 designs the search mapping.

**Reason.** A GUID is how Atlas reads, writes and refers to an entity, and a get by id is Elasticsearch's only real-time read. One index serves every type, as one graph holds every vertex; per-type indices would multiply shards with the number of types. A qualified name is defined by one attribute definition, whose type may not change (TDS-08), so one field never holds two value types, which Elasticsearch could not map. Leaving attributes unindexed until search needs them keeps 2.2 from deciding analysis and field types it cannot yet test.

**Alternatives.** Attributes keyed by their plain names: the same name with different types in two entity types cannot share one mapping. An index per entity type: thousands of small indices for Atlas's models alone, and queries across a super type touch them all.

**Consequences.** The store's client reads floats as decimals and is given documents as the codec's bytes (DD-039), so values keep their digits through Elasticsearch. 4.1 adds attribute mappings and indexes the existing documents again (an `update_by_query`), the first change ADR 023 records as a migration if data exists by then. Reading an entity back maps qualified names to attribute names through the type registry (2.3).

### DD-044. A GUID is a random UUID

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** The store gives a new entity a random (version 4) UUID in canonical lower-case text, as Atlas's `UUID.randomUUID().toString()`.

**Reason.** Atlas's clients see and keep GUIDs of this form; any process can make one without coordination, and the chance of two equal ones is negligible.

**Alternatives.** Time-ordered UUIDs (version 7): better index locality, but a GUID would reveal its creation time and differ in form from Atlas's.

**Consequences.** None beyond Atlas's.

### DD-045. Unique values are reserved by create-only documents

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** For each unique attribute value an `ACTIVE` entity has, the store keeps a reservation document in `aurelius-atlas-unique-values`, whose id is a SHA-256 of the entity type name, the attribute's qualified name and the value as the codec writes it, and which names the GUID holding it. A reservation is made with `op_type=create`, so of two processes reserving the same value one fails, and is deleted when the entity changes the value or leaves `ACTIVE`. A lookup by unique attributes reads the reservations by id, in real time.

**Reason.** Atlas enforces unique attributes with a JanusGraph unique index on a shadow property (`__u_Referenceable.qualifiedName`), composite with the type name (`PER_TYPE_UNIQUE`), removed when an entity is deleted. Elasticsearch has no unique constraint except the document id, and a search would see neither a value written a moment ago nor one being written concurrently. A create-only document with a deterministic id is atomic across processes.

**Alternatives.** Search the entity index before writing: races between processes, and misses unrefreshed writes. The value itself as the document id: limited to 512 bytes, while a `qualifiedName` may be longer.

**Consequences.** Every write of an entity with unique attributes writes one more document per changed value. Reservations belong to the write that made them until it ends (DD-046), so recovery can release those of a write that never finished.

### DD-046. A multi-entity write is all or nothing, through a journal

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** A write of several entities runs in steps:

1. a journal entry in `aurelius-atlas-entity-journal` records the write's id, a lease time and the state of every entity before it (or that it is new);
2. every unique value the write needs is reserved; a value held by another entity ends the write, before any entity is written, with an error 2.4 turns into an answer;
3. all entities are written in one bulk request, each conditionally (DD-047) and marked with the write's id;
4. if any entity fails, every entity written is restored to its state before, and the write's reservations are released;
5. the journal entry is marked committed; values no longer held are released and the entry is deleted.

Recovery, at start-up, finds journal entries whose lease has passed. A committed entry only has its releases finished; any other is undone as in step 4: it restores an entity only while it still carries that write's id, and releases only reservations made by that write.

**Reason.** Atlas commits all entities of a request in one graph transaction (`GraphTransactionInterceptor`). Elasticsearch writes one document atomically but no more (ADR 047). The user chose an all-or-nothing outcome, also after a crash, over per-entity writes or full isolation (2026-10-22): the journal makes the outcome recoverable at the cost of one document per write, while isolation would make every read look up write states.

**Alternatives.** Per-entity atomicity: a failed batch leaves part of it written. Isolation through pending versions and a committed flag: no reader sees a partial write, but every read pays for it.

**Consequences.** Between steps 3 and 4 another reader may see part of a write (DV-16). A write must finish within its lease (60 seconds) or recovery may undo it; a write that finds its lease passed before step 3 gives up. Recovery runs at start-up, so a crash's leftovers stay until a process starts.

### DD-047. Entities are written conditionally on their Elasticsearch version

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** A changed entity is written with the `if_seq_no` and `if_primary_term` it was read with, and a new one with `op_type=create`. A conflict fails the write (DD-046 restores the rest) with a version conflict the caller handles by reading again. Atlas's `version` field is stored as the entity has it and plays no part.

**Reason.** Atlas serialises writes inside one JanusGraph transaction per request; several server processes writing to one Elasticsearch need optimistic concurrency, as the type definitions do (DD-029). Atlas never increments an entity's `version` itself (`getEntityVersion` takes the entity's or 0), so it cannot serve as a concurrency token without changing what clients see.

**Alternatives.** A lock document per entity: needs expiry when its holder dies. Incrementing `version`: changes Atlas's responses.

**Consequences.** 2.4 decides how a write request retries after a conflict and what it answers when it gives up.

### DD-048. A type is in use while the entity index holds one of it

- **Status:** Proposed
- **Increment:** 2.2
- **Date:** 2026-10-22

**Decision.** The typedef store's usage check (DD-030) refreshes the entity index and counts the documents whose type name is the type, in any state, as Atlas's `typeHasInstanceVertex` counts vertices of the type. Classification and relationship types join the check when their instances are stored (3.1, 3.3).

**Reason.** A count is near real time; the refresh makes an entity written a moment ago count. Deleting a type is rare, so the refresh's cost does not matter.

**Alternatives.** Keeping a counter per type: one more document to update atomically with every write.

**Consequences.** Until 3.1 and 3.3, a classification or relationship type is never in use.

### DD-049. Attribute values are stored normalised; a struct inline, a reference as a GUID

- **Status:** Proposed
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** An entity document holds each attribute value as its attribute's type normalises it (`getNormalizedValue`), in the codec's JSON (DD-039): a date as epoch milliseconds, an enum as its value's name, numbers with their digits. A struct value is held inline as `{"typeName": …, "attributes": {…}}`, its attributes by name and normalised the same way. A reference to an entity, whether an `objectid` attribute, an element of an array or a value of a map, is held as the referenced entity's GUID; a soft reference (`isSoftReference`) is held as Atlas holds it, `typeName:guid`. Reading an entity gets the entities its attributes refer to by GUID, in one request, to build their object ids and owned entities; a GUID that finds no entity reads as nothing, as an edge to a removed vertex does.

**Reason.** Atlas keeps a struct in a vertex of its own and a reference as an edge; Elasticsearch has neither, and one document per entity is what DD-043 decided. A struct belongs to its entity alone, so it stays inside it. A reference's GUID never changes, where the referenced entity's unique attributes and type may, so the GUID is the only stable thing to store; everything else the object id shows is read from the referenced entity, as `toAtlasObjectId` reads it from the vertex.

**Alternatives.** Storing the object id with its unique attributes: stale once the referenced entity changes. Structs as documents of their own: a second read per struct, and nothing ever refers to one.

**Consequences.** 2.4 writes values in this form, resolving every object id it is given, by GUID or by unique attributes, to a GUID first. A reference read needs a second `mget` per nesting level of owned entities. 3.1 decides how relationship attributes are stored; references that are also relationship ends (legacy attributes) move there then.

### DD-050. Relationship attributes read empty until relationships are stored

- **Status:** Superseded by DD-064
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** Until 3.1 stores relationships, an entity reads as Atlas reads one without relationship edges: `relationshipAttributes` names every relationship attribute of its type, null for a `SINGLE` end and `[]` for a `LIST` or `SET` end, the end chosen as Atlas chooses it without edges (the attribute's first relationship type). `ignoreRelationships=true` leaves `relationshipAttributes` out.

**Reason.** The keys and the empty values are what Atlas answers for an entity no relationship has reached yet; answering them now keeps the response's shape, and 3.1 only fills values in.

**Alternatives.** Leaving `relationshipAttributes` out until 3.1: a different shape for every entity, which clients that read the keys would notice.

**Consequences.** Until 3.1, a reference given as a legacy relationship attribute (DD-049) reads in `attributes` but not in `relationshipAttributes` (DV-18).

### DD-051. Entity reads are tested on entities written through the store until 2.4

- **Status:** Proposed
- **Increment:** 2.3
- **Date:** 2026-10-22

**Decision.** 2.3's HTTP tests write the entities they read through `EntityStore` (2.2), in the stored form of DD-049, and check every read rule on them. Its parity scenarios cover what needs no entity: unknown GUIDs and types, invalid and missing unique attributes, values that find nothing. 2.4 adds scenarios that create entities over REST and read them back.

**Reason.** A parity scenario only reaches the server over REST, and entities can be created over REST from 2.4 on. Seeding through the store tests the read path now without porting the write path early.

**Alternatives.** Merging 2.3 into 2.4: one pull request far above the size limit. Moving 2.4 before 2.3: a write increment whose responses could not be read back.

**Consequences.** Until 2.4, the stored form the tests write is checked against Atlas's responses only by the expectations read from the Java source; 2.4's scenarios check both directions.

### DD-052. A request is mapped in memory and written once; a lost race runs it again

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** `EntityWriter` reads every stored entity a create or update request names, discovers and resolves its references, and maps its entities to their new stored form in memory, together with the entities EWR-12 touches. The response's headers are built from that form. The result is one `EntityStore.write` (ENS-07), each changed entity conditional on the version it was read in (ENS-08). When the write loses a race, the whole request is read, mapped and written again, once; a second loss, or a unique value another entity holds, is answered with `INTERNAL_ERROR` naming the cause (DV-20).

**Reason.** Atlas maps a request onto vertices inside one graph transaction and commits at the end; mapping onto documents in memory and writing them in one all-or-nothing write is the same shape on Elasticsearch (DD-046). Running the request again on the newer state is what a client would do, as DD-029 does for types.

**Alternatives.** Writing each entity as it is mapped: a failure part-way would leave a half-written request for recovery to undo, and headers would be read from the index. Answering a lost race with an error at once: two clients updating different attributes of an entity would fail where Atlas, serialising them, succeeds.

**Consequences.** A request's memory grows with its entities, as Atlas's transaction does. A unique value clash is no `400`: Atlas resolves an entity by its unique values before writing, so a clash needs an update that moves a value onto another entity, or two new entities with the same value in one request.

### DD-053. Relationship attribute values are resolved, but stored only as legacy attributes until 3.1

- **Status:** Superseded by DD-064
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** Until 3.1 stores relationships, a relationship attribute's value in a write is discovered, resolved, checked and normalised as Atlas does, so its errors are Atlas's. It is stored only when the entity's type has an attribute of the same name (a legacy relationship end, such as `hive_table.db`), as that attribute's value (DD-049); a relationship attribute without such an attribute is not stored (DV-22).

**Reason.** A legacy end is read from `attributes` (DD-050, DV-18); storing it there keeps what clients write readable. Storing other relationship values needs relationship instances, their GUIDs and both ends, which is 3.1's.

**Alternatives.** Rejecting relationship attributes until 3.1: requests Atlas accepts, such as the hook models', would fail. Storing them as plain references on one end: 3.1 would have to migrate them.

**Consequences.** 3.1 replaces this: relationship values become relationships, and the legacy attributes' values move to them.

### DD-054. Dynamic attributes are evaluated in first-seen dependency order

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** An entity type's dynamic attributes are ordered by a depth-first topological sort over their templates, visiting them in the order their `dynAttribute:` options appear, so that an attribute another template names is evaluated first.

**Reason.** Java sorts the same graph but starts from the keys of a `HashMap`; where the dependencies leave the order open, first-seen order is stable, as DD-027 chooses for derived type sets.

**Alternatives.** Sorting by name: stable too, but unrelated to the definition.

**Consequences.** Independent dynamic attributes may be evaluated in another order than Atlas's; their values do not depend on it.

### DD-055. Scenarios name what they create with a per-run value

- **Status:** Proposed
- **Increment:** 2.4
- **Date:** 2026-10-22

**Decision.** The parity harness provides `{run}`, a value unique to each run of a scenario, in letters and digits, before any stage has saved a value. Entity scenarios name their types and entities with it, and leave them in the store until 2.5 lets them delete what they created (DD-035).

**Reason.** The dev store keeps its contents between runs. A scenario that creates an entity again on a second run would find it, update it and get a different answer; a type in use cannot be deleted.

**Alternatives.** Deleting the entity index before scenarios: other tests and a developer's data share the dev store. Waiting for 2.5: 2.4's writes would have no parity check (DD-051).

**Consequences.** Each run of the entity scenarios leaves a few types and entities in the dev store until 2.5; CI starts from an empty store.

### DD-056. An entity write also removes documents, journaled like the others

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** An `EntityChange` may remove its entity instead of writing a new state. The removal is a `delete` action of the same bulk request, conditional on the version read (DD-047); the journal entry records the entity's state before and lists the removed GUIDs. A failed write restores a removed entity; recovery restores a removed entity of an unfinished write when no document has its GUID. A removed entity holds no unique value: its reservations are released as for one that left `ACTIVE`.

**Reason.** A hard delete or a purge removes entities and changes those referring to them in one request; the all-or-nothing write of DD-046 already covers the changes, and removals need the same guarantee.

**Alternatives.** Marking removed entities and deleting them in a second step: a reader would see them in between, and a crash would leave them. Removing them after the write commits: a crash in between leaves entities the response called purged.

**Consequences.** Recovery cannot tell a removal undone by it from a later write's removal of the same GUID; a GUID is removed once, so this does not arise.

### DD-057. Entities referring to one are found through an indexed field of GUIDs

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** Every entity document holds `references`, a keyword field of the GUIDs its references name (its own object id attributes and the elements and values of its arrays and maps of object ids; not soft references, not references in structs), set by `EntityStore` on every write. Deleting an entity refreshes the entity index, then searches `references` for its GUID, in pages. Preparing the store adds the field's mapping to an existing entity index; documents written before it have no `references` until they are written again.

**Reason.** Atlas follows an entity's incoming edges; documents have none. Of the alternatives offered, the indexed field keeps writes to the entities written (DD-052), and the refresh makes every write finished before the delete visible.

**Alternatives.** A reverse list on each referenced entity, kept by the same write: exact, but every write that adds or drops a reference rewrites the entities it names, and popular entities become write hot spots.

**Consequences.** A referrer written while the delete runs may be missed (DV-27). Lineage (5.1) and relationships (3.1) can use the same field.

### DD-058. A stored reference stands for an edge: active for a delete, deleted for a purge

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** A stored reference has no state of its own. A delete treats the references to the entities it deletes, and those of an `ACTIVE` owner to its owned entities, as active edges; a purge treats them as deleted edges, which a soft delete left behind.

**Reason.** Atlas soft-deletes an entity's edges with it: the edges a purge finds deleted are those of entities a delete made `DELETED`, which is what this rule reads from the entities' states.

**Alternatives.** A state per reference in the stored form (DD-049): an exact copy of the edges' states, at the cost of a second representation of every reference until 3.1 stores relationships.

**Consequences.** A reference written to an entity after it was deleted counts as deleted for a purge, where Atlas would hold an active edge and leave it.

### DD-059. The delete type and its override are server settings

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** `AURELIUS_ATLAS_SERVER_DELETE_TYPE` (`soft` by default, or `hard`) stands for `atlas.DeleteHandlerV1.impl`; `AURELIUS_ATLAS_SERVER_DELETE_TYPE_OVERRIDE` (`false` by default) for `atlas.rest.enable.delete.type.override`, which lets a request's `deleteType` choose.

**Reason.** Atlas configures both in `atlas-application.properties`; the server's settings are its equivalent.

**Alternatives.** Soft deletes only: deployments that configure Atlas for hard deletes could not move.

**Consequences.** None beyond two settings with Atlas's defaults.

### DD-060. The owned-reference cascade moves from 3.2 to 2.5

- **Status:** Proposed
- **Increment:** 2.5
- **Date:** 2026-10-22

**Decision.** Deleting an entity deletes the entities its owned reference attributes name (`ownedRef`), as `DeleteHandlerV1.getOwnedVertices` does, from 2.5. Composition through `relationshipDefs` and deleting an owned entity whose reference an update drops stay with 3.2.

**Reason.** Owned references are stored as GUIDs (DD-049); following them needs no relationships, and without them a delete would leave owned entities `ACTIVE`, unlike Atlas.

**Alternatives.** All cascades in 3.2, as the roadmap first had it: deletes would differ from Atlas until then.

**Consequences.** The roadmap's 2.5 and 3.2 rows change accordingly.

### DD-061. Relationships are documents of their own index, listed by both ends

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** A relationship instance is one document of the index behind `aurelius-atlas-relationships`, keyed by its GUID: type name, label, end 1 and end 2 GUIDs, status, times, users, version, provenance type, home id, tag propagation and attribute values (as DD-049 stores values). Each end entity's document lists the GUIDs of the relationships it is an end of (`relationshipGuids`), written with the relationship. Reading an entity's relationships is a get of its document and of the listed relationships, in real time.

**Reason.** Atlas keeps a relationship as an edge both vertices reach. Listing the GUIDs on both ends keeps entity reads to gets by id, never a search that waits for a refresh, at the cost of writing the ends with the relationship.

**Alternatives.** Relationship documents found by searching their end GUIDs: writes touch only the relationship, but every entity read with relationships pays a refresh and a search, and may miss one just written.

**Consequences.** An entity at the centre of many relationships (a database with thousands of tables) has a long list in its document, and writers relating entities to it conflict on it and retry (DD-052, DV-30). Ten thousand GUIDs are about 400 KB, well inside Elasticsearch's document size.

### DD-062. An entity write also writes relationships, all or nothing

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** `EntityStore.write` takes relationship changes next to entity changes: new, changed and removed relationships, conditional on the version read, in the same bulk request and the same journal entry as the entities (DD-046, DD-056). Recovery restores relationships as it restores entities.

**Reason.** Creating a relationship changes three documents, deleting an entity may change many; a partial write would leave a relationship its ends do not list, or a list naming a relationship that does not exist.

**Alternatives.** A separate relationship store with its own journal: two writes per request, with a window in which one is done and the other not.

**Consequences.** The journal entry holds the relationships' states before the write too.

### DD-063. 3.1 is split into relationship instances and relationship attributes

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** 3.1a ports relationship instances: models, the relationship type's value side, storage and `RelationshipREST`, and the deletion of an entity's relationships. 3.1b ports relationship attributes of entities: `relationshipAttributes` in reads, relationships created, changed and deleted by entity writes, legacy ends read through relationships, and inverse references; it replaces DD-053.

**Reason.** Together they are two to three times the size an increment may have (ADR 051).

**Alternatives.** One increment: one pull request far above the limit.

**Consequences.** Until 3.1b, entities read with empty relationship attributes (DD-050) even when relationships created over `RelationshipREST` name them.

### DD-064. Relationship attribute values are relationships

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** From 3.1b an entity write maps the values of relationship attributes, legacy ends included, to relationship instances (DD-061) as `EntityGraphMapper` maps them to edges, and stores none of them as an attribute value. Reads answer `relationshipAttributes`, and the legacy ends in `attributes`, from the entity's relationships. It supersedes DD-050 and DD-053. Entity documents written before 3.1b keep the legacy ends 2.4 stored as attribute values; they are not migrated, since no deployment holds entities yet.

**Reason.** Atlas keeps a relationship attribute's value only as the edge; one place for it keeps a value written through an entity and one written through `RelationshipREST` the same.

**Alternatives.** Keeping legacy ends as attribute values as well: two copies of every such reference, which every relationship write would have to keep equal.

**Consequences.** DV-18 and DV-22 end. Plain references, those of attributes that are no relationship end, stay attribute values (DD-049).

### DD-065. A relationship keeps one array index, the last writer's

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** A relationship document holds `index`, Atlas's `__index` edge property: the position the last write of an array relationship attribute gave it, at either end. An array of relationships reads in the order of their indices when the first has one, else in the order the entity lists them.

**Reason.** Atlas stores the position on the edge, so both ends of a `LIST`-to-`LIST` relationship share it; one field reproduces what Atlas reads, its quirks included.

**Alternatives.** A position per end: an order Atlas does not keep.

**Consequences.** An array whose elements are also in an array at the other end may read in another order after the other end is written, as in Atlas.

### DD-066. Relationship attributes are mapped in memory and written with the entities

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** `RelationshipMapper` maps a request's relationship attributes in memory, after its entities are discovered: it reads the relationships the entities list as it needs them, keeps the ones it creates, changes and removes, and the changes to the ends' lists, and the writer writes them with the entities in the one write of DD-052 and DD-062. A relationship between two entities is looked for among the relationships both list.

**Reason.** A request is all or nothing (DD-052), and the lists on both ends (DD-061) make the relationships of an entity, and those between two, readable by id without a search.

**Alternatives.** Writing each relationship as it is mapped: a failing request would leave some behind.

**Consequences.** A write reads every relationship of the entities whose relationship attributes it maps; an entity at the centre of many is costly to update through them, as Atlas iterating its edges is.

### DD-067. Delete cascades follow owned relationships from 3.1b

- **Status:** Proposed
- **Increment:** 3.1
- **Date:** 2026-10-22

**Decision.** The owned-reference cascade of a delete (DD-060) also follows the relationships of owned relationship attributes, from 3.1b rather than 3.2. 3.2 keeps the owned entities an update replaces or drops.

**Reason.** From 3.1b a legacy end such as `hive_table.columns` is no longer stored as an attribute value (DD-064), so a cascade that read only attribute values would stop at it until 3.2.

**Alternatives.** Leaving it to 3.2: deletes between 3.1b and 3.2 would leave owned entities behind that 2.5 deleted.

**Consequences.** 3.2's roadmap row narrows to the owned entities an update drops (DV-31).

### DD-068. Owned entities an update drops are deleted through a view of the request

- **Status:** Proposed
- **Increment:** 3.2
- **Date:** 2026-10-22

**Decision.** After a write request is mapped (DD-052, DD-066), the owned entities it dropped are deleted by the delete handlers of 2.5, reading through `TransactionView`: the entity store as the request has changed it, its changed entities and relationships read as changed, the relationships it removed gone, and the entities referring to a deleted one found by the search of DD-057 and checked against their changed references. The deletes' changes replace the request's own for the same documents, and everything is written in the request's one write.

**Reason.** Atlas deletes them inside the update's transaction, after the update's own edge changes; the view gives the handlers that state without a second write, so the request stays all or nothing.

**Alternatives.** Deleting them in a second write after the update: simpler, but an update could then succeed while the deletes fail, which Atlas never shows.

**Consequences.** The delete handlers read the store through a protocol (`EntityView`) that both `EntityStore` and `TransactionView` answer.

### DD-069. A reference to a deleted entity stands for a deleted edge when reviving

- **Status:** Proposed
- **Increment:** 3.2
- **Date:** 2026-10-22

**Decision.** `updateInConsistentOwnedMapVertices` revives an owned map entry whose edge and entity are both `DELETED`; a stored plain reference has no state (DD-058), so an entry that keeps naming a `DELETED` entity is taken as one with a deleted edge, and the entity becomes `ACTIVE` again.

**Reason.** Atlas soft-deletes the edges to an entity with it, so a `DELETED` entity is the case in which its edge is deleted too.

**Alternatives.** A state per stored reference: rejected with DD-058.

**Consequences.** An entity deleted without its owner, its owner's entry kept by the soft delete, is revived by the owner's next update that keeps the entry, as in Atlas.

### DD-070. Classification instances are documents of their own index, listed by their entity

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** A classification instance is one document of the index behind `aurelius-atlas-classifications`, keyed by a GUID of its own: type name, the GUID and status of the entity it is attached to, `propagate`, `removePropagationsOnEntityDelete`, validity periods and attribute values (as DD-049 stores values). The entity's document lists the GUIDs of its classifications (`classificationGuids`), in the order they were attached. Reading an entity's classifications is a get of the listed documents, in real time.

**Reason.** Atlas keeps a classification as a vertex the entity reaches by an edge, and a propagated one is the same vertex reached by many entities. A document per instance keeps that: 3.4 lists a propagated instance on every entity it reaches, and an update of it changes one document. Listing GUIDs keeps reads to gets by id, as DD-061 does for relationships.

**Alternatives.** Classifications embedded in the entity document: no second read, but 3.4 would copy a propagated classification into every entity it reaches and rewrite every copy on each change.

**Consequences.** An entity read with classifications costs one more `mget`. The GUID of an instance is internal: Atlas's classifications have none in their JSON.

### DD-071. An entity write also writes classification instances, all or nothing

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** `EntityStore.write` also writes, changes and removes classification instances, in the same bulk request and journal entry as the entities, as DD-062 does for relationships; recovery restores them too.

**Reason.** Attaching a classification changes the entity's list and the instance together; Atlas does both in one graph transaction.

**Alternatives.** Writing the instance first and the entity after: a failure between leaves an instance no entity lists.

**Consequences.** The journal entry holds the classifications' states before the write, as it does for entities and relationships.

### DD-072. The propagation defaults are Atlas's defaults

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** A classification attached without `propagate` gets `true` (`atlas.classification.propagation.default`), without `removePropagationsOnEntityDelete` gets `false` (`atlas.classification.propagation.remove.on.entity.delete`); both are Atlas 2.4.0's defaults, fixed in code.

**Reason.** No deployment changes them yet, and both decide 3.4's propagation, which will read the stored values.

**Alternatives.** Server settings now: two settings with no effect until 3.4.

**Consequences.** 3.4 may turn them into server settings.

### DD-073. 3.3 is split into direct classifications and the bulk associator

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** 3.3a ports classifications attached directly: storage, reads, the per-entity and `bulk/classification` endpoints, classifications of created entities and of deleted ones. 3.3b ports `bulk/setClassifications` (`ClassificationAssociator`) and `bulk/headers?tagUpdateStartTime`.

**Reason.** Together they are above the size an increment may have (ADR 051); the associator builds on 3.3a's operations.

**Alternatives.** One increment: one pull request far above the limit.

**Consequences.** Until 3.3b, `bulk/setClassifications` and `bulk/headers` answer `404`.

### DD-074. `bulk/headers` moves to 3.5

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** `GET bulk/headers?tagUpdateStartTime` (`ClassificationAssociator.Retriever`) is ported with the entity audit in 3.5 rather than in 3.3b.

**Reason.** It lists the entities whose classifications changed in a time window by asking the audit repository (`getEntitiesWithTagChanges`); without audit events it could only answer an empty list, or keep a second record of classification changes that 3.5 would replace.

**Alternatives.** An index of classification change times now: a record 3.5's audit events supersede.

**Consequences.** Until 3.5 the endpoint answers `404`. 3.3b ports `bulk/setClassifications` alone.

### DD-075. A propagated classification is listed by the entities it reaches

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** An entity a classification is propagated to lists the instance's GUID in its `classificationGuids`, after its own, as its entity does; an instance listed by an entity other than its `entityGuid` is propagated to it. Atlas's propagated `classifiedAs` edge is this listing.

**Reason.** One instance stays one document (DD-070): an update of it reaches every entity listing it at once, as in Atlas, and an entity's reads stay gets by id.

**Alternatives.** A copy of the classification per entity reached: every change rewrites every copy.

**Consequences.** A classification propagated far makes many entity documents change in one write (DD-071), and writers relating those entities conflict more (DV-30).

### DD-076. The entities a classification reached are found through an indexed field

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** `classificationGuids` is indexed; the entities listing an instance are found by searching it after a refresh, page by page, as DD-057 finds referring entities, and checked against the request's own changes.

**Reason.** Removing a propagation needs the entities a classification reached (`getPropagatedEdges`); a search keeps the classification's document small however far it propagates.

**Alternatives.** The instance listing the entities it reached: exact and real time, but as large as its reach, and rewritten on every change of it.

**Consequences.** A search may miss an entity a concurrent write has just made list the instance, as DV-27 says for references.

### DD-077. Propagation runs within the request until 3.4b

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** In 3.4a, the request that causes a propagation computes and writes it, as Atlas does with `atlas.tasks.enabled=false`; 3.4b defers it to tasks, Atlas's default.

**Reason.** The propagation itself is the same either way; deferring it is a second, separable concern with its own queue, worker and endpoints.

**Alternatives.** Tasks from the start: one increment far above the size limit.

**Consequences.** Until 3.4b a request that propagates far takes as long as its propagation, and entities have no `pendingTasks`.

### DD-078. 3.4 is split into propagation and propagation tasks

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** 3.4a ports propagation and its triggers, run within the request (DD-077); 3.4b ports the deferred tasks: the task index and worker, `pendingTasks`, `admin/tasks` and the checks of pending tasks.

**Reason.** Together they are above the size an increment may have (ADR 051).

**Alternatives.** One increment.

**Consequences.** 3.4b changes when propagation runs, not what it does.

### DD-079. Tasks are documents of their own index, written with the change that records them

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** A task is one document of the index behind `aurelius-atlas-tasks`, keyed by its GUID: Atlas's task fields and the claim of DD-080. The entity it is queued on lists its GUID in `pendingTasks` (a relationship update's task, the relationship). A task is written in the write of the change that records it, as relationships and classification instances are (DD-062, DD-071), and journaled with it.

**Reason.** Atlas creates the task vertex in the request's graph transaction: a change and its task commit together or not at all.

**Alternatives.** Queuing tasks after the write: a crash in between loses the propagation.

**Consequences.** `EntityStore.write` takes task changes as a third kind of listed document.

### DD-080. Every server process runs tasks, each claimed with a lease

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** Each server process runs a worker that takes `PENDING` tasks oldest first. It claims one by writing it `IN_PROGRESS`, with its start time and a claim lease, conditionally on the version it read; a claim another process won is skipped. A task claimed by a process that stopped is taken over once its lease has passed. A request that records tasks wakes its own process's worker; the workers also look for tasks at an interval.

**Reason.** Several processes may share one store; the conditional claim lets any run any task exactly once at a time, without electing a leader, and a stopped process's tasks are resumed.

**Alternatives.** One worker on an elected leader, as Atlas's active instance: leader election and takeover to build for no gain in correctness.

**Consequences.** Tasks of different entities may run side by side in different processes (DV-38).

### DD-081. Tasks are enabled by a server setting, on by default

- **Status:** Proposed
- **Increment:** 3.4
- **Date:** 2026-10-23

**Decision.** `AURELIUS_ATLAS_SERVER_TASKS_ENABLED` (default `true`, Atlas's `atlas.tasks.enabled`) chooses whether propagation is deferred to tasks; `false` keeps 3.4a's propagation within the request.

**Reason.** Atlas's default defers it; the setting keeps the synchronous form for deployments and tests that want a write to be complete when it answers.

**Alternatives.** Always deferred: no way to have a propagation done when its request answers.

**Consequences.** The core takes the choice as a parameter of the writers and stores that propagate. The parity scenarios run against a server with tasks disabled, as against an Atlas with `atlas.tasks.enabled=false`: they check what propagation produces, not when, and `admin/session` reports the setting.

### DD-082. Audit events are documents of their own index, written after the change

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** Increment 3.5 is split: 3.5a records the events of entity writes, deletes and purges and answers `{guid}/audit`; 3.5b adds the classification events and `bulk/headers`. An audit event is one document of the index behind `aurelius-atlas-entity-audits`. The events of a change are written once the change has committed, from the entities read back, in one bulk request; they are not part of the change's journaled write.

**Reason.** Atlas keeps its audit in HBase, apart from the graph, and writes it in the request before the graph commits; neither store's write includes the other's. Reading the committed entities gives the details exactly as a later read answers them, without computing them from a request's view in every writer.

**Alternatives.** Events as a further kind of document in the journaled write (DD-079): no event lost, but each writer would compute the details before its write.

**Consequences.** A process that stops between the write and its events loses them (DV-40).

### DD-083. Audit events keep Atlas's event keys and their order

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** An event's `eventKey` is the HBase row key Atlas writes, `<entityId>:<timestamp>:<index>:<now>`, a keyword of the event's document. Events are read newest first by sorting on it descending, as Atlas's reversed HBase scan reads them; `startKey` is a bound on it. The document's id is a new GUID, so two events with one key are both kept.

**Reason.** Keyword order is the byte order HBase sorts row keys in, so the order and the `startKey` paging the dashboards and clients rely on stay Atlas's, quirks included.

**Alternatives.** Sorting by timestamp: events of one millisecond would come in another order, and `startKey` would need a translation.

**Consequences.** Where HBase would overwrite an event whose key repeats, both events are listed.

### DD-084. The entity writer tells a change notifier what it changed

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** `EntityWriter` takes an optional `EntityChangeNotifier`, Atlas's `AtlasEntityChangeNotifier`, and gives it each committed response with the request's user. The notifier prunes the response and calls its listeners; the audit listener is the only one. Without a notifier nothing is recorded.

**Reason.** Atlas's entity store notifies after every mutation; one hook in the writer covers creates, updates, deletes and purges, and tests of the writer need no audit.

**Alternatives.** The server recording events after each route: every route would repeat it, and core callers would record nothing.

**Consequences.** 3.5b gives the classification operations the same notifier. The writer prunes every response as `pruneResponse` does, also without a notifier, since Atlas answers the response it pruned: an entity listed as deleted is no longer also listed as updated (OWN-03).

### DD-085. Classification events are collected in the request and recorded after its write

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** The classification operations, the entity writer, the relationship store and the propagation tasks take the change notifier, as the entity writer does (DD-084), and tell it, once their write has committed, what Atlas's would have told it during the request, in Atlas's order: the notifier's classification methods, then `notifyPropagatedEntities` where Atlas calls it.

**Reason.** The events are recorded after the change, as entity events are (DD-082); keeping Atlas's order keeps the events' keys, and so the order in which `{guid}/audit` lists them.

**Alternatives.** Events derived from the stored differences after the write: Atlas's quirks, such as one update event per updated classification on each entity notified, would be lost.

**Consequences.** Every propagating operation answers what it propagated, to whom; 3.5b adds that to `TagPropagation`'s results (DD-086).

### DD-086. Tag propagation records the propagations a request added and removed

- **Status:** Proposed
- **Increment:** 3.5
- **Date:** 2026-10-23

**Decision.** `TagPropagation` keeps, per entity, the classification instances it newly listed and those it stopped listing, in the order it changed them, as `RequestContext` keeps added and removed propagations. The callers give them to the notifier after their write (CAU-05).

**Reason.** The propagation is computed in one place (DD-075); recording there covers every caller, including the delete handlers and the tasks.

**Alternatives.** Comparing the entities' classification lists before and after the write: a classification added and removed again within a request would be missed, and the order lost.

**Consequences.** `propagate` answers the entities it propagated to, which the add events need (CAU-02).

### DD-087. Basic search is split into entity and classification search

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** Increment 4.1 is split: 4.1a searches entities by type, entity filters, state, sort and paging, with the search fields it needs (DD-088); 4.1b adds the classification search of `ClassificationSearchProcessor`. The free-text `query` of basic search goes with quick search to 4.2.

**Reason.** Atlas's two processors are separate, and each is as large as one increment.

**Alternatives.** One increment of about twice the size; the free text with 4.1, where it would need the full text index 4.2 builds anyway.

**Consequences.** Until 4.1b a search naming a classification is refused (DV-46).

### DD-088. Entity attributes are searched in typed search fields named after their defining type

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** An entity document carries `search`, a flat object (`subobjects: false`) of its searchable values: each primitive, enum or array-of-primitive attribute under `<kind>.<qualified name>`, the qualified name being Atlas's vertex property key (`hive_table.name`, `Referenceable.qualifiedName`, `__guid`), and `<kind>` the Elasticsearch type its Atlas type maps to: `keyword` for strings and enums, `long` for the integer types and dates, `double` for `float`, `double` and the big number types, `boolean`. Dynamic templates on the kind map each new field. The system attributes of the entity root are filled from the document's own fields. The entity store computes `search` with the registry when it writes an entity.

**Reason.** Atlas's index keys a property by its defining type, so one attribute is one field across sub types, and its type decides how it compares. A kind in the field's name lets Elasticsearch map a field the first time it is written, in any process, without a mapping kept in step with the type definitions.

**Alternatives.** Mapping each field from the type definitions when they change: the same fields, but every process and every type change would update the mapping. One `flattened` field: no range or numeric sort. Filtering in memory: every search reads every entity of its types.

**Consequences.** Entities written before 4.1a have no `search` until written again. The field limit of the entity index is raised to 100,000. The big number types compare as doubles.

### DD-089. A search is a query of the entity documents, ordered by creation when no sort is given

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** `EntitySearchProcessor` builds a search query of its own: the types, the state, the filter tree over search fields with Atlas's operators, the sort, offset and size. The entity documents answer it with the matching entities and their total, which is `approximateCount`; Elasticsearch as a `bool` query, the in-memory documents by evaluating it. Without `sortBy` entities come by creation time, then GUID.

**Reason.** One query instead of Atlas's index query, graph query and in-memory predicates, whose combination the rules of SRC-05 state; Atlas's order without a sort is the index's and has nothing to keep.

**Alternatives.** Elasticsearch's query language in the core: the in-memory documents could not answer it.

**Consequences.** `approximateCount` is exact.

### DD-090. A classification search finds instances first, then the entities listing them

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** The entity documents gain what Atlas keeps on an entity vertex of its classifications, computed when an entity is written from the instances it lists: `__traitNames` and `__propagatedTraitNames`, the type names of those attached and propagated, `__classificationNames` and `__propagatedClassificationNames` as `|a|b|`, and the GUIDs of the instances. A search naming classifications without tag filters tests the type names, as Atlas's `buildTraitPredict` does; with tag filters it reads the instances of the types named from the classification index, keeps those that match, evaluated with the search query's predicates over their attribute values, and adds to the entity query that the entity lists one of them.

**Reason.** An entity already lists every classification it carries, propagated ones included (DD-070, DD-075), and tag filters are what classification instances are searched by; no mapping of classification attributes is needed, and the filter semantics are the ones entity filters have.

**Alternatives.** Search fields on classification documents: the same answers, with a second set of mappings. Classification type names on the entity only: tag filters could not be answered.

**Consequences.** A search reads every instance of the types it names; an entity query names at most 65,536 instances, Elasticsearch's `terms` limit, beyond which the search fails.

### DD-091. Free text is split from quick search

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** Increment 4.2 is split: 4.2a indexes and searches free text, in basic search's `query` and in `search/fulltext`; 4.2b answers `search/quick` with its facets, and `search/suggestions`.

**Reason.** Quick search and suggestions build on the free text; each part is about one increment.

**Alternatives.** One increment of about twice the size.

**Consequences.** Until 4.2b, the dashboards' quick search box finds nothing.

### DD-092. String search fields carry an analysed text sub-field, searched with Atlas's weights

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** The dynamic template of `keyword` search fields gives each a `text` sub-field, analysed by Elasticsearch's standard analyser, and keeps values over 8,191 characters out of the keyword. An entity's search fields gain `__classificationsText`. A free-text query is a `simple_query_string` over the text sub-fields of the string attributes of the non-internal entity types and of `__classificationsText`, `__labels`, `__customAttributes` and `__typeName`, each boosted by the weight Atlas's `SolrIndexHelper` gives its Solr field. The in-memory documents match words the same way, without Elasticsearch's scoring.

**Reason.** Atlas's free text is Solr's `edismax` over the same fields with the same weights as `qf`; a sub-field keeps each attribute's weight and its exact `keyword` for the filters of 4.1.

**Alternatives.** One catch-all text field: every attribute would weigh the same, and 4.2b's suggestions could not keep to the fields weighted 8 or more. `query_string`: closer to `edismax`, but a malformed query fails.

**Consequences.** Fields mapped before 4.2a have no text sub-field; an entity index created before needs creating again.

### DD-093. Facets are aggregations of the search's own query

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** Quick search counts its facets with `terms` aggregations over the `keyword` search fields of `__typeName`, `__state` and `Asset.owner`, in the same Elasticsearch request as the page of results: the query of the search, unpaged, at most 100 values each, ordered by count and then by value. `ServiceType` is added up from the `__typeName` counts with the registry's types. The in-memory documents count the same.

**Reason.** Atlas facets the Solr query its `AtlasSolrQueryBuilder` rebuilds from the same query, types, filters and state as the search; aggregating the search's own query counts exactly the entities found, without a second translation of the filters. 100 is Solr's default `facet.limit`.

**Alternatives.** A second request for the counts: one more round trip for the same query.

**Consequences.** Facets count what the search query matches, classification criteria included, which quick search does not take.

### DD-094. Suggestions are terms aggregations of the text sub-fields

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** The text sub-field of DD-092 enables `fielddata`. Suggestions are, for each field weighted 8 or more (or the one named), a `terms` aggregation of its text sub-field over every entity document, of the 5 terms matching the prefix, most documents first; the fields' terms are then summed and the top 5 kept. The in-memory documents count the words of the same fields.

**Reason.** Atlas reads Solr's terms component on the fields with `terms.limit` 5 and adds up the frequencies; a terms aggregation is the Elasticsearch reading of a field's terms and their document frequencies. The `_terms_enum` API knows no frequencies, and keyword fields hold whole values, not words.

**Alternatives.** A completion suggester: a field of its own per attribute, suggesting whole values. Terms of the keyword fields: values, not words, and only case-sensitive prefixes.

**Consequences.** Fielddata of a text sub-field is loaded into the heap the first time it is aggregated, which suggestions limit to the few fields weighted 8 or more. Fields mapped before 4.2b have no fielddata; an entity index created before needs creating again.

### DD-126. The webapp is a new project, not the Aurelius app upgraded in place

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The Aurelius interface is rewritten as `apps/aurelius-atlas-webapp`, a new Nx project on this workspace's Angular 22, Nx 23, and TypeScript 6. Only source moves: the Aurelius `project.json`, `tslint.json`, Jest config, `jest-preset-angular`, and the root dependency set are left in the Aurelius repository. Targets are inferred by this workspace's plugins, and tests are Vitest.

**Reason.** An in-place upgrade must cross five `ng update` majors with the custom abstractions intact, and needs `@angular/platform-browser-dynamic`, which this workspace does not install because its apps bootstrap with `bootstrapApplication`. Vendoring the upgraded result therefore adds a deprecated dependency and lands the whole NgModule graph in one review. A new project lets each slice arrive on the target's rules, and the Aurelius app keeps serving while they do ([ADR 053](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/053-the-webapp-is-rewritten-in-angular-idiom-slice-by-slice/index.md>)).

**Alternatives.** Upgrade in place then modernise: fails the "no replaced pattern survives" rule and produces one unreviewable migration. Serve the Aurelius app as an external artifact: leaves two Angular toolchains and two dependency trees to maintain. Port into `aurelius-atlas-frontend-example`: destroys the small legible reference the example is for.

**Consequences.** The same screens exist in two codebases until 7.10 removes the example app. The clone is kept at `.scratch/aurelius` as the reference checkout, git-ignored and outside the Nx graph; every `Aurelius origin` citation in the 7.x increments points into it, and it is re-fetched by path when a citation must be checked.

### DD-127. Signals replace the custom store; each slice owns its state

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The Aurelius `@models4insight/redux` layer (`Store`, `BasicStore`, `StoreService`, `ReduxModule.forRoot`) is not ported and has no adapter. Each slice rewrites its state as `signal()` with `computed()` for derived values, in an injectable following the signal-service pattern of `aurelius-atlas-frontend-example`. A `Subject` survives only as an event stream inside RxJS interop (`toObservable`, `toSignal`, `takeUntilDestroyed`), never as the owner of state.

**Reason.** The wrapper is a hand-rolled Redux: 24 Aurelius files import it, and its `BehaviorSubject` state is the main reason the app cannot run zoneless — change detection depends on zone patches seeing the emissions. Signals give the same explicit state, the same derived values, and change detection that needs no zone. Keeping a compatibility layer would preserve the abstraction the rewrite exists to remove, and every reader of a screen would meet it first.

**Alternatives.** NgRx: a dependency ADR 050 removes from the system, and signals make its store, selectors, and effects redundant here. Keep the wrapper on Angular 22: cheapest per slice, and it leaves the custom abstraction in front of every screen, which is what the requirement forbids. Component-local signals with no service: shares nothing, so the cross-screen state the wrapper carries (selected entity, filters, breadcrumbs) finds no home.

**Consequences.** State behaviour is re-expressed, not inherited, so the Aurelius store specs are read as the source of assertions (ADR 053 R5). The purity check fails a state-owning `Subject`, so a slice cannot keep one by accident.

### DD-128. Aurelius dictionaries become XLIFF, migrated whole, with the JSON as fixture

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius flat-JSON dictionaries (105 keys, `en-US` and `nl-NL`) are converted in full to XLIFF catalogues for the built-in `@angular/localize` at 7.1, before any screen needs them. The Aurelius JSON is vendored into `apps/aurelius-atlas-webapp/tests/fixtures/` and a Vitest test asserts every key, English value, and Dutch value appears in both catalogues. `nx extract-i18n` maintains the template catalogue from then on.

**Reason.** The Aurelius app localises through `@ngx-translate/core` and its own `I18nService`, registered in the module constructor; this workspace localises with `@angular/localize`, whose catalogues the build compiles and which needs no service, so no runtime translation lookup survives. Converting all 105 keys at once keeps one slice responsible for the dictionary: a per-screen migration scatters the work, and the missing keys surface as untranslated Dutch long after the screen that introduced them is accepted. The vendored JSON makes completeness a checked fact that runs offline, not a claim in a pull request.

**Alternatives.** Port `I18nService` as a shim over `$localize`: keeps a `translate` pipe and a `@ngx-translate`-shaped API the workspace has replaced. Migrate keys per slice: no completeness gate, and Dutch gaps found in deployment. Machine-translate the Dutch: the Aurelius `nl-NL` dictionary is human-reviewed work, and replacing it discards that.

**Consequences.** `{{ }}` placeholders in Aurelius strings become `$localize` interpolated expressions, and the `TranslateService.get()` call sites become static messages. Aurelius keys with no consumer after 7.10 are dead weight until swept; the completeness test is what keeps them named rather than silently dropped.

### DD-129. Google Analytics and clickstream are dropped, not ported

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** `@models4insight/google-analytics` and `@models4insight/services/clickstream`, both wired by `Core.imports`, are dropped. The webapp's operational signals go to OpenTelemetry through `aurelius-atlas-observability`, as every other app's do.

**Reason.** The workspace observes itself internally and its operational data never leaves it ([ADR 016](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/016-the-system-observes-itself-internally/index.md>)). The example app's content security policy keeps `connect-src 'self'` and names only the Keycloak origins ([ADR 039](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests/index.md>)); a browser call to a third-party analytics host would need that policy opened for a second telemetry path that duplicates what OTel traces and metrics already carry.

**Alternatives.** Port it behind a config flag: keeps the egress and the policy exception available in production, which is the exposure the decision avoids. Keep clickstream to OpenTelemetry: page-view tracking is the part of it worth having, and it belongs in the observability library, not in a port of one app's vendor integration.

**Consequences.** Product usage analytics from the browser stop when the webapp replaces the Aurelius interface at 7.10; page views can be re-added to `aurelius-atlas-observability` as a deliberate feature. No Aurelius code is translated, so this is the one part of `Core.imports` that has no destination.

### DD-130. The webapp's config is a typed AppConfig, and `environment.ts` is not ported

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius `environments/environment.ts` (and its `production` flag, Keycloak settings, `shell.appName`, i18n, telemetry, and notifications blocks, all read by `Core.imports`) is not ported. The webapp reads a typed `AppConfig` from `/config.json` at bootstrap, following `apps/aurelius-atlas-frontend-example`: the file is fetched and validated before `bootstrapApplication`, and a missing, unreachable, or malformed file throws.

**Reason.** Build-time settings make one artifact behave differently per deployment, so the unit validated is not the unit that ships ([ADR 010](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/010-the-unit-validated-is-the-unit-that-ships/index.md>)), and settings arriving through one channel that fails loudly is the workspace rule ([ADR 018](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)). The Aurelius app already compiles a separate bundle per environment, and its `environment.ts` carries the Keycloak client and realm that a deployment must be free to set.

**Alternatives.** Keep `environment.ts` for dev and add `config.json` for production: two channels, and the dev one is the one developers exercise. Read settings from `NGINX_*` variables at container start: the hardened runtime image has no shell tooling to render them (the example app's `AGENTS.md` records why its nginx template is resolved by the consumer, not at start).

**Consequences.** Every Aurelius call site that read `environment.x` reads `AppConfig`, so a setting has one shape per deployment rather than one per build. The `dev/config.json` pattern means development assets are bundled only in the development build, so a real secret never rides in a production bundle.

### DD-131. Webapp purity is a checked gate, not a review convention

- **Status:** Proposed
- **Increment:** 7.0
- **Date:** 2026-10-20

**Decision.** The rules that say the webapp is not the old app are enforced by a check that runs in CI: `nx run aurelius-atlas-webapp:check-purity` greps `apps/aurelius-atlas-webapp` and `libs/angular` for `@NgModule`, `platformBrowserDynamic`, `@models4insight/`, `@ngx-translate/`, `environments/environment`, and a state-owning `new BehaviorSubject` outside RxJS interop, and fails on a match. The same rules are expressed as ESLint restrictions where the plugin supports them.

**Reason.** Four slices in, a reviewer's attention is on the feature, and a copied Aurelius file arrives with its `NgModule` and its `BehaviorSubject` attached — the exact imports the Aurelius codebase is full of, and the ones ADR 053 forbids. A rule that only a person can notice during review is a rule that decays, and the gate that refuses a change is defined once and runs everywhere ([ADR 014](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)).

**Alternatives.** Rely on code review: free, and it decays exactly when slices get large. Rely on the compiler: it catches `@ngx-translate` when the package is absent, and catches nothing about `Subject`-owned state, which compiles cleanly. Rely on ESLint alone: no rule exists for "this `Subject` owns state", so the grep carries what lint cannot.

**Consequences.** The gate is a maintenance cost of its own and must be read as a floor, not as the definition of good Angular — idioms it cannot see (`input()` versus `@Input`, control flow, `OnPush`) stay with review. Its allow-list is where an exemption is argued in the open, so an escape hatch is a reviewed change rather than a quiet one.

### DD-132. The wildcard fallback redirects to the destination, not through the root

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The Aurelius fallback `{ path: '**', redirectTo: '' }` is ported as `{ path: '**', redirectTo: 'search/browse', pathMatch: 'full' }`. The chain `'**' -> '' -> '/search/browse'` that the Aurelius router resolves in two hops is one hop here.

**Reason.** Angular 22.2's router no longer re-triggers the empty-path redirect after a wildcard redirect lands on `''` (angular/angular router fix `e9bf52aa03`, "require outlets to match a route before processing child segments"), so the literal port lands on `/` and renders a blank router outlet — verified in a browser, not theorised. SHL-05 promises the observable Aurelius behaviour: an unknown path ends on the default destination.

**Alternatives.** Keep `redirectTo: ''` and add a redirect-triggering route: a workaround whose shape exists only to dodge a router fix. Land on `/` and let the root redirect handle it: changes the observable URL (`/` vs `/search/browse`), which is the parity SHL-05 is written against.

**Consequences.** If a future Angular restores chained redirects, the one-hop form keeps working — it encodes the destination, not the chain. The `''` route remains the single definition of the default destination; the fallback names it, so a later slice that moves the default edits both lines, and `routes.spec.ts` pins both.

### DD-133. Operational telemetry lands with 7.1; the auth wiring stays with 7.3

- **Status:** Proposed
- **Increment:** 7.1
- **Date:** 2026-10-20

**Decision.** The webapp's OpenTelemetry wiring — trace and metric exporters, the tracing `ErrorHandler`, and the `traceparent` HTTP interceptor, all from `aurelius-atlas-observability` — lands with 7.1, not with 7.3. The Keycloak providers and the bearer-token interceptor stay in 7.3, which owns the auth wiring.

**Reason.** DD-129 attaches the telemetry replacement to this increment, and the shell is where the Aurelius `Core.imports` (the single wiring point that carried both GA/clickstream and the app's providers) dissolves — so the OTel half of that dissolution belongs here. The exporter endpoint is already a 7.1 config field (SHL-02), the image already proxies `/otel/` (SHL-11), and the CSP already allows it (SHL-11); deferring the wiring to 7.3 left the plumbing with no consumer. Telemetry is also the shell's own operational signal — the earlier it covers the app, the more of the port it observes.

**Alternatives.** Wire everything in 7.3: keeps one bootstrap commit, but leaves DD-129 unsatisfied for a whole increment and pairs telemetry with auth for no dependency that exists — the OTel providers need only `AppConfig`. Wire traces only, metrics in a later slice: the metrics provider is the same call with a metrics exporter; splitting them adds no review value.

**Consequences.** The e2e `/otel/` proxy test (SHL-11) gains a producer: the served app now exports through it. The interceptor covers the API calls 7.3 adds, so trace propagation is in place before the first request exists. The bootstrap in `app.config.ts` matches the example app's provider set minus Keycloak, which is the visible difference between the two files.

### DD-134. The design-system slice ports the in-use components, not the library

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** 7.2 ports the eight `@models4insight/components` folders the Aurelius search/browse surface imports — `accordion`, `modal`, `hero`, `simple-search-input`, `sortable-table-shell` + `sortable-table`, with `card` + `pagination` already present — and defers the rest of the 34-folder library to the slices that consume them: `select`/`quickview` to 7.7, `markdown`/`tree`/`date-picker` to 7.6, the project/branch/user/permission modal family and the two search-input engines to 7.8 at the earliest.

**Reason.** All 29 import sites in `apps/atlas/src` live under `app/search/**`; the deferred families are imported by screens that arrive in 7.4–7.9, and a fifth of them by nothing in the ported surface at all. Porting a component before its screen exists means writing its stories and its specs against a guess of its caller, and ADR 053 R4 asks each increment for one readable capability, not a bulk migration. The leaf primitives the legacy app styles with (buttons, tags, switches, checkboxes) are Bulma classes in templates, not components, so they need no port.

**Alternatives.** Port all 34 folders: a PR roughly four times the budget of root AGENTS.md, most of it unexercised. Port none and build components as screens need them: each feature slice then invents its own card and modal, which is the shared-once rule (ADR 053 R7) dissolved into ten slices.

**Consequences.** The roadmap row for 7.2 says "legacy shared components"; it now means the in-use set, and the deferred folders are named in the increment's not-in-scope table with their slice. A later slice that needs a deferred component adds it under its own increment, where its caller can be reviewed with it.

### DD-135. Component services dissolve into signal state; nothing is ported as a store

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** The services the legacy components carry are dissolved rather than ported. `SortableTableShellService` (a redux `BasicStore` holding sort, page and selection) becomes `model()` state on `SortableTable`; `AbstractControlShell` and its context objects become plain inputs with Bulma markup inlined; `FuzzySearchInputService` and the `MonitorAsync` plumbing are not ported at all; `PageScrollService` in `Hero` is dropped for the router's own scroll restoration. Where legacy state was persisted (sort and page survive navigation via the store), persistence moves to the caller.

**Reason.** The custom store is the pattern the port exists to remove (DD-127, ADR 053 R3), and the purity gate refuses a state-owning `BehaviorSubject` in this tree. The state those services hold is view state — which column is sorted, which page is open — which is exactly what a `model()` is for, and a component that owns it in a signal can be rendered in isolation in a story. Persistence is not the component's concern: the browse screen keeps its sort in the URL (7.5), which is also what makes it shareable.

**Alternatives.** Port the store as a signal-based service in the lib: keeps the file count low and gives every table a store it does not need, and a lib that owns application state is what `libs/angular/AGENTS.md` forbids. Keep persistence in the component with a `localStorage` key: works for one screen and breaks the moment two tables share a route, as the browse surface does.

**Consequences.** Two legacy outputs (`rowIntersectionChanged`, from the intersection observer used for infinite scroll) are dropped: paging is explicit, so the infinite-scroll signal has no consumer. The legacy Jest assertions about store interaction are re-expressed as component-level assertions (UIC-06), so the behavioural knowledge survives while the abstraction does not.

### DD-136. Shared chrome strings are localisation units keyed by the legacy dictionary paths

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** A shared component's own strings — "Previous", "Next page", "No data available", "Toggle content", the quickview tooltips — are `i18n` units in the component's template, and their ids reuse the legacy `components.*` dictionary paths (`@@components.sortableTableShell.previous`). The legacy component library's translations (7 keys, `en-US` and `nl-NL`) are vendored as fixtures beside the app dictionaries, and the webapp's generator bridges them into the same XLIFF catalogues that carry the app's 495 strings. Text that belongs to a caller (a modal title, a table's column names) is passed as content nodes, not as a string input.

**Reason.** WBP-05 forbids literal prose in a template, and the Dutch translations of these seven strings already exist — dropping them would ship an untranslated table header in the one language the port promises. The bridge keys catalogues by dictionary path (DD-128) so a reviewer can diff a unit against the legacy entry, and the completeness spec proves both locales; reusing the legacy paths keeps component chrome and app text in one catalogue with one mechanism. Content nodes for caller-owned text is what the built-in localisation cannot do for a string input: a translated string that arrives as an `input()` is invisible to `extract-i18n`, so it can never be translated.

**Alternatives.** `output()` events with the app supplying every string: no component is usable in a story without its caller's dictionary, and the example app's existing usage breaks (UIC-09). A `$localize` call per string: works, and loses the dictionary path that ties a unit to its legacy source.

**Consequences.** `nx extract-i18n aurelius-atlas-webapp` now emits the lib's units, because the app builds the library from source through the `tsconfig.base.json` path alias. A component string with no legacy key (a state the Aurelius component never had) gets a new id under `components.*` and gains a Dutch entry in the fixtures, so the completeness gate is the point where a new chrome string is argued.

### DD-137. The purity gate is made executable over `libs/angular`

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** `check-webapp-purity.sh` gains the `libs/angular` tree it was documented to grep (DD-131), and `aurelius-atlas-ui` gets a `check-purity` target wired as a `dependsOn` of its `test` target, so CI enforces the legacy-construct ban on the library as well as the app.

**Reason.** DD-131 states the gate greps `apps/aurelius-atlas-webapp` and `libs/angular`; the script greps only the app's `src/`. The claim was written when the library held six hand-written components and 7.2 is the first slice to fill it with ported code — exactly the material a copied Aurelius file arrives in, with its `NgModule` and its `BehaviorSubject` attached. A rule that is documented and not checked is the failure mode DD-131 was written against.

**Alternatives.** An ESLint rule set in the library: carries what a linter can see (`@NgModule`, a banned import) and nothing about a service that owns state in a subject, so the grep is still needed. A shared CI step over both trees: correct, and it puts the rule outside the project that documents itself (ADR 003), where a reviewer editing the library will not find it.

**Consequences.** The gate runs twice per CI job, over two roots, from one script — so one list of forbidden constructs stays the definition. Any exemption is an allow-list entry in that script, a reviewed change in the open (DD-131's consequence), and 7.2's ported components are expected to need none: the six existing library components are already clean.

### DD-138. The Storybook preview loads `@angular/localize/init`

- **Status:** Proposed
- **Increment:** 7.2
- **Date:** 2026-10-20

**Decision.** `.storybook/preview.ts` imports `@angular/localize/init` as its first side-effect, the same polyfill the webapp build loads through its `polyfills` option.

**Reason.** A chrome string in a component template (DD-136) compiles to a `$localize` call. Under the app's build that global exists; under Storybook's build it does not, so every story whose template carries an `i18n` attribute throws `$localize is not defined` at render — the `i18n` bridge silently made every story with chrome text unrenderable, and the failure surfaces only in the browser, not in a unit test (Vitest never runs the compiled template through localize).

**Alternatives.** A `polyfills` option on the Storybook targets: the executor schema does not accept one. A no-op `$localize` in a story helper: works, and re-implements the polyfill by hand, so it drifts from the real one.

**Consequences.** Stories render the English source text, which is what a visual baseline and the `play()` queries assert on. A story that needs the Dutch text is out of scope — translation is a per-app build-time concern; the completeness spec (SHL-08, UIC-04) is what proves the catalogues carry both locales.

### DD-139. The client owns the base URL; the proxy forwards the prefix untouched

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The REST client composes every URL from the injected `API_BASE_URL` token (`/api` from runtime `/config.json`), and the webapp's proxies — dev and e2e — forward `/api` to the Atlas server with the prefix intact. The Aurelius mechanism (relative URLs resolved against `<base href>`, prefix injected by the deployment proxy: dev `proxy.conf.json` rewrites `/atlas` → `:21000/api/atlas`, k8s Apache `ProxyPass` rewrites `/<ns>/atlas/atlas/` → `atlas:21000/api/atlas/`) is not ported.

**Reason.** The 7.0 audit asked how the legacy app reaches the server and found: nowhere in the code — the coupling lives entirely in deployment. That is invisible to the compiler, untestable against a stub, and the reason the legacy client cannot say which API it speaks to. Aurelius Atlas inverts it: the client names its base URL from config (DD-130's runtime-settings channel), the proxy is a dumb forwarder, and a deployment moves the API by serving a `config.json`, not by editing proxy tables. The server's routes already carry the `/api/atlas/...` prefix, so a rewriting proxy would double-strip it; forwarding untouched is the composition that type-checks (`${apiBaseUrl}` + `/atlas/v2/...`).

**Alternatives.** Port the Aurelius split (relative URLs + rewriting proxy): keeps parity with a deployment model this workspace does not share, and re-hides the coupling. Have the browser call the server origin directly (`https://server:21000`): needs CORS policy and per-deployment origins in the CSP, reopening the same-origin boundary ADR 039 closes.

**Consequences.** The webapp's dev proxy no longer points at the FastAPI example's `:8000` (the copied line retargets at `:21000`); the example app keeps its own chain until 7.10 retires it. The e2e nginx's `/api/` placeholder comment ("the Atlas API server joins this proxy when 7.3 wires real data") is redeemed by DD-142.

### DD-140. The REST client ports the live surface; the search client is redesigned in 7.4

- **Status:** Proposed (the lineage/validate exclusion is superseded by [ADR 055](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/adr/055-the-lineage-chain-is-a-named-data-surface/index.md>) — increments 8.x build those backends; the App Search exclusion stands)
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The ported client covers the endpoints the server implements today: the typedefs of 1.6 (`/api/atlas/v2/types/**`) and the admin trio (`version`, `status`, `session`). The legacy search stack — `AppSearchService`, the engine subclasses, the `{provide: AppSearchService, useClass: AtlasEntitySearchService}` alias, \~300 lines of App Search DTOs — is not ported in this slice. 7.4 designs the search client when browse consumes it, against `/v2/search/basic` (increment 4.1), not against the App Search shape.

**Reason.** The audit found the Aurelius search posts to DuckDuckGo Enterprise App Search engines (`/elastic`, `/gov_quality`, `/data_quality`) — a third-party search backend Aurelius Atlas does not have and will not gain: search is Elasticsearch-native here (ADR: the store). The server's Atlas-native search is increment 4.1, planned. Porting the App Search DTOs now would ship typed structs for a wire format no server speaks, specs asserting calls that answer 404, and a mapping layer 4.1 reworks anyway (DD-140's consequence). The rest of the legacy surface (entity, glossary, relationship, lineage, validate, dashboard) has the same property in smaller doses: endpoints 2.3+ have not landed, and the lineage/validate/dashboard backends are separate services with no Aurelius equivalent.

**Alternatives.** Port all 65 files now: a client that lies about the system, with dead code at day one (the legacy app itself leaves half of it unused). Port search against the legacy shape with an adapter: the adapter's shape is guesswork against an unbuilt endpoint.

**Consequences.** The client grows one method-set per server increment — each method lands testable against the real server, and the specs stay honest through 7.4–7.9. The legacy's service+free-function duplication (e.g. `EntityAPIService.getEntityById` and `get-entity-by-id/`) collapses to one method each as each set is ported.

### DD-141. Auth is guarded at the app root; the bearer token is stated inert until 6.1

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The webapp wires the example app's Keycloak set — `provideKeycloak` (check-sso, silent-SSO, DD-004's in-memory token store), `createAuthGuard` on the app root route, `includeBearerTokenInterceptor` on `/api` — and guards every route. The Aurelius `libs/authentication` (raw `keycloak-js`, `ReplaySubject` auth state, manual `updateToken(5)` loop, guard applied by `Shell.childRoutes`) is not ported (WBP-02). The Atlas server does not verify tokens until 6.1; the webapp sends the bearer token anyway.

**Reason.** The legacy shell guards every search route (`Shell.childRoutes` with `requiresAuth: true`), so parity of behaviour means guarding. keycloak-angular's `createAuthGuard` declares the guard where routing is declared — the app root — instead of a library wrapping routes from the outside; the Aurelius `AuthTokenProvider` constructor-injection (each API client wiring its own auth interceptor) disappears with the interceptor's URL-pattern config. The token is sent from day one so 6.1 activates authentication with no webapp change, and ADR 038's precedent covers the state it describes: "every authenticated person can do everything" is a stated condition of the pre-6.2 system, not a security property — the same is said here of the pre-6.1 server.

**Alternatives.** Ship providers without guards until 6.1: leaves the app public in production while the product's own UI never was; the e2e suite would also keep testing an unauthenticated flow nobody uses. Enforce per-screen guards as each screen arrives: the root guard is one line and no screen can forget it.

**Consequences.** Dev and e2e now need Keycloak up (serve `dependsOn` gains it; the e2e suite gains the example's authenticated-login fixture as `aurelius-writer`). The unauthenticated redirect-to-sign-in is itself tested (APC-05) — the sign-in page is the app's first collaborator, and the flow is proven in CI, not assumed.

### DD-142. The webapp e2e stack runs the real Atlas server behind the proxy

- **Status:** Proposed
- **Increment:** 7.3
- **Date:** 2026-10-20

**Decision.** The webapp's e2e compose grows an `atlas-server` service (the image its own `docker-build` produces, TLS, joined to the dev Elasticsearch network), and the e2e nginx `/api/` location proxies it with CA verification. The placeholder assertion (`/api/` → Keycloak, `{"realm": "master"}`) is replaced by `GET /api/atlas/admin/version` answered by the real server.

**Reason.** The placeholder nginx comment records the intent: "the Atlas API server joins this proxy when 7.3 wires real data". A proxy test that passes against a stand-in backend proves only nginx config; with the server in the stack, one e2e request proves the whole chain this slice builds — nginx location, TLS verify, prefix forwarding (APC-08), server routing, ES store — against the parity-tested surface. The image and its env already exist for the server's own e2e; reusing them is copying, not building.

**Alternatives.** Keep Keycloak as the `/api/` backend: cheapest, and the chain stays untested until 7.4 — the same gap 7.1 accepted with a comment; 7.3 is where the comment matures. Mock the server in nginx config: a mock that answers like the server is a second server to maintain.

**Consequences.** Webapp e2e `dependsOn` gains `aurelius-atlas-server:docker-build` and the dev Elasticsearch `up`; the suite's boot chain lengthens by one container (ES is already up for the server's own e2e, so cache-hit order matters little). The dev-pair `nx serve aurelius-atlas-server` + `nx serve aurelius-atlas-webapp` becomes the documented development loop.

### DD-143. The landing page is ported statically; search affordances and Shell chrome join the search slice

- **Status:** Proposed
- **Increment:** 7.5
- **Date:** 2026-10-20

**Decision.** 7.5 ports the Aurelius landing page (`browse`) as the static screen it is: hero, the three context cards, and the info modals with their hardcoded type tables. The cards' `simple-search-input` fields and `directTo*` "explore" buttons — every affordance that sets `SearchService.query/filters` and routes to `/search/results` — are not ported in this slice, and the Shell chrome (header/footer, whose centrepiece is the global search bar) is deferred with them. Both join the search slice (7.4), which the user has placed on hold until the server search API exists (4.1 basic search, 2.3 entity read).

**Reason.** The landing page's content — cards, info modals, type tables — is entirely static and fully keyed in the XLIFF bridge, so the screen can be ported and proven today; its search affordances are navigation into a screen that has no API, and shipping a search box whose results page 404s is the speculative build DD-140 refuses, one level up. The Shell is deferred for the same reason in chrome form: Aurelius's header carries the global search bar and session UI, so wiring the chrome is one decision taken together with the search entry point, not two. The user's 2026-10-20 direction ("port the landing page; hold off on any search until the API is ready") fixes exactly this seam.

**Alternatives.** Port the cards with their search fields wired to a stub: the affordance works in dev and dies in the e2e stack's real server — a UI promise the increment cannot keep. Ship the Shell now and hide its search bar: chrome with its main control removed is neither the legacy screen nor a clean seam.

**Consequences.** The 7.5 page has no route out except the info modals (BRW-06); 7.4 re-adds the affordances as part of the search slice, at which point the Shell row of the 7.x ledger is taken with it. The 7.5 roadmap row is retitled to the landing page; browse domain grids, if kept from the legacy design, follow with the search slice.

### DD-144. i18n ids carry no description suffix; the bridge key must equal the extracted id

- **Status:** Proposed
- **Increment:** 7.5
- **Date:** 2026-10-20

**Decision.** An `i18n` attribute in the webapp or `aurelius-atlas-ui` is written `i18n="@@<dictionary.path>"` only — never `@@<id>|<description>`. Where a unit wants a translator note, the note lives in an adjacent comment. `aurelius-atlas-ui`'s four chrome units (`components.sortableTableShell.previous|next|noData`, `components.accordion.toggleContent`) drop their `| … (DD-136)` suffixes, and the `SortableTable` component drops `TableColumn`/`TableRow` from its `imports` (caller-projected directives, NG8113).

**Reason.** Angular joins the `|description` half into the extracted trans-unit id, so the key-keyed bridge (DD-128, DD-136) can never match such a unit: `extract-i18n` emits `components.sortableTableShell.next|Aurelius table shell …` where the catalogue carries plain `components.sortableTableShell.next`. The nl-NL build then answers "No translation found" for the unit — the chrome string ships untranslated in the one language the bridge exists for. The defect was latent in 7.2 (the ui-lib has no app build of its own to surface it; the accordion unit never matched, unnoticed) and surfaced in 7.5 when the landing's info-modals pulled the sortable table and its pagination into the app's translation graph. The completeness spec cannot catch it: it compares the committed catalogues to the fixtures, and extracts ids only as a set-diff (`UIC-04` scans template `@@components.*` literals, which include the suffix). The production build is the gate that sees it. NG8113 has the same root as the import fix: the table's own template never applies the column/row directives — callers do — so listing them is a lie the compiler now flags once the table is app-compiled.

**Alternatives.** Keep the descriptions and teach the bridge to split on `|`: one more key-mangling rule in the generator for a note the XLIFF `<note>` element (which `extract-i18n` emits from the marker's description) already carries — the catalogue already proves round-tripping works without it. Register the chrome strings in the catalogues *with* the suffix: breaks the "id equals the legacy dictionary path" invariant DD-136 states in its title.

**Consequences.** `nx extract-i18n aurelius-atlas-webapp` output is now a strict subset of the bridge catalogue, so `nx build aurelius-atlas-webapp` is warning-clean and can be used as the id-parity gate; the 7.2 spec's chrome-string rule (UIC-04) is unchanged, and the accordion's toggle-content unit starts translating in nl-NL for the first time.

### DD-145. The Shell chrome is ported search-free; the root composes header and footer

- **Status:** Proposed (the "navbar search bar" wording superseded by [DD-218](<#dd-218--74-splits-in-two-and-the-search-bar-lands-in-the-hero-the-list-is-infinite-scroll>))
- **Increment:** 7.11
- **Date:** 2026-10-20

**Decision.** The Aurelius chrome (header, footer) is ported now, on the user's request, as its own slice (7.11), composed directly by the root component — `Header` (the 7.2 ui-lib component) over the router outlet, footer below. What is ported: the brand (app name from `/config.json`, linking to the default route), the Documentation link, the language dropdown, the account dropdown (identity, Keycloak account console, logout), and the copyright footer. What is not: the global search bar and nav buttons (they join 7.4, unchanged from DD-143's reasoning), the PWA install/update buttons (no service worker is ported), the Models4Insight services dropdown (not part of this product), the sticky loading/pipeline block (nothing to track yet), and the login button (every route is guarded, APC-05 — the logged-out navbar is unreachable). The navbar is not `is-fixed-top`. Switching language is a full-page navigation into the locale tree, not ngx-translate's runtime swap.

**Reason.** DD-143 deferred the chrome *with the search bar* because wiring them was one decision; the user has since asked for the shell as its own deliverable, so the seam moves: the frame is orthogonal to search, and a screen wearing its header/footer is strictly closer to the product than a bare outlet. DD-143's search half stands unchanged — this entry supersedes only its Shell-chrome sentence. The deferred controls each fail a test this workspace already enforces: an install button with no service worker is a promise the build does not keep; a services dropdown points at products outside this repo; a login button behind a guard is dead markup; a loading bar has no long navigation to track while the only screen is static. Aurelius's `Shell` module, its service (token refresh on window focus — keycloak-angular owns refresh, DD-141) and its reusable-route strategy are Redux-era plumbing the port's idioms replace (DD-135).

**Alternatives.** Port the shell wholesale with the deferred controls hidden behind config flags (Aurelius's own `standalone`/`hideDocumentation` knobs): config that only one deployment ever flips is dead code (the atlas environments never set them); the user asked for the shell, not for a feature-flag audit. Wait for 7.4: the chrome is search-independent and the user wants it now.

**Consequences.** The 7.11 navbar is static; 7.4 adds the search bar and nav buttons to it, at which point `is-fixed-top` and the content offset return together with the sticky loading bar (a pinned header is a layout contract, not a class). The root's "bare outlet" spec (SHL-03, 7.1) is superseded by SHC-01 — the Aurelius root *is* the shell, and the reading that motivated 7.1's placeholder retires. The shell's chrome strings are new vendored fixtures (`shell.header.*`, `shell.footer.*`), bridged like the components dictionary (DD-136), so UIC-04's invented-string gate extends to them.

### DD-146. Session chrome injects the keycloak-js `Keycloak` instance, not keycloak-angular's `KeycloakService`

- **Status:** Accepted
- **Increment:** 7.11
- **Date:** 2026-10-20

**Decision.** `Session` and `ShellHeader` inject the `Keycloak` client instance (keycloak-js) — the token `provideKeycloak` registers — for the identity read (`tokenParsed`) and for `logout()`. keycloak-angular's `KeycloakService` is not injected anywhere.

**Reason.** `KeycloakService` is the deprecated pre-v19 class: v21's `provideKeycloak` provides the `Keycloak` instance and the event signal and does **not** register `KeycloakService` (the library's own services and guards inject `Keycloak`, e.g. `includeBearerTokenInterceptor`, `createAuthGuard`'s `AuthGuardData.keycloak`). Injecting the not-provided class crashes the production image at boot (NG0201 NullInjectorError, found by the 7.11 e2e run: every authenticated scenario errored in the guard, where the chrome renders). Unit specs missed it — they mock the token; the dev server never renders the chrome before the guard redirects, so only the built image exercised it.

**Alternatives.** Provide `KeycloakService` manually (`useExisting: Keycloak` -style): re-provides a deprecated facade for a class slated for removal. `inject(KEYCLOAK_EVENT_SIGNAL)`: a signal wrapper, not the client — no `logout()` on it.

**Consequences.** SHC-05/SHC-08's "Keycloak client" is now precise: the keycloak-js instance. Spec test providers use `{ provide: Keycloak, … }`. 7.4's session-touching code follows the same token.

### DD-147. Dev Keycloak users carry `default-roles-master` explicitly

- **Status:** Accepted
- **Increment:** 7.11 (dev infrastructure)
- **Date:** 2026-10-21

**Decision.** The dev users in `dev/keycloak/import/master.json` (`aurelius-writer`, `aurelius-reader`) declare `"realmRoles": ["default-roles-master"]`.

**Reason.** The SHC-05 Account-security link opens the Keycloak Account Console, whose REST calls (`/realms/master/account/*`) require the `account` client's `manage-account`/`view-profile`; those roles reach a user only through `default-roles-master`'s composites. Keycloak's realm import does **not** auto-grant the realm default role to imported users, so the dev users reached the console with no roles and every REST call 401s — the console renders "Something went wrong". Verified live: with the role granted, the console's profile page renders; without it, the same session 401s on `supportedLocales` and the account root. The Admin REST cannot repair a running realm here (every `role-mappings/realm` POST answers 404 "Role not found" for these users), which makes the import file the single declarative place the grant can live.

**Alternatives.** Grant the roles per user through the admin console by hand: invisible to new clones, lost on stack recreate. Add the account client roles directly to the users: duplicates what `default-roles-master` already composites and drifts when Keycloak version changes reshape that role. A `defaultRoles` realm attribute (makes the role default for users created after import): does not reach the users the import itself creates.

**Consequences.** The Account Console works for both dev users, dev and e2e. Applying the change to a running stack requires recreating the users — a boot re-import skips an existing realm wholesale — the recipe is in `dev/keycloak/AGENTS.md`. New realm-default-role needs (e.g. `offline_access` for refresh tokens) arrive here, not per client.

### DD-148. The Aurelius brand lands on Bulma 1 tokens, light-forced, legacy metrics pinned

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** The Aurelius palette and the legacy chrome metrics ship as Bulma 1 CSS custom properties in `@aurelius/atlas-brand` (SHM-01..04): the Aurelius blue as `primary`/`link`, Bulma 0.9.4's greys (`#f5f5f5` light/navbar bands, `#363636` invert), the blue footer band, BlinkMacSystemFont-first stack, 16px, 1.5 line-height, `#4a4a4a` ink, 4.25rem navbar. They are emitted after Bulma's own `:root`, on `:root` for the global tokens and on `.navbar`/ `.footer` for the ones Bulma scopes on its components. Light is forced with `data-theme="light"` on the document root; the brand tokens live outside the `:root:not([data-theme])` scheme machinery so a future dark scheme keeps them. The sticky footer is a flex-column body + `.is-tall-container` band (`flex: 1 1 auto`), the pinned navbar is `is-fixed-top` + `has-navbar-fixed-top`, navbar content sits in a Bulma `container` (SHM-05).

**Reason.** The legacy (Bulma 0.9.4) baked its look through SASS variables; the workspace is on Bulma 1, which reads CSS custom properties and defaults to a different design (Inter, 1rem, turquoise primary, white footer, 3.25rem navbar) — without the overrides the app renders the wrong brand entirely. Two Bulma 1 traps found by measurement against the live demo: component-scoped tokens (`.navbar`/`.footer` re-declare their own background, shadowing `:root`), and `hsl(var(--h), …)` requiring degree-unit hues (a percentage hue silently drops every `has-background-*` rule — the demo's `#f5f5f5` band came out transparent). Light-forcing is Bulma 1's scheme machinery, one attribute; the brand colours stay scheme-independent so the switch has nothing to re-brand. The flex-column footer replaces the legacy's `.is-tall-container{min-height:100vh}`-inside-fixed-padding trick with the modern equivalent (DD-145's static-navbar reading is superseded — the pinned navbar is what the demo ships).

**Alternatives.** Stay on the Bulma-1 defaults and re-skin component by component (the 7.2 status quo): every new surface drifts from the legacy brand. Port `@models4insight/styles` (DD-126 reversal): a Bulma 0.9.4 theme package, the dependency the workspace adopted away from. Pin the legacy `has-background-*` classes only (no tokens): the demo's own utility CSS, and the token overrides are the one lever — the utilities read the same HSL triplets.

**Consequences.** The chrome matches the reference demo on every measured value (SHM-06's e2e scenarios pin them). The theme switch is a later slice: one attribute (`data-theme`), no re-brand. Bulma utilities read the brand colours (`has-background-light` = `#f5f5f5`), so 7.4+ surfaces inherit the look. The greys are Bulma 0.9.4's pair, not Bootstrap's — the brand library's `$gray-*` stays for the `is-dark` pair (`#363636`).

### DD-149. Critical-CSS inlining is off: the zoneless CSR app never swaps the print sheet

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** The webapp's production build sets `optimization.styles.inlineCritical: false`. The stylesheet loads as a normal render-blocking `<link>`; nothing is inlined into `index.html` and no `media="print"` swap is involved.

**Reason.** Angular's critical-CSS inliner (beasties) rewrites the stylesheet to `media="print"` and ships a script that swaps it back at load. In this zoneless CSR app the swap never runs (e2e measurement: every browser, the sheet stayed on `print`, 3,024 rules inert), so the app rendered from the \~115 rules the inliner had copied into the HTML — Bulma base styles applied, brand overrides on `.navbar`/`.footer` and utilities like `has-background-light` did not (transparent bands, no blue footer). The inliner has no element to inline *for* in a CSR shell — `index.html`'s body is the app root and the router content appears after boot, so "critical" is meaningless here. Dev mode (`optimization: false`) never showed this, which is what made the demo-match in dev coexist with broken e2e.

**Alternatives.** Keep inlining and fix the swap script (it is Angular generated — no supported knob). Load the sheet with a forced `media="all"` (build emits the print attribute as part of the inliner's output — off is the supported switch). Serve with SSR/prerender so the inliner has real content (7.x is a client-rendered SPA; the dashboard is a separate app).

**Consequences.** First paint ships the full stylesheet (\~770 kB minified, gzip \~90 kB) — the same payload the legacy demo ships. The e2e suite now measures the CSS the browser actually applies. If LCP ever matters, re-measure with the inliner enabled in a browser that executes the swap script before re-enabling.

### DD-150. The sticky footer is the legacy rule verbatim; page content sits on Bulma's grid

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** `.is-tall-container` is ported verbatim — `flex: 1 1 auto` **and** `min-height: 100vh` (the legacy `shell.component.scss`) — so the outlet band is a full viewport and the footer begins at the fold, off the first screen. Page content is inset by Bulma's grid, not hand-rolled margins: the landing wraps in `section.section > div.container` (the anatomy every legacy routed page uses — `details`, `domains`, `create-entity` all start with `div.container`), the footer keeps its `container` (the legacy footer's own anatomy), and the `#f5f5f5` band behind the content stays full-bleed. SHM-05/SHM-07.

**Reason.** Measured against the live demo: its footer starts at y=1346 in a 900px viewport (band `min-height: 900px` — the footer is never on the first screen), while the first-cut port (flex-grow only) filled the band to exactly the fold, pulling the footer into it. And the demo's landing content is inset on Bulma's responsive grid (box x=56 at 1280, the navbar brand's column), while the port rendered edge-to-edge. Both are the legacy's own rules — the port had read `.is-tall-container` selectively and had not ported the page wrapper at all.

**Alternatives.** Keep flex-grow-only (footer flush at the fold): it diverges from the demo on the one axis the user measured — "the footer should always be below the fold". Hand-rolled page padding (`.is-tall-container { padding: … }`): invents a grid Bulma already owns; the `container` is responsive (fixed widths per breakpoint, 32px margins below desktop), a hand-rolled inset is not. `section.hero` instead of `section.section` (the demo's landing hero is a hero): the teal hero is the 7.4 search slice, out of scope here.

**Consequences.** The landing matches the demo's measured insets (box x≈56 at 1280) and the footer is below the fold at any viewport. The `section > container` wrapper is the pattern for 7.4+ routed pages (details, search results) — they inherit the grid from their first element. `min-height: 100vh` on the band means short pages scroll the footer into view; that is the legacy behaviour the demo shows.

### DD-151. The brand re-emits Bulma 0.9.4's text ramp, not just the body metrics

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** SHM-03 covers the whole type ramp, not only the body. The brand library emits Bulma 0.9.4's neutral greys on Bulma 1's **channels** (`--bulma-text-h/s/l`, `--bulma-text-strong-*`, `--bulma-text-weak-*`), so every derived token — `text`, `text-strong`, `text-weak`, the navbar and dropdown ink chain — resolves to the legacy ramp: `#4a4a4a` body/box/ content ink, `#363636` headings, `#7a7a7a` weak. The weights Bulma 1 moved are pinned back on the selectors that scope them (`.title`/`.subtitle` 600, `.button` 400) plus `--bulma-strong-weight: 700` and `--bulma-navbar-item-color: #4a4a4a` (the demo's navbar ink is the body ink, links and `strong` alike). `.content` is `#4a4a4a` with `#363636` 600 headings. SHM-03.

**Reason.** Reviewing the font story against the live demo: DD-148 pinned the body (stack, 16px/1.5, `#4a4a4a`) and the chrome bands, and every body-level value matched — but Bulma 1 re-tinted its whole grey ramp 221 degrees (`text` `#4a5568`, `text-strong` `#2e333d`) and re-weighted the ramp (title 600→800, strong 700→600, button 400→500). The app rendered with a blue-grey cast: titles `rgb(46,51,61)` at 800, box ink `rgb(64,70,84)`, navbar links `#535353`, dropdown ink `#404654` — none of them the demo's values. The size scale (`is-2` 40px/45, `is-6` 16/18, dropdown 14px, the 4.25rem bar) was already identical; only the ramp diverged. Pinning the channels (not the derived tokens) fixes the entire chain at once, including selectors the brand file does not enumerate.

**Alternatives.** Override each derived token at every use site (`.title { color }`, `.box { color }`, …): whack-a-mole across Bulma's long hsl-composed chains (the navbar dropdown composes `h`/`s` from the scheme with the `text` lightness — enumerating all compositions misses them, as the first cut did). Pin only the body (DD-148 as landed): the user-visible difference is exactly what the review found — a blue-grey app where the demo is neutral grey.

**Consequences.** Every landing text/weight pair is demo-parity, pinned by `test__type_ramp_matches_the_legacy_page`. The emission is scheme-independent (channels live outside Bulma's `data-theme` blocks), so a future dark scheme inherits Aurelius' neutral ramp machinery unchanged. `--bulma-text-rgb`-style companions are emitted for `text`/`text-strong`/`text-weak` (consumers read them raw).

### DD-152. The accent ramp: primary stays Bulma teal, the accents take the Bootstrap map

**Decision.** The brand library overrides the **accent** colours, not primary. `--bulma-primary` keeps Bulma's own teal `#00d1b2` (identical in 0.9.4 and 1.x — the demo's landing icons, hero buttons and `.is-primary` fills are teal, measured `rgb(0,209,178)`, hover `rgb(0,196,167)`), with only `--bulma-primary-invert-l: 100%` pinned: Bulma 1 derives solid-fill ink from `primary-05-l` (6 % — near-black) where 0.9.4 and the demo use white. The Bootstrap map the legacy theme applied to its accents is re-emitted from `$bulma-accent-overrides`: `link` `#0073dd`, `info` `#17a2b8`, `success` `#28a745`, `warning` `#ffc107`, `danger` `#dc3545`, each with its value, `-base`/`-rgb` and `h`/`s`/`l` channels, and its solid-fill ink pinned white — except `warning`, which keeps Bulma's dark ink (the demo's `btn-warning` text is `rgba(0,0,0,.7)`). The navbar's hover/active band renders `#f5f5f5` with `#000` ink (the demo's `.navbar-link:hover`); Bulma 1 derives it from the hero chain and renders a blue-tinted plate. The plate composes `hsl(navbar-h/s, navbar-item-background-l + hover-delta, a)`, so the brand neutralises the `navbar` hue/saturation channels (the DD-151 pattern) and sets the hover/active deltas to the band grey's 96 % lightness; Bulma 1 has **no** hover-ink token at all (0.9.4's `navbar-item-hover-color` is gone), so the black ink rides on a scoped hover rule mirroring Bulma's plate triggers. SHM-04.

**Reason.** The 7.12 first cut mapped `"primary": $blue` onto `--bulma-primary` as a placeholder (the shell chrome is blue-banded, so primary *looked* like `#0073dd`). Measuring the demo's landing page shows the icons the user flagged — the business/technical/governance card glyphs, `has-text-primary` — are Bulma teal `rgb(0,209,178)`, not blue: `#0073dd` in the legacy theme is `$link` (anchors) and the footer band, never `$primary`. Bulma 1's defaults for the untouched accents (its own cyan/green/yellow/red) are likewise not the demo's — the demo carries the Bootstrap palette, which the legacy `@models4insight/styles` theme mapped onto Bulma's accents (the same map SHM-04 already uses for `link`/footer). Fixing primary and leaving the accents on Bulma's defaults keeps half the deviation.

**Alternatives.** Keep primary `#0073dd` (as landed): every `has-text-primary`/`is-primary` surface — the landing icons the user compared side by side — stays blue where the demo is teal. Port all of Bulma 0.9.4's derived accent tokens (each family emits \~30 variables): unnecessary, the channel triple plus `-base`/`-rgb`/`-invert-l` covers what Bulma 1 composes at runtime.

**Consequences.** The landing page's icon highlights match the demo. `$bulma-token-overrides` shrinks to the four chrome greys; accents have their own `$bulma-accent-overrides` map (value + ink lightness). The navbar hover/active emission joins the navbar block (DD-148's "scope on `.navbar`" pattern), with the one ink rule outside the token machinery — the first brand rule that must set a state colour Bulma 1 never tokenised. Pinned by `test__accent_ramp_matches_the_demo`.

### DD-153. The mobile burger chrome: grey burger, blended dropdowns, legacy logout anchor

**Decision.** The brand carries the legacy theme's mobile navbar on Bulma 1: `--bulma-navbar-burger-color: #4a4a4a` with the burger **channels** set black (the hover/active plate composes them at 10 %/20 % alpha — 0.9.4's plate is `rgba($black, .1)` over the band, Bulma 1 tints it from link), and `--bulma-navbar-dropdown-arrow: #000` (the legacy pins `$navbar-dropdown-arrow: $black`; Bulma 1 derives it from link). The selected plate (`.is-active`, the locale's current item) lands on white/`#000` (the demo's measured pair — 0.9.4's, Bulma 1's default is the link-blue plate). Under `max-width: 1023px` the burger menu's `.navbar-dropdown` blends into the band (0.9.4 zeroes its background/colour/padding — Bulma 1's dropdown-item plate rule is **not** media-scoped, so its items render as white tiles on the grey band) and the dropdown chevron is hidden (Bulma 1 regression jgthms/bulma\#4173: the `%arrow` placeholder's `:not(.is-arrowless)` display beats the media rule's plain `.navbar-link::after`). The Logout item is the legacy `a.navbar-item[role=button]` — navbar ink, no `has-text-danger` (the legacy shell has none; the dropdown ink chain styles anchors, a `<button>` keeps the UA's centred text and the dropdown plate's white tile). SHM-04/SHC-05.

**Reason.** Reviewing the mobile chrome: the burger and its hover plate rendered Aurelius blue, the logout item sat centred on a white tile inside the grey menu, and the menu's dropdowns showed as white panels with blue chevrons. The legacy theme (`.scratch/aurelius` `libs/styles/src/styles/_theme.scss`) sets exactly four navbar rules — height, background, dropdown-arrow black, hover `#f5f5f5`/`#000` (DD-152) — and inherits 0.9.4's defaults for the rest; every mobile deviation is Bulma 1 changing those defaults (burger/arrow from link, unscoped dropdown plates, the chevron regression) or the port deviating from the legacy markup (Logout as a red `<button>`).

**Alternatives.** Restyle the red logout `button` (padding/background overrides): the legacy ink is navbar grey, not red — the red was never in the product; the anchor is the legacy element and rides the dropdown's own ink chain for free. Ship the blue burger (Bulma 1's default): the demo's chrome is the greys, and the blue plate on the grey band is the mismatch the review flagged.

**Consequences.** The mobile menu reads as one grey band with grey ink, as the demo. The media block is the brand's first responsive emission; the chevron rule documents the upstream regression it mirrors. Pinned by `test__burger_menu_matches_the_legacy_mobile_chrome`.

### DD-154. The entity card emits `entityClicked`; the caller navigates

The ported `entity-card` (7.13) emits `entityClicked(guid)` on a title click and does not navigate. The legacy `DetailsCardComponent` injected `Router` and, on a title click with no parent listener attached, navigated to `search/details/{guid}` itself — its template probed `entityClicked.observers` to choose emit-or-navigate.

**Reason.** The ui lib is dumb by workspace rule (ADR 053, user rule: components are dumb and live in `aurelius-atlas-ui`); an injected `Router` inside a lib component re-creates the coupling the port exists to remove, and the `observers.length` probe is a side-channel, not an API. Emitting always and letting the app route is the DD-135 pattern (`SearchField` emits, the caller filters).

**Alternatives.** Port the probe (emit-if-observed, else navigate): keeps the legacy one-liner call sites, at the cost of a Router in the lib and behaviour that changes with the parent's subscription list. A `routerLink` on the title anchor: the details route belongs to 7.6, the lib must not know its path.

**Consequences.** 7.6 wires `entityClicked` to the router. The card is testable and storyable with zero app services.

### DD-155. The select is one field with a `searchRequested` output

The ported `select` (7.13) is the Bulma select field plus a search button that emits `searchRequested`. The legacy `SelectComponent` embedded a `SearchModalComponent` (a repository-fed `sortable-table-shell` inside a modal, selected row confirmed into the field) and sat on the reactive-form `AbstractControlShell` base.

**Reason.** The modal's data comes from `@models4insight/repository` — exactly the API coupling 7.2 set aside for the app slices (7.7 owns the editor anatomy). The presentation half (field, options, null/no-data messages, timestamp display, required help) is pure, so it ports now; the modal half arrives as app wiring listening to `searchRequested`. The reactive form dissolves into `value = model()` exactly as DD-135 did for `SearchField`, and the `compareWith` default becomes strict equality — the lodash `isEqual` deep compare was a legacy default the Aurelius callers never relied on.

**Alternatives.** Port the whole component including the modal: drags the repository and `task-manager` into the lib. Defer the select entirely to 7.7, per 7.2's table: the details screens want a pure select today, and the presentation/data split lets 7.7 wire only the modal.

**Consequences.** 7.7 composes select + modal; the lib stays pure. Option identity is strict reference equality — callers pass stable objects.

### DD-156. The brand ships a dark ink ramp on Bulma's dark hosts

The brand theme (DD-148, DD-151) pins the light ink chain in `:root` — body `#4a4a4a`, the neutral text ramp, `.content` — and `:root` out-cascades Bulma's own `[data-theme=dark]` block (equal specificity, later source). The result: under a dark scheme (the storybook theme switch, any future `DarkModeService` use) the surfaces flip to Bulma's dark scheme and the ink stays light-mode grey — illegible. This adds a dark ink ramp emitted on both of Bulma's dark hosts, `[data-theme="dark"]` (the explicit toggle, `DarkModeService`'s attribute) and `:root:not([data-theme])` inside `prefers-color-scheme: dark` (the OS path, Bulma's `system-theme` pattern): the text chain re-pins to Bulma's dark-scheme lightnesses over the DD-151 neutral hue (text 71% `#b5b5b5`, strong 93% `#ededed`, weak 53% `#878787` — \~9:1 on the 9% surface), the body ink/background return to the scheme tokens, `.content` follows, the link lifts to Bulma's own dark adaptation (`link-on-scheme-l`, 73% — `#0073dd` is \~3.9:1 dark-on- dark), and the ui lib's legacy `.technical` type ink (pure `#0000ff`, \~2:1) lifts to the same 75% lightness Bulma's contrast loop derives. `.technical` is the only legacy type colour that fails on dark: orange, teal and the grey all read 8:1+ and stay.

**Reason.** The switch must show the real app theme, and the app's dark mode (7.11's `DarkModeService` ships the toggle, 7.12 defers the theme) has no usable ink. Bulma 1's scheme machinery is the platform: its dark lightnesses are the WCAG-calibrated defaults, and its `generate-on-scheme- colors` contrast loop is the exact precedent for lifting `#0073dd`/ `#0000ff` — the ramp mirrors those numbers instead of inventing greys. The chrome bands stay pinned (SHM-01: "the brand colours do not follow the scheme"): the navbar's `#f5f5f5`/`#4a4a4a` and the footer's blue/ white are the legacy chrome in either scheme, and a light navbar over a dark page is Bulma's own `.navbar.is-light` idiom.

**Alternatives.** Unpin the ink from `:root` and let Bulma's schemes own it: correct, but it deletes the DD-151 legacy ramp (Bulma 1's dark ink is 221°-tinted, the demo's is neutral) and out-of-scope churn on a light- only slice. A full brand dark palette (every accent re-tuned): the demo has no dark mode to measure against (the legacy Aurelius is light-only — verified in `.scratch/aurelius`), so every value would be invented; only the ink that fails contrast is lifted, the rest of SHM-04 stays.

**Consequences.** The storybook switch previews a legible app; a future theme-switch slice inherits the ramp. The webapp's `index.html` keeps pinning `data-theme="light"` (SHM-01 untouched) — the dark ramp reaches the app only through an explicit switch. Play tests cover the ramp on the entity-card/breadcrumbs dark composition stories; the light ramp is unchanged (SHM-03's measurements stand).

### DD-157. The drawer is a new ui-lib component, not a Modal or a dropdown

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The settings panel opens in a new `Drawer` component in `aurelius-atlas-ui`: a fixed right-side panel with a scrim, styled with custom SCSS on Bulma tokens, carrying the `Modal`'s dismissal set (`active` as `model()`, backdrop click, close button, Escape → `dismiss()`).

**Reason.** The user chose a side drawer for the settings panel, and Bulma 1.0.4 ships no drawer — `sass/elements/` has no such layer; the overlay primitives are modal and navbar-dropdown. A drawer keeps the page content visible beside the settings (the point of a side panel), which the centred modal does not. Building it on Bulma tokens (`--bulma-scheme-main`, the text chain, the border ramp) makes DD-156's dark ink ramp apply to it for free. The dismissal semantics copy the `Modal` because that component proved the a11y pattern this repo accepts: the backdrop is the pointer path, Escape on the dialog is the keyboard path (the S1077 precedent in `modal.component.html`).

**Alternatives.** Reuse `Modal`: centred, occludes the page — the user's choice ruled it out, and a right-docked modal fights Bulma's centred `.modal-content`. A Bulma `has-dropdown` under the gear (the navbar idiom today): cramped for radios, selects and toggles, hover-open (unusable on touch), and it dismisses on every outside click the panel needs to survive while a control is used. `@angular/cdk`'s drawer/overlay: a new third-party dependency the purity gate and the ui-lib's zero-overlay-dependency standing do not justify for one panel.

**Consequences.** The drawer owns its focus choreography (focus moves to the panel on open, Escape returns it to the opener) — the `Modal` defers this to its buttons, the drawer has a focusable form. The component is generic (`title`, projected content), so the 7.6 filters/detail side panels can reuse it. Stories carry an OnDark variant like every overlay the lib ships.

### DD-158. The telemetry switch stops exports immediately and starts them on reload

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The telemetry setting is honoured asymmetrically: switching it **off** calls the OpenTelemetry providers' shutdown (`trace.disable()` + the meter provider's shutdown) so exports stop within the session; switching it **on** stores the preference and takes effect on the next reload, and the panel says so.

**Reason.** The SDK is assembled at bootstrap in `app.config.ts`: the `NodeTracerProvider`/`MeterProvider` are built in `createAureliusOpenTelemetry` provider factories and the propagation interceptor is registered with `withInterceptors` — both are startup-time DI, not swappable at runtime. Stopping is the one direction the SDK API supports cleanly (`shutdown()` flushes and closes the exporter); starting needs a provider re-assembly DI will not do mid-session. An honest one-way switch (off now, on after reload, stated in the panel) beats a switch that silently does nothing until restart in both directions.

**Alternatives.** Auto-reload the page on toggle: jars the user out of their session (lost form state) to start telemetry — the least urgent reason to reload. A runtime gate via a no-op proxy exporter/provider registered at bootstrap: the real machinery the SDK hides (span processors, batch exporters, the interceptor's active-span context) then runs with the toggle off, which is exactly what "telemetry off" promises not to do. No toggle at all: the user asked for one, and an off switch for browser telemetry is a reasonable privacy affordance.

**Consequences.** The stored preference is read by `app.config.ts` before the providers are built (off at bootstrap = providers are never created — not even the no-op path). The panel's reload hint is a rule with a test (SPL-11). A served-app scenario (no OTLP requests after off) lands with the 7.10 e2e set that serves the app.

### DD-159. The theme choice is applied pre-render; SHM-01's light pin is superseded by a light default

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `data-theme="light"` pin on `index.html`'s root is removed. A two-line inline script in the head applies the stored theme before the first paint: the stored value (`light`/`dark`) is written, `auto` (or no stored key with no value) **removes** the attribute and — because the app's default must stay light (SHM-01's promise) — the script writes `data-theme="light"` when nothing is stored. `DarkModeService.initialize()` reads the same attribute, so the service and the page agree from the first frame.

**Reason.** `DarkModeService.initialize()` treats the root attribute as the highest-priority explicit choice; the 7.12 pin therefore outvoted a stored `dark`/`auto` on every load — the switch could not survive it. The pin can also not just move to runtime service code: Angular bootstraps after CSS, so a service effect paints one frame in the wrong scheme (the classic dark-mode flash). The inline script is the standard pre-render pattern and keeps SHM-01's user-visible promise exactly — no stored choice ⇒ light under any OS preference — with the default in the script + the service, not in static html. 7.12's scope note anticipated the switch ("a later slice flips the `data-theme` attribute"); this is that slice superseding the mechanism, not the promise.

**Alternatives.** Keep the pin and let the service overwrite it after bootstrap: not a flash problem only — `initialize()` returns the pin as the user's explicit choice, so stored Dark is ignored outright. Drop the light default and let no-stored-key follow the OS (Bulma's native behaviour): breaks SHM-01 — the legacy app is light-only and the demo renders light under a dark OS; the pin's promise was measured, and 7.12's specs assert it.

**Consequences.** SHM-01's row in 7.12 gains a supersede note (the promise stands, the mechanism moves). The service's `updateDataThemeAttribute` must **remove** the attribute for `auto` rather than write `data-theme=""` — the empty attribute does not match Bulma's `:root:not([data-theme])` OS path, so Auto would never follow the OS. The 7.12 spec's html-attribute assertions keep passing because the script writes `light` when nothing is stored.

### DD-160. Settings are a facade over one owner service per category

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** `SettingsService` (webapp) is a thin facade: it exposes each setting's signal and setter and delegates to exactly one **owner** service per category — theme → `DarkModeService` (the ui-lib's existing owner), language → `LocaleNavigationService`, time zone → `TimezoneService`, page size → `PageSizeService`, telemetry → `TelemetryService`. Each persistence- backed owner stores through a shared `UserPreference` helper (signal + synchronous `localStorage` read at construction + write-through), which is the only code touching `localStorage`.

**Reason.** The user asked for the `DarkModeService` facade pattern to extend to the other categories. It generalises what the lib already does: `DarkModeService` is the sanctioned persistence owner and the AGENTS.md exception to the dumb-component rule, and it owns its key (`data-theme`). One owner per key keeps a single writer per storage slot; the panel consumes only the facade (one injectable, one test double); the bootstrap providers (`DATE_PIPE_DEFAULT_TIMEZONE`, the telemetry gate) read the owners directly, which is legal because `UserPreference` reads storage synchronously at construction. The seam for the promised server-side persistence is the helper's internals (GET/PUT behind the same signal API) — owners, facade, and panel do not change then.

**Alternatives.** One monolithic `SettingsService` owning every key: it would write `data-theme`, a key `DarkModeService` already owns — two writers, and the webapp would fork the theme mechanism the lib ships. Panel injecting the owners directly: no facade to double in tests, and every setting change touches the panel's imports. A global signal store/ngrx: the webapp has no global-store convention (AGENTS.md: feature state lives in signal stores under the feature folder).

**Consequences.** The `SPL-10` rule is testable per owner: each owner is the sole writer of its key. Adding a setting = one owner + one facade member; the 7.6/7.7 screens consume owners directly (a table reads `PageSizeService`, not the facade) — the facade serves the panel, owners serve consumers. Server-side sync, when it lands, adds the PUT path in `UserPreference` and a hydrate step at bootstrap (DD-161).

### DD-161. Settings are browser-scoped localStorage; server-side persistence is the follow-up slice

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The v1 settings store in `localStorage` under `data-theme` (the theme's existing key) and `aurelius-atlas.settings.{timezone,pageSize,telemetry}`. They are user-experience conveniences, scoped to the browser: nothing that identifies a user, grants a permission, or belongs to the catalogue is kept there. Server-side per-user persistence (Keycloak profile attributes, or the Atlas session settings ADM-05 exposes) is a deliberate later slice behind the `UserPreference` seam (DD-160).

**Reason.** The user chose localStorage for now and named Keycloak's user profile as the server-side direction. The two server channels are not ready: `GET /atlas/admin/session` (ADM-05) publishes settings but Atlas 2.4.0 has no settings-write endpoint, and Keycloak profile writes need admin token-roles — both are increments of their own. The privacy line matters for DD-158's off switch: a browser-scoped store keeps the promise simple (off means this browser sends nothing; nothing was sent about a user).

**Alternatives.** Cookies: sent to the server on every request for data the server never reads. IndexedDB: asynchronous for values this small — the synchronous bootstrap read SPL-07/SPL-11 need becomes an ordering problem. Server-first now: blocks the panel on the 6.1 identity + a new endpoint, putting a UI feature behind API work the user scoped later.

**Consequences.** DV-65 records the panel as a deliberate addition (Atlas has none). A shared browser shares its settings — acceptable for v1, named for the server-side slice to fix. Key names are documented in this entry so the server-side slice can migrate them.

### DD-162. The drawer animates in and out; the layer's life is the exit animation's

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `Drawer`'s panel slides in from the right edge over a fading scrim (200ms, ease-out) and plays the reverse on close (ease-in, `forwards`). Dismissal is state-first: `active` flips to false at once — focus restoration, the caller's binding, and `cancelRequested` all land immediately — and a `closing` signal keeps the layer rendered for the exit pass; the panel's `animationend` (name-checked, so content animations bubbling out of the projected body are ignored) drops it. Reopening mid-slide-out clears the flag and the enter animation plays on the layer that never left. `prefers-reduced-motion: reduce` shortens the animations to 0.01ms; it does not remove them. Plain CSS keyframes — no `@angular/animations`, and the component stays a dumb `aurelius-atlas-ui` component (its AGENTS convention): the animation is styling, not service work.

**Reason.** The user asked for the drawer to be animated. A `@if (active())` template removes the DOM on close, so an exit animation needs a second signal to keep the layer alive; keying the layer's life to the exit animation's end is the CSS-native answer (the same lifecycle modal libraries use). State-first dismissal keeps every rule SPL-02 states — focus returns on close, `active` is false on dismissal — true *on close*, not 200ms later; tests and consumers never wait on motion. 0.01ms rather than `animation: none` under reduced motion because the exit's `animationend` is what removes the layer: no animation, no event, a drawer stranded on screen.

**Alternatives.** `@angular/animations`: a new dependency for the lib's peer set and a second styling system, for two translate keyframes. Enter only (keep `@if (active())`): simplest, and the snap-out reads as a bug next to the slide-in. Hiding with `visibility` after a timer: timers instead of the animation's own event, to race on every speed. Transition on a class toggle: keyframes were needed because the enter plays on element creation, where a transition has no start state.

**Consequences.** Focus restoration fires when `active` flips, so it lands before the slide-out finishes — the panel animates out behind the focus move; acceptable, named. The drawer spec drives `animationend` manually (jsdom runs no CSS animations, and ships no `AnimationEvent` constructor). Storybook's polling `expect` absorbs the 200ms close in the `play()` functions. Keyframe names are prefixed `aurelius-drawer-`; the exit's `animationend` is matched by containment, because Angular's emulated encapsulation decorates keyframe names (computed `_ngcontent-ng-…_aurelius-drawer-out`), not by prefix.

### DD-163. The drawer styles itself with fallbacks; Bulma's modal tokens are `.modal`-scoped

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The drawer's head/body padding, scrim colour and z-band keep the Bulma token names for the override seam, and add explicit fallbacks: `var(--bulma-modal-card-head-padding, 2rem)`, a scrim spelled from the root-scoped scheme ramp at Bulma's 0.86 alpha, and the existing z fallback. The drawer ships no padding of its own beyond this.

**Reason.** The user asked for edge padding; measuring the live drawer showed the real bug: Bulma 1 emits `--bulma-modal-*` on the `.modal`/`.modal-card-*` selectors, not on `:root` — verified in `node_modules/bulma/css/bulma.css` — so outside a modal the tokens are undefined: bare `var(...)` collapsed the head/body padding to 0 and painted the scrim transparent. A plain literal padding would fix the symptom; the `var(name, literal)` form keeps the brand's override seam (open the drawer's tokens to the brand ramp later) and documents the scope trap.

**Alternatives.** Import Bulma's modal layer in the brand (it drags the whole component's CSS for three tokens). Define the tokens on `:root` in the brand (duplicates Bulma's values, and a brand-wide change to fix one component). Plain literals (loses the seam).

**Consequences.** The drawer's computed padding is 2rem; the scrim is Bulma's modal-background recipe, dark-ramp aware (DD-156). The fallbacks drift if a future Bulma changes the modal defaults — named, low-risk, the component owns its layer (DD-157).

### DD-164. The Appearance picker is the ui-lib Select; the Select gains `searchVisible`

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The settings panel's Appearance section is the ui-lib `Select` with `searchVisible` off — the section heading is the control's own label, the rows are the three modes (Auto first, selected). The Select gains the `searchVisible` input (default on: the Aurelius modal opener stays for repository pickers); off, the addons layout collapses with the button and the field is a plain labelled dropdown.

**Reason.** The user asked for the component library's select. The Select is the lib's only select, ported from Aurelius with a search button welded in; an input is the minimal honest generalisation — the button is the legacy `activateSearchModal` affordance, not part of "pick one of three themes".

**Alternatives.** Keep the radios (rejected by the user). Native Bulma select markup, as the Time zone section uses (duplicates the lib's control, and loses the UIC-14 label pairing). Fork a plain select component (a second select in the lib, no).

**Consequences.** The panel's `.select select` list gains a first element (specs index it). The Select gains a `NoSearch` story. A selected row can never be cleared — the placeholder is `hidden` and `setTheme` ignores null; the panel always has a theme.

### DD-165. About shows one version; the server is not fetched

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The About section shows the app name and the app version from the runtime config, and nothing else. The `getVersion` fetch and the server line are removed, with them the `shell.settings.server` and `shell.settings.serverUnavailable` strings (catalogues: 533 units).

**Reason.** The user set the rule: app and server always carry the same number — one Nx release cuts the workspace, and the image labels derive from it — so the server line can only echo the app version, and a version the panel has to fetch can only be *shown* to differ while the fetch is in flight. Removing the row removes the question.

**Alternatives.** Show the fetched server version (states a known-true equality, and adds an ADM-01 call per open). Show "app (server: same)" (noise). Keep the fetch, show it on mismatch only (two code paths for a state the release strategy rules out).

**Consequences.** The panel's construction fetch is `getSession` only (SPL-07 keeps its degradation test). ADM-01's endpoint stands on the server; the panel is no longer its consumer, and DV-03's parity scope does not change.

### DD-166. The settings panel is a routed overlay in the `drawer` aux outlet

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The `drawer` named outlet at the app root carries routed overlays (SPL-14). The settings panel is a route (`(drawer:settings)`): the header gear is a `routerLink` to it — with the panel open the link targets the URL it is on, and the router cancels that duplicate navigation, so the gear is a no-op; dismissal (backdrop, close, Escape) navigates the segment away. The component opens at construction (`active` starts true) and loads its chrome data then. Future drawers — an alerts drawer is named — get their own outlet segments and compose in the URL: `(settings:…)(alerts:…)`.

**Reason.** Switching language is a full-page navigation into the locale tree (DD-128), and the user wants the reload to land on the same page with the settings open. The URL is the only state that survives a full reload, and named outlets are Angular's mechanism for putting an overlay in the URL — the segment rides `localeHref()` untouched, so the requirement falls out. (The term: auxiliary routes.)

**Alternatives.** A query param (`?settings=1`) — works, and invents a parallel navigation system outside the router; the outlet form is the router-native one, composable, and the Angular idiom. localStorage "open" flag — reloads open, survives everything, unbookmarkable and sticky. A service + effect — doesn't survive the reload, which is the requirement.

**Consequences.** Closing destroys the panel, so the drawer's exit animation (DD-162) is not awaited there — accepted, named; the DD-162 lifecycle remains for the drawer's own API (`close()` on a non-routed drawer), and the enter animation plays on open, including after the locale reload. Dismissal is destructive (no panel state to keep — the facade owns it, DD-160). Deep links work: visiting `/search/browse(drawer:settings)` opens the panel on that page. The `serverUnavailable` fallback and the `open()` API are gone; the panel spec drives the component directly (as the routed-component test pattern prescribes).

### DD-167. Settings-drawer polish: lit gear, scheme-following band, Browser-default picker, `.label` headings

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** Four fixes from the user's review of the open drawer. (1) The gear carries `routerLinkActive="is-active"`: Bulma styles `a.navbar-item.is-active`, and the active state keys off the `drawer` outlet segment — the gear is lit exactly while the panel route is open (SPL-01). (2) The outlet band drops `has-background-light` for Bulma's bare `.has-background` (`var(--bulma-background)`): the legacy light in light mode, the dark scheme's surface in dark (SPL-05's theme switch now repaints the page, not just the drawer). SHM-05's pinned chrome bands are unchanged. (3) The time-zone picker binds the stored zone directly — `null` when unset selects the "Browser default" option (SPL-07); the browser's resolved zone is no longer injected into the select, where it rendered blank whenever it was not one of the server's ADM-05 ids. (4) Every settings section heading is a Bulma `.label` — the form-controls guide's field label (the guide the user linked) — replacing `.menu-label`; the Appearance heading already renders as `.label` through the Select, so all six now match.

**Reason.** The gear gives no affordance that it owns the open panel. `has-background-light` is Bulma's fixed light colour family, not a scheme role, so a dark page kept a light band. A select whose value matches no option renders empty — the "Browser default" option is the honest display of an unset zone, since its effective value *is* the browser's, applied at the date pipe. `.menu-label` is the sidebar-menu heading (uppercase, small, weak); inside a form column it reads as a different component than the `.label` the Select shows.

**Alternatives.** (1) A signal shared header→panel — state the URL already carries. (2) `has-background-scheme-main` — the body colour, leaving no surface distinction from the footer band; `--bulma-background` is Bulma's surface role and matches what cards/tables sit on. (3) Add the resolved zone as an extra option — the list is the server's (ADM-05), and a local zone the server may not accept is a false promise. (4) Keep `.menu-label` — the inconsistency the user flagged.

**Consequences.** The band's computed background follows the scheme (verified live in both modes). `timezoneValue` narrows to `string | null` — the same value the facade stores, making the panel a pure pass-through. The `.label` heads are normal-case and stronger ink; the panel scss comment follows. No string ids change.

### DD-168. The navbar follows the scheme: the dark slate band

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** In dark mode the navbar leaves the pinned light band (SHM-01's "the brand colours do not follow the scheme", for the navbar only) for a neutral slate, \#72757d — hsl(224, 4%, 47%), the faint cool cast of $blue. The bar's chrome composes on the slate: ink \#000 (5.6:1), hover/active the light plate (Bulma's +8%/+12% deltas, DD-152's deltas inverted for a dark band), the gear's `is-active` the white plate (DD-152's selected pair), the `is-dark` Documentation button's ink/border black (its pinned \#363636 rides at 2.5:1 on the slate). The account dropdown keeps Bulma's scheme composition. The footer stays pinned (SHM-07 — blue/white reads the same in either scheme). The logo keeps its brand size in both schemes.

**Reason.** The user's review: dark mode kept a light navbar. The binding constraint is the logo, measured from the PNG: its wordmark is navy `#151487` at \~11% lightness, so every dark surface (the scheme's `#1f2229`, the brand blue `#0073dd`) collides with it (1.0–1.3:1) and the wordmark's WCAG-3:1 floor (graphics) sets the bar's ceiling at \~47% lightness. The slate is the darkest background that keeps the mark legible (3.1:1); the user chose it over the brand blue, then over the first bluer/lighter cut — 4% saturation, one step under the floor.

**Alternatives.** Brand blue \#0073dd (the footer's blue — wordmark 3.5:1, the user declined: reads as a blue bar). A true dark band (\#131a26) with a light logo variant — the proper dark-mode look, needs a design asset; the seam is this mixin's token block. Keeping the navbar pinned light (the status quo the user rejected). Darkening the slate below 47% (the wordmark falls under 3:1).

**Consequences.** The navbar tokens are a brand-theme block on both of Bulma's dark hosts (0,2,0, out-cascading the light `.navbar` pins). The logo's navy/cyan palette is now load-bearing across schemes: a future rebrand or light-variant asset replaces this decision (supersede, don't edit). The light band is untouched (SHM-05 stays the light-mode chrome).

### DD-169. Settings headings are the controls' accessible names

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** Every settings control's `.label` heading is its accessible name (the Bulma form guide's labelled control, the guide DD-167 adopted): Time zone and Page size are `label[for]`/`id` pairs on the native selects, Telemetry on the checkbox (the label moves from the old wrapping `.checkbox` — the checkbox is a plain control on the section grid), Appearance rides the ui-lib Select's own `label[for]`/`aria-labelledby`, and the language links — not a form control — are a `role="group"` labelled by their heading. About is a section title, not a field, and is not associated.

**Reason.** The user's review of the DD-167 layout: the headings looked right and were wired to nothing — clicking a label did nothing, and a screen reader announced bare "combobox"/"checkbox". The Bulma form guide the headings already follow prescribes the association; DD-167 adopted the shape and left out the link.

**Alternatives.** `aria-labelledby` everywhere (works, and the `label[for]` is the HTML-native form the guide shows; the group and the Select use it where no single labelable control exists). Keeping the wrapping `.checkbox` label (an accessible name, and the Bulma checkbox idiom — rejected: the guide's stacked label/field shape is what DD-167 just standardised on, and the checkbox label had no text to wrap).

**Consequences.** Fixed ids (`settings-timezone`, …): the panel is a singleton route, so collision is impossible. The checkbox loses Bulma's `.checkbox` hover affordance (the label click replaces it). The panel spec asserts each pair.

### DD-170. The active locale is filled with the Aurelius blue

- **Status:** Accepted
- **Increment:** 7.14
- **Date:** 2026-10-21

**Decision.** The active locale link in the settings drawer's Language section is a solid Aurelius-blue plate (`#0073dd`, white ink): the panel scss fills the `is-selected` button the template already marks (SPL-06). The pair is pinned, not scheme-following — the same `#0073dd`/white the footer's brand block pins (SHM-07).

**Reason.** The user's review: "For the locales can we ensure the current locale is highlighted?" The SHC-04 port carries the `is-selected`/`aria-current` marking (7.12), and the template binds it — but Bulma 1 styles a selected button with nothing (verified: `.button.is-selected` has no rule, and the rendered active and inactive links measure identical ink and plate). The marker is semantic, invisible; the highlight the user asked for is the missing visual half of it.

**Alternatives.** `is-active` (Bulma composes an `l-delta` from it — a shadow on the plate, not a fill; the same non-result). A check-mark icon on the active link (a decoration needing a string and an id on both locales, for what a fill says for free). `var(--bulma-link)` (the scheme-following accent — rejected: DD-156 lightens it to 73% in dark, and white ink on a 73% light-blue fails; the pinned pair holds 4.6:1 in either scheme).

**Consequences.** `.buttons.has-addons` keeps the links joined, and the fill joins them visually as a segmented control: the active plate is blue, its neighbours stay plain. The panel spec asserts the `is-selected` class on the active link (the scss fill itself is a style, not a testable DOM fact).

### DD-171. The alerts store groups by a quiet window

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** `AlertsService` is the app's one alert door (ALR-03): an in-memory signal list of groups, newest first, capped at 30 (oldest evicted). Grouping is a quiet window — an alert whose key (severity + source + message) matches the **newest** group's merges into it while the window is open (60 s from that group's last alert: `count` +1, `lastSeen` moves); after the gap, a new group starts. A `newGroups` counter counts arrivals, not alerts (merges do not move it — ALR-02a's ring signal). The clock is an injectable token (`ALERT_CLOCK`), not fake timers.

**Reason.** The user's review of the plan: "Sometimes the same error occurs multiple times in quick succession. I'd like to be able to group notifications so the user doesn't get overloaded." A flapping endpoint fails per retry — ungrouped, one drawer row per failure. Merging by key shows a burst as one row with a count (×7, 14:20–14:22). The window bound keeps history honest: merging session-wide would weld an hour-old error to a new burst of the same message; after the gap the old burst is context, and the new one needs its own row. The newest-only merge keeps the store append-only (a burst ends when anything else arrives — the row's count is the burst's, not the message's total).

**Alternatives.** Merge into any group with the same key, session-wide (one row per message forever — the user's phrasing "in quick succession" named a window, and history loses its timestamps). Timestamp-bucketed grouping (fixed 60 s bins split a burst at a bin edge). A capped ring of raw alerts, grouped at render (the store then knows nothing, and every consumer re-derives the same groups; the bell's ring needs arrival counting, which raw-alert caps lose). `fakeAsync`/`tick` for the window (the token clock makes the window a constructor argument of the test, no zone patching under zoneless).

**Consequences.** In-memory: alerts die with the tab — session events, not preferences; the persisted lane is DD-161's and this stays out of it. `AlertGroup` (the ui-lib model, ALR-10) is the store's public row; the merge-key `source` is internal to the store. A 60 s constant; raising it is a one-line change. The cap's eviction is silent (alerts are cheap, the drawer is not an archive).

### DD-172. The app's ErrorHandler chains: alert, then trace

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The root `ErrorHandler` is `AlertsErrorHandler`, composing the trace handler: record the uncaught error as an `error` alert (source `app`), then delegate to `AureliusTraceErrorHandler`, which keeps its own delegation to Angular's default (ALR-04). Recording is wrapped in try/catch — alerting must never break the error path. The composition is a factory in `app.config.ts` (`useFactory: alertsErrorHandlerFactory`), not a class the app subclasses.

**Reason.** SHL-14's telemetry (7.1) owns the root handler; the alerts drawer (ALR-04) needs the same event. Composition keeps both promises exactly: the trace handler sees the untouched error, the user sees the alert. The order is record-first: a delegate that throws (the default handler re-throws in dev mode) must not cost the user the alert.

**Alternatives.** Subclass the trace handler (`super.handleError` then record — the user's alert would depend on the delegate surviving, and the app inherits a library's constructor). A second `ErrorHandler` provider (DI: one token, one value). `provideEnvironmentInitializer` with `window.addEventListener("error")` (the listeners are the DI handler's input, `provideBrowserGlobalErrorListeners` already wires them; a second listener double-records).

**Consequences.** Every uncaught error is now user-visible — noisy runtime bugs surface in the drawer (the intent, ALR-04; the store's window, DD-171, absorbs repeat spam). The trace path is unchanged: the `app.config.spec.ts` provider-set specs keep SHL-14's shape.

### DD-173. The HTTP reporter: 5xx and network failures on /api

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** A functional interceptor, last of the three on `provideHttpClient`, watches the response and reports the reportable set (ALR-05): `5xx` responses and status-0 network failures on URLs matching `/api/` — the bearer interceptor's pattern (APC-06), not a hardcoded prefix. The message names method, path, and status (`no response` for status 0) and rides the server's plain `error` message when it sends one. The interceptor reports and re-throws; the caller's observable is untouched. 4xx is silent.

**Reason.** The user asked for "any app error messages if they occur" — a failing catalogue call is the app's most common real error. The `5xx`-plus-network cut is the plan's standing default, accepted: a 4xx is a client-side correction the calling feature already handles (its form, its not-found view), and reporting it would train users to ignore the drawer. The report is the drawer's, not the caller's: 7.4+ features keep their own `onError` UX; DD-171's window folds the pairs into one row.

**Alternatives.** Per-call `onError` reporting at each feature (every slice re-wires it, and un-wired calls go missing). Reporting 4xx too (the noise the plan asked about; Atlas proxies 404 through the 6.x ramp). A `HttpInterceptorFn` on the data-access library (the SDK is feature code's door; the app owns chrome-level alerting — the interceptor sits in the webapp's provider chain, where the bearer and OTLP interceptors sit).

**Consequences.** A failed `/api` call is visible twice when the feature also shows its own error (accepted: the drawer is the collected record). The status-0 case cannot tell an offline browser from a refused connection — one message covers both.

### DD-174. The bell: severity badge and ring, one outlet

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The header bell is the gear's pattern (DD-166, DD-167): a `navbar-item` routerLink to `(drawer:alerts)`, `is-active` while open, and the one `drawer` outlet swaps the settings panel and the alerts drawer (ALR-01). It carries the ui-lib `Badge`: a presence dot, visible while the store is non-empty, coloured by the highest severity present — presence, not a count, no read-state (ALR-02). The dot is `aria-hidden`: inside the bell's link it would join the link's accessible name. New groups animate the bell, a \~650 ms Web Animations pendulum swing on the icon (the effect watches `newGroups`, so a burst rings once, ALR-02a); `prefers-reduced-motion: reduce` skips it.

**Reason.** The user asked for a badge "to indicate notifications are available", the "color of the highest severity notification available", and "a little animation on the bell whenever an alert becomes available" — the ring is the arrival, the dot is the presence, the colour is the worst. Presence beats a count: the store caps at 30 and merges bursts, so a count badge overflows its own model. The single-outlet swap is DD-166's mechanism with a second segment (the URL owns which drawer is open; the locale switch's reload keeps it, SPL-14's mechanic reused). The ring is WAAPI, not a CSS class: the animation restarts cleanly mid-swing (a class re-trigger needs a reflow hack); the pivot (`transform-origin: top center`) is scss on the icon, the keyframes are the component's.

**Alternatives.** A count badge (Bulma's `.tag`, overflow-prone, read-state invented for it). An unread-only dot (the user's word was "available", not "unread"). A CSS `@keyframes` class toggle (the re-trigger hack; reduced-motion media queries alone cannot skip a JS-driven replay). `@angular/animations` (not a dependency; the zoneless app has no animation renderer, WAAPI is the browser's).

**Consequences.** The dot's contrast on the navbar bands is the Badge's problem (its ring, DD-175's note); the header keeps the DD-168 slate. The dot is a component, not Bulma's `.badge` idiom (the lib has no Bulma DOM assumptions). A future read-model (server events, 6.x) adds a source to the store, not a new door.

### DD-175. AlertList and Badge are ui-lib presentational components

- **Status:** Accepted (the `clearAll()` half of the contract superseded by DD-176)
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The feed and the dot live in `aurelius-atlas-ui` as presentational components (ALR-10): `AlertList` renders a caller-supplied `AlertGroup[]` (the model the lib exports — the row's shape is presentation vocabulary) and emits `dismiss(id)`/`clearAll()`; `Badge` wraps content, shows a severity dot on `visible`. Labels are inputs with English defaults (the `Drawer.ariaLabel` pattern), so the lib keeps no translation dependency and the app passes `@@shell.alerts.*` strings (ALR-08). The store, the window, and the routing stay app-side.

**Reason.** The user: "let's ensure we make a reusable ui component for alerts." The feed has a second consumer by the plan's own logic (7.6+ feature slices push alerts through the same store, and the drawer is the product's surface); the dot generalises to any nav item. The lib's rule is the same one `Drawer` keeps (DD-157): Bulma-shaped presentational markup, state in the caller. The lib's chrome-strings lane (DD-136: legacy dictionary paths) has no alert keys to reuse — these are Aurelius's own strings (DV-66) — so the inputs carry defaults and the app's catalogue owns the translations; the XLIFF gate (SHL-08) and the purity gate (DD-137) stay app-side, the lib stays service-free (its AGENTS.md convention).

**Alternatives.** App-local components under `src/app/alerts` (not reusable — the user's ask). A smart `AlertsDrawer` in the lib that injects a store (the lib owns no app state, no xlf dependency). `model()` for the alerts array (the list never edits rows; dismiss is an event, not a two-way value).

**Consequences.** The `AlertGroup` type is public API of the lib (`src/index.ts`). The stories ship per UIC-15's bar (visual regression covers the feed and the dot). The badge's ring is Bulma-token ink (`--bulma-navbar-item-color`, currentColor fallback) — a future non- navbar host keeps a visible edge without a new input.

### DD-176. The chip's pinned pair; Clear all in the drawer head

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** Two live-review fixes to the alert feed (ALR-06, ALR-07): the burst chip's pair is pinned — `#f5f5f5` plate, `#363636` ink — not Bulma's `tag is-light`; and the "Clear all" button is a content action in the drawer's head, not part of the feed. The Drawer grows a `drawer-actions` projection slot between the title and the close button and AlertList loses its `clearLabel`/`clearAll` — clearing a store the list does not own was the list's borrowed business (DD-175's presentational rule).

**Reason.** The user's review of the live drawer: "the counter text is not visible on the white background" and the "clear all" button "will become buried" on a long feed — "let's keep it above the notifications". The chip's invisibility is a scheme trap, measured: the brand pins the `light` colour pair at `:root`, outside Bulma's scheme machinery (SHM-04, so the chrome colours survive), while Bulma 1's dark theme re-pins `light`'s invert to a scheme-following ink — the `is-light` tag composed the brand's white plate under dark-mode white ink (white-on-white). The pinned `#f5f5f5`/`#363636` pair is the footer's idiom (SHM-07): the same marker in either scheme, 9.3:1. The first fix placed Clear all above the rows inside the scrolling body (DD-176's first pass, unit-tested); on review the head is the stronger answer — the body scrolls, so the hatch must ride the sticky head.

**Alternatives.** Pin `light-invert` in the brand's `dark-ink` ramp (fixes the tag and every `is-light` surface app-wide — rejected as wider than the bug: DD-156's ramp re-pins the ink chain Bulma itself adapts; `light` is a colour pair SHM-04 pins deliberately, and dark-adapting it reopens SHM-01's promise). A severity-coloured chip (the row is already severity-coloured; the chip is metadata, not a second signal). Clear all above the rows inside the body (the first pass: on a long feed the drawer body scrolls, taking the hatch away — rejected on review). A `clearLabel`/`clearAll` on AlertList kept "for reusability": a feed that owns a store-clearing button presumes the store's shape — the head slot keeps the list the rows.

**Consequences.** The chip is the third pinned pair in the product (footer SHM-07, active locale DD-170, chip DD-176) — the growing list of surfaces that read the same in both schemes. The Drawer's head anatomy (DD-157's, shared with settings) gains an optional slot: the settings panel projects nothing and is unchanged. The alerts drawer's tab order is close, then Clear all (both in the head), then the rows.

### DD-177. The parallel tracks' colliding DD/DV ids renumber to the 7.x/8.x side

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into `feat/api-client-libraries`, PR \#143)
- **Date:** 2026-10-24

**Decision.** The 2.x/3.x track (server spine, entity store, relationships, classifications, tasks, audits) and the 7.x/8.x track (webapp shell, aux APIs, client libraries) branched at DD-036/DV-10 and minted ids in parallel: main took DD-037..089 and DV-11..46, the branch took DD-037..088 (51 ids, the same numbers, different decisions) and DV-11..27. The merge renumbers the **branch side above both ranges**: DD-037..088 → DD-126..176 and DV-11..27 → DV-47..61 in ascending order — DV-18/DV-22 included, to DV-62/DV-63, because main's DD-049 retired its own DV-18/DV-22 rows and retired numbers are never reused — and this entry (DD-177) records it. Main's ids keep their numbers. The citation sweep rewrote every spec, doc, code comment, scenario, `.env` comment, and trace marker on the branch side; a chain whose members renumber non-consecutively becomes an explicit list (`DD-059/062` → `DD-148, DD-151`).

**Reason.** Main's 2.x decisions are merged and cited by merged code — they are the accepted record, and the ledger's rule (numbers are never reused, accepted entries are never edited) protects them. The branch's specs are the in-progress side of the same ledger, so it is the side allowed to move; moving 51+17 ids in one mechanical, reviewable sweep costs less than living with ids that mean two things. The branch's non-colliding ids stay: DD-089..125 is untouched, and the new range starts above main's DD-089 with room for this entry. DD-065 is main's alone (the branch mints no DD-065).

**Consequences.** The merge of main into the branch is conflict-free for the id ledger: the two tracks occupy disjoint ranges. The mapping table (branch old → new) is this entry's appendix, below; every pre-merge commit message cites the OLD numbers — commit history is not rewritten, and the appendix is the lookup from a commit's citation to the merged record. The design-log and deviations tables are sorted by number, so the renumbered entries interleave with main's by position only after the merge sorts them; within the branch the sweep is in-place (ascending order). The untracked dev `.env` files (decrypted from the renumbered `.env.enc` comments) refresh on the next `nx decrypt`.

| Old | New | Old | New | Old | New |
| --- | --- | --- | --- | --- | --- |
| DD-037 | DD-126 | DD-056 | DD-145 | DD-075 | DD-163 |
| DD-038 | DD-127 | DD-057 | DD-146 | DD-076 | DD-164 |
| DD-039 | DD-128 | DD-058 | DD-147 | DD-077 | DD-165 |
| DD-040 | DD-129 | DD-059 | DD-148 | DD-078 | DD-166 |
| DD-041 | DD-130 | DD-060 | DD-149 | DD-079 | DD-167 |
| DD-042 | DD-131 | DD-061 | DD-150 | DD-080 | DD-168 |
| DD-043 | DD-132 | DD-062 | DD-151 | DD-081 | DD-169 |
| DD-044 | DD-133 | DD-063 | DD-152 | DD-082 | DD-170 |
| DD-045 | DD-134 | DD-064 | DD-153 | DD-083 | DD-171 |
| DD-046 | DD-135 | DD-066 | DD-154 | DD-084 | DD-172 |
| DD-047 | DD-136 | DD-067 | DD-155 | DD-085 | DD-173 |
| DD-048 | DD-137 | DD-068 | DD-156 | DD-086 | DD-174 |
| DD-049 | DD-138 | DD-069 | DD-157 | DD-087 | DD-175 |
| DD-050 | DD-139 | DD-070 | DD-158 | DD-088 | DD-176 |
| DD-051 | DD-140 | DD-071 | DD-159 | DV-11 | DV-47 |
| DD-052 | DD-141 | DD-072 | DD-160 | DV-12 | DV-48 |
| DD-053 | DD-142 | DD-073 | DD-161 | DV-13 | DV-49 |
| DD-054 | DD-143 | DD-074 | DD-162 | DV-14 | DV-50 |
| DD-055 | DD-144 | — | — | DV-15 | DV-51 |
| — | — | — | — | DV-16 | DV-52 |
| DV-17 | DV-53 | DV-21 | DV-56 | DV-25 | DV-59 |
| DV-18 | DV-62 | DV-22 | DV-63 | DV-26 | DV-60 |
| DV-19 | DV-54 | DV-23 | DV-57 | DV-27 | DV-61 |
| DV-20 | DV-55 | DV-24 | DV-58 | — | — |

DD-065 is main's alone (the branch mints no DD-065), and the branch's DD-089..125 sit above main's range — both untouched.

### DD-178. The merge resolves the OpenTelemetry version split to the 1.45.1/0.66b1 set

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into `feat/api-client-libraries`, PR \#143)
- **Date:** 2026-10-24

**Decision.** The merged `uv.lock` is re-resolved to one OpenTelemetry set: the OTLP exporter and SDK at 1.45.1, the instrumentation family (core, asgi, fastapi, httpx, logging, system-metrics) at 0.66b1 — main's set. The text merge had kept the branch's `opentelemetry-instrumentation-logging`/ `-system-metrics` at 0.65b0 under main's `opentelemetry-instrumentation` 0.66b1, and 0.65b0 pins the core at `==0.65b0`: the four app Docker builds fail `ResolutionImpossible`. The two otel seam tests follow the 1.45.1 exporter's internals: the ingest session moved from `OTLPSpanExporter._session` to `._client._transport._session`, and the metric exporter's resolved headers from `._headers` to `._client._headers`.

**Reason.** Main's lock is the accepted record (DD-177), and the pins are exact-equality inside the instrumentation family — a mixed set is not a solution pip can install, so the merged lock must resolve to one generation. The seam tests assert the wiring through the exporter's private structure (their declared purpose: the session/headers the ingest pipeline attaches); re-pointing them at the moved attributes keeps the same assertion on the same object graph.

**Consequences.** `nx run-many -t test e2e -c ci` is green again for the otel lib and the four Docker builds. The exporter's private attributes are not a public API: the tests are pinned to the locked version, and a future OTel bump must re-point them the same way. No production code changed — `build_otlp_pipeline` passes `session=` through the constructor, which is public in both versions.

### DD-179. The branch's second collision band renumbers above main's tail

- **Status:** Accepted
- **Increment:** — (merge hygiene; lands with the merge of main into `feat/api-client-libraries`, PR \#143)
- **Date:** 2026-10-24

**Decision.** Round 1 (DD-177) planned to main's DD-089 and DV-46; main's tail is DD-090 and DV-47 (the classification-search entry and row, 4.1). The merge of main's ledger keyed by id and kept HEAD, dropping main's DD-090 entry and DV-47 row; this entry restores both, and renumbers the branch's second band above main's tail and above DD-177/DD-178: DD-090..125 → DD-180..214 (the branch mints no DD-104, so the shift is not uniform) and DV-47..63 → DV-64..80, with the citation sweep over every spec, doc, code comment, scenario, `.env` comment, and trace marker on the branch side. The mapping table is this entry's appendix.

**Reason.** The same as DD-177: main's ids are the accepted record cited by merged code, and the ledger's rule (numbers are never reused, accepted entries are never edited) protects them; the in-progress side moves. The band DD-090..125 minted above DD-088 because main's tail was DD-089 when it was minted — main kept minting, and the merge proved the tail moved.

**Consequences.** The id ranges of the two tracks are disjoint: main DD-001..090 / DV-1..47, the branch DD-126..176, DD-180..214 / DV-64..80. Every pre-merge commit message cites the OLD numbers; DD-177's and this entry's appendices are the lookup. The untracked dev `.env` files refresh on the next `nx decrypt`.

| Old | New | Old | New | Old | New |
| --- | --- | --- | --- | --- | --- |
| DD-090 | DD-180 | DD-103 | DD-193 | DD-116 | DD-205 |
| DD-091 | DD-181 | DD-105 | DD-194 | DD-117 | DD-206 |
| DD-092 | DD-182 | DD-106 | DD-195 | DD-118 | DD-207 |
| DD-093 | DD-183 | DD-107 | DD-196 | DD-119 | DD-208 |
| DD-094 | DD-184 | DD-108 | DD-197 | DD-120 | DD-209 |
| DD-095 | DD-185 | DD-109 | DD-198 | DD-121 | DD-210 |
| DD-096 | DD-186 | DD-110 | DD-199 | DD-122 | DD-211 |
| DD-097 | DD-187 | DD-111 | DD-200 | DD-123 | DD-212 |
| DD-098 | DD-188 | DD-112 | DD-201 | DD-124 | DD-213 |
| DD-099 | DD-189 | DD-113 | DD-202 | DD-125 | DD-214 |
| DD-100 | DD-190 | DD-114 | DD-203 | DV-47 | DV-64 |
| DD-101 | DD-191 | DD-115 | DD-204 | DV-48 | DV-65 |
| DD-102 | DD-192 | — | — | DV-49 | DV-66 |
| — | — | — | — | DV-50 | DV-67 |
| — | — | — | — | DV-51 | DV-68 |
| — | — | — | — | DV-52 | DV-69 |
| — | — | — | — | DV-53 | DV-70 |
| — | — | — | — | DV-54 | DV-71 |
| — | — | — | — | DV-55 | DV-72 |
| — | — | — | — | DV-56 | DV-73 |
| — | — | — | — | DV-57 | DV-74 |
| — | — | — | — | DV-58 | DV-75 |
| — | — | — | — | DV-59 | DV-76 |
| — | — | — | — | DV-60 | DV-77 |
| — | — | — | — | DV-61 | DV-78 |
| — | — | — | — | DV-62 | DV-79 |
| — | — | — | — | DV-63 | DV-80 |

### DD-180 — The inbox bar: severity chips, read tracking, Clear all in the bar

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The drawer head's Clear all grows into a full-width inbox bar (ALR-11): a new ui-lib `AlertInbox`, a Bulma `buttons has-addons` group of one chip per severity (`is-expanded`, feed order, an empty severity's chip included), each chip a filter toggle showing that severity's **total** group count, a dot riding the DD-152 ramp while any of its groups is unread, and the caller's Clear all projected into the bar's end. The Drawer grows a second projection slot, `drawer-subhead`, a strip between the head and the body; the bar rides it. Read tracking lands with it (ALR-12): every `AlertGroup` carries `read`; an arrival — or a merge bumping a read burst — marks unread, and the panel's effect marks every group read while the drawer is open (visible-is-read). The bell badge answers unread presence in the highest **unread** severity's colour, superseding ALR-02's store-top reading.

**Reason.** The user's ask: a bar showing the count per severity, each severity a show/hide button, Clear all kept, "keep track of whether notifications have been read", and the question of totals vs unread on the chips. Totals won: the chips are filters, and a filter's number is what it covers — unread counts on filter chips make the bar flicker under reading (the chips zero out as the drawer reads the feed, the turn the user is mid-reading through vanishes). Unread stays where the attention question is asked: the bell dot, the row, the chip's dot. Visible-is-read won over a per-row read toggle: the drawer is 28rem of rows the user came to read; a list that requires marking each row read is a queue, not a feed, and the merge-re-unreads rule means a returning burst re-asks for attention on its own. Filter state is the panel's, not the store's: the store's counts and the bell must answer with the whole store, and a view filter is not data.

**Alternatives.** Chips showing unread counts (rejected above — the number changes under the user's eyes as the drawer reads). Filter state in the store (rejected: the bell's badge and the chips' totals must see everything, and persistence of a view toggle is scope the in-memory store does not have). A per-group read button (a queue; rejected). `markAllRead` on close (rejected: the badge would stay lit while the user is reading, and the ring/dot answers "has this been seen" — seen means seen). Clear all staying in the head beside the bar (two fixed strips stacked, the head's action orphaned from the bar it serves; the bar is the feed's command strip — the hatch belongs at its end).

**Consequences.** The Drawer has two content slots, actions (head) and subhead (the strip); the settings panel uses neither. The alerts drawer's tab order is close, the three chips, Clear all, then the rows. `AlertGroup.read` joins the lib's model — the third field the store owns and the list renders (ALR-10's vocabulary grows). The bell badge goes quiet on open, which is the point: it asked for attention and got it. DD-176's Clear all in the head is superseded in placement (its "above the notifications" requirement keeps holding — the bar never scrolls, DD-181); DD-176's chip-pair pinning stands.

### DD-181 — The drawer's body is the scroll container

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-21

**Decision.** The Drawer's panel clips (`overflow: hidden`) and its body scrolls (`min-height: 0`, `overflow-y: auto`): the head and the `drawer-subhead` strip are fixed, the content scrolls under them (DD-180's inbox bar, ALR-06/ALR-11's escape hatch).

**Reason.** Found while answering the user's question about a long feed: the panel carried `overflow-y: auto`, so the whole drawer scrolled — the head, title, close button, and DD-176's Clear all slid away with the feed, and the "head does not scroll" clause ALR-06 cited was not true. A drawer whose chrome scrolls away is a page, not a drawer: the close control and the command strip must be reachable at any scroll depth, and the inbox bar (DD-180) only pays off fixed.

**Alternatives.** A sticky head inside the scrolling panel (`position: sticky`: works, but the scrim/panel geometry makes it fragile with the slide animation, and the head's border composes over scrolled content under the rounded corners). Two scroll containers (rejected: nested scrolling on a 28rem panel is a trap).

**Consequences.** The settings panel's long body (six sections) now scrolls under a fixed head — the intended drawer reading, and the settings drawer's head carries its accessible name, so the panel reading it never loses it. jsdom runs no layout, so the scroll split is pinned by the spec's slot-placement test (DD-180) and the dev-server check, not by a unit assertion.

### DD-182 — The inbox bar is one joined group, severity-coloured, ramp order

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** Three follow-ups to the inbox bar (ALR-11, DD-180), from the user's review: every segment of the bar — the three chips, show all, and the projected Clear all — is an `is-expanded` member of the one `buttons has-addons` group (the actions join the joined bar, not beside it); the chip order flips to the ramp ascending — `info`, `warning`, `error`, calm to urgent (SEVERITIES, the countSeverities output, and the chips all follow); and a shown chip rides its severity's fill — the DD-152 pinned ramp (`#17a2b8`/`#ffc107`/`#dc3545`) with the ramp's own inks (black on warning and info, white on danger), not a single Aurelius blue. The unread dot rides the chip's ink (currentColor) with a hairline ring in the chip's plate, and the fill rides `is-sev-*` classes, not Bulma's `is-info`/`is-warning`/`is-danger` button colours.

**Reason.** The user's review of the live bar. The ramp order reads a bar the way the feed reads a stack — the urgent end lands beside the feed's own newest-first errors, and a bar whose colour intensifies left-to-right says "here is the dial". The severity fills carry the bar's own information: a chip IS a severity, and one blue bar made the chips interchangeable — the colours are the legend. Bulma's own `.button.is-info`-family fills are scheme-following token tints, and the brand pins `light` outside Bulma's scheme machinery (SHM-04): the pinned ramp is the product's severity vocabulary (DD-152, DD-168) and reads the same in both schemes, like the badge's dot and the footer's pair. The dot flips to ink for the same reason DD-176 pinned the count chip: a ramp-coloured dot on a ramp-coloured chip rides its own colour and vanishes.

**Alternatives.** Bulma's `.button.is-info`/`.is-warning`/`.is-danger` fills (scheme-following: the tints shift with the theme and collide with the brand's pinned plates — DD-176's trap, measured once on this very bar). Severity text ink on a plain chip, fill reserved (the user asked for coloured buttons; an outline bar reads disabled, not filtered). Ramp descending (error first, DD-180's first pass — kept for the feed's rows, newest/urgest-first; the bar is a dial, not a feed). The actions outside the group, flush right (DD-180's first pass: two visual systems on one strip — the user asked for one joined bar).

**Consequences.** `SEVERITIES` is the inbox's order and the bar is the model's only consumer of it; the feed's order is the store's own (newest first), untouched. The clear-all button's contract is "an expanded member of the group" — the panel's button and the host test carry `is-expanded`. The unread dot loses its severity classes (`is-*`): the chip's face is the severity, the dot only marks news. The bar's tab order is info, warning, error, \[show all\], clear all.

### DD-183 — The inbox bar is one height: the count badge is compacted

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** The inbox bar's count badge sheds Bulma's `.tag` height: `height: auto`, `line-height: 1`, `0.125em` vertical padding — the badge is compacted to the small button's scale, so every member of the group (chips, show all, Clear all) computes to the plain small-button height (ALR-11, DD-182).

**Reason.** The user's review of the live bar: Show all and Clear all sat a step shorter than the severity chips. The cause was the badge, not the actions: Bulma's `.tag` is a 2em control, and at the small button's font that is 1.5rem of content inside a chip whose own line is 1.125rem — the badge stretched its chip, and the group's flex stretch dragged Show all and Clear all up to match. DD-182's "is-expanded everywhere" made the step visible: joined segments expose each other's heights.

**Alternatives.** `align-items: flex-start` on the group (leaves the tall chips and short actions as they are, the join shows the gap). A plain `<span>` instead of a Bulma `.tag` (the tag's plate/rounding is the chip vocabulary, DD-176's pinned pair; the height is the only part to shed). `is-normal` on the tag (the size modifiers are font sizes, the `2em` height rides them all).

**Consequences.** The badge reads as the button's own metadata (a superscript plate) rather than a control sharing the row. The unit test pins the compaction's two properties; the equal height across segments is the group's stretch, verified on the dev server.

### DD-184 — The void chip: an empty severity greys out

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** An inbox chip whose severity the feed holds no alerts of is disabled (ALR-11): greyed by Bulma's disabled-button rule (the scheme-main plate, 0.5 opacity), unpressed, and carrying no severity fill. A chip with rows keeps DD-182's fills; a filtered-out chip keeps DD-180's plain-button reading. The three states read: severity-coloured = showing, plain = hidden by the user, grey = nothing to show.

**Reason.** The user's review: "grey out the buttons that have no alerts". DD-182 made every chip severity-coloured, so a severity with zero alerts kept its full-colour face — the bar shouted three severities for a feed with one. The states now map to the chip's truth: the fill answers "this severity is on the screen", plain answers "you filtered it", grey answers "there is nothing of this". A disabled chip is also inert, which is honest: toggling a filter with nothing to filter changes nothing, and a chip whose click is a no-op should not look clickable (the pointer cursor promises a state change).

**Alternatives.** Keep it clickable, greyed by class only (a click that does nothing — the affordance lies). Hide the empty chips (DD-180 chose a fixed three-chip bar — the shape is the legend; hiding makes the bar reshuffle as the feed churns). Strike the zero, keep the colour (a coloured zero still reads "on").

**Consequences.** The `is-selected` fill gate moves from "not hidden" to "has alerts and not shown hidden" — the `isOn`/`isVoid` pair on the component. `allHidden` (DD-180) was already void-aware: an empty severity's chip does not keep the show-all control away, and its disabled chip cannot be clicked off, so the control cannot strand a void-only bar. The panel hides the whole bar on an empty store, so the all-void state shows only in isolation (the Empty story).

### DD-185 — Show all is gone: the bar's shape never shifts

- **Status:** Accepted
- **Increment:** 7.15
- **Date:** 2026-10-22

**Decision.** The inbox bar has no show-all control (ALR-11). The `showAllLabel` input, the `showAll` output, the `allHidden` computed, the conditional button, and the panel's `showAll()`/`showAllLabel` are removed; the way back from a fully-filtered feed is a chip — a hidden chip stays enabled (only a void chip is disabled, DD-184), and clicking it shows its severity again. DD-182's "actions as group members" stands for the projected clear-all; it no longer covers show-all.

**Reason.** The user's review: appearing at full filtering, the control joined the `buttons has-addons` group as a fourth `is-expanded` segment — the three chips each jumped from a third to a quarter of the row, every toggle into and out of the fully-hidden state. A bar whose segments resize on state change reads as broken furniture; the escape hatch was worth less than the jump. It was also redundant: the chips were always clickable in that state (the hiding is per-severity and independent), so show-all only ever did what three clicks — usually one — already did.

**Alternatives.** A fixed-width reserved slot (a gap in the bar, always sized for a button that is almost never there). Absolute positioning outside the group (a floating control breaking the joined bar, DD-182's shape). Auto-restoring the filter when the feed empties (filtering to nothing is a legitimate state — the counts stay, the user chose it; silently undoing it is worse than no control).

**Consequences.** The bar's segment count is constant while it shows (chips + projected action), so the joined strip never reflows. The fully-filtered state shows the feed's empty line under all-flat chips — self-explanatory, and the counts on the chips say what is hidden. The `shell.alerts.showAll` string leaves both fixture locales and both catalogues (25 shell.alerts entries → 24). The AllHidden story and the two bar tests carry the new contract: no control, three expanded segments, a hidden chip toggles back on.

### DD-186 — Entity details arrives as a routed skeleton; its data spine joins 2.3

- **Status:** Proposed
- **Increment:** 7.6
- **Date:** 2026-10-22

**Decision.** 7.6 ports the Aurelius details screen (`search/details/:guid`) as the skeleton the data-free webapp can host today: the route contract, the header shape (title, type-name line, the 7.13 `breadcrumbs`), the description box, the properties accordion, and the side navigation — every part in its empty state, fed by the bridge keys `search.details.*` already in the catalogue. No entity fetch: `GET /v2/entity/guid/{guid}` is server 2.3 (planned), the type dispatch is nine `m4i_*` governance layouts, and the lineage/quality cards post to backends Aurelius Atlas will not have (DD-140). The wiring increment — the resolver, the header data, the type components, lineage — is named in the spec and lands when 2.3 does.

**Reason.** Every Aurelius details section reads one resolved entity; the Aurelius `DetailsResolver` feeds a search stack that DD-140 deliberately left unported. Shipping the fetch against a 404 is the speculative build DD-140 refuses, and shipping mock entity data is a UI promise the slice cannot keep — the 7.5 seam (DD-143) again, one screen deeper. The skeleton is what is true today: the URL is the screen's address, the chrome's strings are all keyed, the 7.13 components already render the trail and the rows, and the deep-link contract (DET-07) is testable end to end with zero data.

**Alternatives.** A full port against `HttpTestingController` mocks (the e2e stack runs the real server — the mocks evaporate at the first served test). A stub server (a second source of truth the parity harness must then ignore). Waiting for 2.3 entirely (the route, the layout, and the strings are real work that 2.3 does not gate; the 7.5 precedent ports exactly this kind of slice).

**Consequences.** The webapp owns a details route that renders a provable empty state; 2.3+7.6 is composition, not design — the resolver calls the client method DET-03 builds, the header binds the DTO, the type components join the shell. The nine `m4i_*` layouts stay deferred: Aurelius's own type model, out of Aurelius Atlas's scope until its data exists (the slice table names the wiring increment).

### DD-187 — The entity client is built test-first against the Atlas wire format

- **Status:** Proposed
- **Increment:** 7.6
- **Date:** 2026-10-22

**Decision.** `AtlasEntitiesService.getEntityByGuid(guid)` lands in 7.6: the DTOs are typed from the Apache Atlas 2.4.0 source (`AtlasEntity.java`, `EntityREST.java`), cited at the type, and the specs are `HttpTestingController` assertions on the request (path, headers, guid encoding) and the response mapping. No screen calls it (DD-186's skeleton fetches nothing); the 2.3+7.6 wiring increment consumes it.

**Reason.** DD-140's rule is one method per server increment, "each method lands testable against the real server." The entity-by-guid read is the surface 2.3 implements, and its wire format is fixed by Atlas's source and tests, not by this workspace — so the DTOs and the request shape are knowable today, and a spec that asserts them is honest (it never claims a 200). Building the client in the wiring increment makes that PR data + layout + client at once; splitting it keeps 2.3+7.6 about the server round-trip.

**Alternatives.** Grow the client in 2.3+7.6 (the honest choice 7.3's pattern allows — accepted as the fallback if the split adds review load). Port the whole legacy `EntityAPIService` surface (create, update, bulk, relationships — endpoints 2.4/3.x, unportable per DD-140's audit).

**Consequences.** The data-access lib gains one Atlas-native entity method, the typedefs client's shape (APC-01 base url, one method per legacy duplication, DD-140). When 2.3 lands, the e2e wiring scenario is the method's first real 200; its specs keep asserting the request until then.

### DD-188 — One API base: the client's URLs all ride the API\_BASE\_URL token

- **Status:** Accepted
- **Increment:** 7.6
- **Date:** 2026-10-22

**Decision.** ADR 054's rule, in client shape: every Aurelius Atlas **data** request composes its URL from the injected `API_BASE_URL` token (the APC-01 rule, now carrying the consolidated-server decision), and the webapp ships no second data-plane base URL, no hard-coded data host, and no search-backend client. Non-data surfaces keep their own configuration — Keycloak's URL (APC-05), the OTel exporter (SHL-11) — named at the deployment boundary, not through the token. The served-app boundary holds the rule closed: the CSP keeps `connect-src 'self'` for `/api`, widened only for Keycloak's origins, and the e2e CSP scenario asserts the baseline.

**Reason.** The user's direction, 2026-10-22: "the legacy app had a split between the app search api and apache atlas api. This new version consolidates these into the server api... All requests can be expected to be made to the server api," scoped the same day: "we may have other surfaces eventually but this is the one that replaces app search and the apache atlas apis" — the decision fixes the data plane's successor, and does not fence in identity, telemetry, or future non-data surfaces. The audit (7.3, DD-140) found the legacy split's two clients — the Atlas REST set and the App Search stack (`/elastic`, `/gov_quality`, `/data_quality`) — and ported only endpoints the server answers; the state already matches the rule. Recording it turns an audit outcome into a contract the search slice (7.4) cannot erode: when search lands, it lands as a server endpoint family (4.1) behind the same token, not as a second stack.

**Alternatives.** Record nothing (true today, silent tomorrow — 7.4 is the slice where a legacy-shaped search client would sneak back in). A purity-gate grep for the legacy hosts (the CSP assertion is the served-app's proof, the token is the code's; a grep bans strings, not shapes).

**Consequences.** DET-03's entity client composes from the token like the typedefs client; 7.4's search client joins it, specified from the Atlas source. The template example's `EntitiesService` (FastAPI CRUD/SSE, one SSE stream) stays a retiring example (DD-019, 7.10), not a second API. Any future non-server call site is an ADR event, not a pull request.

### DD-189 — The details chip is the classification chip; its sources project in

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `classification-chip` is the Bulma `tags.has-addons` chip of `search/components/classification/`: icon lead tag, label tag with tooltip, loading tag, and the optional propagation tag whose hoverable dropdown projects the sources list via `[chip-sources]`. The legacy `ClassificationService` (the type-definition lookup by name) and `ClassificationSourceService` (the repository-fed source rows) are inputs and projection — name, description, `propagated`, and the sources content arrive from the caller. The glossary-term chip (`search/components/term/`) is the same atom with `is-info` on the lead tag, so it is not a second component: the lead colour is an input.

**Reason.** The two legacy chips are byte-identical markup around one colour class and one label key; a `term-chip` twin would be a copy. Everything the chip's services fetched is a fact the caller already holds wherever the chip renders (the details header reads classifications off the entity DTO; 2.3's entity read carries them) — the service indirection existed to cache per-name lookups, a data concern, and the lib's rule (UIC-15) is that the caller supplies what it has. The sources rows stay projected rather than modelled because their shape (a media row: name link, crumbs, type badge) is the app's `classification-source` anatomy — the 7.6 deferral table's repository-fed part — and the chip should not reach past a slot into it.

**Alternatives.** One generic `tag-chip` with colour + icon + label inputs (refused — it erases the propagation dropdown, the chip's real behaviour, and "details chip" named for no legacy source). Two components, classification + term (refused — the copy-paste twin). Model the sources as `{guid, name}` inputs with a built-in row (refused — the row is repository-fed, the wiring 7.6 defers).

**Consequences.** The chip is speccable and storyable with zero data (the sources slot stories the dropdown's content). When 2.3 lands, the header composes `@for (c of entity.classificationNames)` chips and feeds the slot from the propagated-sources lookup — the chip itself does not change. The term chip's key (`search.components.term.term`, "Term") becomes the term call site's lead label input.

### DD-190 — The type-name badge is extracted from entity-card

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `type-name` is its own component: the `span.icon-text` badge (icon, `typeAlias ?? typeName`, base-type suffix) of `search/components/type-name/`, with `iconsByType` as caller inputs (UIC-15). 7.13 inlined this badge inside `entity-card` (UIC-12); `entity-card` now renders `type-name`, and UIC-12's rendered output is unchanged — its spec is the extraction's regression proof.

**Reason.** The badge's call sites in the legacy app outnumber the card's: the details header's `.subtitle.name` line, the propagated-sources rows, the editor (7.7), the results cards. 7.13 inlined it because the card was the only component shipping it then; the details audit found three more call sites, and an inlined badge gets copied at each. The `iconsByType` index the legacy badge reads is app meta (UIC-15's split), so the standalone form needs no app code: icon and class are inputs, as the card already passes them.

**Alternatives.** Keep the badge inlined and let the header compose the badge markup by hand (a third copy of the badge's markup in the webapp, inside the skeleton 2.3+7.6 then edits again). Export the badge as a directive on `entity-card`'s internals (refused — the lib's components are the public surface; internals are not).

**Consequences.** One badge implementation; `entity-card`'s inputs pass through to it (the public API is unchanged — UIC-12's spec stays the guard). The details header composition (2.3+7.6) uses it for the type line without touching the card. `classification-chip`'s sources slot rows use it as their badge (DD-189).

### DD-191 — Details navigation is a shell; the scroll directive stays app-side

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `details-navigation` ports the shell of `details/components/navigation/`: `box.is-paddingless` around a Bulma `dropdown.is-up.is-right`, the toggle button (caller icon input, `is-active` toggled on click), and the `nav.menu` with the label input and the `ul.menu-list` fed by `ng-content`. The legacy `DetailsNavigationItem` directive — click scrolls the target into view — is not ported into the lib; items are caller markup, and the app wires their behaviour.

**Reason.** The shell is presentational and complete on its own (the Bulma dropdown's open/close is pure CSS once `is-active` toggles). The directive is DOM behaviour on the application's document (`document.body` is the legacy label's target): a lib component that scrolled the page would own layout the app owns — the purity rule's same line as `breadcrumbs`' routing split (UIC-11). Keeping `li`s as projected content also means the nav composes with any anchor scheme: the 7.6 skeleton's same-page `#section` hrefs today, the wiring increment's hash-router links later, without the lib changing.

**Alternatives.** Port the directive too (a lib scrolling the host document is library overreach, and the target ids are app anatomy). Emit `itemClicked(target)` like `section-stats` (refused for the nav: the legacy nav's items are arbitrary projected markup, the directive is the wiring — an emit would only cover component-owned anchors, i.e. it would cover the shape that isn't here).

**Consequences.** The webapp's 7.6 side nav swaps its inline `nav.menu` for this shell and (in 2.3+7.6) adds a small app-side directive for scroll — named in 7.16's deferral table. Storybook stories the shell with static items; the toggle's `play()` test proves the interaction.

### DD-192 — The count bar is section-stats: one component, two call sites

- **Status:** Proposed
- **Increment:** 7.16
- **Date:** 2026-10-22

**Decision.** `section-stats` ports the `nav.level` count bar the legacy details screens duplicate — `default-details.component.html` (one stat: properties) and `gov-quality-details.component.html` (three: non-compliant, compliant, properties) — as one component: `items: { label, target, count }`, `p.heading > a` (href `#target`) + `p.title` per item, `itemClicked(target)` on activation (DD-154's emit-instead-of-navigate pattern; the anchor's href is the keyboard path).

**Reason.** The two bars are the same Bulma block with a different item count, and the details header (2.3+7.6) and editor (7.7) repeat it again — the Aurelius pattern is "a heading-link that jumps to the section, with its count above the fold". The legacy count came from a service stream; here the count is a string the caller renders (it is a count, not a number with locale semantics — the legacy template interpolated it raw). Making `target` a plain id keeps the href honest for the same-page case the skeleton is (7.6), and `itemClicked` lets the app intercept (the nav directive's smooth-scroll, analytics, hash-router links).

**Alternatives.** A `properties-count` special case (refused — the gov-quality bar proves the shape generalizes). Bulma `level` as slots per item (refused — items are homogeneous, an array input is the smaller API).

**Consequences.** The 7.6 skeleton's inline count bar becomes `section-stats` with one item when the wiring increment lands (the skeleton stays as specced until then — DET-02's zero-row bar is its contract). Gov-quality (7.8) composes three. The strings ride the caller's inputs; the bridge keys (`search.details.default.properties`, `search.details.govQuality.*`) already exist.

### DD-193 — Collector ingest is authenticated in two legs: user JWTs for browsers, a shared token for services

- **Status:** Proposed
- **Increment:** 7.17
- **Date:** 2026-10-22

**Decision.** The OTel collector's OTLP receivers stop accepting anonymous writes, with a per-leg proof of the writer (CIA-01). The **browser leg** (HTTP 4318) authenticates the signed-in user: the collector's `oidc` extension validates the Keycloak access token the SPA sends — issuer, signature, and the `otel-collector` audience the realm's `otel-ingest` client scope mints — so every span and metric carries the user's identity (the `sub` claim). The **service leg** (gRPC 4317, HTTP 4319) keeps a shared ingest token (`bearertokenauth`): headless producers — the Atlas server, the FastAPI example, Keycloak's own OTLP, the slice pullers — present it through the standard `OTEL_EXPORTER_OTLP_HEADERS` / their exporter's `headers` block (CIA-04). The browser's proxies pass the `Authorization` header through untouched (nginx's default, and http-proxy's): the proxy is a pipe, not a credential (CIA-02). The SPA attaches the token through the OTLP exporters' `headers` factory — an async callback OTel invokes per export (the OTLP transport rides XHR/fetch outside Angular's HttpClient, so the bearer interceptor cannot cover it). The seam is shared, not per-app: `createAureliusOtelIngestAuth` in `aurelius-atlas-observability` carries the factory and an `attach` binding, and each app hands it the live `Keycloak` client in a `provideAppInitializer` (the webapp's sits inside its telemetry gate — with telemetry off there is no exporter to feed); no registration order is load-bearing, as the factory resolves the token at export time. `updateToken(30)` per export covers the dev realm's 60s token. The collector's host publishes pin to 127.0.0.1 (4317/4318/4319) and the prometheus exporter's publish drops — CIA-03. The issuer URL is compose env (dev default at the plaintext `:8080` issuer, ADR 039's relaxation; the e2e conftests override with the TLS `:8443` issuer plus the shared dev CA, matching each stack's `iss` claim); the extension discovers JWKS from the issuer itself and needs Keycloak reachable at startup. The dev token lives in `dev/observability/.env(.enc)` and every producer project's `.env.enc`.

**Reason.** ADR 039 states the collector's ingest rule as TLS — that proves *which collector* a writer reaches, not *who* writes: on a dev machine the published 4317/4318 accepted anonymous writes from anything that could route to the Docker host, and through the webapp's own `/otel/` proxy from anywhere that could reach the site. The credentials stack on the verified channel; ADR 034's one collection point stays (a credential, not a hop). The browser leg chooses user JWTs over a shared secret for **attribution**: forged telemetry carries the forger's `sub` and is revocable per user, and the telemetry's user joins the traces the SDK already correlates. This corrects the claim made earlier in this increment's design (and in the NasTech write-up's counterexample) that a public client makes a JWT gate worthless: `publicClient` means the *client* holds no secret, not that tokens are free — auth-code + PKCE still requires the user's credentials, so "anyone with a connection" becomes "anyone with an account", the same bar a shared proxy secret sets, with identity for free.

**Alternatives.** One shared token on both legs, the proxy injecting the browser's (this design's first cut, refused — it closes open ingest but attributes nothing, and a leaked proxy secret forges un-attributed telemetry forever; the user-JWT gate has the same bar and keeps the identity). Making the `aurelius` client confidential (refused — an SPA is a public client by definition: anything shipped in the bundle is public, keycloak-js's PKCE flow rejects confidential clients, and confidentiality protects the client, not the token — attribution rides the token's `sub`). Keycloak JWTs on the service leg too (refused for now — Keycloak bootstrapping itself as its own telemetry's issuer is a chicken/egg, the pullers need a client-credentials `oauth2client` extension, the Python SDK's headers env is static so a 5-min JWT needs a refresh shim, and the observability stack starts before Keycloak by design — the per-service graduation stays open: the extension validates JWKS for any audience. (Delivered by DD-196 in 7.18: the pullers' `oauth2client` extension, the server's refresh shim, and the issuer-shaped boot order each closed one named wall; Keycloak-native — the one producer with no answer — keeps the shared token on the legacy leg.) `optional: true` on the OIDC receiver, or starting OTel after auth, to keep pre-login telemetry flowing (both refused — unauthenticated pass-through reopens the exact door this closes, and a post-auth SDK start loses the cold-load Core Web Vitals the dashboard is built on; the first-load telemetry loss is **accepted**, the login is the telemetry gate). Keeping the seam per-app (refused at the review pass — the first draft carried a byte-identical copy in each app config; the seam is the OTLP transport's relation to auth, which is `aurelius-atlas-observability`'s knowledge, and one tested copy beats two. The lib's exporter-agnostic rule is untouched: the seam types its client structurally — `authenticated` / `updateToken` / `token`, the same shape keycloak-angular's interceptor reads — so the lib depends on a shape, not on `keycloak-js`).

**Consequences.** The browser leg makes Keycloak a dependency of browser ingest: the collector fetches JWKS from it, the e2e conftests start Keycloak before the collector's issuer is consulted, and a dev machine exporting browser telemetry with Keycloak down sees 401s (the service leg keeps flowing). Pre-login exports (the landing page's first spans/metrics) are rejected — accepted. Every service producer must present the token, including future ones — each slice's `nx serve`/e2e runs are the gate (CIA-04, the webapp e2e's accepted-export test plus every slice's suite). The realm's `otel-ingest` scope is part of the `aurelius` client contract: tokens minted before a realm re-import carry no `aud` and are rejected (dev/keycloak AGENTS.md). The e2e suites mint a real user token (password grant, the dev sign-in user) to drive the browser-leg tests, and the collector's compose gains `OTEL_COLLECTOR_OIDC_*` env with a `/dev-ca` CA mount; `dev/observability` gains a `.env.enc`, so its compose targets now `dependsOn` `decrypt` like every other slice. The NasTech pattern this follows (OIDC extension on the HTTP receiver, user token from Keycloak) is credited: [https://blog.nashtechglobal.com/secure-opentelemetry-collector-for-tracing-front-end/](<https://blog.nashtechglobal.com/secure-opentelemetry-collector-for-tracing-front-end/>)

### DD-194 — The collector stamps the verified user onto the telemetry: `enduser.id`

- **Status:** Accepted
- **Increment:** 7.17
- **Date:** 2026-10-22

**Decision.** DD-193's browser leg verifies the user's token; this makes the verified identity ride the data (CIA-05). The collector's shared `resource` processor copies the OIDC context's subject claim onto every browser-leg push: `key: enduser.id, from_context: auth.claims.sub` (the claims land in the request context under their **raw JWT names** — Keycloak's subject claim is `sub`; the extension README's `auth.claims.subject` example fits issuers that name the claim that, and a missing source upserts an **empty** attribute, not nothing — verified against 0.162 with a Tempo read-back). The attribute key is `enduser.id` (the semconv registry's key for a user identifier; `subject` alone is ambiguous next to `service.name`). The traces/metrics pipelines share the processor, so a user's spans and web metrics carry it. On the metrics leg a `transform` processor (`context: datapoint`, `set(attributes["enduser.id"], resource.attributes["enduser.id"])`) promotes it to datapoint level, where the prometheus exporter turns it into the `enduser_id` label — the exporter keeps only a few resource attributes as labels (`service.name` → `exported_job`) and drops the rest, so without the promotion the stamped identity never reaches Prometheus. The service leg has no OIDC context: its pushes carry `enduser.id=""` (empty upsert, above) — producers stay unattributed, and the label is one constant value, no cardinality growth.

**Reason.** Attribution was the browser leg's reason for user JWTs over a shared secret (DD-193): a forged push is attributable to the account that minted the token. That clause is only true once the identity is ON the data — verification alone leaves Tempo/Prometheus blind to which user a span came from, and the dashboards (keyed on `service_name`/`exported_job`) cannot answer "whose load is this". Tempo searches it as a resource attribute (`{ .resource["enduser.id"] = "<sub>" }`, TraceQL 2.3 scoped syntax) and the e2e reads it back through trace-by-id.

**Alternatives.** `resourcedetection` with an auth detector (refused — no auth detector exists; the claim copy is the `resource`/`transform` processors' job). Span-attribute copy instead of resource (refused — the resource is the per-push envelope: one copy per push, every span in it inherits; a span-level copy needs OTTL per span and misses metrics, whose datapoints the transform already covers). `enduser.id` + `enduser.name` (`preferred_username`) (deferred — the readable name doubles the PII surface for a dev stack; the `sub` UUID is joinable to Keycloak's admin at query time; add the display name with the audit slice if the dashboards need it). Tempo's `metrics_generator` with `dimensions: [enduser.id]` (refused for now — it would generate span-metrics/service-graphs series per user from traces; the collector-side label promotion covers the dashboards, the generator stays off as in the rest of the stack).

**Consequences.** `sub` (a UUID) is PII-adjacent: it is a persistent per-user identifier inside telemetry retention — accepted for the dev stack, and the production posture note is ADR 039's (the collector's own). Dashboards can group by `enduser_id` (metrics) or filter `{ .resource["enduser.id"] = … }` (Traces); Tempo's live-store search indexes span attributes only, so resource-predicate searches hit backend blocks (older than \~30 min) — Grafana's TraceQL UI handles the fan-out, the e2e asserts storage through trace-by-id (`GET /api/traces/<id>?encoding=json` — Tempo 3.x's route is the plural, the singular `api/trace/` 404s, and the default encoding is protobuf). Pre-login telemetry stays lost (DD-193's accepted trade).

### DD-195 — The collector rides out Keycloak's boot: bounded restart, awaited readiness

- **Status:** Accepted
- **Increment:** 7.17
- **Date:** 2026-10-22

**Decision.** DD-193's `oidc` extension discovers JWKS at extension start, so the collector exits 1 whenever Keycloak is not answering yet. The boot order makes that window structural: keycloak (and the postgres/elasticsearch slice composes) attach `aurelius-atlas-dev-observability-network` as an **external** network, so observability must come up first — Nx's `implicitDependencies`/ `^up` chain and the e2e conftest fixtures both start it before Keycloak. The fix is therefore on the collector side, not the order: `restart: on-failure:15` in `dev/observability/docker-compose.yaml` (Docker backs off 100ms doubling to a 1min cap — \~15 attempts span \~6 minutes, far past Keycloak's boot, and the bound means a Keycloak that never comes up ends in a loud `compose up --wait` exit rather than an infinite crash loop). Keycloak's readiness gate is compose's own: the conftest fixtures' `start()` runs `up --wait` and the keycloak service carries a healthcheck, so the command returns when Keycloak is ready. The fixtures' post-start `HealthcheckWaitStrategy` registration is dead code (`waiting_for` is a setter, `start()` runs the strategies) and is removed from the webapp/frontend-example conftests — it could never have worked: the strategy reads docker-py `attrs`, which the `ComposeContainer` wrapper `DockerCompose.get_container()` returns does not have (verified: it raises `AttributeError` the moment it runs). The fastapi-example's dead registration stays — its `_wait_for_dev_users` poll is that suite's real Keycloak gate.

**Reason.** Found as a full e2e failure: with a cold stack, `docker compose up --wait` on observability exits 1 on the collector's first crash, every fixture errors, and 90 tests never run. Verified: `up --wait`'s watcher survives the intermediate exits and returns when the container lands on a running/exit-0 state, so the restart policy makes the cold start self-heal (collector \~30s behind Keycloak's health).

**Alternatives.** Start Keycloak first (refused — the external-network attachment makes the order structural, and the Nx graph would invert for a dev-stack-only reason). A healthcheck-gated collector (refused — the image is shell-less/hardened, and compose has no keycloak service to gate on from this stack). A testcontainers `HealthcheckWaitStrategy` on the keycloak fixture (refused — the strategy reads docker-py `attrs` the `ComposeContainer` wrapper does not expose, so it raises `AttributeError`; `up --wait` already gates on the service healthcheck). Retries inside the extension (refused — the oidc extension has no retry knob; discovery hard-fails at start by design). An unbounded `restart: on-failure` (refused — a permanently broken issuer then crash-loops forever and `up --wait` never returns; the bounded count keeps the failure loud).

**Consequences.** A cold `nx up`/e2e start costs the collector a few restart cycles (\~30s) — invisible behind Keycloak's own \~40s boot. The dev stack's plaintext :8080 issuer keeps the same window. The nginx `/otel/` proxy in the webapp/frontend-example e2e configs moves to a variable upstream (`set $otel_upstream` + resolver) like the `/api/` block: a literal `proxy_pass https://otel-collector:4318` resolves at config load, which fails nginx while the collector is restarting (DD-195 makes that window normal). The `set` must precede the `rewrite ... break` — `break` halts the rewrite module, of which `set` is a directive, so a `set` after the rewrite never runs and the upstream host resolves empty (500, "no host in upstream"; the shipped production template orders them the same way, discovered by measurement). The `collector_container` fixture polls for the settled running state — a restarting container reports no port bindings, which the loopback-pinned test reads.

### DD-196 — The service leg graduates to per-service identity: Keycloak client-credentials JWTs, azp-stamped

- **Status:** Proposed
- **Increment:** 7.18
- **Date:** 2026-10-23

**Decision.** DD-193's service leg proved *that a writer holds the shared secret*, not *which writer* — a leaked secret forges un-attributed service telemetry forever. The graduable headless producers now mint their own Keycloak identity: four confidential service-account clients (`otel-postgres`, `otel-keycloak`, `otel-elasticsearch`, `otel-atlas-server`) on the `otel-ingest` default scope (the same `aud: otel-collector` mapper as the browser leg), the shared dev client secret carried as an `${OTEL_INGEST_CLIENT_SECRET}` placeholder in the realm import (the dev-users' pattern). The collector's `otlp/services` receivers (gRPC 4317 / HTTP 4319) swap `bearertokenauth` for the **same `oidc` extension** the browser leg uses — one issuer, one validator, both legs (the contrib image has no `compositeauth`, so a port carries one authenticator: the per-service leg and the legacy leg are separate ports by construction). The three slice metrics-pullers present their JWT through the contrib collector's own `oauth2client` extension (mint/cache/refresh natively, zero custom code, `restart: on-failure:15` for the DD-195 race, issuer-shaped now). The Atlas server (Python, logfire) presents its JWT through an in-app refresh seam: `ClientCredentialsTokenSource` (stdlib urllib, thread-safe cache, refresh-ahead, header-less export on mint failure = the visible 401) feeding per-export `headers` into app-owned OTLP exporters wired through logfire's `additional_span_processors` / `MetricsOptions.additional_readers` — the static `OTEL_EXPORTER_OTLP_HEADERS` env is dropped, the app owns the OTLP export (logfire reads it statically; a 60s dev token cannot ride a static header). Staying on the **legacy leg** (a new `otlp/legacy` pair, gRPC 4320 / HTTP 4321, `bearertokenauth`, loopback-published): **Keycloak's native OTLP** — the issuer cannot present a token it has not minted yet at cold boot (DD-193's chicken-and-egg, now scoped to exactly this) — and the **FastAPI example** (the same static-header wall as the server, paid at the server where it earns). Attribution (DD-194 extended): the resource processor upserts `otel.ingest.client` from the verified token's `azp`, and a `transform/identity` (resource context) clears `enduser.id` for service-account pushes (`azp` prefix `otel-`) — human and machine identity stay distinguishable in Tempo/Prometheus; browser pushes carry `otel.ingest.client="aurelius"` + `enduser.id=<sub>`, legacy pushes carry neither (DD-194's empty-upsert rule, unchanged).

**Reason.** DD-193 refused this graduation for four reasons (Keycloak self-boot, the pullers' client-credentials need, the Python SDK's static headers, the boot order) — every one has a bounded answer now: the `oauth2client` extension is the pullers' client-credentials mint+refresh, the shim is the Python answer, and Keycloak-native — the one producer with no answer — keeps the shared token on its own leg. Keycloak is the issuer of record for every credential in the stack (browsers, APIs); reusing it for services means one validator, one trust story, and the same `otel-ingest` audience contract on both legs. Per-client attribution de-anonymizes the shared secret's blast radius: a leaked `otel-postgres` secret forges only postgres telemetry, visibly.

**Alternatives.** Static JWTs in env (refused — the dev realm mints 60s tokens; static bearer JWTs expire in a minute, the whole point of mint+refresh). One leg with two authenticators (refused — contrib 0.162 has no `compositeauth`; a client-id allowlist inside one OIDC leg was also refused: the extension verifies credential *type*, not identity, so the honest posture is credential-typed legs, every push authenticated and attributed — a user token on the service leg is a curiosity, not a hole). Per-service dev secrets (deferred — the clients already carry distinct ids, which is what the stamp and the revocation target use; distinct secrets rotate per-producer and the realm placeholder machinery multiplies; prod deployments inject per-client secrets, the realm import supports it as-is). A mint sidecar for the Python producers (refused — a sidecar adds a boot unit per app and a localhost hop; the shim is \~100 stdlib lines with a unit suite, and the server owns its telemetry the way it owns its store). A client-credentials file credential source (the OTel spec's `credentials-file` shape, not implemented in the Python SDK) — the shim is its stdlib form (watch this: upstream, delete the shim). Permissive-issuer boot windows for Keycloak-native (refused — an unauthenticated window at cold boot reopens DD-193's door). Dropping Keycloak-native OTLP (refused — the IdP's own traces/logs are first-class telemetry for an auth-gated platform; the puller covers its DB metrics only).

**Consequences.** The dev stack's ingest surface is five loopback-published ports (4317/4319 per-service OIDC, 4318 browser OIDC, 4320/4321 legacy shared). Keycloak boot is now load-bearing for the per-service leg the same way it is for the browser leg: the pullers and the server 401 until the issuer answers (restart policies + refresh-ahead carry them; DD-195's collector restart covers the collector itself). The collector's `enduser.id=""` for services (was DD-193: `sub`-shaped UUID on service pushes under the DD-194 stamp) is a **label change** for the dashboards: service series move to `enduser_id=""` + `otel_ingest_client=<id>`; the dev-stack dashboards' queries ride this increment. The shared ingest token survives for exactly two producers (Keycloak-native, FastAPI example) — the legacy leg retires when a gRPC-native producer can present a JWT (a Quarkus bearer-header hook) and the example app adopts the shim pattern. Realm re-import rotates the dev client secret: every `.env.enc` carrying it re-encrypts in the same PR (the DD-193 `otel-ingest` note, extended). e2e: the webapp suite mints a service token (client\_credentials grant, the `otel-atlas-server` client) beside the 7.17 `user_token` fixture; `test__collector_accepts_the_shared_ingest_token` moves to the legacy port; the loopback-pin test's socket set grows to 4317–4321.

### DD-197 — The auxiliary APIs share one foundation: the OTel and auth libs

Each auxiliary app gets its own ingest client (increment 8.0).

- **Status:** Proposed
- **Increment:** 8.0
- **Date:** 2026-11-08

**Decision.** The auxiliary API apps of ADR 055 (8.1–8.3) do not each re-implement the plumbing. Two libraries carry it, both extracted from code this workspace already runs and tests:

- `libs/python/aurelius-atlas-otel` — DD-196's ingest mechanism (the client-credentials token source with refresh-ahead + 401-retry, the OTLP pipeline builder, console-only dev mode) moves verbatim out of `aurelius_atlas_server/otel_ingest.py` with its six tests. The server imports the lib; every future service gets the same collector leg by configuring three settings. The per-service identity story extends: `otel-data2model`, `otel-lineage-model` and `otel-validate-entity` join the `otel-<service>` confidential-client family on the `otel-ingest` scope (DD-196's audience/mapper unchanged), each carrying its own `${OTEL_INGEST_CLIENT_SECRET}` placeholder.
- `libs/python/aurelius-atlas-auth` — the FastAPI example's OIDC verifier (OIDC discovery + JWKS behind a circuit breaker, kid-pinned RS256 verify, issuer check, `azp`∪`aud` audience match, realm-roles-plus-own-audience roles per DD-132) becomes the workspace's auth library. The auxiliary apps consume it as `require_auth` / `require_write` dependencies; the raw bearer dependency exists for forwarding only, never authorisation (AUX-05).

**Reason.** The example app's auth prototype is the workspace's only verified OIDC implementation, and DD-196's ingest shim is the only verified service-identity implementation — a third FastAPI app copying either file is three copies of a security path (049's test-naming rule argues the same: one named test per rule, not three near-identical ones). Extraction is cheaper now than convergence later, and both libs ship with the server's green suites. Per-service ingest clients (vs one shared auxiliary client): DD-196's least-privilege reasoning applies verbatim — a leaked `otel-data2model` secret forges only data2model telemetry, visibly.

**Alternatives.** Copy-paste per app (refused — three drift-prone copies of auth + ingest). One shared ingest client for all auxiliary apps (refused — DD-196 rejected exactly this for the server fleet). Put auth inside the server app and import across apps (refused — the server is an app, not a lib; apps importing apps inverts the dependency graph and drags the store). A dedicated `aurelius-atlas-fastapi-base` app template with auth+otel baked in (deferred — premature until three real consumers exist; the two libs compose into the 8.x apps with ten wiring lines each, and a template can formalise from those).

**Consequences.** The server's `app.py` gains one import (`aurelius_atlas_otel`) and loses `otel_ingest.py`; its six CIA-07 tests move to the lib unchanged (the spec-file rule ids ride along: the tests cite CIA-07, defined in 7.18's spec, unchanged). The Keycloak realm import grows three clients; realm re-import rotates nothing new (shared dev secret, DD-196's note). 8.1–8.3 each add: a settings model (env prefix), the app factory, auth dependencies from the lib, `build_otlp_pipeline` from the lib, one `otel-<app>` client's secret in `.env.enc`, and their own rule ids. CSRF stays out of scope: the auxiliary APIs are bearer-first like the metadata API; the cookie/CSRF story is the webapp increment that serves them (8.4+).

### DD-198 — The 8.x ports are pandas-free: pydantic rule models, plain row maps

- **Status:** Proposed
- **Increment:** 8.1
- **Date:** 2026-10-23

**Decision.** The data2model port (8.1) adds no pandas. The request's `rules` parse as pydantic models (the app's public request contract, validated at the boundary: unknown types, missing keys and dangling rule references are 400 at parse time, DTM-11/DTM-12); the tabular `data` is a plain `list[dict[str, Any]]` of row maps, and extraction, dedup, view selection and layout are plain Python over that list. The same rule applies to 8.2 (lineage-model) and 8.3 (validate-entity).

**Reason.** The legacy chain reaches pandas through `m4i-analytics`: `DataFrame(data)` is the legacy representation of the request body, and the DataFrame ops (`drop_duplicates`, `isin`, boolean masks) are the extraction semantics the DTM rules state directly — the spec cites behaviour, not pandas, and the browser contract is the response JSON, not the representation. The workspace's spine is pydantic (FastAPI settings, model validation; ADR 050's "only what the catalogue needs"), the user's stated convention, and a pandas dependency buys nothing the DTM rules need: the lineage chain's row counts are a lineage neighbourhood's edges, not a data science corpus. One less native dependency in a dhi.io/alpine wheel set (pandas' `numpy`/`pyarrow` transitives), and the app's typed surface is the pydantic rule models, which FastAPI documents for free.

**Alternatives.** Port `m4i-analytics`'s DataFrame pipeline (refused — DV-68 already refuses the library; its graphviz/bokeh tree arrives with it). Pandas inside a thin native shell (refused — every DTM rule has a five-line plain-Python form; pandas would be a dependency of a dozen `drop_duplicates` calls). pydantic row models for `data` (refused — the columns are the *caller's* rule keys: a row model would be `model_config = ConfigDict(extra="allow")` with declared fields for nothing; a row is a map, the rules name its columns).

**Consequences.** The NaN semantics travel as null: a pandas NaN reaches the legacy extractor through `read_json`-shaped payloads, and the JSON request body can only carry it as `null` — the DTM rules state null-drop/null-empty directly (the `'nan'`-string artefacts a NaN id produced in the legacy are a legacy accident, recorded in 8.1's deviations, not a contract). The app's pyproject gains `pydantic`/`fastapi` and no pandas; 8.2's flattening (12 columns, fixed keys) is the same shape and stays plain dicts.

### DD-199 — App unit tests clear the injected `.env` prefix in an autouse fixture

- **Status:** Accepted
- **Increment:** 8.1
- **Date:** 2026-10-23

**Decision.** Every Python app's `tests/conftest.py` carries an autouse fixture that deletes every environment variable starting with the app's `ENV_PREFIX` before each test. Tests and fixtures then set exactly the variables they mean.

**Reason.** Nx injects a project's `.env` into **every** task's environment for that project, and pydantic-settings reads the environment for every field a test does not pass explicitly — `model_validate` included. The dev `.env` stores TLS material and directories as workspace-root-relative paths, while `nx test` runs pytest with `cwd=projectRoot`, so the paths do not resolve and every `FilePath` field fails validation: under `nx test -c ci`, the server's suite reported 50 setup errors and data2model's 12 — identical for both apps, invisible to a plain `uv run pytest` from the workspace root, and invisible to CI, whose PR gate selects tasks the `test`-affecting files do not touch. Clearing the prefix is the smallest hermetic fix; the alternative — absolute paths in `.env` — breaks the containers (the compose files resolve them against the project dir) and `nx serve` (which runs from the workspace root, the one cwd where the relative paths do resolve).

**Consequences.** Unit tests no longer read dev secrets, dev endpoints, or dev certificates, in any working directory. The settings tests keep testing environment reading — their `environment` fixture sets the variables it needs after the clear. `e2e/` conftests keep loading the real `.env` on purpose: those tests talk to the real dev stack.

### DD-200 — The 8.2 proxy app injects its upstream HTTP client; the e2e Atlas is a canned-file server

- **Status:** Accepted
- **Increment:** 8.2
- **Date:** 2026-10-23

**Decision.** `create_app(settings, auth=None, http=None)` takes the upstream `httpx.Client` the lineage fetch and the `/extract` call run on; production builds one (timeout, CA), tests inject a `MockTransport`. The e2e stand-in for the Atlas lineage feed (5.1, DV-69) is a **canned-file fixture Atlas**: a dhi.io Python image serving `http.server`, whose `--directory` is the suite's fixture directory, answering `GET /v2/lineage/<guid>` from `<guid>.lineage.json` (404 for an absent file, matching Atlas).

**Reason.** The app's contract is a proxy: everything interesting about it is which upstream requests it makes with which headers, so the client must be inspectable — an injectable client makes the fetch/extract calls, the forwarded `Authorization` header, and the 404/400/5xx mapping unit-testable with no sockets (the 8.1 suite's fake issuer established the pattern). For e2e, the real Atlas feed is increment 5.1; the fixture is the smallest process that speaks the `v2/lineage/{guid}` shape — no build, no app image, no Python in the sandbox image (the stdlib ships with the dhi.io python image), and a file tree a reviewer can read as the scenario data. Serving it from plain files keeps the fixture honest about the wire shape: the camelCase JSON is Atlas's, not a mock's invention.

**Alternatives.** A python fixture container with a hand-written handler (refused — the stdlib server plus a file per guid is the same test surface with less code to own). testcontainers MockServer/WireMock (refused — a Java/Go image for a two-route contract; the workspace's e2e stack stays dhi.io images plus stdlib). Pointing the suite at a real Atlas (refused — 5.1 is not built; DV-69 is the stated stub).

**Consequences.** The 8.2 e2e chain (Keycloak → lineage-model → real data2model → fixture Atlas) exercises the full browser path minus the metadata store. When 5.1 lands, the suite repoints `ATLAS_BASE_URL` at the server and keeps the canned fixtures as regression data.

### DD-201 — The 8.3 mock ships as module data; the verifier is injectable

- **Status:** Accepted
- **Increment:** 8.3
- **Date:** 2026-10-23

**Decision.** `aurelius_atlas_validate_entity.mock.MOCK_VALIDATION` holds the legacy `output` dict verbatim, as module data — the endpoint answers `json` of that constant, byte-for-byte. `create_app(settings, auth=None)` takes the shared `KeycloakAuth` verifier; production builds one from the settings, tests inject one pointed at the fake issuer. No request model: `POST /` does not read its body (the legacy mock ignores it, and the port keeps that).

**Reason.** The app is a constant: every rule about it is the document's shape (VE-02) and the auth gate (VE-03), so the document lives in one place as data, and the scenario/unit tests compare whole bodies with no volatile fields. An injectable verifier is the DD-197/8.1 pattern (the auth library's own test double is the reference); a request model would invent a contract the mock does not have (DV-67: the body is ignored, malformed bodies answer the document too — VE-01).

**Alternatives.** Pydantic models for the mock document (refused — the document is a fixed literal; modelling it adds code that can drift from the bytes the browser contract is). A `Request`-reading handler that validates the entity (refused — DV-67 is the stated mock: validation is a future server rule, not this increment).

**Consequences.** The 8.x app set is uniform (auth lib, otel lib, liveness, TLS, settings shape); the parity scenario is byte equality, so a change to the document is a visible contract change. When real validation lands (future server rule), this app's endpoint gains an input contract and the constant moves to a fallback path — a new increment, a superseded DV-67.

### DD-202 — One issuer world: producers mint on the TLS listener, the collector validates both

- **Status:** Accepted
- **Increment:** 7.18
- **Date:** 2026-10-23

**Decision.** The per-service ingest leg standardizes on the Keycloak **TLS listener**: every per-service producer — the three slice `metrics-puller` sidecars, the Atlas server, and the 8.x aux APIs — mints its client-credentials JWT from `https://keycloak.localhost:8443`, written as a **literal** in each compose/`.env` (no `${VAR:-default}` indirection), with the mint leg pinned to the slice's copy of the shared mkcert CA. The collector's `oidc` extension drops its env-injected issuer (`OTEL_COLLECTOR_OIDC_ISSUER`/`_CA_FILE` are removed from `dev/observability/docker-compose.yaml`) and lists **both** listeners as `providers` in `config/otel-collector.yaml`: the TLS `:8443` (CA-pinned via the existing `/dev-ca` mount) and the plaintext `:8080`, the audience enforced per provider. The e2e suites' issuer-flip convention (the conftest fixtures that set the four ingest env vars and re-run `up` on the shared stacks) is deleted.

**Reason.** Keycloak stamps `iss` from the listener that served the mint, and the collector's go-oidc verifier matches `iss` exactly. Each producer's mint URL is baked into its container at creation, so the mint issuer is fixed per container while the validator issuer was a per-`up` env: the dev defaults (:8080) and the e2e flip (:8443) are two self-consistent worlds, and any mix 401s the per-service leg — OTLP is dropped silently and Prometheus starves. ESD-06 was the first test to *observe* it: the webapp e2e suite recreates the shared collector with the :8443 issuer, and the store-es suite — started by its own `up` chain with the dev-default puller — polled `count(exported_job= "dev-elasticsearch")` against a collector rejecting the puller's :8080 tokens. The failure is suite-order-dependent because the flip is a side effect of execution order on shared stacks. Accepting both issuers makes the mixed world unrepresentable (one realm, one signing key, two listener URLs — not two trust domains); standardizing the mint on :8443 keeps every automated producer in a single world, so the plaintext listener remains only what ADR 039 always meant it for: the human dev browser, which cannot enroll the mkcert CA.

**Alternatives.** (a) Per-suite isolated telemetry stacks (unique compose project/ports/network per suite): the honest isolation, but the shared-stack design is deliberate (the `nx up` chain, fixed `:9090`, ESD/CIA probes that query the machine's Prometheus) and the change is architectural, not incremental. (b) A shared pytest plugin owning the flip: removes the triplication, not the race — global env mutation stays load-bearing. (c) The store-es conftest flipping the pair itself (the first fix tried): order-independent, but it made the suite a third writer of shared infrastructure state — the same disease with a bigger dose.

**Consequences.** The issuer story is one sentence: *mint at :8443, the collector accepts both listeners.* No e2e suite can starve another's telemetry; the CIA-07 mint fixtures, the slice pullers, and `nx serve` all present the :8443 `iss`. The dev browser (plaintext :8080 tokens) keeps its DD-194 attribution through the second provider. The collector trusts the dev-only plaintext issuer's tokens by design — bounded: dev stacks, loopback listeners, audience-gated, and the legacy leg is unchanged. The `OTEL_INGEST_TOKEN_URL`/`OTEL_INGEST_CA_FILE` quartet retires from the slice composes; the pullers' `restart: on-failure:15` (DD-195, issuer-shaped) stays. `dev/observability` remains slice-agnostic.

### DD-203 — The wire contract lives in a client library; the app imports it

- **Status:** Accepted
- **Increment:** 8.4
- **Date:** 2026-10-23

**Decision.** Each Python HTTP API gets an accompanying library under `libs/python/` that owns its wire contract — the pydantic request/response models — and an API client for it: `aurelius-atlas-server-client`, `aurelius-atlas-data2model-client`, `aurelius-atlas-lineage-model-client`, `aurelius-atlas-validate-entity-client`. The models **move** out of the app that served them (`ExtractionRequest` and the rule family out of `data2model.rules`; `LineageInfo`/`EntityHeaderLite`/`LineageRelation`/`Direction` out of `lineage_model.lineage`) and the response models the apps never had (`ExtractionResponse`, `ValidationResponse`, the admin shapes) are written there. The app then imports its own contract from the library (CL-07), and a consumer and the server validate against one class. The app keeps its logic — `data2model` keeps `types.py`/`extract.py`, `lineage-model` keeps `flatten_relations`/`LINEAGE_RULES`/ `UpstreamError` — only the *contract* relocates.

**Reason.** Before 8.4 the contract was scattered and half-absent: the server answers `.to_json()` dicts with no response models, `data2model` answers an untyped `dict[str, Any]`, `validate-entity` answers a `dict` constant, and there is no Python client at all (`aurelius-atlas-sdk` is utility code; the only outbound calls are ad-hoc `httpx`). One home per contract removes the drift the Angular data-access lib already fights (its DTOs are hand-mirrored from `aurelius_atlas_model`), and gives every API a typed caller for free — `lineage-model` calls `data2model` and Atlas through clients, so the 8.2 chain's payload validates as the 8.1 server's body (CL-21). It is the pattern the workspace already runs for the server's *domain* models (`aurelius-atlas-model`, DD-002/DD-020: models with no I/O, imported by every layer); 8.4 extends it to the *REST* contract and the client.

**Alternatives.** (a) Keep models in-app, have the library mirror them (refused — two copies drift, the exact failure the Angular side lives with). (b) One consolidated `aurelius-atlas-client` for all four APIs (refused — the removable-slice and per-project `AGENTS.md` convention wants a consumer to depend on only the API it calls; a shared lib would tie the aux APIs and the server together). (c) Generate the clients from the OpenAPI schema (deferred — hand-written contracts are reviewable and parity-guarded (ADR 052); a generator is a tooling increment of its own).

**Consequences.** The four libraries join the uv workspace and, being Atlas projects under ADR 049, every public function needs a `covers`-named test (CL ids, this increment's spec). `data2model.rules` becomes a thin re-export of the client lib's family, so the app's DTM docstrings and the 8.1 tests keep citing the same names. The Angular data-access lib stays hand-mirrored (a Python→TypeScript contract generator is out of scope). The client home is per-API, so increment 5.1 adds `AtlasClient.get_lineage` and 2.x–6.x add the entity/search routes to the *server* client as they ship.

### DD-204 — Clients are async httpx with an injectable transport, and read no env

- **Status:** Accepted (the construction sentence — base URL plus TLS/timeout/transport overrides — is superseded by DD-205: the `httpx.AsyncClient` is provided externally)
- **Increment:** 8.4
- **Date:** 2026-10-23

**Decision.** Each client wraps an `httpx.AsyncClient` (not a sync `Client`), built from a base URL, a **token source** (a callable yielding the bearer token), and optional `verify`/`timeout`/`transport` overrides. The transport is injectable so a test answers it with a `MockTransport` and no socket opens — the DD-200 seam, made async. A non-2xx answer raises the library's `*ClientError` (status + parsed `{errorCode, errorMessage}`); an unreachable upstream propagates as `httpx`'s own `RequestError` — mapping a transport failure to an HTTP status stays the **app's** job (5.1's/LM-07's DV-80), not the client's (CL-04/CL-05). A client library reads no environment variables; apps pass their settings' values (the libs-python rule, as `aurelius-atlas-auth` and `aurelius-atlas-otel`).

**Reason.** Async is the workspace's outbound direction: the parity harness injects an `httpx.AsyncClient`, FastAPI routes are `async def`, and the 8.2 chain (fetch lineage, then extract) is two awaits that a sync client serialises. The `httpx.Client` the app used (8.2's `_http`) was the odd sync holdout. The token *source* is a callable, not a stored token, so 8.2's browser-token forwarding (LM-04 — forward the caller's raw token to both upstreams) is one source, not a special case, and the same client serves a long-lived service identity. Keeping transport-failure→status mapping in the app is DD-200/LM-07's existing split (the client raises, the route answers 502): a shared client that invents a status would steal that decision from the specs that own it.

**Alternatives.** (a) Sync `httpx.Client` (refused — the parity harness and async routes are async; a sync client forces `run_in_threadpool` in every caller). (b) Both a sync and an async client per API (refused — doubles the public surface ADR 049 must name, for no in-workspace caller that is sync). (c) The client maps `RequestError` to a 502 (refused — DV-80's mapping is LM-07's rule, app-scope; a library that answers HTTP codes it never received would drift from the spec).

**Consequences.** `lineage-model`'s routes become `async def` and its `create_app(settings, auth=None, atlas=None, d2m=None)` injects the two clients (the `http=` seam becomes typed clients, DD-200). The 8.2 unit suite's `FakeUpstream.client()` returns an `AsyncClient`. The clients are usable by the dashboards' e2e and future 5.1 wiring unchanged. (The sentence moving `UPSTREAM_TIMEOUT_SECONDS` into the client default is superseded by DD-205 — the timeout lives on the externally built httpx client, which the app sets from settings.)

### DD-205 — The client's `httpx.AsyncClient` is provided externally

- **Status:** Accepted
- **Increment:** 8.4
- **Date:** 2026-10-23

**Decision.** Each client is constructed from an externally built `httpx.AsyncClient` and a token source — `Client(http, token)` — replacing DD-204's base-URL-plus-overrides construction (`Client(base_url, token, *, verify, timeout, transport, http)`). The app builds the httpx client from its own settings (TLS material, timeout) and passes it in. The client only borrows the pool: it exposes **no close of its own** — no `aclose`, no context manager — closing belongs to whoever built the httpx client, and `with_token` shares the pool (`type(self)(self._http, token)`, no base-URL round-trip). The client's request paths are **relative to the httpx client's base URL** (httpx appends them), so the caller's URL works as given — pydantic's `HttpUrl` renders with a trailing slash, and the app no longer trims it; the URL-shape expectation lives in the client, where the route paths live. Tests pass an `AsyncClient` on the recorder's `MockTransport` and no socket opens — CL-02's injection moves from the transport to the whole client. The rest of DD-204 stands: async, token source, no env, `*ClientError` on non-2xx, `httpx` errors propagating.

**Reason.** The six-parameter constructor duplicated what `httpx.AsyncClient` already configures — `base_url`, `verify`, `timeout`, `transport` are its constructor's arguments, copied through — and the copy forced an ownership flag (`_owns_http`), a "close only what you built" rule, and a base-URL round-trip in `with_token`. One dependency, injected, is the workspace's own convention everywhere else (`aurelius-atlas-auth` and `aurelius-atlas-otel` take an injectable `http`), and it makes the seam strictly wider: a caller can pass a client with custom event hooks, proxies, limits, or auth, none of which the pass-through constructor could express. The client library stays I/O-light: it owns the paths, the bearer, the error mapping, and the models — the transport stack is httpx's, configured by the app that owns its TLS and settings.

**Alternatives.** (a) Keep the pass-through constructor (refused — six parameters, an ownership flag, and a base-URL round-trip to express one dependency; every setting it copies has an httpx-native way to be set). (b) An optional `http` with a self-built default (refused — keeps both lifecycle stories alive, the exact complexity being removed; an app that has settings can build an `AsyncClient` in one line). (c) Keep `base_url` positional for ergonomics (refused — the httpx client already carries the base URL; a second copy can disagree with the first). (d) The client delegates `aclose`/context- manager to the wrapped pool (refused — a borrower closing a pool it did not build is the double-close bug in waiting; with one owner there is one close, and the client keeps zero lifecycle surface). (e) The client rewrites the pool's `base_url` (refused — mutating an injected dependency; the same effect without side effects is relative request paths, httpx's own join semantics).

**Consequences.** The four clients take `(http, token)` and expose no close; the `with_token` tests simplify with them (the closed-pool flag fixture is just `http.aclose()`, the builder's). The `lineage-model` app builds the two `httpx.AsyncClient`s in `create_app` when it builds the clients (CA file, timeout — `UPSTREAM_TIMEOUT_SECONDS` stays the app's constant, DD-200; the settings' URL passes through untrimmed), keeps them, and closes exactly those pools in the app lifespan — an injected client's pool stays its builder's. The app tests' fixtures build the httpx clients on the fake upstream's transport — one transport per upstream, as before. Spec rules CL-01/CL-02 are reworded in place (this increment is unmerged; the rule ids predate any release).

**Addendum — the empty token (found by the server e2e).** The e2e suite drives the containers through the clients, and the server's admin routes — open until 6.1 — are the first calls made with an empty token source (the app builds `AtlasClient(http, "")`, and the e2e fixture has no user token to forward). `f"Bearer {value}"` then sends the header value "Bearer " — with a trailing space — which h11 rejects as an illegal header value: over the recorders of the unit suites the bug was invisible, since `MockTransport` does not validate headers. `_bearer` now sends no authorization header at all for an empty token — the unauthenticated call, which is what an empty source means (CL-03 reworded in place, unmerged); auth-gated routes answer it 401/403 as any anonymous call, and 8.2's forwarding is unchanged — a forwarded browser token is never empty.

### DD-206 — The lineage-model's upstream breakers live in the app, on pybreaker's `calling()` seam

- **Status:** Accepted
- **Increment:** 8.5
- **Date:** 2026-10-23

**Decision.** The 8.2 app guards each upstream with its own `pybreaker` `CircuitBreaker` (the workspace's existing breaker — `aurelius-atlas-auth` guards the JWKS fetch with one, AUX-02): one for the Atlas `v2/lineage` feed, one for the data2model `/extract`, built in `create_app` from `breaker_fail_max`/`breaker_reset_timeout` (LM-15) and grouped with their clients in the app-private `_Chain`. Each guarded call uses pybreaker's documented **context-manager form** — `with breaker.calling(): await client…` — and maps the open circuit's `CircuitBreakerError` to the 502 of LM-12 at the call site. The `exclude` predicate is the documented callable form: an upstream 4xx (the `*ClientError.status_code` of CL-04) is a fact, not an outage (LM-13); a 5xx and a transport failure (CL-05) count.

**Reason.** A dead upstream turns every request into a full timeout on the app's pool (DD-200's `UPSTREAM_TIMEOUT_SECONDS`), for every caller, forever; LM-07's honest 502 does not protect the pool. The breaker belongs to the app for the same reason the OTLP pipeline does (DD-197): it is the caller's resilience policy, and the client libraries stay transport-only by DD-205 — putting a breaker in `AtlasClient` would force a policy on every caller, and a caller that *wants* the timeout (the e2e suites, the 8.2 e2e chain's first call) could not get it. One breaker per upstream, not one for the chain: the 204 of LM-05 must keep flowing past a dead data2model, and the extract must keep serving the guids the feed can answer (LM-11).

**The seam.** pybreaker's async support is tornado-only (`call_async` is built on `tornado.gen` and raises `NameError` on this Python — verified), and the decorator form (`@breaker`) cannot express a per-request token-bound call. The context manager is the documented third form: `calling()` drives the generator through `call()`, so the generator opens the call (raising before it when the circuit is open), the body awaits inside, and its outcome counts. That nesting is the whole guard — one `with`, one `except CircuitBreakerError` per call. The earlier form of this decision wrapped it in a `_guarded(breaker, thunk, message)` helper with `functools.partial` thunks; that is more indirection than the library needs, and `calling()` at the call site reads as the docs read (LM-11). The breaker state is pybreaker's own — the app never inspects it — so the half-open transition tests drive `half_open()` (the documented management API) rather than sleeping through the reset timeout.

**Alternatives.** (a) A breaker in each client library (refused — DD-205's libs are transports with models; a policy there is a policy for everyone, and the LM/CL rules of 8.4 state what a client owns: paths, bearer, errors, models). (b) One breaker for the chain (refused — couples the two upstreams' fates; LM-11 counts them apart). (c) Count every 4xx as an outage (refused — LM-05's 404 is the guid's, not the upstream's health; the auth library excludes the issuer's 4xx for the same reason, AUX-02). (d) `aiocache`-style caching of the 204 (refused — 8.2's scope note: no cache). (e) The `_guarded(thunk)` helper (superseded by this entry's first revision — the context manager at the call site is the documented, shallower form).

**Consequences.** `app.state.chain` carries the two clients and their two breakers (the old per-upstream `app.state.atlas`/`.d2m` stay reachable through it); the route function keeps its shape and calls the chain, which is one guarded call per upstream. The chain's logic moves out of `create_app` into the module-level `_run_chain` (the route was pushing the factory past ruff's C901/PLR0915 — the same extraction DD-205's `_build_upstreams` made). The e2e chain never opens a circuit (healthy upstreams), so the open path is proven at unit level; the listener logs each state change (the AUX-02 pattern), and a breaker metric leg rides with the otel increments, not here.

### DD-207 — The lineage-model app follows the example app's provider/route layout

**Date.** 2026-10-23 **Status.** Accepted (the `chain.py`/`LineageChain` section superseded by DD-208) **Context.** After 8.5 the app was one 380-line `app.py`: the composition root, the chain (`_Chain`), the breaker factories, the httpx/auth/telemetry factories, the route, and the three error handlers in one module, with private helpers (`_build_upstreams`, `_run_chain`, `_atlas_error`) reaching across concerns. Every read of a request path jumped four layers down the file. The FastAPI example app (`aurelius-atlas-fastapi-example`) shows the workspace's structure for this shape: `globals.py` (name, logger, constants), `providers/` (one factory per collaborator, settings in and object out), `routes/` (APIRouter modules), and a thin `create_app` that composes them. ADR 049's rule that every public function is named by a test is what proves the split honest: each factory's tests run at its own seam. **Decision.** The app is split along those lines, with two additions the example has no need for:

- `globals.py` — `NAME`, `LOGGER`, the status codes, the fast-fail messages, the Atlas error code.
- `errors.py` — `UpstreamError` and `atlas_error` (the body the handlers share); `lineage.py` re-exports the class so its import path stays.
- `chain.py` — `LineageChain`, the public use case (`run`): fetch, flatten, extract, each guarded call translating the open circuit (LM-12) and the client errors (LM-05/LM-07) into `UpstreamError`; the empty graph answers `None` (the route's 204). This is DD-206's `_Chain` + `_run_chain`, merged and given its own module: the chain is the app's one concern, and the pair only existed to dodge `create_app`'s complexity limits.
- `providers/` — `auth.py` (the verifier, the library's `http` seam open), `upstreams.py` (`upstream_http`, `atlas_breaker`/`d2m_breaker`, `is_upstream_fact`, `build_chain` returning the chain and the pools the app owns — DD-205), `telemetry.py` (`ingest_pipeline`, `configure_telemetry`).
- `routes/` — `lineage.py` (`build_router(auth)`: the gated `GET /`, the chain read from `app.state`), `health.py` (the anonymous liveness).
- `app.py` — the composition root and nothing else: build, mount, wire the exception handlers (the mapping is the app's own contract, LM-05/LM-07/ LM-12, so it stays at the root), telemetry.

The injectable seams are unchanged (`create_app(settings, auth, atlas, d2m)`, DD-200), so the e2e chain and every 8.2/8.5 test ride on. **Reason.** Separation of concerns the file had lost: a reader of `chain.py` sees the use case, a reader of `providers/upstreams.py` sees the resilience policy, `app.py` says only which collaborators exist. Dependency injection, not service-locator: the factories take the settings and return objects, `create_app` wires them — no module reads the environment, and the tests replace collaborators by argument, not by monkeypatch (the pool factory is patched only by the two DD-205 pool-ownership tests). **Alternatives.** (a) Keep the single module — rejected: the nesting the user asked twice to remove is the layout itself, and C901 was already shaped by it (DD-205, DD-206's extractions). (b) FastAPI `Depends` factories like the example's `providers/settings.py` — rejected for this app: its collaborators are per-app singletons on `app.state` built once at composition, not per-request dependencies, and `Depends` factories read the environment (`get_settings`), which DD-200's injectable-settings seam forbids. (c) The chain as a provider — rejected: it is the app's use case, not one of its collaborators; `build_chain` composes it from the two providers. **Consequences.** `LineageChain` is public (ADR 049: named by `test__aurelius_atlas_lineage_model_chain.py`), and each provider is named by a test of its own; the trace inventory of the package grows, its gaps do not. The route is a thin adapter: chain answer → verbatim JSON, `None` → 204. `app.state` keeps the same shape (`chain`, `atlas_breaker`, `d2m_breaker`), so 8.5's breaker tests are unchanged. The example app stays the structural reference for the 8.x apps, not a wire contract (ADR 055).

### DD-208 — The lineage flow lives in the route; the chain class is dissolved

**Date.** 2026-10-23 **Status.** accepted **Context.** DD-207 gave the app's use case its own module and class: `chain.py`'s `LineageChain.run` did fetch → flatten → extract, and the route called it and mapped nothing. Review found that an extra layer: the example app — the layout DD-207 adopted — has no use-case class. Its routes *are* the use cases, composed from provider functions (`find_all` opens a session and builds the query; the SSE route drives the broadcaster). A class with one method, called from exactly one route, hides the flow's shape (the 204 path, the token forwarding, where each guard sits) behind a method name — indirection, not separation. **Decision.** Dissolve the class, keep DD-207's layout:

- `chain.py` and `LineageChain` are deleted. `routes/lineage.py` composes the flow directly — fetch, flatten, extract, answer verbatim — with the two guarded calls as private module helpers (`_fetch`, `_extract`): each wraps one client call in pybreaker's `calling()` seam (LM-11, DD-206 — the call site is the route, so the seam sits at the route) and translates the open circuit (LM-12), the lineage 404/400 and the extract failure into the `UpstreamError` of the status to answer. The empty graph answers 204 in place (LM-05/LM-06).
- `providers/upstreams.py` builds data, not behaviour: `build_upstreams` returns the two clients and the pools the app owns (DD-205); `atlas_breaker`/`d2m_breaker` stay factories.
- `create_app` puts `atlas`, `d2m`, `atlas_breaker`, `d2m_breaker` on `app.state` — the breaker names 8.5's rules and tests use are unchanged; LM-11's "exposed on `app.state`" stands.

The injectable seam, the handlers, and the wire behaviour are untouched. **Reason.** The route is where the app's one request path is readable in one function, in the order LM-01 states it; the providers stay the factories that own *how* a collaborator is built. DD-207's chain class solved the file-size problem of the old `app.py`, which the provider/route split had already solved — after DD-207 it solved nothing. **Alternatives.** (a) Keep `LineageChain` — rejected: one-method class, one caller; the user's read of the layout is the review. (b) Move `_fetch`/ `_extract` into `providers/upstreams.py` — rejected: guarding a call is the flow's concern; the providers build collaborators, they do not serve requests. (c) `LineageChain` as a plain dataclass (four fields, no methods) — rejected: it would ride on `app.state` as one extra hop to four names. **Consequences.** DD-207's layout stands; its `chain.py` section is superseded by this entry. `app.state` gains `atlas`/`d2m` and loses `chain`. The chain-module test file is deleted — every fact it proved (verbatim answer, forwarding, 204s, failure mapping, open-circuit fast-fail) is proven at the app seam by `test__app.py`/`test__lineage.py` (LM-01..LM-07, LM-12), and the factories by `test__…_providers_upstreams.py`. The e2e chain is unchanged.

### DD-209 — data2model and validate-entity follow the example app's provider/route layout

**Context.** DD-207 and DD-208 settled the lineage-model app's shape: the collaborators in `providers/`, the endpoints in `routes/` with the route composing its own flow, a thin composition root in `app.py`. The two 8.x apps built on the same foundation (DD-197) before that layout existed never followed: both `aurelius-atlas-data2model/app.py` and `aurelius-atlas-validate-entity/app.py` still define their routes inside `create_app`, carry a private `_auth` builder, and inline the same \~35-line `logfire.configure` block with its conditional dict-spread — `_auth` is identical in all three apps, the telemetry block differs only by `NAME`. **Decision.** Both apps move to the DD-207/DD-208 layout, layout only:

- Each app gains `globals.py` (NAME, LOGGER, its status constants) and the two providers, `providers/auth.py` (`build_auth`, the library's `http` seam open as lineage-model's) and `providers/telemetry.py` (`ingest_pipeline`, `configure_telemetry`) — the copy lineage-model already has.
- Each app gains `routes/health.py` (the anonymous `/liveness`, module-level so ADR 049 names it) and its endpoint module: `routes/extract.py` (`build_router(auth)`, the gated `POST /extract` calling the engine directly — the engine stays `extract.py`, the pure DTM-02..09 parser with its own tests) and `routes/validate.py` (`build_router(auth)`, the gated `POST /` answering the mock constant). The routes *are* the use cases (DD-208): no new classes, no chain.
- `app.py` becomes the composition root: `create_app` builds the verifier, includes the routers, mounts the error contract, configures the telemetry. data2model's 400 handler stays at the root — the mapping is the app's contract, as lineage-model's handlers are (DD-207).
- `create_app(settings, auth=None)` keeps its injectable seam (DD-200..201) on both apps; the wire contract (paths, statuses, bodies, the DTM/VE rules) is untouched.

**Reason.** Three apps, one shape: the layout the example app proves, and a review of data2model/validate-entity sees the same tangle DD-207 fixed — routes, collaborators and telemetry in one function. Duplicating `_auth` and the OTLP block per app is DD-196/DD-197's deliberate decision (the app owns its export); duplicating them *inside* one module, in `create_app`, is not that decision — the providers hold them, one copy per app. **Alternatives.** (a) Lift auth+telemetry into a shared lib — rejected: it supersedes DD-196/DD-197 (per-app ingest clients, app-owned export), and three copies of a 20-line factory is the accepted cost of that decision. (b) Refactor data2model only — rejected: validate-entity carries the same `create_app`-defined routes; one entry keeps the family uniform. (c) A use-case class per route — rejected by DD-208 already. **Consequences.** `test__app.py` on both apps keeps its covers targets (`create_app` stays canonical); new provider/route test files name the new public functions (ADR 049). The specs' design-log fields gain DD-209; no rule id changes meaning. The e2e suites are untouched — they ride the wire.

### DD-210 — Telemetry goes native: the OTel SDK replaces the logfire shell

- **Status:** Proposed
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row — no Atlas REST semantics)
- **Date:** 2026-10-23

**Decision.** All five Python apps (the Atlas server, the FastAPI example, data2model, lineage-model, validate-entity) drop `logfire` and configure OpenTelemetry natively. The `aurelius-atlas-otel` lib gains `telemetry.py`: `build_providers` assembles the SDK `TracerProvider`/`MeterProvider`/ `LoggerProvider` from a service name/version, the app-built ingest pipeline (DD-196's `build_otlp_pipeline` pair, now a single `pipeline=` parameter), a standard-OTLP **env leg** that switches on when `OTEL_EXPORTER_OTLP_ENDPOINT` is present in the process environment, and a stdout **console leg** for debug-level runs; `setup_telemetry` installs them on the OTel globals (the set-once first call wins, as the FastAPI test harnesses create one app per test), and `bridge_logging` attaches the supported `opentelemetry-instrumentation-logging` handler to named loggers. The apps call `setup_telemetry` plus the native instrumentors (`FastAPIInstrumentor`, and the example's `HTTPXClientInstrumentor`/ `PsycopgInstrumentor`); the example's SSE gauge registers through `metrics.get_meter().create_observable_gauge`, and its settings' level type becomes a plain `Literal` (the set logfire's `LevelName` carried). The wire to the collector is plain OTLP/HTTP on both legs, unchanged: the per-service leg (4319, JWT per export, CIA-07) and the example's legacy leg (4321, the shared static bearer — exactly the static-header shape the SDK reads from `OTEL_EXPORTER_OTLP_HEADERS`, CIA-10). This supersedes DD-196's logfire integration detail (`additional_span_processors` / `MetricsOptions.additional_readers` — the mechanism is the same app-built pair, now installed by the lib instead of adopted by the shell) and DD-209's copy of the `logfire.configure` block.

**Reason.** Every logfire use was a thin wrapper: `send_to_logfire=False` in all five apps (the SaaS is never contacted), no structured logging (`logfire.info`) and no `@logfire.instrument` decorators anywhere, and `instrument_fastapi`/`httpx`/`psycopg` are the native `opentelemetry-instrumentation-*` packages behind a rename. The one feature of value — the dev console — is replaced by `ConsoleSpanExporter`/ `ConsoleLogRecordExporter` on debug runs, where the extra verbosity is free. The wrapper also caused the workspace's import oddity: the apps imported `opentelemetry.*` symbols (the example's `Observation`, `LoggingHandler`) through a dependency declared on logfire, and the otel lib carried lazy "arrives transitively via logfire" imports while already declaring `opentelemetry-sdk` directly. Native providers make the dependency graph honest: each app declares what it imports.

**Alternatives.** Keep logfire (refused — a wrapper with one vendored feature, paid in a transitive dependency graph and a second config surface; the collector stack is the observability product, logfire's console was its only local value). Console export at info level (refused — the SDK's span JSON dwarfs the request logs; the dev console earns its keep at debug, and debug already implies verbose). `LoggingInstrumentor().instrument()` for the log bridge (refused — it attaches on the *root* logger and installs a record factory; the example's contract is per-named-logger handlers with propagation off, which `bridge_logging` keeps). Keeping logfire on the example app alone for its log tail (refused — one shell, one mechanism, and the native log pipeline covers the tail: `logs=True` builds the logger provider the bridge feeds).

**Consequences.** Five pyprojects swap `logfire[...]` for the native `opentelemetry-instrumentation-*` packages (locked at the same `0.65b0`/`1.44.0` the shell pinned); `uv.lock` loses logfire. The otel lib gains `opentelemetry-instrumentation-logging` (the supported handler — the SDK's own `LoggingHandler` is deprecated in 1.44). The example's legacy leg is now the SDK reading standard env: its `.env`/compose pair (`OTEL_EXPORTER_OTLP_ENDPOINT`/`_CERTIFICATE`/`_HEADERS`) is unchanged — DD-196's CIA-10 posture, restated without the shell. The otel lib reads the standard `OTEL_EXPORTER_OTLP_ENDPOINT` env var — the one exception to its "reads no env vars" rule, recorded in its `AGENTS.md` (a third-party-runtime name, bare by the workspace's env-prefix rule). Unit specs: the lib gains `test__telemetry.py` (the legs, the install guard, the bridge — CIA-07/ CIA-10); the three 8.x apps' telemetry specs swap the `logfire.configure`-monkeypatch seam for `setup_telemetry`/ `FastAPIInstrumentor` on the app module. `setup_telemetry` is set-once per process, so a second `create_app` in one test process keeps the first call's providers — the same lifecycle logfire's `configure` had. The e2e suites are untouched — they ride the wire (the collector accepts the same OTLP/HTTP pushes on the same legs). AUX-03's rule id stands (unset credential = no OTLP leg); its "console only" wording now means the stdout leg of debug-level runs — at info/warning an app with no credential exports nothing, where logfire's pretty console used to print (this supersedes that detail of the 8.0 spec's AUX-03 row).

**Chain stitching (same increment).** The switch kept the example's httpx instrumentation 1:1 (`logfire.instrument_httpx` → `HTTPXClientInstrumentor`), and the e2e walk showed what the other apps deliberately left uninstrumented: the 8.2 chain's upstream calls (lineage-model → Atlas fetch, → data2model extract, LM-04) carried no W3C `traceparent`, so every service rooted its own trace in Tempo. lineage-model graduates: `HTTPXClientInstrumentor` rides its composition root, so the caller's trace rides the chain's httpx calls and the 8.2 chain (browser → lineage-model → data2model) is one trace. The e2e suite adds the stitch probe (`test__the_chain_shares_one_trace_with_the_caller`): a minted trace id as `traceparent`, then the Tempo read-back shows the lineage-model `GET /` span and the data2model `POST /extract` span under the caller's id (LM-04's calls, DD-210). The issuer mints (the auth lib) and the OTLP ingest shim stay uninstrumented — mint spans are per-request noise, and instrumenting the exporter is a self-referential span loop.

**Every HTTP call visible (same increment).** The issuer-mint refusal above is reversed for httpx (user call): every FastAPI app that reaches the network over httpx now installs `HTTPXClientInstrumentor` — the example (as before), lineage-model (the chain, above), and data2model/validate-entity (the auth library's issuer verification and JWKS fetches ride the caller's trace). The server's outbound legs are deliberately not httpx: its store calls ride the elasticsearch client (below, natively instrumented) and its OTLP export rides `requests` inside the ingest shim, which stays uninstrumented (the self-referential span loop above stands). `build_providers` registers the per-process system metrics on every app's meter provider (DD-210): the system-metrics package's default instrument set minus the host-wide `system.*` group — the dev/e2e apps share one host, so five containers would report the same host series five times (infra host metrics ride the pullers). The set lands in Prometheus next to the RED series (`process_cpu_time_seconds_total`, `process_memory_usage_bytes`, `cpython_gc_collections_total`, per `exported_job`). Elasticsearch needs no package at all: elasticsearch-py ≥ 8.13 emits a span per store operation on the global tracer, on by default (the contrib package is stale and self-disables on native clients), so the server's ES spans ride the app-owned leg as installed (`db.system.name`, `db.operation.name` on each). The server suite adds the guard probe (`test__the_store_calls_ride_the_server_trace`): a minted `traceparent` on a typedefs call, and the Tempo read-back requires the request span and an elasticsearch span under the caller's trace id.

### DD-211 — httpx2 replaces httpx across the HTTP surface

- **Status:** Proposed
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row — no Atlas REST semantics)
- **Date:** 2026-10-24

**Decision.** Every first-party httpx use moves to **httpx2** (`pydantic/httpx2`, the Pydantic-stewardship continuation of httpx): the nine pyprojects that required `httpx>=0.28.1` (the example, lineage-model, the auth lib, the five client libs, parity, sdk) require `httpx2>=2.0.0` instead, the six FastAPI-dependent pyprojects raise their floor to `fastapi>=0.162.0` (the first release whose extras require httpx2), and every `import httpx` becomes `import httpx2 as httpx` — the alias starlette's own testclient uses, keeping call sites (`httpx.AsyncClient`, `httpx.RequestError`, …) untouched. The four apps' `configure_telemetry` swap `HTTPXClientInstrumentor` for the `HTTPX2ClientInstrumentor` that `opentelemetry-instrumentation-httpx` 0.65b0 already ships (same import path, same spans: `http.method`/`http.url`/ `http.status_code`). Where a CA file configured TLS, the deprecated `verify=<path>` string becomes `verify=ssl.create_default_context(cafile=...)` (the auth lib, the example's outbound provider, lineage-model's upstreams).

**Reason.** Starlette 1.6 deprecates `httpx` with its `TestClient` (`StarletteDeprecationWarning: … install httpx2 instead` — the warning the user reported), and httpx2 is where httpx's stewardship continues. The migration surface is small and verified: every symbol the repo uses exists on httpx2 (`Client`, `AsyncClient`, `Response`, `MockTransport`, `ASGITransport`, `Timeout`, the error family, `codes`, `QueryParams`); OTel instruments httpx2 natively at 0.65b0, so DD-210's "every HTTP call visible" rule rides unchanged; fastapi core never required httpx at all (only its extras), so bumping to 0.162.0 drops the httpx pin from the apps' transitive closure with no code change — `fastapi.testclient` is unchanged and silently rides httpx2.

**Deliberate deviations.** httpx2 reads the **OS trust store** by default (`truststore`), not certifi: a deployment that trusted a CA through `SSL_CERT_FILE` for httpx must pass `verify=ssl.create_default_context(cafile=…)` (the pattern this DD lands on the three CA-aware sites). `verify=<str>` is deprecated on httpx2, which is why the string CA paths are gone from first-party code. **httpx stays in the venv**, pulled by `python-keycloak` (dev-only, the example's e2e fixtures): its sync path rides `requests` — which takes a str CA path and rejects an `SSLContext` — and its async path is classic httpx, whose `verify=<path>` deprecation warning is python-keycloak's own, not first-party. Starlette prefers httpx2 when both are importable, so the TestClient warning is gone with both installed.

**Consequences.** `uv.lock`: `httpx2`/`httpcore2`/`truststore`/`httpx2-jsfetch` in, `fastapi` 0.141.1 → 0.162.0, `httpx` demoted to a python-keycloak-only dependency. The auth lib gains `_tls_context` (a CA-rooted context, or system trust when unconfigured — the same trust httpx's `verify=<path>`/`verify=True` built); the example's provider spec asserts the context, not the string. The fix rides DD-210's audit trail: 51 e2e (all five apps, rebuilt images bundling the httpx2 wheels) and the per-project unit suites pass, the `StarletteDeprecationWarning` is gone from every warnings summary, and the OTel spans over httpx2 are read back from Tempo by the unchanged chain and store probes.

### DD-212 — The 8.x apps' app/scenario test modules carry their package name

- **Status:** Accepted
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row — no Atlas REST semantics)
- **Date:** 2026-10-24

**Context.** A repository-wide pytest run (`uv run pytest apps libs`, the root's Common Commands) fails collection with `import file mismatch`: the three 8.x apps each carry `tests/test__app.py` and `tests/test__scenarios.py`. The `tests/` dirs are not packages (INP001 is waived for test files), so pytest's default prepend import mode puts each `tests/` dir on `sys.path` and imports by basename — the first app collected owns the module name and the other two error. Per-app runs (`nx test`, `cwd` = project root) never collided; the collision is what a uniform basename across apps means for root collection.

**Decision.** The six files take the package-prefixed names the apps' sibling test files already use (`test__<package>_<module>.py`): `test__app.py` → `test__aurelius_atlas_data2model_app.py`, `test__aurelius_atlas_lineage_model_app.py`, `test__aurelius_atlas_validate_entity_app.py`, and the same for the three `test__scenarios.py`. The specs' test lists cite the new names.

**Reason.** Unique basenames are pytest's own hint for this error, and the prefix is each app's established convention for every other test module (`test__aurelius_atlas_data2model_settings.py`, …) — the collision is the two names that predate DD-209's layout settling. Renaming all three apps (not just the two losers of the import race) keeps the family uniform.

**Alternatives.** (a) Add `__init__.py` to every `tests/` dir — rejected: the conftest and tests/ helper imports (the 8.2 fake upstream, the 8.4 recorders) and the pyright `extraPaths` execution environments are built on `tests/` riding `sys.path`, not on it being a package. (b) `importmode=importlib` at the root — rejected: it changes collection semantics workspace-wide to fix two names. (c) Rename only data2model's pair (it wins the alphabetical race) — rejected: the other two stay collision-prone for every future sibling app.

**Consequences.** Rule ids and `covers` markers are untouched — the trace plugin reads them from the files, and the per-app `trace.json`/`junit.xml`/ `coverage.xml` artifacts (untracked, `tools/plugins/python.ts`) regenerate with the new nodeids on the next `nx test -c ci`. DD-208's and DD-209's Consequences mention `test__app.py` as history and are not edited. The specs' test lists (8.1, 8.2, 8.3, 8.5) name the new files in the same change.

### DD-213 — The lineage guid is a UUID on every typed surface

- **Status:** Accepted
- **Increment:** 8.5 (rides the client-libraries branch; no new roadmap row — the guid's type is a contract detail of the 8.2/8.4 surfaces, DV-78)
- **Date:** 2026-10-24

**Context.** The lineage chain carried the entity guid as `str` end to end: `LineageModelParams.guid`, `AtlasClient.get_lineage`, `LineageModelClient.get`, the app route's query parameter, `EntityHeaderLite.guid`, `LineageRelation`'s endpoint ids, and `LineageInfo.guid_entity_map`'s keys. Atlas's own guids are UUIDs (`Entity.getGuidAsString` returns the canonical string of a `UUID`), and the 5.1 feed will answer `v2/lineage/{guid}` with them. A `str` guid accepts any token — the fixtures grew readable ids (`e-in`) that no Atlas entity could have, and a malformed guid travels all the way to the upstream before failing.

**Decision.** Every lineage guid is `uuid.UUID` on the typed surface: the client models and methods, the app route's `guid` query parameter (FastAPI parses it, so a non-UUID is DV-73's `400` before any upstream call), `EntityHeaderLite.guid`, `LineageRelation.fromEntityId`/`toEntityId`, and `LineageInfo.guidEntityMap`'s keys. `LineageRelation.relationshipId` stays `str` — it is a relation id, not an entity guid, and the legacy fixtures give it readable values. The Java-parity typedef/instance guids of the server surface (`aurelius-atlas-model`) are untouched — this is the lineage chain only. Fixtures use fixed UUIDs (`00000000-0000-4000-8000-0000000000NN`); names, labels, and relation ids stay readable.

**Reason.** Pydantic parses and serialises UUIDs natively (the OpenAPI schema gains `format: uuid`; JSON string keys coerce into `dict[UUID, ...]`), httpx stringifies a UUID into the canonical lowercase form on the wire, and the extract engine's `_legacy_str` stringifies the UUID cells of the flattened rows — so the wire stays byte-identical to Atlas's, while every Python surface rejects a malformed guid at its own boundary. A `str`-typed chain would leave the route answering DV-73's 400 only for *missing* guids and forwarding garbage for present-but-invalid ones.

**Alternatives.** (a) `Annotated[str, UuidCheck]` validators — rejected: re-implements what `UUID` gives for free, and the schema loses `format: uuid`. (b) Typing the Java-parity guids too — rejected for now: the 1.x/5.x surfaces mirror Atlas's Java DTOs, where guid is `String` at the wire; DV-78's row scopes this to the lineage chain, and a parity spec change is Java-reference work (ADR 052), not a client-library detail.

**Consequences.** The e2e fixture file is named for its guid, so `e2e/fixtures/v2/lineage/e-in` becomes the UUID-named file the fixture `http.server` maps `/v2/lineage/<guid>` onto. `test__lineage.py` gains `test__a_guid_that_is_not_a_uuid_is_400` (LM-07); the dangling-guid test's endpoint becomes a well-formed UUID the map lacks — a malformed guid can no longer reach the flattening at all, which is the point.

### DD-214 — The test suite review of 2026-10-24 scopes the hardening increments

- **Status:** Accepted
- **Increment:** cross-cutting (rides the delivery docs; no roadmap row — the hardening increments 8.6/8.7/7.19/9.1 carry their own rows when specified)
- **Date:** 2026-10-24

**Context.** Development added tests ad hoc per increment. A workspace-wide review (all apps, all Python libraries, all frontend projects, both e2e suites) measured coverage and scored every suite against the five non-happy flow categories (input/validation, business rule/auth, infrastructure, interrupted/async, edge-case). Findings: infrastructure failure testing is a house strength (lineage-model, store-es, auth); the systematic holes are mid-request infra failures (server, core), frontend session lifecycle and error UX breadth (7 of 71 webapp-side specs assert an HTTP error), the client libraries' response-shape failures (2xx-with-garbage-body, timeout vs connect error), and data2model's view-edge/dynamic-view engine paths (0%). No coverage threshold exists in CI, and the Python libraries' `coverage.xml` is generated in CI only, not committed.

**Decision.** The review's findings, verdicts, ranked deferred backlog, and template-code exemptions are recorded in [Test Suite Review](<https://aureliusenterprise.github.io/phase6-6.1-authentication/architecture/platform/delivery/testing-review/index.md>), kept as a dated review page (reviews record, they do not drift). Four hardening increments proceed from it, one PR each, spec-first. The review's first finding about the ledger: **the failure semantics are almost all already specified — the tests are what is missing** (DTM-04/06/07 state the view-edge and dynamic-view paths at 0% coverage; LM-07/11/12/13 state the transport-failure, fast-fail, and outage-counting behaviours; CL-04/05/06 state the client failure contract; APC-04/05, ALR-04/05, SHC-05 state the frontend's). The increments therefore cite the existing ids, and mint new ones only where a finding names behaviour no rule states: **8.6** aux API failure hardening (proves DTM/LM/VE ids, adds negative parity scenarios), **8.7** client failure contract (adds CL-08 — a 2xx body that fails its model is the contract failing, not succeeding; proves CL-04/05/06), **7.19** frontend failure UX (proves APC/ALR/SPL/SHC ids; the example app's editor has no increment spec, its tests carry plain names), **9.1** resilience e2e with targeted container-stopping scenarios (the only new prefix, `RSL`). Coverage enforcement stays where it is: the SonarQube quality gate — no `--cov-fail-under`, no Vitest `coverage.thresholds`, no new CI flag. The server-spine findings (mid-request store failure, concurrent store writes) are explicitly deferred to the 2.x track as ranked backlog \#1, not dropped.

**Reason.** The gate already measures coverage (the `-c ci` configs write `coverage.xml`/`lcov.info`, CI uploads them, `nx affected -t sonar` feeds Sonar, whose quality gate fails on low levels — including new-code coverage, which ratchets naturally with every hardening PR); a second local flag would duplicate the gate and fight ADR 014's "defined once, runs everywhere". The priority split (frontend / aux APIs / clients first) follows where the representativeness gaps bite the conversion's next increments; the server spine's mid-request failures pair with 2.2's entity-store work, which changes those same call paths.

**Alternatives.** (a) A per-project coverage ratchet in the Nx python plugin and Vitest configs — refused, see Reason (and the user's call of this date). (b) One workspace-wide coverage floor — refused: the template baseline is heterogeneous and a uniform floor would punish the vendored dashboard and the example apps. (c) Destructive failure-injection e2e as a nightly resilience suite — refused for now in favour of a small number of targeted scenarios inside the existing per-PR e2e suites (≤2 min budget each), the same realism bar as ADR 012.

**Consequences.** The review page is the reference for "what was known on this date"; its numbers are a snapshot, the trace report stays the live system of record. Rule-id reservations: **CL-08** (8.7's one new rule) and `RSL-01…` (9.1); the other increments cite existing ids — minting new ids for already-specified behaviour would fork the ledger. The fastapi-example, `sdk`'s aws/msal/logger, aurelius-atlas-example, and the dashboard are exempted from hardening (matching the trace check's `exclude-projects` and DD-017). Phase ordering: 8.6 and 8.7 parallel, 7.19 parallel, 9.1 after 8.6 and 7.19.

### DD-215 — The CI pipeline drops the traceability check and report

- **Status:** Accepted
- **Increment:** cross-cutting (rides the CI pipeline; no roadmap row)
- **Date:** 2026-10-24

**Context.** Increment 0.3 wired [ADR 049](<https://aureliusenterprise.github.io/phase6-6.1-authentication/adr/049-every-function-and-rule-is-traceable-to-a-test/index.md>) into the pipeline: the `validate` job runs `aurelius-atlas-trace check` (collection only, no test runs) and the `test` job builds an HTML trace report from the JUnit, coverage, and trace files. The check proves that a test *names* a function or rule id; it never runs anything. The desired behaviour of every increment is already encoded in its unit tests, which the pipeline runs, so the gate restates what the suites prove. Keeping the declarations true across the whole surface — TypeScript citations, end-to-end claims, rules whose proof lives in another repo — turned into bookkeeping that fails CI without indicating a missing test.

**Decision.** `.github/workflows/ci.yaml` drops both steps: the `validate` job no longer runs `aurelius-atlas-trace check`, and the `test` job no longer runs `aurelius-atlas-trace report` or uploads the `test-report` artifact. What blocks a merge is a failing test. The trace lib, the `covers` marker, and the `--trace-json` plumbing stay in the repo as local tools and a code-review convention — `nx test`/`nx e2e` keep writing the files, and anyone can run `check` or `report` themselves. Coverage enforcement is unchanged: the SonarQube quality gate ([DD-214](<#dd-214--the-test-suite-review-of-2026-10-24-scopes-the-hardening-increments>)). Parity scenarios keep their citation discipline ([ADR 052](<https://aureliusenterprise.github.io/phase6-6.1-authentication/adr/052-behaviour-is-specified-by-scenarios-read-from-the-reference-source/index.md>)) and the parity lib keeps its own checks — that is how expected behaviour is justified, not a trace gate. The business-level decision is [ADR 056](<https://aureliusenterprise.github.io/phase6-6.1-authentication/adr/056-behaviour-is-proven-by-executed-tests-not-by-a-trace-gate/index.md>), which supersedes ADR 049; [DD-009](<#dd-009-traceability-is-checked-from-collected-markers-not-from-a-test-run>), [DD-010](<#dd-010-the-traceability-check-covers-atlas-code-from-increment-02-on>), and [DD-011](<#dd-011-the-test-report-is-generated-from-junit-coverage-and-trace-files>) describe the tools, which remain, so they stand as written.

**Alternatives.** (a) Widen the gate to prove the gaps away (TypeScript citations, end-to-end markers, seams for cross-repo rules) — refused: more mechanism proving declarations, no executed behaviour. (b) Keep the check as a non-blocking warning — refused: an unenforced gate is documentation nobody reads, and the noise stays. (c) Delete the trace lib as a slice now — refused: the marker is a useful review pointer and removing it would rewrite every test's metadata for no gain; it is removable later as one slice.

**Consequences.** The pipeline is smaller and says only what it can prove. The per-change published trace report is gone; reviewers read the tests and the coverage report. Increment specs that list `aurelius-atlas-trace check` in their "gates" describe the verification the increment was accepted with — they are dated records, not promises about current CI, and are not edited.

### DD-216 — Stacks own the TLS material they mount

- **Status:** Accepted
- **Increment:** cross-cutting (e2e wiring; no roadmap row)
- **Date:** 2026-10-25

**Context.** The webapp's e2e stack runs the real Atlas server behind the nginx `/api/` proxy ([DD-142](<#dd-142-the-webapp-e2e-stack-runs-the-real-atlas-server-behind-the-proxy>)), and the server container mounted `apps/aurelius-atlas-server/certs` — the server project's own material, because its leaf carries the `aurelius-atlas-server` SAN nginx verifies against. The webapp's `e2e` target declared the server's `docker-build` and the dev stacks' `up` as `dependsOn` but not the server's `certgen`: Nx's compose plugin infers `certgen` from the compose **owner's** `tls.json` (tools/plugins/docker-compose.ts), so a sibling project's `certs/` mount is invisible to it. When the devcontainer was rebuilt, mkcert regenerated its root CA and every project self-healed its own material on its next `certgen` — the server's stayed signed by the old CA, its server container failed Elasticsearch TLS verification, exited 3 during `docker compose up --wait`, and every webapp e2e test errored at fixture setup.

**Decision.** The stack mounts only its owning project's certs. `tls.json` for the webapp gains an `aurelius-atlas-server` service (the same SANs the server project issues: the service name, localhost, 127.0.0.1), so the webapp's own `certgen` — already a `dependsOn` of `e2e` and `serve`, and auto-wired by the compose plugin's rule — generates the leaf the server container wears. `e2e/docker-compose.yaml` mounts `../certs` for it, and no cross-project `certgen` dependency is needed. The CA bundle is the shared mkcert root, so the server's verification of the dev Elasticsearch, the collector, and Keycloak is unchanged; the dev server (`nx serve aurelius-atlas-server`) still presents the server project's own leaf.

**Alternatives.** (a) Declare `{projects: ["aurelius-atlas-server"], target: "certgen"}` on the webapp's `e2e` — the pattern PR \#143 used for lineage-model → data2model, and correct: it keeps one issuer per identity. Refused for the webapp because the mount is part of the webapp's e2e stack, and a stack should carry its own material: with the `dependsOn`, "the webapp project needs the server project's certs" is a fact recorded only in a mount string, and certgen stays a target whose trigger (the devcontainer rebuild) lives outside the project that consumes it. (b) Have `certgen.sh` refresh every project's material — refused: a project's target writing into other projects breaks the slice ownership ADR 002 relies on. (c) Teach the compose plugin to parse volume mounts and auto-add the owning project's `certgen` — deferred; it generalises the inference rule but adds plugin magic for a pattern (stacks that embed a sibling's image) the explicit `dependsOn`/manifest already covers.

**Consequences.** `nx e2e aurelius-atlas-webapp` is self-sufficient for TLS: a fresh container rebuilds the webapp's `certs/` (server leaf included) before compose starts. Two projects now issue a leaf for the `aurelius-atlas-server` name — the server's for its own stacks, the webapp's for the e2e stack — which is dev-only identity, gitignored and never shipped (ADR 006); `apps/aurelius-atlas-server/certs` is no longer read by the webapp stack. The same audit swept the workspace's other two cross-project cert mounts (the only ones beyond this): the observability collector pinned its OIDC `issuer_ca_path` to the webapp's CA copy mounted at `/dev-ca`, which no target produced — it now verifies the issuer against its own `certs/ca.pem` (the mkcert root is shared workspace-wide, byte-identical copies), so the mount and its producer disappear together. The lineage-model e2e stack mounted data2model's certs behind an explicit cross-project `certgen` `dependsOn` (PR \#143 — the pattern this entry's alternative (a)); it now follows this entry's decision: `tls.json` gains the `aurelius-atlas-data2model` service, the stack mounts `../certs`, and the cross-project `certgen` `dependsOn` is gone (its `docker-build` stays — the image is data2model's artifact). After this, no compose file mounts another project's `certs/`: every stack's TLS material is generated by the stack owner's own `certgen`, matching the frontend-example, whose `tls.json` already listed all three services its e2e stack hosts.

### DD-217 — The search client lands on both sides of the wire, ahead of 7.4

- **Status:** Accepted
- **Increment:** cross-cutting (the 8.4 client family and the 7.3 Angular client; no roadmap row)
- **Date:** 2026-10-26

**Context.** Increments 4.1/4.2 gave the server the discovery routes (`/api/atlas/v2/search/**`), and the Python client gained them as `AtlasClient.search` (CL-13, the 8.4 family). On the frontend, 7.3 deliberately ported only the surface the server implemented then (DD-140), leaving every search call to 7.4 ("the search slice, gated by server 4.1/2.3"). With server 4.1/4.2 merged, the gate's server half is met, and 7.4's first line needs `SearchService` to exist — the client is the seam 7.4 consumes, and a client built without its consumer is the speculative build DD-140 rejects.

**Decision.** Land the typed search client on both sides of the wire now, as data-layer only: `AtlasClient.search` (CL-13) and, in `libs/angular/aurelius-atlas-data-access`, `SearchService` (APC-11, `search.service.ts`) with the search DTO cluster (`atlas-search.ts`, APC-03's hand-mirror of `aurelius_atlas_model/discovery.py`). No screen calls it: the browse landing's affordances, the header search bar, and the results screen stay 7.4's. The GET searches send the Java defaults (a false flag, a `0` page) as their absence, matching the server routes' `flag`/`java_number` reading; the POST searches send the parameters as the body `validate_basic_search_parameters` / `validate_quick_search_parameters` validate.

**Alternatives.** (a) Wait for 7.4 and build the client inside it — refused: 7.4 is a UI slice (the results screen redesign), and bundling the wire contract into it makes its review carry both; (b) generate the TS DTOs from the Python models — deferred with the same open question as the typedef cluster's hand-sync (APC-03), one mechanism for all DTOs is better than one per cluster.

**Consequences.** 7.4 consumes `SearchService` directly; the webapp's e2e stack already runs the real server behind the proxy (DD-142), so a 7.4 flow test needs no new wiring. The two DTO clusters (`atlas-search.ts`, `aurelius_atlas_model/discovery.py`) join the hand-sync list in `aurelius-atlas-data-access/AGENTS.md`. The Python side is proven against the container (`apps/aurelius-atlas-server/e2e/test__aurelius_atlas_server_search_e2e.py`); the Angular side is proven against `HttpTestingController` — the e2e proof of a search through the proxy lands with 7.4's screen.

### DD-218 — 7.4 splits in two, and the search bar lands in the hero; the list is infinite scroll

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** The 7.4 row ("Query and results, the first slice with real data") grew into the collection point of three deferrals: the results screen itself, the browse cards' affordances (DD-143), and the Shell's search chrome (DD-145). AGENTS.md caps an increment at roughly 1,500 production lines and says to split before coding. The reading of the legacy app (`.scratch/aurelius`, the `Aurelius origin` citation of 7-0) settled two UX questions the roadmap row left open. The search bar: DD-145's wording ("the global search bar ... join 7.4") reads like a navbar feature, but the legacy navbar's start slot renders one button per visible top-level route, and Atlas's only such route is `hidden` — the legacy navbar carries **zero** nav buttons, and the search input lives in the hero of the search subtree (`search.component.html`, the `simple-search-input` above the routed content). The list: the legacy results screen is an infinite scroll (a sentinel `IntersectionObserver` over the results box, a "Load next page..." button as the keyboard/no-API fallback, pages appended, page size 10), not a paged grid — the ui-lib `pagination` component has no legacy results-screen to wire to.

**Decision.** Split 7.4 into **7.4a Search results** (this increment: the hero with the search field, the results route and screen, infinite scroll, the results → details entry, the browse affordances of DD-143, the sticky navigation bar of DD-145) and **7.4b Search discovery** (facets from quick-search `aggregationMetrics`, typeahead suggestions, advanced filters — the parts with no legacy equivalent, so the slice that invents UX ships separately from the slice that ports it). The search bar lands **in the hero**, the legacy fact; DD-145's navbar wording is superseded, and the navbar's start slot stays empty because Atlas shows no nav buttons. The results list keeps **infinite scroll** (UIC-21..23 port the container); `Pagination` stays unused on this screen. The split line is the discovery boundary: 7.4a answers "type and see", 7.4b answers "narrow down".

**Alternatives.** (a) One 7.4 increment — refused: \~2,500 production lines against the 1,500 budget, and it welds the ported screen to net-new facets; (b) split results | entry points (header bar + browse cards) — refused: the affordances without their destination screen are exactly the half-wired slice DD-143 defers, and the e2e flow (card → results → details) cannot split across PRs; (c) a paged grid with the existing `Pagination` — refused: the legacy infinite scroll **is** the product UX (the user named it), and DD-140's redesign licence covers the wire (App Search → `/v2/search/basic`), not the screen; (d) a navbar search bar per DD-145's literal wording — refused: the legacy source shows the bar in the hero, and DD-145's own reasoning is "the header's centrepiece is the global search bar" — in Aurelius Atlas, as in the legacy app, that centrepiece is the search hero.

**Consequences.** The roadmap row splits; DD-217's "7.4 consumes `SearchService` directly" rides unchanged. The sticky navigation bar (DD-145's deferred half) lands with 7.4a, closing the Shell chrome deferral. 7.4b carries its own spec and rule ids (SDX) with the typeahead design it has no legacy copy of. The ui-lib grows one dumb component (the infinite-scroll container) on the UIC series; `Pagination` remains in the library for the screens that page.

### DD-219 — The results URL carries the query only

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** The legacy resolver reads one URL parameter (`query`) and leaves filters, sort, and the accumulated pages in the in-memory store; navigating to browse wipes the store. A modern reading would put page/sort/filters in the URL (shareable, back-button-correct), and the 7.6 details screen already made the URL the screen's whole state. But 7.4a ships no facets (7.4b) and no sort control (the legacy results screen has none — ordering is relevance, the server default), so the parameters to share do not exist yet on this screen.

**Decision.** `search/results?query=` is the whole URL contract of 7.4a (SRH-02, SRH-08): the deep link carries the query, the store carries pages and the explore buttons' type filters, and leaving the subtree destroys the store (provided by the layout component) so a fresh browse visit resets the search — the legacy `NavigationEnd` reset, by construction. 7.4b will record its own decision for filter parameters when filters exist to name.

**Alternatives.** (a) Query + page + sort + filters in the URL — refused for 7.4a: inventing a parameter grammar the legacy app lacks, for state this slice does not expose, is the speculative design DD-140 refuses; the grammar lands with the controls, in 7.4b. (b) Path-based `search/basic/:queryText` (the Atlas dashboard's shape) — refused: the Aurelius product (the port's origin) uses the query-parameter form (ADR 046 keeps the dashboard's REST contract, not the dashboard's routes; 7.x ports Aurelius's UI).

**Consequences.** The e2e deep link is `search/results?query=…`; the back button re-runs the query (the resolver's `paramsOrQueryParamsChange` contract, SRH-02). The store's page accumulation needs no URL mirror, and the spec's "the URL is the screen's state" line is scoped to the query — the 7.6 skeleton's stronger rule (DET-07) applies to the details screen, where the guid is the entity's address.

### DD-220 — The demo pass restores the search screens' legacy chrome: title, typography, shell and plate

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** The 7.4a code review compared the running webapp side-by-side with the legacy Aurelius demo (the `.scratch/aurelius` origin, rendered at `google.aurelius-atlas.com/demo/atlas`) on the browse, results, and no-results screens. The geometry (hero, container inset, two-column shape) matched; seven details did not, each verbatim in the legacy source: the hero's title is the literal `"Atlas"` the legacy `search.component.html` hard-codes as `title="Atlas"` — not the app name (the first port rendered `appName` into it); the filter shell's empty state is the legacy `#noFilters` block, a `div.content` around `p.is-italic.has-text-centered` (the first port shipped a bare paragraph); the count header is `h6.title.is-6` **inside** the results box (the first port floated it outside, unstyled); the 80vh cap sits on the box (`.box { height: 100%; max-height: 80vh }`) with the inner `.results-container` as the scroll owner (the first port scrolled the box itself); the no-results state is the legacy `#noData` twin — a `.card` at the **top level**, replacing the whole two-column block (filter shell included), its `card-content` centered by the legacy `text-align-last: center`, message `p.title.is-4`, advice `h6.title.is-6` (the first port shipped a small `.box` inside the results column); each result row is a Bulma `.column`, whose 0.75rem padding is the gap between cards; and every search field carries the `ControlShell`'s left icon plate (`context.icon` = `faSearch`, `icon is-left has-text-info` — cyan on the demo), which the DD-135 port of `simple-search-input` dropped with the rest of the shell.

**Decision.** Port all seven verbatim: the hero title is the literal "Atlas", the filter box's empty state is the legacy `content`/`is-italic`/`has-text-centered` paragraph, the count moves inside `.results-box` as `h6.title.is-6`, the box/container split takes the legacy rules, `.card.no-results-card` replaces the columns (the `ngIf`/`ngIf:else` shape — SRH-06's pair, SRH-07's shell shown only with data), each row is the legacy `div.column` wrapping the card (the column's auto height keeps the card host's `min-height: 100%` inert — stretched to the scroll container's definite height, the cards inflate to one per screen; its 0.75rem padding is the gap between rows), and the ui-lib `search-field` renders the left plate (its UIC-01 markup set, completed).

**Alternatives.** (a) Keep the first port's cleaner shapes — refused: the legacy look is the product look (DD-150/152), and the demo is the parity oracle (ADR 052); (a reader comparing screens notices all seven). (b) Port the demo's centered **card** titles — refused: that is the demo's stuck "Loading …" per-card-GET state (DV-83's target: the demo's search answers never resolve there); with cards rendered from the hit, the legacy centered line applies only to the no-results card, as ported.

**Consequences.** The 7.4b facet sidebar fills the shell that only shows with data; the `search-field` story and its specs name the plate; the results specs pin the count-inside-box and the top-level `#noData` (no `.column` without data); the layout spec pins the hero's "Atlas" title, the results spec the styled no-filters paragraph.

### DD-221 — The empty query lists every entity through the `_ALL_ENTITY_TYPES` marker

- **Status:** Accepted
- **Increment:** 7.4a
- **Date:** 2026-10-26

**Context.** Opening the results screen without a query (`/search/results`, the URL the explore buttons land on, a bookmark, a reload) showed the no-results card with the invitation to "try another query". The legacy app answers that URL with everything: the Aurelius `QueryResolver` defaults `query` to `''` — "so that when we load the page without a search term, we can still see results" — and the demo answers the bare URL with 683. SRH-02's wording already says the empty parameter "searches `""`, which answers"; the store deviated, refusing to fire at all. The refusal has a real reason: a basic search with no term, type, classification, or term is `INVALID_SEARCH_PARAMS` (SRC-02, ATLAS-400-00-047), so posting `query: ""` alone is a 400, not a list.

**Decision.** The store sends the empty query with Atlas's every-entity marker: `{typeName: "_ALL_ENTITY_TYPES", query: ""}` (SRC-03 — the marker stands for every entity, and the type satisfies SRC-02's requirement). A session type filter wins over the marker (SRH-08's explore); a non-empty query sends no `typeName` at all, as before. The URL effect's re-run guard becomes "the store has already run this text" rather than "the text matches the store's": the legacy resolver ran on every arrival, query-less included, so a first arrival at a bare `/search/results` fires the list-everything search, while the hero-submit-then-same-URL-navigation no-op (DD-219) is preserved.

**Alternatives.** (a) Fire `query: ""` with no type — refused: the server answers 400 (SRC-02), and the alerts drawer would fill on every landing. (b) Keep the first port's refusal (no request, the no-results card) — refused: SRH-02 already promises the empty query answers, the demo is the parity oracle (ADR 052), and the card's advice is wrong for a URL that is the app's own default landing. (c) Send `typeName: "AtlasBaseType"` — refused: Atlas 2.4.0 has no such type (`UNKNOWN_TYPENAME`, SRC-03); the marker is the every-entity shape the store's own tests already use.

**Consequences.** The bare URL is a real landing, matching the demo; the results specs pin the marker body and the "first arrival fires" rule; the explore e2e's reload step asserts more rows than the one seeded glossary (the filtered re-run's count) — the every-entity search proving the session filter is gone.

### DD-222 — The Python apps emit the stable HTTP semantic conventions

- **Status:** Accepted
- **Increment:** cross-cutting (telemetry; no Atlas REST semantics — no roadmap row, DD-210's pattern)
- **Date:** 2026-10-26

**Context.** The webapp → server → Elasticsearch trace (7.18/7.19) carried two HTTP conventions at once. The browser leg (JS SDK 2.12) and elasticsearch-py's native spans emit the stable set (`http.request.method`, `url.full`, `db.system.name` — the latter stable natively since 8.13, DD-210); the FastAPI/ASGI leg (instrumentation 0.66b1) emits the old set by default (`http.method`, `http.url`, `http.status_code`, `net.peer.*`). Every span-attribute filter written against the stable names silently misses the request spans — the exact trap DD-210's ES-span probe steps around by matching `db.system.name` only. The same split lands on metrics: the RED panels read the old `http_server_duration_milliseconds` (ms), which the instrumentor stops reporting under the opt-in.

**Decision.** All five Python apps set the standard `OTEL_SEMCONV_STABILITY_OPT_IN=http` (value `http`, not `http/dup` — the old set is dropped, not doubled). It is a bare `OTEL_*` name (third-party-runtime consumer, the root `AGENTS.md` env rule) set in two places per app: the `Dockerfile` `ENV` (the e2e/prod image) and the project `.env`/`.env.enc` (`nx serve`, whose process environment Nx builds from the project env). The FastAPI RED dashboard moves with it in the same change: `http_server_request_duration_seconds` (stable; the SDK emits seconds, the ms panels multiply the quantiles by 1000), `http_server_response_body_size_bytes`, labels `http_route` / `http_response_status_code`; `http_server_active_requests` keeps its name (the panel uses a bare `sum()`; the stable label set is a subset). The SSE exclusion also fixes a stale route: the old `http_target!="/sse"` never matched the real route `/entities/sse` (the router mounts it under its prefix), so the p95-excl-SSE panel silently included stream durations. The server e2e store-span probe (DD-210) gains the convention pin: the request span must carry `http.request.method=GET` and none of `http.method`/`http.url`/`http.status_code`.

**Alternatives.** (a) `http/dup` — refused: it doubles span attributes and metrics series forever; the migration it exists for has no second consumer here (the collector pipeline and every dashboard in-repo are updated in this change, and no external consumer reads these series). (b) Set the opt-in in code (the instrumentor constructors accept no equivalent; the SDK reads it once at first instrumentation, and the apps' composition roots instrument at import-adjacent time) — refused: env is the mechanism the standard defines, and `nx serve`/image/dashboards stay declarative. (c) Leave the server legacy and rewrite the ES-span filters to old names — refused: the stable set is where OTel has standardised (the JS browser SDK and elasticsearch-py are already there), and one trace carrying one convention is the point.

**Consequences.** Server and auxiliary-app spans drop `http.url`/`http.status_code`/`net.peer.*` (nothing in-repo filters on them; the webapp/frontend/keycloak dashboards read web-vital, Micrometer, and resource attributes only — verified). Metric history is split at the flip: the old `http_server_duration_milliseconds` series stop, the new ones start (dev dashboards, acceptable; Grafana's time range covers the gap). The active-requests gauge loses its `http_host`/`http_server_name` labels (the stable set is method+scheme; the panel is a bare sum). The server e2e probe is the regression gate: a dropped `ENV` in an image fails the store-span test with a named message. The 8.x aux apps carry the same ENV pair for symmetry — their spans join the stable set on the next trace they ride (the 8.2 chain, DD-210). Tempo's search by `resource.*` and the Grafana Explore panels are unaffected (resource attributes are not part of the HTTP semconv switch).

### DD-223 — E2E suites never restart shared dev infra; layout parity leaves e2e

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure)
- **Date:** 2026-10-27

**Decision.** An e2e suite may read and write the shared `dev/*` services, but it must **never restart** them: no `docker compose down`/`up`, no container cycling, on a stack other suites ride. Writes stay allowed when namespaced and self-cleaned (the webapp's uuid-prefixed indices, the server's `scenario_*` writes, the example apps' fixture rows). Concretely:

- `aurelius-atlas-store-es` e2e drops its ESD-04 restart-persistence test — the only test in the fleet that took the shared dev Elasticsearch down and up mid-suite. The rule moves to the increment spec as deliberately untested: the named-volume behaviour is verified by review, and the healthcheck (DD-008) covers the "stack comes back up" half. With no restart left in the suite, its `parallelism: false` pin (project.json) is deleted — store-es e2e now runs beside every other task.
- The rationalisation sweep that rides along: the ESD-03 credential-hygiene test moves from store-es e2e to a unit test (`tests/test__dev_elasticsearch_config.py` — it inspects committed files, never a running store; the `test` target decrypts the dev project's `.env` first), and the two FastAPI-framework probes in fastapi-example e2e (`/docs`, `/openapi.json` — they assert FastAPI defaults, not Aurelius behaviour, and carried no `covers` rule) are deleted.
- Layout-parity pins leave the webapp e2e suite (with the user's directive: interactions are what e2e guards, layout is what unit/visual tests guard). Eight tests go: the navbar logo box, the body type/ink, the type ramp, the chrome-band palette, the accent ramp, footer-below-the-fold, the landing container inset, and the dark-OS light pin. Their checks land in the webapp's Vitest component specs (`header.component.spec.ts`, `footer.component.spec.ts`, app/shell template structure) as class/token/attribute assertions — the parts a jsdom browser can verify — while the computed-pixel measurements (Bulma ramp values, band heights, bounding boxes) are dropped: they pinned the demo at parity-establishing time and can only fail on CSS refactorings, not on behaviour. The interaction half of the burger-menu test (click, dropdown, logout entry) stays in e2e; only its CSS pins go. A Storybook visual-test setup for the webapp (it has no `storybook` target today) is a follow-up increment, not part of this change.

**Reason.** CI runs `nx affected -t test e2e` in parallel, and the fleet rides the shared `dev/*` services. ESD-04's dev-ES down/up races every suite mid-flight — lost-connection failures are on record (the `parallelism: false` pin was that outage's scar tissue, and it serialised the suite forever after). The fix is to remove the restart, not to isolate every writer: a per-suite store stack was built and verified in this cycle (ES ×3, Postgres ×1) and rejected as over-correction — the dev stores' standing data is a debug aid, namespaced writes are already the convention, and one restart-test does not justify four extra cold boots per CI run. The proof half is the same story: tests that assert framework defaults (`/docs` returns 200) or demo-measured pixels (navbar height 68px, ink `#4a4a4a`) can only fail for non-Aurelius reasons, and they are the slowest to debug when they do.

**Alternatives.** (a) Suite-owned stores for every writer (the shape this session built and verified: store-es/webapp/server on their own ES, fastapi-example on its own Postgres) — refused on the user's direction: the ban is on restarts, writes are fine, and four cold store boots per CI run is a lot of boot to buy what namespaced writes already provide. The work is preserved in this branch's history if a suite ever needs isolation (the suite-stack compose recipe — dev image, node config mounted read-only, DD-216 certs, openssl healthcheck — is on record). (b) Keep ESD-04 with a global serialisation — refused: `parallelism: false` taxes the whole fleet forever to run one test, and the dev-ES restart is the exact race the pin documents. (c) Move the layout pins to Storybook visual tests now — refused as scope: the webapp has no storybook target, and porting eight computed- style pins to a visual harness is its own increment; the Vitest component specs cover the structure that jsdom can see, the pixels return with the storybook slice.

**Consequences.** store-es e2e runs in parallel (one serialised suite gone); the dev Elasticsearch is never cycled mid-suite, so co-scheduled suites stop losing connections. ESD-04 is the fleet's first explicitly untested rule, with the note in the increment spec carrying why. The webapp e2e suite drops eight tests (\~135 → 127 collected, all browsers) and the shell's computed-style coverage moves to unit specs as structural assertions; a true visual-parity harness waits on a webapp Storybook slice. The dev stores' data survives e2e runs (writes are namespaced and self-cleaned, and the webapp glossary purge rides its own uuid-prefixed types). `AGENTS.md` gains all three rules: no restarts, prove Aurelius behaviour not framework defaults, guard interactions not layout.

### DD-224 — The webapp e2e signs in once per browser and replays the session

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure; follows DD-223's time audit)
- **Date:** 2026-10-27

**Decision.** The webapp suite's `authenticated` fixture no longer runs the Keycloak form login per test. A session fixture signs in **once per browser**, saves the context as a Playwright `storage_state` (the realm's SSO cookie, `KEYCLOAK_IDENTITY`), and every test now gets its **own context seeded from that state**: the SPA boots with `check-sso` and the silent-iframe redirect (APC-05), so a pre-authed context mints its own 60s access tokens from the stored SSO session — the login form never opens. The fixture watches the boot: navbar → signed in; login form (session died — e.g. the resilience logout test ends the realm session, RSL-02) → run the form login and refresh the shared state, so the next test replays from a live session again. The per-test context keeps cookies/storage/cache isolated exactly as the per-test login left them.

**Reason.** The slow-e2e diagnosis: the suite's \~37 authenticated tests per browser each paid a full Keycloak sign-in (\~1.5s of form fill, redirect and token exchange) — \~60% of the suite's wall time and the fleet's biggest single cost. The realm's SSO session (30-minute idle window, refreshed by every test's visit) plus the SPA's silent check-sso is exactly the mechanism the reuse rides: it is the flow a real returning user takes, so the fixture now proves the SSO path end to end as part of every test.

**Alternatives.** (a) Keep the per-test login — refused: it is the cost this decision exists to remove. (b) One shared context for the whole session — refused: tests mutate storage/cookies (locale, settings panel, theme); isolation stays, only the session is shared. (c) Mint tokens by REST and inject them — refused: keycloak-js keeps its tokens in JS memory, not storage; the storage\_state path is the browser's own session story and needs no injection hack. (d) Test-only Keycloak config with longer token lifetimes — refused: it drifts from the dev realm every suite rides.

**Consequences.** The suite measured 1.28s/test after the change vs 2.24s before (full matrix, all browsers): the webapp e2e drops from \~4m to \~2m20. The realm's 60s access token and 30-minute SSO window bound the suite: \~4 minutes of sessions fit with room, and the self-heal covers the tail. The state file lives under pytest's tmp path — cookies only, never the user's password. The resilience suite's logout test (which ends the realm session and re-signs-in by form) runs on the shared state and proves the recovery path in-suite.

### DD-225 — E2E containers export spans every second so Tempo probes land sooner

- **Status:** Accepted
- **Increment:** cross-cutting (e2e infrastructure; follows DD-224's time audit)
- **Date:** 2026-10-27

**Decision.** The OTLP-emitting app services in the e2e compose stacks (the server stack's `aurelius-atlas-server`, the webapp stack's `atlas-server`, the lineage chain's `data2model` and `lineage-model`) set `OTEL_BSP_SCHEDULE_DELAY: "1000"`, and the Tempo read-back probe loops (server store-ride, lineage chain, webapp stamping/ingest) poll every 1s instead of every 3s. Deadlines stay as they were (60–120s).

**Reason.** The probes ride `BatchSpanProcessor`, which the apps construct with no arguments — its 5000ms schedule delay is the floor under every read-back: the first poll that can succeed lands ≥5s after the request, Tempo's block ingest adds 1–3s, and the 3s sleeps then quantise arrival to \~6–9s. The floor is the exporter, not the polling, and the SDK reads `OTEL_BSP_SCHEDULE_DELAY` from the environment when the processor is built, so the compose env reaches it with no code change. The key stays bare (`OTEL_*` is a third-party consumer, per the env-prefix rule) and rides the e2e compose only: prod images keep the SDK default.

**Alternatives.** (a) Keep the 3s sleeps — refused: they were tuned to a 5s floor the fleet no longer has, and each quantises 1–3s of latency per probe per browser. (b) Force an export per request (a `SimpleSpanProcessor` under test) — refused: it changes the pipeline the suite exercises. (c) Shorten the deadlines — refused: the deadlines are the failure budget, not the expected path.

**Consequences.** Measured solo: the server store-ride probe 12.2s → 6.2s (suite 31.9s → 28.8s), the lineage chain probe 6.1s → 1.0s, the webapp suite 2m36s → 2m08s (its probes ride three browsers). The 84.6s server-dashboard number from the same audit needed no fix: it is contention, not the test — measured clean, the dashboard pair is 7.2s + 0.8s. Export cadence rises (dev containers only, negligible collector load); probes fail only on real ingest loss.

### DD-226 — The dev stacks' restart windows are unbounded

- **Status:** Accepted
- **Increment:** cross-cutting (dev-stack wiring; rides the CI pipeline, no roadmap row)
- **Date:** 2026-10-26

**Context.** DD-195 chose `restart: on-failure:15` for the collector and DD-202 extended the pattern to the slice metrics-pullers, reasoning that 15 attempts ≈ 6 minutes spans any Keycloak boot and the bound keeps a permanently broken stack loud. Both halves proved wrong under the CI e2e fan-out (run 40292544843). The attempt count burns out in \~6 minutes — Docker's backoff doubles per *attempt* (100 ms → 60 s ceiling), so six minutes of failing is 15 attempts, not 6 minutes of wall clock — and Keycloak's TLS listener is not reliably up that fast when the fan-out shares one 4-vCPU node and the Elasticsearch stack boots last. When the budget expires Docker stops restarting the container *permanently*, and the failure is silent: ESD-06 polled Prometheus for 420 s against a puller that had given up for good, reviving one second after the test gave up (the green/red history of that rule — green 40279621021/40282797027/40289090955, red 40286077875/40292544843 — was this race, not the poll budget). The loud-exit property also proved illusory: `compose up --wait` gates on the healthcheck, and a restarting-then-dead container never reports healthy, so the bound exits on the final crash exactly when the unbounded form keeps trying through it.

**Decision.** All four dev composes (`dev/elasticsearch`, `dev/keycloak`, `dev/postgres`, `dev/observability`) carry unbounded `restart: on-failure` on every container whose readiness depends on Keycloak — the collector and the metrics-pullers. This supersedes the bounded-restart half of DD-195 (the awaited readiness — `up --wait` + healthchecks — stands) and the `restart: on-failure:15` detail of DD-202. Loudness moves from the restart count to the state Docker reports: a permanently bad config sits in a visible `restarting` loop, in `docker compose ps` and in the compose `up --wait` that never returns healthy.

**Consequences.** Keycloak readiness is no longer raced: the 60 s backoff ceiling lands a puller within a minute of the issuer coming up, at any cold-start delay, so ESD-06's budget measures ES metrics latency (its stated subject) instead of Docker's restart arithmetic. The cost of the unbounded form is that a permanently broken puller retries forever — visible, not loud; acceptable for dev stacks, where the same loop is the normal boot shape during Keycloak's startup.

### DD-227 — The store-es e2e suite is removed: it evaluated the dev environment, not production

- **Status:** Accepted
- **Increment:** cross-cutting (test strategy; follows DD-223, DD-225)
- **Date:** 2026-10-27

**Decision.** `libs/python/aurelius-atlas-store-es/e2e/` is deleted: ESD-01, ESD-02, ESD-05 and ESD-06 lose their automated tests. The rules stay specified in the 0-2 increment; the dev stack carries them — `up --wait` gates on the compose healthchecks (ESD-01), every app's e2e suite reaches the store over verified HTTPS with credentials (ESD-02 in the production path), heap and puller wiring are config under review (ESD-05, ESD-06). ESD-03 (credential hygiene) remains a unit test in `tests/`; ESD-04 was already untested by DD-223's choice.

**Reason.** The suite asserted the dev environment's state, not the library's production behaviour — the same bar DD-223 set for the FastAPI `/docs` probes. The shape-A runner made the cost concrete: the ESD-06 metrics test burned its full 420s budget and failed the pipeline (run 40465196293) while the ES metrics-puller sat in DD-226's unbounded restart backoff waiting on Keycloak — a dev-stack readiness race, charged to the test suite, blocking production work. A test whose green state is "the dev box is warm" is a flake generator; what the store library must prove is in its unit/container tests (STO-01 to STO-08) and in the apps' suites, which ride the real code path against this store.

**Alternatives.** (a) Keep it with a larger budget — refused: the 420s fix was already tuning a test that should not exist. (b) Keep ESD-02/ESD-05 as e2e against the dev store — refused: the server e2e suite proves TLS + auth + store round-trips from the Atlas side, on the production client path. (c) Move the suite to CI infra validation — refused: dev-stack health is the compose healthchecks' job, already wired to `up --wait`.

**Consequences.** CI's longest e2e suite disappears (7 min worst case, 0s green — the ESD-06 poll dominated it); the 420s `METRICS_TIMEOUT_SECONDS` leaves with the suite. The traceability report gains four explicitly-untested rules beside ESD-04, with this entry as the note. The dev/elasticsearch puller and its DD-226 restart posture stay — Grafana reads them; only the CI assertion on their warm-up is gone.

### DD-228 — Dev-posture tests leave the suites: the sweep of DD-223's rule, applied

- **Status:** Accepted
- **Increment:** cross-cutting (test strategy; follows DD-223, DD-225, DD-227)
- **Date:** 2026-10-27

**Decision.** Six e2e tests are removed: the webapp suite's `test__browser_facing_tls_verifies_against_ca`, `test__collector_accepts_the_dev_plaintext_issuer`, `test__collector_accepts_the_shared_ingest_token`, `test__collector_publishes_are_loopback_pinned` and `test__producers_keep_flowing_with_the_token`, and the frontend-example suite's `test__browser_facing_tls_verifies_against_ca`. Their conftest support leaves with them (`plaintext_service_token`, `collector_container` and the dev issuer constants). The rules they pinned — CIA-03, CIA-07, CIA-10, CIA-11 and SHL-11's TLS half — keep their specs, with an "untested by choice" note where each acceptance list named the test.

**Reason.** DD-223's rule — e2e proves Aurelius behaviour, not the dev box — applied as a sweep. Each cut test asserted dev deployment posture: a certificate chain signed by the workspace mkcert CA, the collector's 127.0.0.1 port publishes, the plaintext :8080 Keycloak listener only the dev browser uses, the shared ingest token's dev-only legacy leg, and the dev pullers' liveness read through the Docker API. None of it exists in production. Two of them (the loopback-pin, the producers-flow) were also the suite's flake-prone container-internals tests — the same family DD-227 deleted at the store-es end. The proofs that ride shipped config stay: the CIA-01/06/08 credential rejects, the browser/service-leg accepts, the proxy paths, the CSP.

**Alternatives.** (a) Move them to a CI "infra validation" suite — refused: the dev stack's readiness is the compose healthchecks' job (DD-226), and a separate infra suite is where flakes go to be ignored. (b) Keep CIA-07's producers-flow as the telemetry canary — refused: Grafana's stack dashboard shows the pullers live, and every producer's own suite going green proves its export; a 90 s log-poll on the dev box proves less. (c) Keep the TLS test, verify against the container's own CA — refused: the CA is the workspace's, so the chain proves dev wiring by construction.

**Consequences.** The webapp e2e drops from 36 to 31 tests per browser (the two container-internals tests carried 120 s/90 s poll floors); the frontend-example suite from 17 to 16. Four CIA rules and SHL-11's TLS half join the fleet's explicitly-untested list, each with its note in the increment spec that owns it — the ledger DD-223 started, and the shape-A runner's first failure (DD-227's ESD-06) is exactly the flake class this sweep thins.

### DD-229 — The shape-A tail overlaps, the test graph shares its daemon

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; follows the shape-A consolidation)
- **Date:** 2026-10-27

**Context.** Run 40471177041 — the first fully green shape-A pipeline — spent 38m 26s: tests 16m 59s (Nx: 9m 22s recoverable, default parallelism 3 against the container's 6 CPUs), Sonar 13m 28s (Nx: 85 % recoverable — the 25 scanners queue on the SonarQube Cloud server and idle the node), and fixed costs the serialised graph left on the table: docker-build (60 s) waits behind every test although images depend on source, the node\_modules cache save re-uploads \~40 s after a hit, and Storybook+Chromatic (2 m) wait behind sonar's queue.

**Decision.** Three overlaps in the single job, no new jobs: docker-build joins the test step's graph (`affected -t test e2e docker-build`) at `--parallel=5` — one CPU stays headroom for the e2e stacks' containers, which share this cgroup; the Storybook build launches in the background of the sonar step (detached with `setsid` — the runner kills each step's process tree at the step boundary, so a plain `&` dies there) and an "Await Storybook build" step joins its exit code after sonar, keeping the verdict; the cache save runs only on a restore miss. Sonar keeps its position — coverage, lcov and sarif must exist — and the overlap exploits its waiting.

**Alternatives.** (a) A parallel `storybook` job — refused: the consolidation to one job (shape A) is the point of the migration, and a second job pays pod startup plus a second daemon to save what the background build saves for free. (b) `--parallel=6` — the e2e composes' Keycloak/Elasticsearch/Tempo containers compete in the same cgroup; 5 leaves them a core. (c) Scoping Sonar engines per project (`sonar.javascript.file.suffixes=` etc.) — deferred: real, but it changes what Sonar analyses; it deserves its own measurement, not a ride-along.

**Consequences.** Expected 38m 26s → \~33m: \~1 min from the build overlap, up to 5m 21s from parallelism (Nx's estimate; contention caps the real recovery), \~2 min from storybook-under-sonar, \~40 s from the conditional save. The Storybook log moves to `storybook.log`, echoed at the join — failures appear at the await step, not live. If `--parallel=5` turns out to inflate e2e contention past what it recovers, the knob is one flag.

### DD-230 — Parallelism stays at the default, the scanner cache moves to the PVC

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; supersedes DD-229's parallelism clause)
- **Date:** 2026-10-27

**Context.** DD-229's `--parallel=5` run (40486044342) failed two unit suites and got slower: the store-es suite's testcontainers Elasticsearch missed its 180 s health window, a fastapi auth fixture read-timed out, and the critical path grew 7m 37s → 10m 35s (run 17m 36s). Nx's "recoverable time" assumes tasks idle on CPU; here the 6-CPU cgroup is already spent on compose-stack JVMs (Elasticsearch, Keycloak, Tempo) and pytest workers, so the fifth lane buys queueing, not throughput. The same week's sonar measurement (store-es, local scanner): paired A/B runs of the as-is config vs engine-scoped suffixes (JS/TS/CSS/YAML/JSON/XML emptied) averaged 39.2 s vs 39.0 s — no effect. The 3.8 s → 0.2 s "plugin download" saving claimed earlier was a cold-vs-warm cache artifact: the scanner's download cache (\~382 MB — the cloud engine jar, a JRE, 13 plugin jars, content-addressed under `~/.sonar`) is identical for both configs; SonarCloud ships the full bundle to the CLI regardless of project languages. What the cache does explain is the CI sonar step's shape: the first task per pod pays the cold bootstrap (run 40471177041: otel:sonar 109 s vs \~15 s steady-state) because HOME is the container layer, wiped on every runner-pod boot, while uv/npm/ pre-commit caches live on PVC subPaths (arc-shapea-values.yaml).

**Decision.** (a) The test step keeps DD-229's docker-build graft at Nx's default parallelism — one flag, DD-229's consequence named it. (b) The scanner cache joins the PVC subPath set: `SONAR_USER_HOME=/var/cache/ci/sonar` in the runner command, a `.ci-cache/sonar` mount, dir created by cache-init — every pod's first sonar task stops paying \~94 s of jar downloads, and the first pod boot pays them once. (c) Sonar engine scoping is measured away: the suffix knobs are NOT added to any sonar-project.properties, retracting the store-es trial before it shipped.

**Alternatives.** (a) Keep `--parallel=5` with longer testcontainers timeouts — refused: DD-222..228 spent a week deleting exactly this flake class, and tuning a timeout to feed a lane Nx cannot fill is backwards. (b) actions/cache for `~/.sonar` — refused: the PVC subPaths are the established shape-A pattern for toolchain caches (no cache-server round-trip, warm across pods by construction). (c) Bake `~/.sonar` into the runner image — refused for now: the image rebuild cadence is slower than SonarCloud's plugin rotation, and stale cache entries are re-fetched by content hash anyway; the PVC gets the same warmth with no skew.

**Consequences.** The parallelism clause of DD-229 is retired (the overlaps survive — this run's own failures were unit tests, not the grafted builds). The sonar step's per-pod floor drops \~94 s; the engine-scoping idea retires with paired-run evidence, and DD-229's "85 % recoverable" sonar figure is re-read as the server queue, which no scanner flag fixes — future sonar tuning starts from the CI per-task times, not local guesses. The values change lands on the next `infra/arc/install.sh` run (helm upgrade evicts in-flight runner pods — run it between jobs).

### DD-231 — Teardown downs the compose stacks: prune only sweeps corpses

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; repairs DD-229's teardown step)
- **Date:** 2026-10-27

**Context.** The shape-A teardown step names its purpose in its own comment — Keycloak/Postgres/Elasticsearch/observability hold \~8 Gi of the node's memory and the scan/sonar tail must not pay for it. It never happened: `docker container prune -f` sweeps only STOPPED containers, and the suites leave their stacks Up, so every run's teardown deleted exactly one corpse — the 28.67 kB testcontainers ryuk (runs 40471177041, 40486044342 and 40489544189 each report the same single container) — while the \~8 Gi rode through docker-build, the vuln scan, sonar and Chromatic on a node capped at 11 Gi.

**Decision.** The teardown iterates `docker compose ls --all -q` and runs `docker compose --project-name <p> down -v --remove-orphans` per project — the same project-name pattern the diagnostics step uses — keeping the prune pair behind it as the sweeper for non-compose strays (ryuk, anonymous volumes). `down` deletes containers, named volumes and networks; images stay, so the scan's daemon-read and the warm base-layer store are untouched (unchanged from the prune semantics).

**Alternatives.** (a) `docker stop $(docker ps -q)` — kills the stacks bluntly, with no per-project attribution in the log; refused for the readable footprint ("Tearing down compose project: …"). (b) Each suite downs its own stack — refused: the suites share the `dev/*` stacks (the E2E suite rule, DD-223), and a suite stopping one mid-graph evicts its neighbours. (c) Leave it — refused: the tail's memory pressure is the cgroup's, and sonar and Storybook pay it.

**Consequences.** The scan/sonar/Chromatic tail runs with the stacks' \~8 Gi free; the teardown step grows from 1 s to the seconds a four-stack `down` takes, naming each project as it goes. The stopped-container foreclosure the old comment guarded (run 40231127680) carries over unchanged. The step's log is the verification: it names each project it downs, and the prune tail stops reporting one 28.67 kB corpse as the step's whole output.

### DD-232 — The CI pipeline is a fan-out DAG; the pool is per-pod emptyDir

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; supersedes DD-229's single-job clause)
- **Date:** 2026-10-27

**Context.** The single shape-A job (38m 04s green, run 40501485238) is two workloads stitched serially: the test phase (\~17 min of CPU/RAM saturation — e2e suites plus compose-stack JVMs) and the sonar step (13m 28s wall, \~85% of it SonarCloud *server* queue — 2m 4s of scanner, DD-230's re-read). One job on one 6-CPU cgroup can overlap them only by the DD-229 setsid dance, which hides Storybook, not sonar. The pool forbade splitting: the 50 Gi cache PD is ReadWriteOnce, so `arc-shapea-values.yaml` pins `maxRunners: 1` — a second runner pod cannot mount the work volume, and the docs recorded "a job on a second node starts cold". A spike scale set (own helm release, prod untouched) with an emptyDir work volume and `maxRunners: 2` measured the two open questions (run 40520070483, probes 14:20:02Z→14:23:09Z and 14:20:03Z→14:23:59Z): two jobs on the pool label run CONCURRENTLY on separate pods; per-pod markers on the work volume stay per-pod (no shared state); JIT pod boot is 15–17 s on a warm node (a cold node pays \~3 min pulling the 546 MB runner image); and a cold daemon pulls the two heaviest dev-stack images in 48 s, the second in 0.0 s once the node has the layers (GKE image-cache sharing). Node facts measured at the same time: 3 × (4 CPU / 13.6 Gi allocatable), so pod *requests* of 1 CPU/4 Gi let three runner pods pack on ONE node — anti-affinity, not requests, is what spreads them.

**Decision.** (a) `ci.yaml` becomes a fan-out DAG: `validate` (checkout, install, pre-commit --all-files, decrypt, unit `test`, coverage upload) gates three concurrent jobs — `e2e` (the `e2e` + `docker-build` graph, diagnostics, DD-231 teardown), `scan-sonar` (image rebuild from the buildcache, trivy, sarif, `sonar`), and `chromatic` (Storybook build + publish). Scan and sonar co-locate in one job: the sarif handoff stays on the work volume. (b) Cross-job state rides artifacts (coverage upload/download) or rebuilds (GHCR buildcache images) — jobs never share files through the volume. (c) The pool: the RWO PD retires; the work volume becomes a per-pod 20 Gi `emptyDir` (warm within a pod — caches, image stores, registry auth survive between jobs; cold across pods — 48 s worst measured). `minRunners: 2` (warm pair: fan-out jobs start in \~15 s; a cold-node start pays the image pull), `maxRunners: 3` (the three fan-out jobs), a PREFERRED pod anti-affinity on `kubernetes.io/hostname` (spreads across nodes; packing degrades gracefully where `required` would deadlock a queue), requests stay 1 CPU/4 Gi (limits 6 CPU/11 Gi), and the cluster autoscaler ceiling goes 2 → 3 nodes.

**Alternatives.** (a) Per-pod PDs via a StorageClass — dead before the spike: ARC builds job pods from `template.spec`, with no StatefulSet and no `volumeClaimTemplates` (chart 0.15.1), so per-runner PVCs need an external provisioner webhook. (b) Filestore (RWX) shared cache — blocked by billing-account policy (on record). (c) Keep the single job and parallelise inside it — exhausted: DD-229/230 measured the in-job overlaps and the parallelism knob; the serial test→sonar wall is the server queue, which only a second job (running *while* the first waits) dissolves. (d) `requiredDuringScheduling` anti-affinity — refused: three nodes is the steady state, not a guarantee; a job queued forever while the autoscaler provisions is worse than a packed pod.

**Consequences.** Wall-time target: 38 min → \~26–28 min: validate \~7 min, then the longest fan-out branch (e2e \~17 min with its own stacks, scan-sonar \~15 min mostly server-queue). Measured on the first run (40531441140, green): **27m 48s** — validate 8m 55s gates chromatic 3m 46s, scan-sonar 16m 20s (sonar 11m 12s of server queue, 2m 49s the buildcache rebuild) and e2e 17m 42s (15m 32s of suites) on three pods; the e2e job is the critical path, 2m 19s off the sonar branch. The DD-229 setsid/await dance retires with the single job. Each job pays checkout+install (\~2 min, node\_modules from the cache server) — the fork's price, \~3×. The `e2e` job is now the pipeline's only stack owner, so DD-231's teardown is a single named step, not a tail. Caches are per-pod: a pod respawn cold-starts uv/npm/sonar/docker once (48 s–2 min), the warm pair absorbs it. Next free DD: 233.

### DD-233 — The toolchain caches bridge pod churn through the cache server

- **Status:** Accepted
- **Increment:** cross-cutting (CI pipeline; repairs DD-232's cache-warmth assumption)
- **Date:** 2026-10-27

**Context.** DD-232 recorded that per-pod emptyDir caches make a pod respawn cold "once (48 s–2 min), the warm pair absorbs it". The fan-out pool churns pods constantly — scale-in after every run, helm deploys, preemptions — so a `validate` landing on a never-seen pod is the norm. Measured on run 40538065508 (warm run, fresh pod): the pre-commit step spent 66 s re-`Installing environment` for its seven hook repos (talisman's Go build alone \~40 s) before the first hook ran — step time 181 s where the RWO-PD single job (a pod alive for weeks, caches hot) spent 83 s; hook *execution* is identical in both (96 s). The install step pays the same tax on uv's side (\~25 s of wheel re-downloads; npm does not — node\_modules rides the cache server and restores in \~10 s). The old pipeline's "4 s python / 20s node" warmth was the PD's weeks-long pod life, not a better mechanism.

**Decision.** Bridge the cold-pod gap through the existing in-cluster `actions/cache` server (the same backend node\_modules uses, LAN speed, OIDC-scoped): `validate` restores uv (keyed `uv.lock`) and pre-commit (keyed `.pre-commit-config.yaml`) and saves both on miss — single writer, the node\_modules shape; the three fan-out jobs restore uv; `scan-sonar` restores/saves the SonarScanner jar cache (DD-230's \~94 s per-pod bootstrap, save after the analysis since the jars land during it). The emptyDir stays the warm tier *within* a pod; the cache server is the cross-pod tier. Keying on the config files makes every cache rebuild exactly-once per version bump.

**Alternatives.** (a) Pin runner pods warm (higher `minRunners`) — refused: absorbs some churn, pays idle pods for all of it, and helm deploys evict anyway. (b) Return to a shared RWX volume — Filestore is blocked by billing-account policy (on record). (c) Bake the caches into the runner image — refused for the same reasons as DD-230's `~/.sonar` bake (rotation cadence), and the config-keyed caches self-invalidate where image layers go stale.

**Consequences.** Cold-pod validate drops \~66 s (pre-commit envs) and \~25 s (uv wheels); scan-sonar's first-run sonar bootstrap drops \~94 s on a fresh pod. First run per key version pays the build (the save-on-miss upload, \~1 min for the uv cache at LAN speed) and every pod everywhere rides the artifact after. The cache server PD (20 Gi, LRU at 90 %) grows by uv (\~2–3 Gi) + pre-commit (\~0.5 Gi) + sonar (\~0.4 Gi) — headroom verified against the 18 Gi eviction line. The "4 s/20 s" memory is restored where it applies (warm installs on any pod); the ephemeral-tree rule is untouched. Next free DD: 234.

Measured (run 40549779734, fixed fleet, all caches warm on the server): all restores hit and extract clean (zero `Cannot utime`), validate's pre-commit step 181s -\> **82s** (the old always-warm PD pod was 83s - parity), uv install 26s, scan-sonar 16m 20s -\> **12m 2s** (the sonar jar cache rides the bridge too), validate 8m 55s -\> **7m 0s**, full pipeline 27m 48s -\> **25m 48s** with the e2e suites now the critical path. The restore step's metadata bug (subPath mount roots stay root-owned under fsGroup - k8s applies it to volume roots only; cache-init chowns them now) shipped in the same change.

### DD-234 — TLS material is a required setting; the server never serves plaintext

- **Status:** Accepted
- **Increment:** 9.2
- **Date:** 2026-10-27

**Decision.** `TLS_CERT_FILE` and `TLS_KEY_FILE` become required settings with no default, joining the store endpoints/password/CA in the SRV-01/SRV-02 idiom: a missing one stops start-up with a pydantic error naming the field. The both-or-neither pair check is deleted — the "neither" arm no longer exists — and `ServerSettings.tls` always returns the pair. `uvicorn_options` always carries `ssl_certfile`/`ssl_keyfile`. The image bakes `ENV` defaults pointing at `/certs/server.pem` / `/certs/server-key.pem` (DD-216's stack-owned mount), and its healthcheck speaks HTTPS with CA verification. SRV-06 supersedes the second sentence of SRV-03.

**Reason.** ADR 039 states TLS is the only serving mode, and every deployment arrangement (dev, e2e, CI, the compose stacks) already supplies the pair — plaintext is reachable only by misconfiguration, and a pentest (H3) counts a plaintext listener as the finding it is. Making the setting required turns the deployment's silent failure mode (an HTTP listener answering where HTTPS was expected) into a start-up error that names itself, which is how every other required setting already behaves.

**Alternatives.** (a) Keep the pair rule and fail when both are unset — refused: "unset is valid" is the whole hole; it also keeps a dead code path (plaintext uvicorn options) in `__main__`. (b) Terminate TLS at the proxy and serve plaintext on loopback — refused: ADR 039's store-side pinning applies equally server-side, the e2e/dashboards ride the server's own HTTPS, and a loopback-only assumption is unenforceable inside a shared pod network. (c) Self-signed material generated at start-up when unset — refused: silently untrusted material is the failure mode users report as "the browser blocks the site", and start-up crypto is the anti-pattern DD-216 removed for the stacks.

**Consequences.** Unit tests supply a stub pair (the `tls_pair` fixture; `FilePath` validates existence, uvicorn never starts under test). A bare `docker run` of the image without a mounted pair fails at start-up naming `AURELIUS_ATLAS_SERVER_TLS_CERT_FILE` — the design working, documented as such. The healthcheck no longer has a plaintext branch. Next free DD: 235.

### DD-235 — A 5xx answer is opaque and carries the trace id as `requestId`

- **Status:** Accepted
- **Increment:** 9.2
- **Date:** 2026-10-27

**Decision.** `atlas_error_handler` stops echoing `errorCause` for a 5xx: the body keeps `errorCode`/`errorMessage`, the cause's text goes only to the log (as `exc_info`, as before), and the answer gains the current OTel trace id — 32-hex `requestId` in the body, `X-Request-Id` in the headers — so a user's screenshot correlates to the logged stack trace and the trace. 4xx answers keep SRV-04's cause echo; Atlas's own validation messages are client-facing and the parity scenarios pin them. DV-85 records the deviation from `AtlasBaseExceptionMapper`.

**Reason.** Pentest M5: the 5xx echo leaks internals (store URLs, index names, exception classes from the ES client) to any caller who can trigger a server fault — readiness against a downed store leaks the store URI. Atlas echoes because its own logs were the only consumer of its UI's error dialogs; Aurelius ships the whole OTel pipeline, so a trace id is the correlation key the support flow needs, and the body stays Atlas's shape for every field the scenarios pin.

**Alternatives.** (a) Env flag for verbose errors — refused: an always-on leak-by-default with a mitigation nobody enables; DD-016's fail-loud philosophy is loud in the log, not on the wire. (b) Random per-request uuid as the id — refused: the logs carry the trace id already (structlog/OTel), a random id correlates to nothing. (c) Suppress 4xx causes too — refused: they are parity-pinned client-facing messages (`UNKNOWN_TYPENAME`, validation detail).

**Consequences.** The client model's `errorCause` stays optional (4xx fills it). In-process tests have recording spans (instrumented app + SDK provider), so `requestId` is assertable; when telemetry is off the field is simply absent. The header is additive, so parity scenarios (expected-response headers only) are unaffected. Next free DD: 236.

### DD-236 — Security response headers are a pure-ASGI middleware split on `/api` path

- **Status:** Accepted
- **Increment:** 9.2
- **Date:** 2026-10-27

**Decision.** One pure-ASGI `SecurityHeadersMiddleware`, added first in `create_app` so it wraps routers, mounts, and the exception handler. `/api/**` answers (by path prefix, so error and 404 answers are covered) get `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a `Permissions-Policy`, `Cache-Control: no-store`, and a CSP that serves no documents (`default-src 'none'; base-uri 'none'; frame-ancestors 'none'`). The dashboard documents get a same-origin CSP with `'unsafe-inline'` + `'unsafe-eval'` scripts and `'unsafe-inline'` styles (DV-86: the vendored `index.html.tpl` inlines the build-varying bust value, and the require-handlebars-plugin compiles templates at runtime with `new Function` — the e2e dashboard boot is the regression guard; what CSP does enforce there is `object-src`/`base-uri`/`frame-ancestors` closed and same-origin sources) and `SAMEORIGIN` framing; assets fetched with the legacy `?bust=` get `public, max-age=31536000, immutable` (the bust param is the legacy's own content-versioning; HTML is excluded so a stale page cannot pin itself). HSTS (max-age 1y, includeSubDomains) rides every answer when `hsts_enabled` — default true, false in the dev `.env` (ADR 039's named dev relaxations: the mkcert CA is not browser-trusted, and localhost must not pin). SRV-08.

**Reason.** Pentest L1: clickjacking on the dashboard, MIME sniffing on API answers, cacheable API JSON, and a missing HSTS policy. A pure-ASGI stamp on `http.response.start` reaches every response path — including the exception handler's `JSONResponse` and static-file answers — where `BaseHTTPMiddleware` wraps streaming awkwardly and StaticFiles bypasses route-level answers.

**Alternatives.** (a) nginx-terminated headers — refused: the server answers directly in e2e and any deployment without the webapp proxy; headers belong to the origin. (b) Strict CSP with hashes/nonces for the dashboards — refused for now: the vendored `index.html.tpl` inline bootstrap inlines the build-varying `<%- bust %>` value, so hashes churn per build (DV-86); the dashboard retirement (6.3) removes the surface. (c) starlette `CORSMiddleware`/`GZip` stacking — refused: none of them set these headers; this is one small middleware, not a framework feature.

**Consequences.** Header tests cover API, 404, dashboard, bust-asset and HSTS-off answers. The parity runner compares expected response headers only, so additive headers keep every scenario green. The dev compose stacks carry `HSTS_ENABLED=false` explicitly (e2e images do not read `.env`). Next free DD: 237.

### DD-237 — Index refresh moves from reads to writes

- **Status:** Accepted
- **Increment:** 9.3
- **Date:** 2026-10-28

**Decision.** Every write a search reads carries `refresh="wait_for"`: the entity/linked bulk (`EntityDocuments.write`), the entity restore, the linked restore, the journal put and delete, and the audit append (`put_events`). No read path calls `indices.refresh` — `count_type`, `referring`, `classified`, `search`, `terms`, `journal`, `list_tasks`, `count_linked_type`, `classifications_of_types`, `list_events`, `entities_with_tag_changes` all lose theirs. Reservations stay unrefreshed: they are read by `mget`, which is real time (ENS-04). `wait_for` (not `true`) also waits for the *concurrent* writes' refresh — the pair that keeps a reader from seeing half of one bulk (DV-16's shape, unchanged). ENS-11.

**Reason.** Pentest M6: every read paid a full index refresh on the request's critical path — a search, a count, an audit listing each forced a refresh of the entities (or audits) index. That is a denial-of-service lever on the store, not a feature: `refresh` is a write-path affordance, and Apache Atlas refreshes nothing on reads (JanusGraph's transactional graph cache makes it pointless there). Read-your-writes (ENS-04, ENS-07's visible contract) needs the refresh *once*, at the write that created the fact; paying for it on every reader multiplies the cost by the read:write ratio.

**Alternatives.** (a) `refresh=true` — refused: it forces a refresh of every shard immediately and serialises concurrent writers on it; `wait_for` joins the refresh the write's own request triggers. (b) Refresh only on the writes that mutate what the UI searches (bulk, restore) and leave journal/audit on reads — refused: the journal read is recovery's (a restart reads entries written moments before), the audit list rides the audit append; a partial move re-introduces the read-side cost on the paths kept. (c) No refresh at all, tolerate stale reads — refused: ENS-04's read-your-writes is scenario-pinned (write → search returns the entity), and Atlas's transactional visibility is the parity behaviour. (d) A `searchRequestCache` -style read-your-writes (ES's real-time GETs + `search_after` on `seq_no`): ES's `mget`-real-time + `wait_for`-refresh pair is the same guarantee with less machinery.

**Consequences.** Write latency rises (the response waits for the refresh); read latency falls off a cliff at the p99. The fake client records the `refresh` kwarg of every write (`write_refreshes`) and keeps counting `indices.refresh` calls (`refreshes`), so the unit tests pin both halves: writes carry `wait_for`, reads call refresh never. The e2e parity scenarios (write → search sequences) are the acceptance over the real store — they stay green unchanged, which *is* the read-your-writes proof. Supersedes the read-side refresh rationale in DD-043, DD-048, DD-057 (their decisions stand; only the refresh's location moves). Next free DD: 238.

### DD-238 — The browser rate limit lives at the nginx edge, not in the server

- **Status:** Accepted
- **Increment:** 9.3
- **Date:** 2026-10-28

**Decision.** The webapp's nginx (`nginx.conf.template`, mirrored by `e2e/config/nginx.conf`) carries a `limit_req` leaky bucket on the `/api/` proxy: key `$binary_remote_addr` through a `geo`/`map` pair that maps the private ranges (RFC 1918 + loopback) to the empty key — nginx does not account requests with an empty key — `rate=300r/m`, `burst=100`, `nodelay`, `limit_req_status 429`. The server itself has no limiter: no middleware, no setting, no 429 error code in the enum. uvicorn's `forwarded_allow_ips` becomes a server setting (default `127.0.0.1`) so the webapp proxy hop is declared and the access log / OTel peer attributes key on the browser's address, not the proxy's (SRV-10). The e2e bucket is test-sized (60r/m, burst 20) so the burst test can outspend it sequentially. SRV-09.

**Reason.** Pentest M6's search-cost half: a browser (or a script posing as one) can fire unbounded searches. The limit belongs where the browser is: at the webapp edge, nginx already terminates TLS, proxies `/api/`, stamps headers — the bucket is one more line of the same job, runs in C, shares state across workers in one shm zone, and refuses before a request costs a handler, a query, or an ES fan-out. The user's steer: internal apps are not the concern — a service bursting the API is working, a browser flooding it is attacking; the private-range allowlist is exactly that split. An application-layer limiter (pure-ASGI token bucket; slowapi/limits) was built and removed: it also limits the internal callers nobody worries about, its limits are per-process (a multi-worker deployment multiplies the budget), and uvicorn's default trust (`127.0.0.1`) makes every proxied request look like the proxy — every browser sharing one bucket. `limits` is also a transitive dependency of a library that is removable (the observability stack), a coupling DD-238's removal notes must keep straight.

**Alternatives.** (a) The pure-ASGI middleware (built first) — removed for the reasons above; kept as a fallback only if a deployment runs the server without the webapp edge and wants a limiter (the server has no knob for it now). (b) slowapi — refused: Flask/FastAPI decorator middleware, same per-process limitation, new vocabulary (strategy/storage) for one rule. (c) `X-Forwarded-For`-keyed limiting in nginx (`realip` module) — refused: the browser cannot spoof the TCP address nginx sees; the webapp is the only front door, no realip hop is needed. (d) Elasticsearch-side throttling (`search.max_concurrent_shard_requests`) — refused for this increment: it protects the store from the server, not the server from browsers.

**Consequences.** The refusal is nginx's 429 (HTML, no Atlas error body, no `Retry-After` — `limit_req` sends none): DV-87 records the deviation, the webapp's alert drawer (ALR-05) is the UX for the refused call. Deployments that front the server with something other than the webapp nginx get no limiter — that is the product boundary, stated in the spec. A deployment whose internal callers arrive from public addresses must extend the geo allowlist. `forwarded_allow_ips` ships `127.0.0.1` (uvicorn's own default — the setting exists to *name the proxy*, not to trust more by default). Next free DD: 239.

### DD-239 — The edge exports spans on the legacy leg, built in the dev-image stage

- **Status:** Accepted
- **Increment:** 9.4
- **Date:** 2026-10-28

**Decision.** The webapp's nginx becomes an OTLP producer through the native `ngx_otel_module` (v0.1.2), compiled in a Docker builder stage on `dhi.io/nginx:1.30-alpine3.24-dev` against the exact nginx source the runtime image ships, loaded via the main-context include the hardened image already provides (`/etc/nginx/modules/*.conf`), and exporting the `/api/` spans to the collector's **legacy gRPC leg** (4320: TLS, CA-pinned, shared ingest token). The edge span propagates W3C context (`extract|inject`), so it stitches browser-app trace → edge span → server request span; static assets stay untraced. The edge is a producer, not a user: the collector stamps no user identity on it (CIA-09's rule, edge edition). ETR-01..03. (Numbering note: PR \#155 reserves DD-237/238; 239 here assumes it merges first.)

**Reason.** The edge is the browser's only entry point and the one hop the stack cannot see; once 9.3's limiter lands, refusals (429) exist *only* at the edge — nginx's refusal lines go to container stderr, which the collector does not collect (OTLP-only receivers), so without this the event is invisible in Tempo/Loki/Grafana. The module's native span carries the edge's own view (`http.status_code`, `net.sock.peer.addr`, the matched route) and joins the trace the browser started. The 2022 blog's Lua/OpenTelemetry-Collector-sidecar route is obsolete next to the native module (nginx measures third-party tracing at \~50% request cost, native at 10-15%).

**Alternatives.** (a) Per-service OAuth like every other producer — the module's export headers are config-parse-time **static strings** with no refresh hook (source: `addExporterHeader` validates at parse, the exporter builds once in `initWorkerProcess`), so a minted Keycloak JWT expires minutes in; a gateway collector presenting `oauth2client` to the services leg is the recorded upgrade path, not this increment. The legacy leg is the defined home for producers that cannot present a JWT (CIA-10 — Keycloak and the FastAPI example ride it). (b) The `-dev` image as runtime — it is a toolchain, not a product; the runtime stage is the hardened image plus the module's 93-lib closure (\~42 MB, gRPC/protobuf/abseil/ICU: gRPC pulls ICU at runtime, verified by ldd). (c) `filelog`-tailing nginx's stderr into Loki — answers "where are the refusal logs" with lines, not spans: no trace join, no client-side stitch, and the collector has no container-log receiver today; the span supersedes the log line. (d) The module from nginx.org's prebuilt dynmodules — built for glibc nginx.org binaries; our base is the hardened musl image (module signature is feature-flag checked, and musl will not resolve Alpine's dangling soname symlinks — the builder tars the closure dereferenced, `-h`).

**Consequences.** The webapp image grows 14→56 MB; the SBOM/license report gains grpc/protobuf/abseil/re2/icu (Apache/BSD). The builder pins the v0.1.2 tag with the cmake-4 policy flag (its `cmake_minimum_required` predates 3.5) and apk's `python-3.14` (the dev image's xcb-proto resolves 3.14; bare `python` is 3.15 now) — reproducible-build facts recorded here. `limit_req` and this module share the `/api/` location: the limiter refuses before the span's `http.status_code` records the 429 (the module samples at the rewrite phase, completes at the log phase — a refused request's span is real, proven in the prototype burst). The v0.1.x line is 2023-frozen (4 open issues, no maintainer activity); re-evaluate at the next nginx baseline (the 1.30 signature check is the compatibility gate — a mismatched module fails at config parse, loudly, at boot). Next free DD: 240.

### DD-240. The DSL parser is generated from Atlas's own grammar

- **Status:** Proposed
- **Increment:** 4.3
- **Date:** 2026-10-30

**Decision.** `aurelius-atlas-dsl` keeps Atlas's `AtlasDSLLexer.g4` and `AtlasDSLParser.g4` unchanged in `grammar/` and generates its lexer and parser from them with the ANTLR 4.13.2 tool (`npx nx generate-parser aurelius-atlas-dsl`, Java needed only then). The generated modules are committed in `aurelius_atlas_dsl/generated` and run on `antlr4-python3-runtime`, pinned to the tool's version. They are left out of ruff, pyright, coverage, Sonar, the hooks, the traceability check and the increment's line budget: nobody writes or reviews them.

**Reason.** The grammar is ambiguous and its lexer has quirks a client can see: the longest match decides between a keyword and a name (`fromDate`, `db.name`, `a.b.c` as `a.b` and `.c`), a sign joins a number (`a -5` is two sources), and ANTLR's adaptive prediction picks among the readings of `singleQrySrc`. Generating from the same grammar reproduces all of it, and ANTLR's syntax error messages, which Atlas puts in `INVALID_DSL_QUERY`. Every query of Atlas's DSL tests reads as Atlas reads it. A warm parse takes about 13 ms.

**Alternatives.** A hand-written recursive descent parser: no runtime dependency and faster, but every lexer rule and every ambiguity resolution re-derived by hand, and ANTLR's error messages imitated. A parser library such as Lark: a second grammar to keep equal to Atlas's. ANTLR 4.7, Atlas's own version: its Python runtime dates from 2017 and is no longer maintained; 4.13 runs the same parsing algorithm.

**Consequences.** A grammar change is Atlas's grammar changed and the package regenerated, never the generated code edited. The runtime is a pure-Python dependency without type information; `tree_builder` reads the contexts through small typed helpers.

### DD-241. The parse tree is handed on as typed, immutable nodes

- **Status:** Proposed
- **Increment:** 4.3
- **Date:** 2026-10-30

**Decision.** `parse` returns a tree of frozen dataclasses (`dsl_tree`), not ANTLR's contexts: one node per grammar rule that `DSLVisitor` reads, named after it, a choosing rule as the union of its alternatives. Every node keeps its `getText()`, and an operator, sort order or literal the text it was written with besides its kind.

**Reason.** `DSLVisitor` and `GremlinQueryComposer` work on rule texts (`getText()`) and on which alternative matched; the nodes keep both, so 4.4 can port that logic, Atlas's quirks included (it upper-cases the operator's spelling before looking it up). Typed nodes let pyright check 4.4's composer and keep the generated code behind one module; equality makes trees easy to assert in tests.

**Alternatives.** Hand ANTLR's contexts to 4.4 as Java does: the closest port, but untyped, mutable and tied to the generated code. An abstract tree that folds Atlas's rules into precedence (`and` before `or`): Atlas joins conditions left to right, and the folding belongs to the composer that reproduces it.

**Consequences.** 4.4 composes Elasticsearch queries from `dsl_tree` alone. A grammar change touches `dsl_tree` and `tree_builder` too.

### DD-242. A DSL query is composed into the basic search's filter tree

- **Status:** Proposed
- **Increment:** 4.4
- **Date:** 2026-10-30

**Decision.** `DSLVisitor` and `GremlinQueryComposer` are replaced by one composer in `aurelius-atlas-core` (`dsl_query_composer`) that walks the syntax tree of 4.3 (DD-241) and writes the `SearchQuery` of the basic search (DD-089): the sources and conditions as one filter tree of `Criterion` and `Group` over the search fields (DD-088), the `orderby` as its sort, the limit and offset as its page. `like` adds two tests to the search query: `REGEX`, a regular expression the whole keyword value matches in case, and `WORD_REGEX`, one a word of the text sub-field (DD-092) matches in any case; Elasticsearch answers both with `regexp`, the in-memory documents with Python's `re`. The composer keeps Atlas's name resolution (`IdentifierHelper.Info`, `RegistryBasedLookup`), its left-to-right joining of `and` and `or`, and its semantic errors, collected and joined into one `INVALID_DSL_QUERY`. `aurelius-atlas-core` depends on `aurelius-atlas-dsl`.

**Reason.** Atlas's composer writes Gremlin text that its executor turns back into a traversal; every clause of 4.4a is a test of the entity's own fields, which the basic search already translates to Elasticsearch and evaluates in memory. One filter tree keeps a DSL query to one Elasticsearch request, reuses the paging, sorting and tie-breaking of the basic search, and lets the in-memory documents answer the core tests.

**Alternatives.** Port `GremlinQueryComposer` clause by clause and translate the clause list: the closest port, but a second translation of every predicate the basic search already has. Elasticsearch's query string syntax: a client's query would reach Elasticsearch's parser, with neither Atlas's grammar nor its errors.

**Consequences.** Traversals into referred entities, classification attributes and projections (4.4b) are not tests of one document's fields; 4.4b decides how they are evaluated, over the relationship documents (DD-061). Lucene's regular expressions are not Java's or Python's: the patterns `like` writes (`.`, `.*`, escaped characters, classes) read the same in all three, which the e2e tests check.

### DD-243. DSL traversals and projections are evaluated in steps

- **Status:** Proposed
- **Increment:** 4.4
- **Date:** 2026-10-30

**Decision.** The DSL composer (DD-242) answers a plan: the filter tree of the final entities, the steps before them, and the `select` and `groupby`. A move to referred entities (a source naming a reference, a `select` of one) is a step: the entities found so far are read, the GUIDs their attribute refers to taken, and the next filter holds for those GUIDs. A condition on a referred entity (`db.name`) or a classification attribute (`Dimension.tagAttr1`) is a criterion whose value the executor resolves to GUIDs before searching: the referred entities matching, the entities referring to them by reference (`references`, DD-057) or relationship end (DD-061) and confirmed by reading the attribute; or the classification instances matching, as the classification search finds them (DD-090). Aggregates, groups and moves read the entities found in one search of at most 10,000; rows and groups are built from them in memory, as `SelectClauseProjections` builds them from vertices.

**Reason.** Atlas walks edges; the documents have none. Resolving to GUIDs keeps each step a search of the entity documents with the filter tree of DD-242, and the in-memory documents answer the same plan. A reference is read as a read answers it, so plain references and relationship ends, legacy or not, give the same answer.

**Alternatives.** Denormalising referred attributes into the referring document's search fields: one query, but every write would have to rewrite the entities referring to the one written. Elasticsearch `terms` lookups across indices: they read one document's field, not a relationship's other end. Aggregating in Elasticsearch: Java's comparison for `min` and `max` (no value least, kinds equal) and row deduplication are not its.

**Consequences.** A step reads at most 10,000 entities (DV-98); a query reaching past them answers from the first 10,000. A condition on a referred entity costs a search, a read of the candidates and of their references.

### DD-244. Saved searches wait for authentication

- **Status:** Accepted
- **Increment:** 4.5
- **Date:** 2026-10-30

**Decision.** Increment 4.5 (saved searches and the user profile) follows 6.1 (authentication) instead of preceding 5.1. The roadmap keeps its number; 5.1 lineage is the next increment. The user chose this on 2026-10-30.

**Reason.** Atlas owns every saved search by the logged-in user: `addSavedSearch` sets the owner from the request's user, `getSavedSearches` defaults to that user, and reading, updating, deleting and executing a search check ownership (`checkSavedSearchOwnership`). Until 6.1 the server has no user (DV-04, DV-06); porting 4.5 now would need a temporary owner, a deviation 6.1 would have to undo, and ownership checks that test nothing.

**Alternatives.** One anonymous owner until 6.1: the endpoints sooner, the checks trivially passing. An owner taken from a request header until 6.1: testable checks, but a spoofable identity to remove later.

**Consequences.** `search/saved*` stays unanswered until after 6.1; the dashboards' saved-search menus fail until then, as they did before.

### DD-245. Lineage walks the relationships of the process edges

- **Status:** Proposed
- **Increment:** 5.1
- **Date:** 2026-10-30

**Decision.** `EntityLineageService` ports Atlas's default traversal (`getLineageInfoV2`) and lineage on demand over the relationship documents (DD-061): an edge `__Process.inputs` or `__Process.outputs` is a relationship of that label, going out of end 1 (the process) into end 2 (the data set), read through the relationships an entity lists, as `graph_helper.edges_for_label` reads them for the other edge lookups. Each entity's relationships are read once per lineage. The Gremlin lineage (`atlas.lineage.query.use.gremlin`) is not ported. Atlas's lineage settings are server settings with Atlas's defaults: on demand off, 3 relations each way, at most 9,000 relations.

**Reason.** The relationships are the edges Atlas walks: one document per edge, listed by both ends, in any state as Atlas's `getEdges` returns them. Walking them keeps Atlas's order of visits, its visited sets and its cap, which decide what a deep or wide lineage answers.

**Alternatives.** A search per step for the relationships of a label whose end is the entity: an index on ends the relationship documents do not have, and a refresh before each read. Denormalising each entity's process edges into its document: a second copy every relationship write would keep equal.

**Consequences.** A lineage costs two reads per entity it reaches (the entity and its relationships); the 9,000 relation cap bounds it. Lineage on demand, off by default as in Atlas, is answered once the setting is on.

### DD-246. Glossary objects are entities written through the entity and relationship stores

- **Status:** Proposed
- **Increment:** 5.2
- **Date:** 2026-10-30

**Decision.** Glossaries and categories (and from 5.2b terms) are entities of Atlas's glossary model (`0011-glossary_model`), as `DataAccess` and the glossary DTOs keep them: an object is saved by creating or updating its entity with `EntityWriter`, which also writes a category's mandatory `anchor`, and loaded back from the entity and its relationship attributes with `EntityRetriever`; the relationships between glossary objects (anchors, the category hierarchy, term categorizations) are written with the `RelationshipStore` as `GlossaryCategoryUtils` writes them, `getOrCreate` taking an existing relationship of the type and ends, and a removed one deleted for good. 5.2 is split by the user into 5.2a (glossaries and categories), 5.2b (terms) and 5.2c (term assignment); glossary import is a later increment.

**Reason.** Atlas's glossary is entities and relationships of internal types, read and written through its stores; the stores here already keep entities, relationships, unique qualified names and internal types' hard deletes as Atlas does, so the glossary's behaviour follows from them without a store of its own.

**Alternatives.** Glossary documents of their own index: simpler reads, but the glossary would no longer be entities the entity API, search and lineage see, as they are in Atlas.

**Consequences.** A glossary write is several entity and relationship writes, each all or nothing on its own, as in Atlas within its graph transaction only when the graph commits; a failure part way leaves what was written. The server's models carry `0011-glossary_model`, as they do with every model loaded.

### DD-247. Journal writes do not wait for a refresh

- **Status:** Proposed
- **Increment:** cross-cutting (no roadmap row; found by 5.2a's e2e)
- **Date:** 2026-10-30

**Decision.** The journal entry's write, its commit and its delete (DD-046) no longer carry `refresh="wait_for"`; the entity bulk, the restores and the audit append keep it (DD-237, ENS-11). Recovery lists the journal's entries by a search, as before, and acts on each as a real-time `get` by its write id reads it now: an entry already deleted, or still within its lease, is left alone. This supersedes DD-237's choice for the journal only; the rest of DD-237 stands.

**Reason.** On the dev store every entity write cost about 2.8 s: four writes each waiting for a refresh (about 1 s each with the default refresh interval), three of them the journal's. A glossary write is several entity and relationship writes, so creating a child category took 9 s and deleting a glossary 18 s, past the e2e client's timeout. DD-237 kept the journal's refresh for recovery, which "reads entries written moments before"; but recovery acts only on entries whose 60-second lease has passed, long after the index's own refresh has made them searchable, and the real-time `get` closes the remaining gap: a listing that lags an entry's commit or delete cannot make recovery undo a write that finished. With the change a write costs about 0.9 s on the dev store.

**Alternatives.** A shorter refresh interval: every write still pays for refreshes no reader needs. Trimming the glossary's writes: helps one feature, and departs from Atlas's sequence of writes.

**Consequences.** A journal entry may be missing from a search for up to the refresh interval after it is written; nothing but recovery searches it. ENS-11's text names the journal as unrefreshed.

### DD-248. An entity's meanings are read from its listed relationships

- **Status:** Proposed
- **Increment:** 5.2c
- **Date:** 2026-10-31

**Decision.** An entity header's `meanings` (GTA-05) are read from the relationships the entity lists (DD-061): those of type `AtlasGlossarySemanticAssignment` whose second end is the entity, in the order listed, with their terms read in one request. The relationships are read once per response, as the header's relationship attributes already read them. Basic search's `termName` and the DSL's `hasTerm` read the terms' listed relationships the same way and search the entities by GUID, as a DSL condition on referred entities does (DD-243).

**Reason.** Atlas reads the entity's incoming edges with the assignment's label. The listing is the one place an entity's relationships are known by real-time `get`s, so a header read right after an assignment shows it, as every other relationship attribute does.

**Alternatives.** A search of the relationship index by type and end: one request per page of headers, but it sees an assignment only after a refresh. A field of meanings on the entity document: every assignment would write the entity too.

**Consequences.** A header costs a read of all the entity's relationships, also for an entity with many and no meanings; a header that reads relationship attributes pays it once. A term assigned to more entities than one search window holds is not searched beyond it.

### DD-249. Uploaded files are read with python-multipart, openpyxl and xlrd

- **Status:** Proposed
- **Increment:** 5.2d
- **Date:** 2026-10-31

**Decision.** The server reads a multipart upload with `python-multipart`, which FastAPI's form parsing requires. The core reads an `xlsx` workbook with `openpyxl` (read-only, cached values) and an `xls` workbook with `xlrd` 2, which reads only that format; a CSV file with the standard library's `csv` module. All three are pure Python.

**Reason.** Atlas reads CSV with opencsv and both Excel formats with Apache POI. Python has no single library for both Excel formats: openpyxl reads only the XML format, xlrd 2 only the binary one, and each is the maintained reader of its format.

**Alternatives.** pandas: reads both, but through these same engines and with numpy behind it. Dropping `xls`: Atlas's clients may upload it, and its error message names it.

**Consequences.** Three new runtime dependencies, in the SBOM. A value is read as Python gives it; DV-104 records where that differs from Atlas.

### DD-250. The server authenticates requests itself against the identity provider

- **Status:** Proposed
- **Increment:** 6.1a
- **Date:** 2026-10-31

**Decision.** The server verifies every request's credentials itself, in a middleware, with the shared verifier `aurelius-atlas-auth` (DD-197): a bearer token is an RS256 JWT of the provider's key set, of its issuer, unexpired, whose `azp` or `aud` names the server's client or a configured further client (the webapp's, which the auxiliary APIs forward). A browser without a token signs in through the server's own confidential client, `aurelius-atlas-server`, by the authorization code flow with PKCE, and keeps a session cookie. A user's name is the `preferred_username` claim by default and their groups the configured groups claim, else the realm roles, as Atlas's provider with `groups_claim` set.

**Reason.** Atlas authenticates in-process with Keycloak's Spring Security adapter: bearer tokens for clients, a login redirect and session for its dashboards, which the server still serves. Verifying tokens in the server keeps one path for every client, needs no proxy in front of it, and reuses the verifier the auxiliary APIs already run. The adapter names a user by `sub` unless `principal-attribute` is set, which deployments set to `preferred_username`, the name people know; it is a setting here too.

**Alternatives.** An authenticating proxy (oauth2-proxy) in front of the server: a second component on every deployment, and the server would trust a header. Bearer tokens only: the vendored dashboards could not sign in. Exchanging `Basic` credentials at the provider, as the adapter can: the server would handle passwords (DV-108).

**Consequences.** The server needs the provider's URL, realm, its client's secret and the further audiences; every client sends a token. The dev realm gains the confidential client; the e2e suites mint tokens and sign the browser in.

### DD-251. Browser sessions are kept in the server's memory

- **Status:** Proposed
- **Increment:** 6.1a
- **Date:** 2026-10-31

**Decision.** A browser's session — its user, its tokens, a sign-in under way and its CSRF token — is kept in the server's memory under a random id in the `ATLASSESSIONID` cookie (`HttpOnly`, `Secure`, `SameSite=Lax`), renewed at sign-in, ended after 60 minutes unused or when the provider refuses to refresh its token. At most 10,000 sessions are kept, the least recently used dropped first.

**Reason.** Atlas keeps its sessions in Jetty's memory, with the same cookie and a 60-minute timeout. The session holds the tokens the server refreshes, so the browser never sees them.

**Alternatives.** A signed cookie holding the tokens: no server state, but the tokens leave the server and a signed-out cookie stays valid until it expires. Sessions in Elasticsearch: survive restarts and serve several instances, at a store round-trip per request.

**Consequences.** A restart signs browsers out; they sign in again at once while their provider session lasts. Several server instances need sticky sessions.
