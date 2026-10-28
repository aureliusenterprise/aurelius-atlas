# syntax=docker/dockerfile:1

# The Elasticsearch coredump-filter javaagent (tools/es-coredump-agent, DD-255).
# GKE nodes deny the /proc/self/coredump_filter write that Elasticsearch 9.x
# treats as fatal at bootstrap; this agent rewrites the path constant to a
# tmpfs file (see CoredumpNoopAgent.java). The atlas-elasticsearch chart mounts
# it via an init container (CHT-15).

# The jar is the committed artifact — the same bytes the dev compose mounts —
# so dev and cluster run one artifact, not two builds. tools/es-coredump-agent/
# build.sh regenerates it from source; the chart-contract test guards the copy.
FROM dhi.io/busybox:1.37

COPY tools/es-coredump-agent/coredump-noop.jar /coredump-noop.jar
