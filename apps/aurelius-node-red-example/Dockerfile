# syntax=docker/dockerfile:1

# Use a hardened base image with Node.js and build tools for the builder stage.
FROM dhi.io/node:24-alpine3.24-dev AS builder

# Install required build dependencies, using cache mounts to speed up the process
RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add --no-cache python3

# Set the working directory
WORKDIR /build

# Copy settings file into the container
COPY apps/aurelius-node-red-example/settings.prod.js ./settings.js

# Copy application files into the container
COPY apps/aurelius-node-red-example/package.json \
    apps/aurelius-node-red-example/flows.json \
    package-lock.json \
    ./

# Install Node-RED and dependencies, using a cache mount to speed up the process
RUN --mount=type=cache,mode=0755,target=/root/.npm \
    npm ci --ignore-scripts && \
    rm package-lock.json

# Replace vulnerable libraries bundled inside the npm package itself.
# npm vendors these in its bundle and pins them, and every npm release up to
# 12.2.0 still ships the vulnerable copies, so they are unreachable through
# package.json overrides. Patch-level drop-ins only: the replacement deps
# (balanced-match, cssesc, util-deprecate) are already satisfied by copies
# inside the same npm bundle.
RUN --mount=type=cache,mode=0755,target=/root/.npm \
    set -eux; \
    for pkg in undici@6.28.1 ip-address@10.7.1 brace-expansion@5.0.12 postcss-selector-parser@7.1.6; do \
    name="${pkg%@*}"; \
    npm pack --silent --pack-destination /tmp "${pkg}"; \
    rm -rf "node_modules/npm/node_modules/${name}"; \
    mkdir -p "node_modules/npm/node_modules/${name}"; \
    tar -xzf /tmp/"${name}"-*.tgz --strip-components=1 --no-same-owner \
    -C "node_modules/npm/node_modules/${name}"; \
    done; \
    rm -f /tmp/*.tgz

# Use a hardened runtime image for the final image.
# Note that the runtime image does not include a shell or package manager.
FROM dhi.io/node:24-alpine3.24 AS runtime

ARG VERSION=local

# Add image metadata
LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="This is an example Node-RED application."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Node-RED Example"
LABEL org.opencontainers.image.version="${VERSION}"

# Expose the default Node-RED port
EXPOSE 1880

# Switch to the non-root user
USER node

# Set working directory to the copied application
WORKDIR /home/node/app

# Copy the built app from the builder stage
COPY --chown=root:root --chmod=0755 --from=builder /build/ ./

# Run the application
CMD [ "./node_modules/.bin/node-red", "-u", "/home/node/app" ]
