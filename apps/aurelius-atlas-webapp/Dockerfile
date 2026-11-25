# syntax=docker/dockerfile:1
# The OTel module must be compiled against this exact nginx (the module
# signature is feature-flag checked at dlopen, and the .so links musl), so
# the builder rides the -dev variant of the same tag: it is the hardened
# image plus apk and the distro's build tree (DD-239). The runtime stage is
# the hardened image proper.
FROM dhi.io/nginx:1.30-alpine3.24 AS runtime-base

FROM dhi.io/nginx:1.30-alpine3.24-dev AS otel-builder

# The python-3.14 pin is apk arithmetic, not taste: the image's xcb-proto is
# resolved against 3.14 and bare `python` now means 3.15, which breaks it.
# nginx-stable-mod-dev ships the source kit the running binary was built
# from (/usr/src/nginx-<version>), pinned (~) to that binary's version: apk's
# newest kit can run ahead of the image, and a dhi patch bump can reach the
# image before its kit does, which then fails at the test -d below. The rest
# is the nginx-otel build recipe. The cache
# mount carries apk's index + package tarballs across builds (plain `apk add`,
# not --no-cache: the flag is what discards them; a cold pass is ~300 MB of
# downloads).
# !python3-ndbm: python-3.14 (the base image ships r4) pulls python3-ndbm as a
# dependency, and the only build in v3.24/main is r2, which re-ships the _dbm
# extension r4 already owns — apk aborts on the file collision (dhi repushed
# the tag with r4 past alpine's split package). Excluding it keeps the base
# image's working module: `import dbm` still resolves, and the layer installs.
RUN --mount=type=cache,id=webapp-otel-apk,target=/var/cache/apk \
    NGINX_VER=$(nginx -v 2>&1 | sed 's|.*/||') \
    && apk add \
    c-ares-dev cmake g++ gcc \
    git grpc-dev make "nginx-stable-mod-dev~$NGINX_VER" \
    ninja openssl-dev protobuf-dev python-3.14 !python3-ndbm \
    re2-dev zlib-dev

# Configure the exact source tree of the running binary — the image's own
# configure args with the out-of-tree dynamic modules dropped (their sources
# are not shipped, and the module signature is feature flags only, which
# --with-compat already satisfies; verified against 1.30.6's ngx_module.h).
# eval, not bare quoting: nginx -V quotes values that contain spaces
# (--with-cc-opt='-O2 ...'), and the substitution must be re-parsed into
# arguments — "$ARGS" alone would pass the whole string as one argument.
#
# The source kit sits in a versioned dir (nginx-1.30.8) while FROM pins only
# the 1.30 minor, so the patch level is read from the running binary and
# routed through a stable symlink — the recipe never hardcodes it, a dhi
# patch bump needs no edit, and a missing source kit fails loudly here.
RUN NGINX_VER=$(nginx -v 2>&1 | sed 's|.*/||') \
    && test -d "/usr/src/nginx-$NGINX_VER" \
    && ln -sfn "/usr/src/nginx-$NGINX_VER" /usr/src/nginx-src
WORKDIR /usr/src/nginx-src
# Run the real entrypoint, `auto/configure`, not the top-level `./configure`.
# The dhi-pushed nginx-stable-mod-dev kit ships the tree with auto/configure
# but without the one-line `./configure` wrapper (the re-pushed 1.30.8-r0 kit
# dropped it; 1.30.6's kit carried it). auto/configure reads its own tree by
# relative path (. auto/options), and the wrapper only did
# `exec sh auto/configure "$@"` from this same dir — so running it directly is
# byte-identical and survives either kit layout.
RUN ARGS=$(nginx -V 2>&1 | grep '^configure arguments:' \
    | sed -e 's/^configure arguments: //' -e 's/--add-dynamic-module=[^ ]*//g') \
    && eval sh auto/configure "$ARGS" --with-compat

