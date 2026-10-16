# syntax=docker/dockerfile:1

# Derived OpenMetadata server image: the hardened upstream plus the
# OpenTelemetry Java agent baked in.
#
# Why the image exists at all: OpenMetadata exposes no Prometheus-scrapeable
# metrics (admin-port /metrics and /metrics/prometheus both serve Dropwizard
# JSON), so JVM/HTTP/JDBC telemetry comes from runtime instrumentation (see
# AGENTS.md "Wiring Checklist"). Baking the agent into the image, rather than
# bind-mounting a host-downloaded jar, keeps `docker compose up`
# self-contained and puts the jar into the image SBOM where the
# docker-sbom/license/vulnerability targets can see it — bind mounts are
# invisible to image scanning.
#
# Why a single stage: a `-dev` builder tag buys nothing here — the DHI dev
# variant of this image ships no curl/wget/python (verified against
# 2.0.4-debian13-dev), so fetching would mean installing tools first.
# BuildKit's ADD downloads the asset itself and --checksum verifies it
# against the release's published SHA-256, so the runtime base is also the
# build stage. Same ADD pattern as the jdbc-sink connector's Dockerfile.
#
# Bumping: OM_VERSION is resolved by the project's docker-build target from
# dev/governance/.env (OPENMETADATA_VERSION — single source of truth; the ARG
# default below serves only standalone `docker build` runs). The agent version
# in the URL and the --checksum must change together, from the release's
# checksums.txt:
# https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases
ARG OM_VERSION=2.0.4

FROM dhi.io/openmetadata:${OM_VERSION}-debian13

# Read-only at runtime; the server enables it via JAVA_TOOL_OPTIONS in
# docker-compose.yaml (the image itself ships no agent config, so it stays
# usable without telemetry — compose decides).
#
# The mkdir is not cosmetic: BuildKit auto-creates an ADD target's missing
# parent with the raw --chmod mode (0644 — no execute bit, verified), and the
# base image runs as uid 1000, which cannot traverse such a directory ("Error
# opening zip file or JAR manifest missing" at JVM startup). Create /otel
# with a proper directory mode as root — numeric 0:0, the DHI image has no
# "root" passwd entry (same quirk as elasticsearch-init in the compose) —
# then restore the base image's non-root user so the container keeps
# running unprivileged.
USER 0:0
RUN mkdir --mode=0755 -p /otel
ADD --chown=0:0 --chmod=0644 \
    --checksum=sha256:f787eb6c7f3d18e69a431e108a15278d25ee37f83d68b678f621e063f3988f82 \
    https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v2.32.0/opentelemetry-javaagent.jar \
    /otel/opentelemetry-javaagent.jar
USER 1000
