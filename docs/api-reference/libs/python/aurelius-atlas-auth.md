# aurelius-atlas-auth

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-auth)

Keycloak bearer-token authentication shared by the Aurelius Atlas services
(8.0, DD-108): OIDC discovery, JWKS verification and the write-role gate.

## Installation

```toml
[project.dependencies]
aurelius-atlas-auth = "*"

[tool.uv.sources.aurelius-atlas-auth]
workspace = true
```

## Documentation

::: aurelius_atlas_auth.auth
