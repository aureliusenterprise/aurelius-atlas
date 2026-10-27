# syntax=docker/dockerfile:1

# Use a hardened Python image with dev tools for the build stage.
FROM dhi.io/python:3.14-alpine3.24-dev AS build-image

WORKDIR /build

# The server's wheel, built by `nx build` with its workspace libraries bundled in.
COPY --chown=root:root --chmod=0755 apps/aurelius-atlas-server/dist/*.whl ./

# Install it with its dependencies, then drop the wheel.
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --only-binary :all: --target=./ ./*.whl && \
    rm ./*.whl

# The hardened runtime image has no shell or package manager.
FROM dhi.io/python:3.14-alpine3.24

ARG VERSION=local

LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="The Aurelius Atlas server: the Apache Atlas REST API on Elasticsearch."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Atlas Server"
LABEL org.opencontainers.image.version="${VERSION}"

# Listen on every interface, on the Apache Atlas port. The Elasticsearch settings have no defaults: the
# server does not start without them (SRV-01, SRV-02).
ENV AURELIUS_ATLAS_SERVER_HOST=0.0.0.0
ENV AURELIUS_ATLAS_SERVER_PORT=21000
# AURELIUS_ATLAS_SERVER_TLS_CA_FILE: CA bundle the healthcheck verifies the server's own certificate
# with when it serves HTTPS (local dev: /certs/ca.pem). Unset: the system trust store.
ENV AURELIUS_ATLAS_SERVER_TLS_CA_FILE=""
# Stable HTTP semantic conventions (DD-222): the OTel instrumentors read this at
# process start and emit only the stable http.*/url.*/server.* span attributes
# (no old http.url/net.peer.* set) and the stable http.server.request.duration
# metrics — matching the elasticsearch client's natively-stable spans, so one
# trace carries one convention. Bare OTEL_* name by the workspace env rule.
ENV OTEL_SEMCONV_STABILITY_OPT_IN=http

WORKDIR /application

COPY --chown=root:root --chmod=0755 --from=build-image /build ./

# The dashboards, built by `nx build aurelius-atlas-dashboard`: dashboardv2 at /, dashboardv3 at /n/ (DD-018).
COPY --chown=root:root --chmod=0755 apps/aurelius-atlas-dashboard/dist ./dashboard
ENV AURELIUS_ATLAS_SERVER_DASHBOARD_DIR=/application/dashboard

USER nonroot

EXPOSE 21000

# Liveness is the right probe for a restart decision: readiness also fails while Elasticsearch is away
# (DD-016).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,ssl,urllib.request; p=os.getenv('AURELIUS_ATLAS_SERVER_PORT','21000'); t=os.getenv('AURELIUS_ATLAS_SERVER_TLS_CERT_FILE',''); ca=os.getenv('AURELIUS_ATLAS_SERVER_TLS_CA_FILE',''); s=('https' if t else 'http')+'://localhost:'+p+'/api/atlas/admin/liveness'; c=(ssl.create_default_context(cafile=ca) if t and ca else ssl.create_default_context() if t else None); urllib.request.urlopen(s,timeout=5,context=c).close()"]

ENTRYPOINT [ "python", "-m", "aurelius_atlas_server" ]
