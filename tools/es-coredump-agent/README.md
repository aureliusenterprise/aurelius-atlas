# aurelius-atlas-elasticsearch-agent

The Elasticsearch **coredump-agent** image (DD-255). A no-op `javaagent` whose
sole job is to be present: ES 9.x treats a failed `java_lang` coredump attempt
as fatal at bootstrap on GKE's containerd nodes, and loading a
`Premain-Class` that does nothing makes the dump "succeed" and the node boot.

The `dev/elasticsearch` store chart mounts this image as an init container
that copies `coredump-noop.jar` to an `emptyDir` the JVM's
`-javaagent:/agent/coredump-noop.jar` flag reads (CHT-15).

## The jar

- `coredump-noop.jar` — the committed, byte-stable artifact (a single
  no-op `premain`). It is **not** built by the image build; the image
  `COPY`s the committed bytes, so the shipped jar is exactly the reviewed
  one and the SBOM/signature chain covers it.
- `CoredumpNoopAgent.java` + `manifest.txt` + `build.sh` — regenerate the
  jar from source (`./build.sh`). Re-run it only if the agent's behaviour
  changes; the committed bytes must stay stable otherwise, so the chart's
  image and the dev stack's `./libs/coredump-noop.jar` stay identical.

## The image

`Dockerfile`: `dhi.io/busybox:1.37` (no `latest` tag exists) plus the jar.
Built, scanned, signed, and published through the normal docker plugin targets
(`nx run aurelius-atlas-elasticsearch-agent:docker-build`) — that supply-chain
coverage is exactly why the agent is an image and not a ConfigMap blob
(DD-255).

```bash
npx nx run aurelius-atlas-elasticsearch-agent:docker-build
./build.sh --help   # regenerate the jar (needs a JDK)
```
