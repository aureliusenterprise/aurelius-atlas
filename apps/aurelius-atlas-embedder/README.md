# aurelius-atlas-embedder

The Aurelius Atlas embedder: text in, its embedding out. It serves the multilingual model
`intfloat/multilingual-e5-small` on the CPU, so a search can find entities by what their names and
descriptions mean, in English or Dutch ([ADR
059](../../docs/architecture/adr/059-the-catalogue-searches-by-meaning-with-a-model-that-runs-on-site.md)).

Introduced by increment 11.2 ([spec](specs/11-2-embedder/spec.md), [design](specs/11-2-embedder/design.md)).
Nothing calls it yet: the server's embedding of entities is 11.3.

## Endpoints

The request and answer follow OpenAI's embeddings API, so another server that speaks it can stand in (DD-430).

| Endpoint              | Answers                                                                                                  |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| `POST /v1/embeddings` | `200` one 384-dimension embedding of length 1 per text, in order; `422` or `404` in OpenAI's error shape |
| `GET /v1/models`      | `200` the model, its dimensions and its pinned revision                                                  |
| `GET /liveness`       | `204` while the process runs                                                                             |
| `GET /readiness`      | `204` once the model has loaded (the image's healthcheck), `503` before                                  |

A request takes `input` (a text, or 1 to 256 texts of up to 32,000 characters), `model` (optional, the served
one), `encoding_format` (`float` only) and `input_type`, which OpenAI's API lacks: `passage` (the default) for
the texts to find, `query` for a search. The model was trained with those prefixes, and the embedder adds
them.

```bash
curl --cacert certs/ca.pem https://localhost:21004/v1/embeddings \
    -H 'Content-Type: application/json' \
    -d '{"input": ["klantadres en woonplaats"], "input_type": "passage"}'
```

The embedder checks no tokens (DD-432): run it only on a closed network, as the standalone stack does.

## Run

```bash
npx nx docker-build aurelius-atlas-embedder   # fetches the model at its pinned revision, checks its SHA-256
npx nx test aurelius-atlas-embedder -c ci     # a fake model: no ONNX Runtime, no download
npx nx e2e aurelius-atlas-embedder            # the image with its real model, over TLS
```

`npx nx serve aurelius-atlas-embedder` runs it from the checkout on `https://localhost:21004`; it needs
`AURELIUS_ATLAS_EMBEDDER_MODEL_DIR`, a directory with the model's `model.onnx` and `tokenizer.json`, and
Python 3.14, since ONNX Runtime has no wheels for 3.15 yet (DD-433).

## Settings

| Variable                                                 | Default                                    | What it sets                          |
| -------------------------------------------------------- | ------------------------------------------ | ------------------------------------- |
| `AURELIUS_ATLAS_EMBEDDER_MODEL_DIR`                      | `/model` in the image                      | The model's directory; never fetched  |
| `AURELIUS_ATLAS_EMBEDDER_MODEL_ID`                       | `intfloat/multilingual-e5-small`           | The id a request's `model` must match |
| `AURELIUS_ATLAS_EMBEDDER_MODEL_REVISION`                 | `614241f622f53c4eeff9890bdc4f31cfecc418b3` | The revision `/v1/models` reports     |
| `AURELIUS_ATLAS_EMBEDDER_MAX_TOKENS`                     | `512`                                      | Tokens a text is cut at               |
| `AURELIUS_ATLAS_EMBEDDER_THREADS`                        | `0`: ONNX Runtime chooses                  | Threads per inference                 |
| `AURELIUS_ATLAS_EMBEDDER_TLS_CERT_FILE`, `_TLS_KEY_FILE` | unset: plain HTTP                          | The certificate pair to serve HTTPS   |
| `AURELIUS_ATLAS_EMBEDDER_HOST`, `_PORT`, `_LOG_LEVEL`    | `localhost`, `21004`, `info`               | Where it listens, and its logging     |

The image takes about 800 MB of memory once the model has loaded, and embeds 64 short texts in about 0.2 s.