# nginx-otel v0.1.2 (latest release): pinned by tag, built against system
# gRPC/protobuf (NGX_OTEL_GRPC=package — the from-source fetch is 40+ min);
# opentelemetry-cpp is vendored by the project's cmake. The policy flag is
# v0.1.2's 2023 cmake meeting cmake 4 (its cmake_minimum_required predates
# 3.5); verified to build clean on the gcc 15.2 the image ships. The closure
# tar is the module's runtime library set (grpc/protobuf/abseil/icu) —
# dereferenced (-h): musl will not resolve dangling soname symlinks.
#
# No build cache mount here: the vendored SDK's configure_file() headers get
# fresh timestamps every pass, so ninja rebuilds its 34 objects regardless of
# what the mount carries (measured: warm = cold, ~17s). The clone + cmake +
# ninja is cheap next to the apk layer.
RUN git clone --depth 1 --branch v0.1.2 https://github.com/nginx/nginx-otel.git /nginx-otel \
    && mkdir -p /out-stage \
    && cmake -G Ninja \
    -S /nginx-otel -B /nginx-otel/build \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DNGX_OTEL_GRPC=package \
    -DNGX_OTEL_NGINX_BUILD_DIR=/usr/src/nginx-src/objs \
    && ninja -C /nginx-otel/build ngx_otel_module \
    && ldd /nginx-otel/build/ngx_otel_module.so \
    | awk '{print $3}' | grep '^/usr' | sort -u \
    | tar -hcf - -T - | tar -xf - -C /out-stage \
    && cp /nginx-otel/build/ngx_otel_module.so /out-stage/

# The load_module directive must live in the *main* context, which the
# hardened image provides: its nginx.conf includes /etc/nginx/modules/*.conf
# there (verified against the shipped config — no patching of the base
# config needed).
COPY apps/aurelius-atlas-webapp/etc/nginx/modules/otel.conf /out-stage/otel.conf

# The module loads only into the nginx it was built against: a different patch
# level stops the container at start ("module ... version 1030007 instead of
# 1030006"). The runtime base has no shell, so its binary is run here, in the
# builder, and compared with the one the module was built for. The runtime
# stage copies the module from this stage, so the check can't be skipped.
FROM otel-builder AS otel-verified
COPY --from=runtime-base /usr/sbin/nginx /tmp/runtime-nginx
RUN BUILT=$(nginx -v 2>&1 | sed 's|.*/||') \
    && RUNTIME=$(/tmp/runtime-nginx -v 2>&1 | sed 's|.*/||') \
    && if [ "$BUILT" != "$RUNTIME" ]; then \
    echo "the OTel module is built for nginx $BUILT, the runtime base runs $RUNTIME:" \
    "pull both bases (docker pull) and build again" >&2; exit 1; fi \
    && echo "nginx $BUILT in both stages"

FROM runtime-base

ARG VERSION=local

# Add image metadata
LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="Aurelius Atlas webapp (Angular 22 port of the Aurelius interface)."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Atlas Webapp"
LABEL org.opencontainers.image.version="${VERSION}"

# The native OTel tracing module (SHL-15, DD-239): the builder's .so into the
# image's configured modules dir, its library closure into /usr/lib, and the
# loader snippet into the main-context include. All root-owned: the runtime
# nginx user (65532) reads them, never writes.
COPY --from=otel-verified --chown=root:root /out-stage/usr/lib/ /usr/lib/
COPY --from=otel-verified --chown=root:root /out-stage/ngx_otel_module.so /usr/lib/nginx/modules/ngx_otel_module.so
COPY --from=otel-verified --chown=root:root /out-stage/otel.conf /etc/nginx/modules/otel.conf

# Copy the built application files (one directory per locale) to the Nginx HTML directory
COPY --chown=root:root --chmod=0755 dist/apps/aurelius-atlas-webapp/browser /usr/share/nginx/html

# Ship the site config (Accept-Language locale routing + /api, /otel proxies)
# over the stock one. It is a template: the ${AURELIUS_ATLAS_WEBAPP_*}
# placeholders are resolved by the deployment, which mounts its filled-in copy
# over /etc/nginx/conf.d/default.conf (e2e does exactly this). A bare
# container with no mount fails at nginx config parse — loud, not silently
# wrong. (SHL-11.)
COPY --chown=root:root apps/aurelius-atlas-webapp/nginx.conf.template /etc/nginx/conf.d/default.conf

# Switch to the nginx user to run the application
USER nginx

# Expose port 8080 for the application
EXPOSE 8080
