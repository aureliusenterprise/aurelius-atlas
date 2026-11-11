# 060. The App Search API returns, as a view over the one store

- **Status:** Accepted
- **Date:** 2026-11-10
- **Deciders:** Aurelius Enterprise

## Decision

Aurelius Atlas answers the search API the original Aurelius Atlas webapp called: App Search's
`POST /api/as/v1/engines/{engine}/search` for its three engines, the entity documents (`/elastic`), the data
quality results (`/data_quality`) and the governance quality results (`/gov_quality`), with the same requests
answered with the same results. The original webapp runs against Aurelius Atlas unchanged.

The answers are a view over the one store ([ADR 047](./047-one-search-store-is-the-system-of-record.md)): what
App Search held, the denormalised entity documents and the quality results, is kept on the entity documents
themselves and brought up to date by tasks of the server when entities change. There is no Enterprise Search,
no Kafka and no Flink: the legacy pipeline that fed App Search becomes those tasks.

This supersedes the part of [ADR 054](./054-the-server-api-is-the-webapps-one-data-plane.md) that retired the
App Search surface and did not port it. The rest of ADR 054 stands: the webapp of this repository keeps the
server's API as its one data plane, and the restored API is one more endpoint family of that server.

## Context

The original Aurelius Atlas webapp searches App Search directly: its search page, its facets, its entity
cards and their quality badges read the App Search engines, which a pipeline of Flink jobs filled from Apache
Atlas's notifications on Kafka. Aurelius Atlas replaced the catalogue behind it with one store and its own
search, and its rewritten webapp no longer needs App Search. The original webapp is still in use, and moving
its users to the rewritten one is not a step every installation can take at once.

Enterprise Search's App Search is deprecated by Elastic and is a separate product to run, license and keep in
step with the catalogue. The pipeline that kept it in step needed Kafka, Flink and their operation, and its
copies of the catalogue could drift from it.

## Requirements

- R1: The original webapp's search, facets, cards and quality views work against Aurelius Atlas, unchanged.
- R2: The same requests answer with the same documents, fields and facets as the legacy pipeline produced for
  the same catalogue.
- R3: One system of record: no second store of the catalogue to keep in step (ADR 047).
- R4: No Enterprise Search, no Kafka and no Flink to run.
- R5: A change in the catalogue reaches the search answers without an operator's step.
- R6: Apache Atlas's own API behaves exactly as before (ADR 046).

## Alternatives

- **Keep Enterprise Search and the Flink pipeline beside Aurelius Atlas.** Meets R1 and R2, fails R3 and R4: two
  products and a pipeline to run, and a copy of the catalogue that can drift.
- **Move every user to the rewritten webapp first (do nothing).** Fails R1 for the installations that cannot
  move yet.
- **A separate index for the App Search documents.** Meets R1, R2 and R4, but splits each entity over two
  documents to keep in step, against R3.
- **Answer the App Search requests from Atlas's search on the fly.** Meets R3 and R4, but breadcrumbs, derived
  relations and quality scores would be computed per request from many reads, too slow for a search page, and
  facets over them impossible; it puts R2 at risk.

## Tradeoffs

- **Positive:** the original webapp keeps working; Enterprise Search, Kafka and Flink are gone; the search
  answers come from the one store and cannot drift from it; the derived documents also feed the search by
  meaning (ADR 059).
- **Negative:** a second search API to keep, with App Search's query language and answer shape; the entity
  documents grow by their derived fields and quality results; a change reaches the derived documents of the
  entities it affects a moment after it is written.
- **Neutral / follow-ups:** the series 14 increments specify the derived documents, their tasks, the API and the
  quality results; the other legacy services behind the original reverse proxy (the lineage REST API, the data
  governance dashboard, the consistency metrics, `/compare`, `/repository`, `/users`) stay as they are for now.
