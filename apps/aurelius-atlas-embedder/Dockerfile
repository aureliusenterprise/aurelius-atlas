# syntax=docker/dockerfile:1

# Debian, not the Alpine of the other apps: ONNX Runtime publishes no musl wheels (DD-431).
FROM dhi.io/python:3.14-debian13-dev AS build-image

WORKDIR /build

# The app's wheel, built by `nx build`.
COPY --chown=root:root --chmod=0755 apps/aurelius-atlas-embedder/dist/*.whl ./

# Install it with its dependencies, then drop the wheel.
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --only-binary :all: --target=./ ./*.whl && \
    rm ./*.whl

# The model's files at a pinned revision, each checked by its SHA-256: a different file fails the build (EMB-10,
# DD-431). The model card carries the model's MIT licence.
FROM scratch AS model
ARG MODEL_URL=https://huggingface.co/intfloat/multilingual-e5-small/resolve/614241f622f53c4eeff9890bdc4f31cfecc418b3
ADD --checksum=sha256:ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665 \
    ${MODEL_URL}/onnx/model.onnx /model/model.onnx
ADD --checksum=sha256:0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39 \
    ${MODEL_URL}/onnx/tokenizer.json /model/tokenizer.json
ADD --checksum=sha256:0038de97aee16258cecbad7ffda4b4febd6953e747a00e0ddbc8e6ed241e9c1c \
    ${MODEL_URL}/README.md /model/MODEL_CARD.md

# The hardened runtime image has no shell or package manager.
FROM dhi.io/python:3.14-debian13

ARG VERSION=local

LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="The Aurelius Atlas embedder: text in, its embedding out, with a multilingual model on the CPU."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Atlas embedder"
LABEL org.opencontainers.image.version="${VERSION}"

# Listen on every interface, on the app's port; the model is the one in the image (EMB-08).
ENV AURELIUS_ATLAS_EMBEDDER_HOST=0.0.0.0
ENV AURELIUS_ATLAS_EMBEDDER_PORT=21004
ENV AURELIUS_ATLAS_EMBEDDER_MODEL_DIR=/model
ENV AURELIUS_ATLAS_EMBEDDER_TLS_CA_FILE=""

WORKDIR /application

COPY --chown=root:root --chmod=0755 --from=build-image /build ./
# 0755, not 0644: BuildKit 0.34 applies --chmod to the directory too, and nonroot must be able to enter it.
COPY --chown=root:root --chmod=0755 --from=model /model /model

USER nonroot

EXPOSE 21004

# Healthy once the model has loaded (EMB-07): what a service that calls the embedder waits for.
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import os,ssl,urllib.request; p=os.getenv('AURELIUS_ATLAS_EMBEDDER_PORT','21004'); t=os.getenv('AURELIUS_ATLAS_EMBEDDER_TLS_CERT_FILE',''); ca=os.getenv('AURELIUS_ATLAS_EMBEDDER_TLS_CA_FILE',''); s=('https' if t else 'http')+'://localhost:'+p+'/readiness'; c=(ssl.create_default_context(cafile=ca) if t and ca else ssl.create_default_context() if t else None); urllib.request.urlopen(s,timeout=5,context=c).close()"]

ENTRYPOINT [ "python", "-m", "aurelius_atlas_embedder" ]
