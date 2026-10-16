## 0.6.1 (2026-10-09)

### 🚀 Features

- switch to logfire for structured logging ([b85ddc4d](https://github.com/aureliusenterprise/project-template/commit/b85ddc4d))
- setup opentelemetry ([#43](https://github.com/aureliusenterprise/project-template/pull/43))
- add HTML report generation for vulnerability scans ([#44](https://github.com/aureliusenterprise/project-template/pull/44))
- add ESLint configuration for pre-commit ([711c997d](https://github.com/aureliusenterprise/project-template/commit/711c997d))
- simplify kafka connect docker image ([#47](https://github.com/aureliusenterprise/project-template/pull/47))
- harden aws lambda images ([#48](https://github.com/aureliusenterprise/project-template/pull/48))
- refactor authentication handling ([4a09d286](https://github.com/aureliusenterprise/project-template/commit/4a09d286))
- harden dev infrastructure images and extend e2e shared services ([#123](https://github.com/aureliusenterprise/project-template/pull/123))
- add cirquit breakers to api example ([7f9a1e6e](https://github.com/aureliusenterprise/project-template/commit/7f9a1e6e))
- **docs:** migrate docs stack to Zensical with llmstxt and pydantic-aware API refs ([e339b2cf](https://github.com/aureliusenterprise/project-template/commit/e339b2cf))
- **frontend:** typed runtime config with configurable API and OTel URLs ([cd7bfb9a](https://github.com/aureliusenterprise/project-template/commit/cd7bfb9a))

### 🩹 Fixes

- patch java producer vulnerabilities ([d1063dde](https://github.com/aureliusenterprise/project-template/commit/d1063dde))
- address sonarqube warning ([efdc876d](https://github.com/aureliusenterprise/project-template/commit/efdc876d))
- update Debezium JDBC connector version to 3.5.1.Final ([ccd33ab5](https://github.com/aureliusenterprise/project-template/commit/ccd33ab5))
- update project-graph plugin version to 0.1.24 ([47c461a6](https://github.com/aureliusenterprise/project-template/commit/47c461a6))
- set avro trusted packages and default time created ([f9503471](https://github.com/aureliusenterprise/project-template/commit/f9503471))
- ensure traces show up in grafana ([f5581b03](https://github.com/aureliusenterprise/project-template/commit/f5581b03))
- **aurelius-example:** derive Entity comparison operators via total_ordering ([3d7acb0c](https://github.com/aureliusenterprise/project-template/commit/3d7acb0c))
- **dev:** make kafka server.properties writable for broker startup ([840496f2](https://github.com/aureliusenterprise/project-template/commit/840496f2))
- **e2e:** start shared dev stacks via nx before e2e tests run ([f43912d8](https://github.com/aureliusenterprise/project-template/commit/f43912d8))
- **fastapi-example:** migrate OpenIdConfig to Pydantic V2 ConfigDict ([1f533a52](https://github.com/aureliusenterprise/project-template/commit/1f533a52))
- **keycloak:** loosen healthcheck timings ([2e5bbbed](https://github.com/aureliusenterprise/project-template/commit/2e5bbbed))
- **release:** make nx release work for manifest-less and Gradle projects ([66dcba14](https://github.com/aureliusenterprise/project-template/commit/66dcba14))
- **report:** update worst severity display logic for unknown severity ([0a682f7d](https://github.com/aureliusenterprise/project-template/commit/0a682f7d))

## 0.6.0 (2026-05-03)

### 🚀 Features

- enhance Docker setup with CycloneDX CLI and SBOM generation ([ae1d847](https://github.com/aureliusenterprise/project-template/commit/ae1d847))
- update SBOM generation commands and add parallelism option ([b41729d](https://github.com/aureliusenterprise/project-template/commit/b41729d))

### 🩹 Fixes

- attest frontend container with angular sbom ([f2ecd26](https://github.com/aureliusenterprise/project-template/commit/f2ecd26))

## 0.5.0 (2026-05-02)

### 🚀 Features

- split broadcaster into reusable listener and generic boadcaster ([#35](https://github.com/aureliusenterprise/project-template/pull/35))
- migrate to psycopg v3 ([73a3a08](https://github.com/aureliusenterprise/project-template/commit/73a3a08))
- setup distroless images ([#38](https://github.com/aureliusenterprise/project-template/pull/38))
- setup distroless image for frontend app ([#39](https://github.com/aureliusenterprise/project-template/pull/39))
- use hardened java image ([#40](https://github.com/aureliusenterprise/project-template/pull/40))
- use hardened image for node-red app ([#41](https://github.com/aureliusenterprise/project-template/pull/41))

### 🩹 Fixes

- enrich notifcations only once rather than for each sse connection ([#36](https://github.com/aureliusenterprise/project-template/pull/36))
- remove additional db lookup ([#37](https://github.com/aureliusenterprise/project-template/pull/37))

## 0.4.0 (2026-04-21)

### 🚀 Features

- extend notification metadata ([#29](https://github.com/aureliusenterprise/project-template/pull/29))
- add timestamp to sse messages ([#30](https://github.com/aureliusenterprise/project-template/pull/30))
- add op field to sse envelope ([#31](https://github.com/aureliusenterprise/project-template/pull/31))
- set up broadcasting for sse messages ([#32](https://github.com/aureliusenterprise/project-template/pull/32))
- register optional sdk dependencies ([#33](https://github.com/aureliusenterprise/project-template/pull/33))

### 🩹 Fixes

- ensure pagination is ordered newest to oldest ([#28](https://github.com/aureliusenterprise/project-template/pull/28))

## 0.3.0 (2026-04-18)

### 🚀 Features

- use schema id in kafka header ([#21](https://github.com/aureliusenterprise/project-template/pull/21))
- support schema id in header for aws lambda ([cfd5aef](https://github.com/aureliusenterprise/project-template/commit/cfd5aef))
- add shared assets to brand library ([6b1f651](https://github.com/aureliusenterprise/project-template/commit/6b1f651))
- add sse example with fastapi ([#24](https://github.com/aureliusenterprise/project-template/pull/24))
- add pagination ui component ([#25](https://github.com/aureliusenterprise/project-template/pull/25))
- improve paginated response from api ([#26](https://github.com/aureliusenterprise/project-template/pull/26))
- add created and modified timestamps ([#27](https://github.com/aureliusenterprise/project-template/pull/27))

### 🩹 Fixes

- add image metadata ([6a39514](https://github.com/aureliusenterprise/project-template/commit/6a39514))
- use correct subject name strategy ([d8aed6e](https://github.com/aureliusenterprise/project-template/commit/d8aed6e))
- add producer callback function ([cd7c556](https://github.com/aureliusenterprise/project-template/commit/cd7c556))
- ensure readiness check has no payload ([233969e](https://github.com/aureliusenterprise/project-template/commit/233969e))
- use runtime safe type ([5347d81](https://github.com/aureliusenterprise/project-template/commit/5347d81))
- improve exception handling and reduce unneeded commits ([8ded5fe](https://github.com/aureliusenterprise/project-template/commit/8ded5fe))
- apply ai review feedback ([ffc24ab](https://github.com/aureliusenterprise/project-template/commit/ffc24ab))
- avoid logging stack traces in production ([52264cb](https://github.com/aureliusenterprise/project-template/commit/52264cb))
- use correct logger name ([ff4e183](https://github.com/aureliusenterprise/project-template/commit/ff4e183))
- flush producer on loop exit ([558e6f9](https://github.com/aureliusenterprise/project-template/commit/558e6f9))
- address sonarqube issues ([5d30453](https://github.com/aureliusenterprise/project-template/commit/5d30453))
- add title header ([f9807d7](https://github.com/aureliusenterprise/project-template/commit/f9807d7))
- reduce permissions on copied files ([5d726da](https://github.com/aureliusenterprise/project-template/commit/5d726da))
- address linter issues ([0cf394b](https://github.com/aureliusenterprise/project-template/commit/0cf394b))
- address linter issues ([947015d](https://github.com/aureliusenterprise/project-template/commit/947015d))
- address linter issues ([92e4345](https://github.com/aureliusenterprise/project-template/commit/92e4345))
- address linter issues ([2cb7214](https://github.com/aureliusenterprise/project-template/commit/2cb7214))
- address linter issues ([2aa5a0d](https://github.com/aureliusenterprise/project-template/commit/2aa5a0d))
- address linter issues ([ee0ee90](https://github.com/aureliusenterprise/project-template/commit/ee0ee90))

## 0.2.0 (2026-02-12)

### 🚀 Features

- add example kafka producer in java ([#16](https://github.com/aureliusenterprise/project-template/pull/16))
- add interval loop for java producer ([#19](https://github.com/aureliusenterprise/project-template/pull/19))

### 🩹 Fixes

- resolve Node-RED to Kafka connectivity issues ([#14](https://github.com/aureliusenterprise/project-template/pull/14))

## 0.1.0 (2026-02-04)

### 🚀 Features

- add example fastapi app ([16e9adc](https://github.com/aureliusenterprise/project-template/commit/16e9adc))
- add example kafka connect sink ([9918fb8](https://github.com/aureliusenterprise/project-template/commit/9918fb8))
- add library with kafka utilities ([c058130](https://github.com/aureliusenterprise/project-template/commit/c058130))
- add some more utilities and simplify module structure ([94cc488](https://github.com/aureliusenterprise/project-template/commit/94cc488))
- add example aws lambda function ([1ef552e](https://github.com/aureliusenterprise/project-template/commit/1ef552e))
- add crud endpoints for example api ([#3](https://github.com/aureliusenterprise/project-template/pull/3))
- add frontend example ([#4](https://github.com/aureliusenterprise/project-template/pull/4))
- upgrade to python 3.14 ([f0c5af0](https://github.com/aureliusenterprise/project-template/commit/f0c5af0))
- migrate to zoneless angular ([21892d6](https://github.com/aureliusenterprise/project-template/commit/21892d6))
- node-red example ([#10](https://github.com/aureliusenterprise/project-template/pull/10))

### 🩹 Fixes

- include additional fields in lambda kafka message parser ([fa2ded4](https://github.com/aureliusenterprise/project-template/commit/fa2ded4))
- remove duplicate route tags ([6f5d6cc](https://github.com/aureliusenterprise/project-template/commit/6f5d6cc))
- add missing image metadata ([0e0342c](https://github.com/aureliusenterprise/project-template/commit/0e0342c))
- revert TYPE_CHECKING blocks ([a15a1ba](https://github.com/aureliusenterprise/project-template/commit/a15a1ba))

<!-- markdownlint-disable-file MD041 -->
