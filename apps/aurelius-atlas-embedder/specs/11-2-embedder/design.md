# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-429. The model is `intfloat/multilingual-e5-small`, run with ONNX Runtime

- **Status:** Proposed
- **Increment:** 11.2
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The embedder serves `intfloat/multilingual-e5-small` (MIT, 384 dimensions, 94 languages with
English and Dutch) from its ONNX export, with ONNX Runtime on the CPU and the model's own tokenizer through
`tokenizers`. The app does the mean pooling and the scaling to length 1 itself, in NumPy.

**Reason.** The catalogue is searched in English and Dutch, so the model must be multilingual. At 384
dimensions a vector of 100,000 entities takes about 40 MB quantised in the store, and the model embeds 64
texts in 0.18 s on one machine's CPU (measured in the image). Running the ONNX export directly keeps the
runtime to three libraries, with no deep-learning framework; the pooling is a few lines.

**Alternatives.**

- `BAAI/bge-m3` or `intfloat/multilingual-e5-large`: better results, 1,024 dimensions, about 2 GB of memory
  and several times slower on a CPU.
- `paraphrase-multilingual-MiniLM-L12-v2`: as small, but trained for sentence similarity rather than
  retrieval.
- `fastembed`: a library around the same runtime, but it does not list this model, and adds its own
  dependencies.
- Sentence Transformers on PyTorch: the reference implementation, and a runtime ten times the size.

**Consequences.** The image holds the 470 MB model. ONNX Runtime has wheels for Python 3.11 to 3.14 on glibc
only, which DD-431 and DD-433 follow from.

### DD-430. The embedder speaks OpenAI's embeddings API, with `input_type`

- **Status:** Proposed
- **Increment:** 11.2
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** `POST /v1/embeddings` and `GET /v1/models` take and answer the shapes of OpenAI's API. One field
is added: `input_type`, `passage` or `query`, from which the embedder sets the prefix the model was trained
with.

**Reason.** The server's client (11.3) is then a client of a common API: a hosted model, a GPU server or
another OpenAI-compatible embedding server can stand in by configuration (ADR 059, R5). The prefix is the
model's convention, so the service that knows the model applies it; a caller states only what the text is.

**Alternatives.**

- Prefixes sent by the caller inside the text: every caller must know the model.
- An API of its own: no other server could stand in.

**Consequences.** A stand-in that ignores `input_type` embeds queries and passages alike; for e5 models the
caller then adds the prefixes itself.

### DD-431. The image is built on Debian, with the model fetched at build time and checked

- **Status:** Proposed
- **Increment:** 11.2
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The image is built on `dhi.io/python:3.14-debian13`, not the Alpine image of the other apps. Its
build stage fetches the model's files from Hugging Face at a pinned revision and checks each against a pinned
SHA-256; the runtime never downloads.

**Reason.** ONNX Runtime publishes no musl wheels, so it does not install on Alpine. A model fetched at
runtime would need network access from the installation and could change under the same name; a pinned
revision with checksums makes the image reproducible and the model the one reviewed.

**Alternatives.**

- The model downloaded on the first start, into a volume: network access at runtime, and a first start of
  minutes.
- The model committed to the repository: 470 MB in Git, through Git LFS.

**Consequences.** Building the image needs access to `huggingface.co`; the build cache keeps the files between
builds.

### DD-432. In the standalone stack the embedder is an internal service, without token authentication

- **Status:** Proposed
- **Increment:** 11.2
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The embedder serves TLS with its own certificate and checks no tokens. In the standalone stack
it has no published port: only services on the stack's network reach it. Token authentication, OTLP export and
network policy come with its Helm chart.

**Reason.** Its only caller will be the server, which today has no service account in the realms to mint a
token with; giving it one changes the dev, demo and production realms, which is the chart increment's work.
The embedder stores nothing and answers only with vectors of the text it is sent, so on a closed network the
risk is its CPU, not data.

**Alternatives.**

- The shared `aurelius-atlas-auth` verifier now, with a service account for the server in every realm: right
  for a cluster, more than this increment.
- No TLS on the stack network: the other services of the stack speak TLS to each other.

**Consequences.** The embedder must not be published or exposed outside a stack's network until it checks
tokens.

### DD-433. ONNX Runtime only where it has wheels; the unit tests need neither it nor the model

- **Status:** Proposed
- **Increment:** 11.2
- **Date:** 2026-11-09
- **Supersedes:** none

**Decision.** The app depends on `onnxruntime` with the marker `python_version < "3.15"`, and imports it only
when it loads the model. The model sits behind a small protocol; the unit tests give the app a fake session
and tokenizer, and the e2e tests run the image with the real model.

**Reason.** The workspace allows Python 3.14 and later, and `uv` resolves local environments to 3.15, for
which ONNX Runtime has no wheel; an unconditional dependency would break `uv sync` for the whole workspace. CI
and the image run 3.14. The unit tests stay fast and need no 470 MB download.

**Alternatives.**

- The embedder outside the `uv` workspace, with its own lock: its own tooling for lint, types and tests.
- Pinning the workspace to Python 3.14: a change for every project, for one dependency.

**Consequences.** On Python 3.15 the app installs but cannot load a model; it says so at start. The marker
goes when ONNX Runtime publishes 3.15 wheels.
