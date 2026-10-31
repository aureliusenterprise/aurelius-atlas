# aurelius-atlas-cluster-lane

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-cluster-lane)

The shared e2e cluster lane: the pytest machinery for driving suites against
the Helm umbrella (10.5b, DD-282).

## Installation

Part of the workspace dev group; e2e conftests import it explicitly (it is
deliberately not a pytest11 plugin — compose runs never autoload kubectl
paths).

```toml
[dependency-groups]
dev = ["aurelius-atlas-cluster-lane"]

[tool.uv.sources.aurelius-atlas-cluster-lane]
workspace = true
```

## Documentation

::: aurelius_atlas_cluster_lane.lane

::: aurelius_atlas_cluster_lane.forward

::: aurelius_atlas_cluster_lane.secrets

::: aurelius_atlas_cluster_lane.hosts
