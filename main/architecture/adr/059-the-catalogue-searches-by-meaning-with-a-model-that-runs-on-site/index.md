# 059\. The catalogue searches by meaning, with a model that runs on site

- **Status:** Proposed
- **Date:** 2026-11-09
- **Deciders:** Aurelius Enterprise

## Decision

Aurelius Atlas finds entities by what their names and descriptions mean, not only by the words they contain: a search for "customer address" also finds a dataset described as "client location data", in English or Dutch. Each entity gets an embedding, a vector computed by a language model from its type, names, description and classifications, kept with the entity in the one store ([ADR 047](<https://aureliusenterprise.github.io/main/architecture/adr/047-one-search-store-is-the-system-of-record/index.md>)). The model runs inside the installation, so no catalogue metadata leaves it.

The searches by meaning are Aurelius endpoints of their own. Apache Atlas's API stays exactly as it is ([ADR 046](<https://aureliusenterprise.github.io/main/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)).

## Context

A data catalogue is searched by people who do not know the words its owners used. Today a search finds an entity only when the query's words, or their stems, appear in it. Users of the catalogue search in English and Dutch, while names and descriptions are written in either. The same capability is the base of a chat on the catalogue: answering a question starts by finding the entities it is about.

Catalogue metadata describes an organisation's systems and data, and some customers may not send it outside their installation. Language models that compute embeddings are available both as hosted services and as open models small enough to run on an ordinary server's CPU.

## Requirements

- R1: A search finds entities whose names and descriptions match the query's meaning, also across English and Dutch.
- R2: The searches keep the filters and counts users have today: type, state, owner and the facets.
- R3: No catalogue metadata leaves the installation unless an operator chooses a hosted model.
- R4: Apache Atlas's API behaves exactly as before; existing clients see no change.
- R5: A model can be replaced without changing the catalogue's API, by re-computing the embeddings.
- R6: An installation without the model runs as today.

## Alternatives

- **Keyword search only (do nothing).** Fails R1: a search finds only the words it contains.
- **Synonym lists maintained by hand.** Partly meets R1 for the terms someone thought of, in one language at a time, and needs constant upkeep; it fails R1 across languages.
- **A hosted embedding service as the default.** Meets R1, R2, R4 and R5, but fails R3: every entity's metadata and every query is sent to a third party. It stays possible as an operator's choice.
- **A separate vector database beside the store.** Meets R1 and R3, but splits each entity over two stores, so the filters and access rules must be kept in step in both, against ADR 047; it puts R2 at risk.
- **Search by meaning through Apache Atlas's own search endpoints.** Meets R1, but changes what existing endpoints return, against R4.

## Tradeoffs

- **Positive:** users find entities by meaning and across English and Dutch; the same embeddings serve a later chat on the catalogue; metadata stays on site; Apache Atlas's API is unchanged.
- **Negative:** an installation runs one more service, which needs CPU and about 1 GB of memory; every change to an entity is followed by a re-computation of its embedding, so a search by meaning sees a change a moment later than a keyword search; a new model means re-computing every embedding.
- **Neutral / follow-ups:** the endpoints, the embedded text and the model are specified increment by increment, from 11.2; the chat needs a record of its own; the Helm chart and the webapp follow the standalone stack.
