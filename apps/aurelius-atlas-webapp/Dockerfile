FROM dhi.io/nginx:1.30-alpine3.24

ARG VERSION=local

# Add image metadata
LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="Aurelius Atlas webapp (Angular 22 port of the Aurelius interface)."
LABEL org.opencontainers.image.licenses=UNLICENSED
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Atlas Webapp"
LABEL org.opencontainers.image.version="${VERSION}"

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
