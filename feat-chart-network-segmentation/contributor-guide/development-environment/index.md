# Development Environment

Follow the steps below to set up your development environment.

This project includes a [development container](<https://containers.dev>) to automatically set up your development environment, including the all tools and dependencies required for local development.

> [!NOTE]
>
> **Prerequisites**
>
> [Docker](<https://www.docker.com>) must be installed on your system to use the development container.
>
> All container images in this repository — application bases as well as the development infrastructure (Elasticsearch, Keycloak, Postgres, observability) — are [Docker Hardened Images](<https://dhi.io>) pulled from the `dhi.io` registry. Pulling them requires a Docker Hub account: run `docker login` on your host before starting the development container or running any `serve`, `test`, or `e2e` target, otherwise image pulls fail with an unauthorized error.
>
> If you're using **Rancher Desktop**, follow the instructions in the [Rancher Desktop documentation](<https://docs.rancherdesktop.io/how-to-guides/vs-code-remote-containers/>) to prepare your environment for use with the development container.

> [!TIP]
>
> **Use WSL on Windows**
>
> If you are using Windows, we **strongly** recommend cloning the repository into the [WSL](<https://learn.microsoft.com/en-us/windows/wsl/>) filesystem instead of the Windows filesystem. This significantly improves I/O performance when running the development container.

## Configure your SSH Key

Follow the steps below to configure your SSH key for accessing the repository:

1. [Generate an SSH key](<https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent>).
2. [Add the SSH key to your GitHub account](<https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account>).

## Configure your SSH Agent

The development container will attempt to pick up your SSH key from your `ssh-agent` when it starts. Follow the guide on [sharing git credentials with the development container](<https://code.visualstudio.com/remote/advancedcontainers/sharing-git-credentials>) to ensure your SSH key is available inside the container.

## Clone the Repository

To clone the repository, run the following command:

```
git clone git@github.com:aureliusenterprise/aurelius-atlas.git
```

This will clone the repository to your local machine using SSH.

## Environment Setup

> [!NOTE]
>
> **Prerequisites**
>
> The [Remote Development Extension Pack](<https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack>) for Visual Studio Code must be installed to work with development containers.

To get started, navigate to the folder where you cloned the repository and run:

```
code .
```

This will open the current directory in Visual Studio Code.

Once Visual Studio Code is open, you will see a notification at the bottom right corner of the window asking if you want to open the project in a development container. Select `Reopen in Container`.

Your development environment will now be set up automatically.

> [!NOTE]
>
> **What if I don't see the notification?**
>
> You can manually open the development container by pressing `F1` to open the command pallette. Type `>Dev Containers: Reopen in Container` and press `Enter` to select the command.

> [!NOTE]
>
> **Detailed Setup Guides**
>
> For more details, refer to the setup guide for your IDE:
>
> - [Visual Studio Code](<https://code.visualstudio.com/docs/devcontainers/tutorial>)
> - [PyCharm](<https://www.jetbrains.com/help/pycharm/connect-to-devcontainer.html>)

## Configure your SOPS Key

Once your development environment is set up, you need to configure your SOPS key, which is used to encrypt and decrypt the secrets in the repository. Please follow the steps in the [Secrets Management](<https://aureliusenterprise.github.io/feat-chart-network-segmentation/contributor-guide/secrets-management/index.md>) guide.

## What Happens on First Start

When the development container starts for the first time, it:

1. Installs the toolchain from the container features.
2. Installs JavaScript dependencies (`npm install`) and Python dependencies (`uv sync`) into the workspace.
3. Generates a personal SOPS/age key pair into `secrets/keys.txt`, unless one already exists.

Local TLS material is not prewarmed: every `serve` or `e2e` target that needs it first runs that project's `certgen` target, which issues the certificates it owns into its own gitignored `certs/` directory. The local `mkcert` certificate authority has no workspace home: `certgen` installs it into the system trust stores on first use (it lives in mkcert's own store, outside the repository) and copies it into each project's `certs/`; run `mkcert -uninstall` to drop it entirely — see [Data Encryption](<https://aureliusenterprise.github.io/feat-chart-network-segmentation/architecture/platform/security/data-encryption/index.md>).

> [!WARNING]
>
> **Your first tests may fail until your key is registered**
>
> Almost every `serve`, `test`, and `e2e` target first runs a `decrypt` step to turn the committed `.env.enc` secret files into plaintext `.env` files. Decryption only succeeds once your public key is listed in `.sops.yaml` and the files have been re-encrypted for you (see [Registering a new key pair](<https://aureliusenterprise.github.io/feat-chart-network-segmentation/contributor-guide/secrets-management/#registering-a-new-key-pair>)). Until then, commands fail with a SOPS/age decryption error — this is expected, not a broken setup.

> [!WARNING]
>
> **Image pulls fail without a Docker Hub login**
>
> The `serve`, `test`, and `e2e` targets pull their base and infrastructure images from [Docker Hardened Images](<https://dhi.io>) (`dhi.io/*`), a registry that requires authentication with Docker Hub credentials. If you have not run `docker login` with a Docker Hub account, pulls fail with an `unauthorized` (or rate-limit) error — see the Prerequisites note at the top of this guide.

## Dev Topology

The development infrastructure is a set of **slices**: each slice under `dev/` is its own compose project with its own network, named `aurelius-atlas-dev-<slice>-network`. An app's `serve` target starts the slices it needs via `dependsOn` (ADR 005); a slice's services reach each other by service name on a shared network.

The rule that surprises people: **services are reached by service name, not `localhost`**. The store's certificate is issued for `elasticsearch`, so an IP or `localhost` fails certificate verification, not connectivity. The server's e2e container attaches to the Elasticsearch and observability networks and reaches the store as `https://elasticsearch:9200`. Certificate plumbing is in [TLS Certificates](<https://aureliusenterprise.github.io/feat-chart-network-segmentation/contributor-guide/tls-certificates/index.md>).

| Service | Host port | Slice | Notes |
| --- | --- | --- | --- |
| Atlas server | 21000 | app | Atlas's own port |
| Elasticsearch | `${ELASTICSEARCH_PORT}` → 9200 | `elasticsearch` | TLS only |
| Postgres (examples) | `${DATABASE_PORT}` → 5432 | `postgres` | Keycloak keeps its own, on its network |
| Keycloak | 8080 / 8443 | `keycloak` | 8080 dev convenience; 8443 is the verified TLS path |
| OTel collector | 127.0.0.1:4317 / 4318 / 4319 | `observability` | OTLP: 4318 browser leg (user JWT), 4317/4319 service leg (shared token); TLS (DD-193), loopback-pinned |
| Prometheus / Loki / Tempo | 9090 / 3100 / 3200 | `observability` | Consumed through the collector |
| Grafana | 127.0.0.1:3000 | `observability` | Loopback only |

Each slice documents its own services, images, and run commands in its colocated README: `dev/elasticsearch`, `dev/keycloak`, `dev/postgres`, `dev/observability`.

> [!WARNING]
>
> **Keycloak's port 8080 is development-only**
>
> The plaintext 8080 listener exists so browser sign-in works in the dev stack; 8443 is the verified TLS path that CI and E2E use. The production arrangement has no plaintext listener — see [Data Encryption](<https://aureliusenterprise.github.io/feat-chart-network-segmentation/architecture/platform/security/data-encryption/#named-relaxation-development-arrangement-only>).

## Runtime Windows

Per [ADR 031](<https://aureliusenterprise.github.io/feat-chart-network-segmentation/architecture/adr/031-runtime-versions-have-a-declared-support-window/index.md>), each runtime the system runs on has one declared window. The pins named here are the answer — this page names where they live, not their values, so there is one place to update. A major-version bump is a reviewed change to every pin at once, approved by the maintainers team.

| Runtime | Supported window | Pins live in |
| --- | --- | --- |
| Python | 3.14 only | `pyproject.toml` (`requires-python`), `.devcontainer` python feature, server `Dockerfile` base image, pyright/ruff target |
| Node.js | 24 (LTS jod) | `.devcontainer` node feature, dashboard `build.Dockerfile` |
| Java | 21 (dev tooling for the vendored dashboards' build only) | `.devcontainer` java feature |
| Elasticsearch | 9.x (dev image 9.5) | `dev/elasticsearch/docker-compose.yaml` image tag |
| Keycloak | 26.x | `dev/keycloak/docker-compose.yaml` image tag |
| PostgreSQL | 18 (Keycloak's database and the template example only — ADR 047) | `dev/postgres`, `dev/keycloak` compose image tags |

Minor and patch releases inside a window follow the dependency rule ([ADR 020](<https://aureliusenterprise.github.io/feat-chart-network-segmentation/architecture/adr/020-dependencies-stay-current-by-default/index.md>)); the floor rises only when every pin above moves in one change.

## Explore the Workspace

The workspace is organized as a monorepo, which means that all the projects are stored in a single repository.

> [!NOTE]
>
> **Workspace Structure**
>
> The workspace is divided into the following main directories:
>
> - `apps`: Contains the main applications and services that make up the workspace.
> - `dev`: Compose files and configuration for the supporting development infrastructure (Elasticsearch, Keycloak, Postgres, observability stack).
> - `docs`: Central location for all project documentation, guides, and reference materials.
> - `libs`: Shared libraries and utilities used by multiple applications within the monorepo.
> - `reports`: License and vulnerability report generators.
> - `schemas`: Avro event schemas used by the template's example library only.
> - `secrets`: Your personal SOPS/age key; this folder is excluded from version control.
> - `tools`: Custom automation (Nx plugins) that wires builds, containers, secrets, and docs into `Nx`.

Workspace automation is managed using [`Nx`](<https://nx.dev/>). Each project in the workspace has its own set of configurations and dependencies, allowing for modular development.

> [!TIP]
>
> **Browse the project graph**
>
> A great way to start exploring the workspace is to visualize the project graph. You can do this by running the following command in the terminal:
>
> ```
> nx graph
> ```
>
> This will open a new tab in your browser with an interactive graph of the workspace, showing the dependencies between the projects. You can click on the nodes to see more details about each project.
