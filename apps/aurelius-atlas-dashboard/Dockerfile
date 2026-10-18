FROM dhi.io/nginx:1.30-alpine3.24

ARG VERSION=local

# Add image metadata
LABEL org.opencontainers.image.authors="Aurelius Enterprise"
LABEL org.opencontainers.image.description="The Apache Atlas 2.4.0 dashboards: dashboardv2 at / and dashboardv3 at /n/, in front of the Aurelius Atlas API."
LABEL org.opencontainers.image.licenses=Apache-2.0
LABEL org.opencontainers.image.source=https://github.com/aureliusenterprise/aurelius-atlas
LABEL org.opencontainers.image.title="Aurelius Atlas Dashboard"
LABEL org.opencontainers.image.version="${VERSION}"

# The built dashboards, written by `nx build aurelius-atlas-dashboard`: dashboardv2 at the root of the
# directory and dashboardv3 in n/ — the layout of Atlas's web application, so it is copied as the site
# root as it stands (DD-034).
COPY --chown=root:root --chmod=0755 apps/aurelius-atlas-dashboard/dist /usr/share/nginx/html

# The serving project's own pages (not the vendored source): the login page nginx answers at
# /login.jsp — Atlas's login URI and logoutSuccessUrl — where the OIDC flow returns the browser
# (DD-040). Kept out of dist/ so `nx build` stays a pure build of the vendored dashboards.
COPY --chown=root:root --chmod=0755 apps/aurelius-atlas-dashboard/webapp /usr/share/nginx/html

# Ship the site config (locale layout of Atlas's webapp + the proxies that keep the API on the same
# origin) over the stock one. It is a template: the ${AURELIUS_ATLAS_DASHBOARD_*} placeholders are
# resolved by the deployment, which mounts its filled-in copy over /etc/nginx/conf.d/default.conf
# (this project's stack does exactly this, through nginx.conf). A bare container with no
# mount fails at nginx config parse — loud, not silently wrong.
COPY --chown=root:root apps/aurelius-atlas-dashboard/nginx.conf.template /etc/nginx/conf.d/default.conf

# Switch to the nginx user to run the application
USER nginx

# Expose port 8080 for the application
EXPOSE 8080
