# syntax=docker/dockerfile:1

# Use a hardened Python image with dev tools for the build stage.
FROM dhi.io/python:3.14-alpine3.24-dev AS build-image

WORKDIR /build

# The app's wheel, built by `nx build` with its workspace libraries bundled in.
COPY --chown=root:root --chmod=0755 apps/aurelius-atlas-validate-entity/dist/*.whl ./

# Install it with its dependencies, then drop the wheel.
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --only-binary :all: --target=./ ./*.whl && \
    rm ./*.whl

# The hardened runtime image has no shell or package manager.
FROM dhi.io/python:3.14-alpine3.24

ARG VERSION=local

LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="The Aurelius Atlas validate-entity API: an entity in, the fixed governance-quality mock out."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Atlas validate-entity"
LABEL org.opencontainers.image.version="${VERSION}"

# Listen on every interface, on the app's port (21003, the third auxiliary API).
ENV AURELIUS_ATLAS_VALIDATE_ENTITY_HOST=0.0.0.0
ENV AURELIUS_ATLAS_VALIDATE_ENTITY_PORT=21003
ENV AURELIUS_ATLAS_VALIDATE_ENTITY_TLS_CA_FILE=""

WORKDIR /application

COPY --chown=root:root --chmod=0755 --from=build-image /build ./

USER nonroot

EXPOSE 21003

# Liveness is the right probe for a restart decision; the app is stateless.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,ssl,urllib.request; p=os.getenv('AURELIUS_ATLAS_VALIDATE_ENTITY_PORT','21003'); t=os.getenv('AURELIUS_ATLAS_VALIDATE_ENTITY_TLS_CERT_FILE',''); ca=os.getenv('AURELIUS_ATLAS_VALIDATE_ENTITY_TLS_CA_FILE',''); s=('https' if t else 'http')+'://localhost:'+p+'/liveness'; c=(ssl.create_default_context(cafile=ca) if t and ca else ssl.create_default_context() if t else None); urllib.request.urlopen(s,timeout=5,context=c).close()"]

ENTRYPOINT [ "python", "-m", "aurelius_atlas_validate_entity" ]
