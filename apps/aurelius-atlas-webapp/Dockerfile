# syntax=docker/dockerfile:1
# The OTel module must be compiled against this exact nginx (the module
# signature is feature-flag checked at dlopen, and the .so links musl), so
# the builder rides the -dev variant of the same tag: it is the hardened
# image plus apk and the distro's build tree (DD-239). The runtime stage is
# the hardened image proper.
FROM dhi.io/nginx:1.30-alpine3.24-dev AS otel-builder

# The python-3.14 pin is apk arithmetic, not taste: the image's xcb-proto is
# resolved against 3.14 and bare `python` now means 3.15, which breaks it.
# nginx-stable-mod-dev ships the source kit the running binary was built
# from (/usr/src/nginx-<version>); the rest is the nginx-otel build recipe. The cache
# mount carries apk's index + package tarballs across builds (plain `apk add`,
# not --no-cache: the flag is what discards them; a cold pass is ~300 MB of
# downloads).
RUN --mount=type=cache,id=webapp-otel-apk,target=/var/cache/apk \
    apk add \
    c-ares-dev cmake g++ gcc \
    git grpc-dev make nginx-stable-mod-dev \
    ninja openssl-dev protobuf-dev python-3.14 \
    re2-dev zlib-dev

# Configure the exact source tree of the running binary — the image's own
# configure args with the out-of-tree dynamic modules dropped (their sources
# are not shipped, and the module signature is feature flags only, which
# --with-compat already satisfies; verified against 1.30.6's ngx_module.h).
# eval, not bare quoting: nginx -V quotes values that contain spaces
# (--with-cc-opt='-O2 ...'), and the substitution must be re-parsed into
# arguments — "$ARGS" alone would pass the whole string as one argument.
#
# The source kit sits in a versioned dir (nginx-1.30.6) while FROM pins only
# the 1.30 minor, so the patch level is read from the running binary and
# routed through a stable symlink — the recipe never hardcodes it, a dhi
# patch bump needs no edit, and a missing source kit fails loudly here.
RUN NGINX_VER=$(nginx -v 2>&1 | sed 's|.*/||') \
    && test -d "/usr/src/nginx-$NGINX_VER" \
    && ln -sfn "/usr/src/nginx-$NGINX_VER" /usr/src/nginx-src
WORKDIR /usr/src/nginx-src
RUN ARGS=$(nginx -V 2>&1 | grep '^configure arguments:' \
    | sed -e 's/^configure arguments: //' -e 's/--add-dynamic-module=[^ ]*//g') \
    && eval sh ./configure "$ARGS" --with-compat

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

FROM dhi.io/nginx:1.30-alpine3.24

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
COPY --from=otel-builder --chown=root:root /out-stage/usr/lib/ /usr/lib/
COPY --from=otel-builder --chown=root:root /out-stage/ngx_otel_module.so /usr/lib/nginx/modules/ngx_otel_module.so
COPY --from=otel-builder --chown=root:root /out-stage/otel.conf /etc/nginx/modules/otel.conf

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
