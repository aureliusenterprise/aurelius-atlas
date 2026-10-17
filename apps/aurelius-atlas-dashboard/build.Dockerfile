# syntax=docker/dockerfile:1

# Builds the vendored Apache Atlas dashboards as Atlas's Maven build does (`grunt build-minify`), in a
# hardened Node 24 image (DD-017). Only the static files leave it:
#   docker buildx build . -f apps/aurelius-atlas-dashboard/build.Dockerfile --output type=local,dest=<dir>
# writes dashboardv2 to <dir>/ and dashboardv3 to <dir>/n/, the layout of Atlas's web application.
# Not named `Dockerfile`, so the Nx Docker plugin does not treat it as an image to publish.

FROM dhi.io/node:24-alpine3.24-dev AS build

WORKDIR /build

# Dependencies first, so a change to the sources reuses the installed packages.
COPY apps/aurelius-atlas-dashboard/dashboardv2/package.json apps/aurelius-atlas-dashboard/dashboardv2/package-lock.json v2/
COPY apps/aurelius-atlas-dashboard/dashboardv3/package.json apps/aurelius-atlas-dashboard/dashboardv3/package-lock.json v3/
RUN --mount=type=cache,target=/root/.npm \
    (cd v2 && npm ci --no-audit --no-fund) && \
    (cd v3 && npm ci --no-audit --no-fund)

COPY apps/aurelius-atlas-dashboard/dashboardv2/gruntfile.js v2/
COPY apps/aurelius-atlas-dashboard/dashboardv2/public v2/public
COPY apps/aurelius-atlas-dashboard/dashboardv3/gruntfile.js v3/
COPY apps/aurelius-atlas-dashboard/dashboardv3/public v3/public
RUN (cd v2 && npx grunt build-minify) && \
    (cd v3 && npx grunt build-minify)

FROM scratch AS dist

COPY --from=build /build/v2/dist/ /
COPY --from=build /build/v3/dist/n/ /n/
