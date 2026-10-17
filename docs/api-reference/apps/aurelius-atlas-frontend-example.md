# aurelius-atlas-frontend-example

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aurelius-atlas-frontend-example)

This is an example frontend application built with Angular.

## Deployment

Deploy using the provided Dockerfile. By default, the app listens on [http://localhost:8080](http://localhost:8080).

## Configuration

The following configuration is required to run the application:

### Client-Facing Configuration

The application is configured at runtime via an externally mounted `config.json` file. This client-facing configuration
file contains the necessary settings for the frontend to communicate with the backend and authentication services.
Below is an example `config.json` file:

```json
{
    "keycloak": {
        "clientId": "aurelius",
        "realm": "master",
        "url": "http://keycloak.localhost:8181"
    }
}
```

Mount the `config.json` file into the container at `/usr/share/nginx/html/config.json` via a Docker volume or
Docker `configs` mechanism.

### Nginx Configuration

The production image already bundles the locale-aware Nginx configuration for the Angular app. The bundled
file is served at `/etc/nginx/conf.d/default.conf`, and optional fragments may be added under
`/etc/nginx/app.d/*.conf` inside the existing `server` block.

The image serves locale-prefixed routes (`/en-US/`, `/nl-NL/`), redirects `/` to the preferred language,
and falls back to the matching locale's `index.html` for client-side routing. Keep the app-serving rules in
the image and add only server-scoped proxy or TLS fragments via `/etc/nginx/app.d/*.conf`.

```nginx
server {
    listen 8080;
    root /usr/share/nginx/html;

    include /etc/nginx/app.d/*.conf;

    set $accept_language en-US;
    location = / {
        if ($http_accept_language ~* "^nl") {
            set $accept_language nl-NL;
        }
        return 302 /$accept_language/$is_args$args;
    }

    location /en-US/ {
        try_files $uri $uri/ /en-US/index.html;
    }

    location /nl-NL/ {
        try_files $uri $uri/ /nl-NL/index.html;
    }

    location / {
        try_files $uri /en-US/index.html;
    }
}
```

Do not define another `server` block or an HTTP-level `map` in a fragment; the hardened image includes
fragments at server scope only.
