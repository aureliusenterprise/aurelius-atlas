# aurelius-atlas-server

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-server)

The Aurelius Atlas server: the Apache Atlas 2.4.0 REST API on Elasticsearch.

## Usage

```bash
npx nx serve aurelius-atlas-server
```

This starts the dev Elasticsearch store and the observability stack, then the server at
[https://localhost:21000](https://localhost:21000), the port Apache Atlas uses.

## Deployment

Deploy the image built from the provided Dockerfile. It listens on port 21000 and needs the
Elasticsearch settings; it does not start without its store.

## Configuration

??? INFO "Settings"

    ::: aurelius_atlas_server.settings.ServerSettings

## Documentation

::: aurelius_atlas_server.app

::: aurelius_atlas_server.errors

::: aurelius_atlas_server.routes.admin
