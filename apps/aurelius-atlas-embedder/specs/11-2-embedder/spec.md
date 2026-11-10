# 11.2 The embedding service

- **Status:** done
- **Pull request:** [#303](https://github.com/aureliusenterprise/aurelius-atlas/pull/303)
- **Records:** ADR 059 (Proposed); DD-429 to DD-433; relies on ADR 047, ADR 051, ADR 056, DD-366 (the demo
  realm's stack)

The first increment of search by meaning (ADR 059): a service that turns text into embeddings with the model
`intfloat/multilingual-e5-small`, run on the CPU inside the image, and its place in the standalone stack.
Nothing calls it yet; the server's embedding of entities follows in 11.3.

## Scope

A new application, `apps/aurelius-atlas-embedder`, on port 21004:

- `POST /v1/embeddings`, in the shape of OpenAI's embeddings API, so any service that speaks it (a hosted
  model, a GPU server) can stand in for it (DD-430);
- `GET /v1/models`, the model it serves and its number of dimensions;
- `GET /liveness` and `GET /readiness`;
- its image, with the model's files fetched at build time from a pinned revision and checked by SHA-256
  (DD-431);
- the service `embedder` in the standalone stack (`apps/aurelius-atlas-server/standalone/`), reachable only on
  the stack's network (DD-432).

Not in scope: the server's client, the vectors on the entities and their indexer (11.3); the search endpoints
(11.4); the webapp (11.5); the dev stack, the Helm chart, OTLP export and token authentication of the embedder
(with the chart, DD-432).

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EMB-01 | `POST /v1/embeddings` takes `input`, a text or a list of 1 to 256 texts; `model`, optional, the served model's id; `encoding_format`, optional, only `float`; and `input_type`, optional, `passage` (the default) or `query`. It answers 200 with one embedding per text, in the order sent |
| EMB-02 | The answer is `{"object": "list", "data": [{"object": "embedding", "index": i, "embedding": [...]}], "model": id, "usage": {"prompt_tokens": n, "total_tokens": n}}`, where `n` counts the tokens the model read, after truncation                                                          |
| EMB-03 | An embedding is the model's last hidden state, mean-pooled over the text's tokens and scaled to length 1: 384 floats. The text is prefixed `passage:` or `query:` and a space, by its `input_type`, as the model was trained, and cut at 512 tokens                                         |
| EMB-04 | A text's embedding does not depend on the other texts in its request                                                                                                                                                                                                                        |
| EMB-05 | A request with no text, more than 256 texts, an empty text, a text of more than 32,000 characters, or an `encoding_format` other than `float` answers 422; a `model` other than the served one answers 404. Both in OpenAI's error shape: `{"error": {"message", "type", "param", "code"}}` |
| EMB-06 | `GET /v1/models` answers `{"object": "list", "data": [{"id", "object": "model", "owned_by": "aurelius-atlas", "dimensions": 384, "revision"}]}`: the served model, its dimensions and its pinned revision                                                                                   |
| EMB-07 | The model loads, and embeds a warm-up text, before the app accepts a connection. `GET /liveness` answers 204 while the process runs; `GET /readiness` answers 204 once the model has loaded, 503 before, as `/v1/embeddings` and `/v1/models` do. None needs credentials                    |
| EMB-08 | The app reads its model from a directory (`AURELIUS_ATLAS_EMBEDDER_MODEL_DIR`) and never fetches it at runtime; it does not start when the directory lacks the model or the tokenizer                                                                                                       |
| EMB-09 | The settings carry the prefix `AURELIUS_ATLAS_EMBEDDER_`: host, port (21004), log level, the TLS pair, the model directory, the model id and revision, and the inference threads                                                                                                            |
| EMB-10 | The image fetches `onnx/model.onnx`, `onnx/tokenizer.json` and the model card of `intfloat/multilingual-e5-small` at revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, and fails its build when a file's SHA-256 differs from the pinned one                                             |
| EMB-11 | The standalone stack runs the embedder on its network with no published port, over TLS with the embedder's own certificate; the stack's other services do not wait for it                                                                                                                   |

## Aurelius origin

None: a new capability (ADR 059). The request and answer follow OpenAI's embeddings API
(`https://platform.openai.com/docs/api-reference/embeddings`); `input_type` is an extension of it, as other
OpenAI-compatible embedding servers have one. The pooling and prefixes follow the model card of
`intfloat/multilingual-e5-small`.

## Deviations

None against Apache Atlas: the embedder is not part of its API.

## Acceptance

- `apps/aurelius-atlas-embedder/tests/`: EMB-01 to EMB-09 on a fake model session, so they run without the
  model or ONNX Runtime (DD-433).
- `apps/aurelius-atlas-embedder/e2e/`: the image with its real model: EMB-01 to EMB-07 and EMB-10 over TLS,
  and the check that a query ranks texts of its meaning, also in Dutch, above an unrelated one.
- `tests/test__standalone_embedder.py`: EMB-11, read from the standalone compose file.
