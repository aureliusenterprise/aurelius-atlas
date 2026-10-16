# syntax=docker/dockerfile:1

# Use a hardened Python image with dev tools for the build stage.
FROM dhi.io/python:3.14-alpine3.24-dev AS build-image

# Set the working directory
WORKDIR /build

# Copy the wheel file into the container. Make sure the command points to the correct path.
COPY --chown=root:root --chmod=0755 apps/aurelius-fastapi-example/dist/*.whl .

# Install package dependencies, then clean up. Use a cache mount to speed up the process.
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --only-binary :all: --target=./ ./*.whl && \
    rm ./*.whl

# Use a hardened Python image for the final application image.
# Note: the hardened image does not include a shell or package manager.
FROM dhi.io/python:3.14-alpine3.24

ARG VERSION=local

# Add image metadata
LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="This is an example FastAPI application."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius FastAPI Example"
LABEL org.opencontainers.image.version="${VERSION}"

# Set default values for the environment variables (AURELIUS_FASTAPI_ prefix:
# matches Settings.env_prefix; bare names belong to other projects).
ENV AURELIUS_FASTAPI_HOST=0.0.0.0
ENV AURELIUS_FASTAPI_PORT=8000
# AURELIUS_FASTAPI_TLS_CA_FILE: PEM CA bundle the healthcheck uses to verify the
# server when TLS is enabled (local dev: /certs/ca.pem, mounted read-only).
# Leave it unset for deployments whose certificate chains to the image's system
# trust store.
ENV AURELIUS_FASTAPI_TLS_CA_FILE=""

# Set the working directory
WORKDIR /application

# Copy in the built dependencies
COPY --chown=root:root --chmod=0755 --from=build-image /build ./

# Switch to the non-root user (built into the base image)
USER nonroot

# Configure a healthcheck to ensure the application is running
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os,ssl,urllib.request; p=os.getenv('AURELIUS_FASTAPI_PORT','8000'); t=os.getenv('AURELIUS_FASTAPI_TLS_CERT_FILE',''); ca=os.getenv('AURELIUS_FASTAPI_TLS_CA_FILE',''); s=('https' if t else 'http')+'://localhost:'+p+'/health/ready'; c=(ssl.create_default_context(cafile=ca) if t and ca else ssl.create_default_context() if t else None); urllib.request.urlopen(s,timeout=5,context=c).close()"]

# Start the application
ENTRYPOINT [ "python", "-m", "aurelius_fastapi_example" ]
