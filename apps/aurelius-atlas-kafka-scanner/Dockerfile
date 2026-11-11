# syntax=docker/dockerfile:1

# Use a hardened Python image with dev tools for the build stage.
FROM dhi.io/python:3.14-alpine3.24-dev AS build-image

WORKDIR /build

# The app's wheel, built by `nx build` with its workspace libraries bundled in.
COPY --chown=root:root --chmod=0755 apps/aurelius-atlas-kafka-scanner/dist/*.whl ./

# Install it with its dependencies, then drop the wheel.
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --only-binary :all: --target=./ ./*.whl && \
    rm ./*.whl

# The hardened runtime image has no shell or package manager.
FROM dhi.io/python:3.14-alpine3.24

ARG VERSION=local

LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="The Aurelius Atlas Kafka cluster scanner: one batch scan of a Kafka cluster's topics and schemas into the catalogue as a system, collection, datasets, and fields."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Atlas Kafka cluster scanner"
LABEL org.opencontainers.image.version="${VERSION}"

# Stable HTTP semantic conventions (DD-222): the OTel instrumentors read this at
# process start; the httpx spans carry only the stable http.*/url.* set.
ENV OTEL_SEMCONV_STABILITY_OPT_IN=http

WORKDIR /application

COPY --chown=root:root --chmod=0755 --from=build-image /build ./

USER nonroot

# A batch job, not a service: no port to publish and no liveness to probe. The
# scheduler (the 13.2 CronJob) owns when it runs; one run scans, writes, exits.
ENTRYPOINT [ "python", "-m", "aurelius_atlas_kafka_scanner" ]
