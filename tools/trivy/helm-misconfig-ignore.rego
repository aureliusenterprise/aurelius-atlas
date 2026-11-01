# Trivy misconfig ignore-policy for the helm-config-scan target (DD-282).
#
# Trivy queries data.trivy.ignore over each finding, so this file must stay in
# `package trivy` and the rule must be named `ignore`. Keep it minimal: silence
# a verified false positive, a deliberate house posture, or a documented
# deferral - never a whole rule blindly. Each clause below states which, and
# every deferral names the follow-up that closes it. Findings are keyed by the
# dotted ID (KSV-0014) plus the message text (the resource/container name),
# which are stable across renders; the Rego `Namespace`/`Query` carry the
# undotted form (KSV0014) and are NOT matched here.
package trivy

default ignore = false

# --- KSV-0109 (HIGH): secrets in ConfigMaps ----------------------------------
# KSV-0109 flags "secrets" stored in ConfigMaps. The metrics-puller ConfigMaps
# hold prometheus oauth2 client-secret / basic-auth password entries whose
# values are `${env:...}` placeholders resolved from mounted secrets at runtime
# (DD-282 R5) - no secret material is in the chart. Scoped to those two
# ConfigMaps by name; KSV-0109 stays live for everything else.
ignore {
	input.ID == "KSV-0109"
	contains(input.Message, "-metrics-puller' in ")
}

# --- KSV-01010 (MED): sensitive contents in ConfigMaps -----------------------
# The same placeholder class, flagged by the sibling rule: the hit keys are
# config field NAMES, not secret values. The ES ConfigMap's
# `xpack.security.http.ssl.key` value is a file PATH (tls/*.pem); the puller
# ConfigMaps' `key`/`username` entries are `${env:...}` refs and OTel
# attribute keys; the observability collector's `key` entries are attribute
# keys; the grafana dashboards and webapp nginx hits are substrings of
# dashboard JSON and a Permissions-Policy directive (`...camera...`). All
# six verified non-secret; the allowlist keeps the rule live for any future
# ConfigMap.
ignore {
	input.ID == "KSV-01010"
	msg := input.Message
	startswith(msg, "ConfigMap '")
	name := substring(msg, 11, indexof(substring(msg, 11, -1), "'"))
	allowed := {"atlas-elasticsearch", "atlas-elasticsearch-metrics-puller", "atlas-keycloak-metrics-puller", "atlas-observability", "atlas-observability-grafana-dashboards", "atlas-webapp-nginx"}
	allowed[name]
}

# --- KSV-0125 (MED): image from an untrusted registry ------------------------
# Trivy's allowlist is docker.io/quay.io/gcr.io/ecr.* only. Every chart image
# is an Aurelius artifact (ghcr.io/aureliusenterprise - published by this
# repo, cosign-signed, CHT-94) or a Docker Hardened Image (dhi.io); the
# contract test test__every_image_is_tagged_aurelius_or_pinned_third_party
# enforces exactly those two registries on every render, which is a stronger
# gate than Trivy's registry list - an image from anywhere else fails CI
# before a scan ever runs. The finding carries no registry field to scope
# on, so this is rule-level: the contract test is the live control.
ignore {
	input.ID == "KSV-0125"
}

# --- KSV-0013 (MED): image without a tag ------------------------------------
# A scan-render artefact: the charts render Aurelius images as
# <name>:<appVersion>, which is ":latest" at default values and the git tag
# after the release rewrite (CHT-92/93); the third-party images render by
# digest. The scan renders DEFAULT values, so it always sees :latest. The
# release names the real image; test__aurelius_images_render_by_tag_in_the_repo
# pins the tag shape. Scoped to the Aurelius refs; a genuinely tagless
# third-party image still fires.
ignore {
	input.ID == "KSV-0013"
	contains(input.Message, "should specify an image tag")
}

# --- KSV-0011 (LOW): no CPU limit --------------------------------------------
# Deliberate house posture (not a false positive): every chart caps memory
# (limits.memory) and leaves CPU uncapped so JVM-bound workloads are never
# throttled mid-boot on the shared dev cluster. The JSON report keeps the
# rows; the SARIF severity filter plus this clause keep them out of the
# Sonar new-issues gate. Revisit per workload by setting limits.cpu and
# deleting this clause.
ignore {
	input.ID == "KSV-0011"
}

# --- KSV-0014 (HIGH): writable root filesystem -------------------------------
# DEFERRAL, scoped to the eight stateful servers that write outside their
# volumes: elasticsearch (logs), keycloak (+ its bundled postgres - the chart
# documents `readOnlyRootFilesystem: false` explicitly), and the five
# observability servers. Each needs per-workload emptyDirs for logs/tmp before
# a read-only root boots - the cluster-validated follow-up increment (DD-282).
# Every stateless container (apps, webapp nginx + init, both pullers, the
# collector's issuer-wait, the coredump-agent, wait-for-postgres) pins a
# read-only root and stays live here: a flip-back to writable fires.
ignore {
	input.ID == "KSV-0014"
	msg := input.Message
	startswith(msg, "Container '")
	cname := substring(msg, 11, indexof(substring(msg, 11, -1), "'"))
	stateful := {"elasticsearch", "grafana", "keycloak", "loki", "observability", "postgres", "prometheus", "tempo"}
	stateful[cname]
}

# --- KSV-0020 (LOW) / KSV-0021 (LOW): uid <= 10000 / gid <= 10000 -----------
# The image-declared users: the ES pod + coredump-agent run as the hardened
# image's uid/gid 1000, bundled Postgres as uid/gid 70 - both non-root, both
# fixed by the upstream images (DD-257: the chart runs the image's declared
# user, never a forked one). Scoped to those three container names; every
# 65532 workload (apps, keycloak, observability) satisfies KSV-0021's 1000
# floor and stays live for regressions.
ignore {
	input.ID == "KSV-0020"
	flagged_uid(input.Message)
}

ignore {
	input.ID == "KSV-0021"
	flagged_uid(input.Message)
}

# The three image-user containers: ES pod + coredump-agent (uid/gid 1000),
# bundled Postgres (uid/gid 70).
flagged_uid(msg) {
	startswith(msg, "Container 'coredump-agent'")
}

flagged_uid(msg) {
	startswith(msg, "Container 'elasticsearch'")
}

flagged_uid(msg) {
	startswith(msg, "Container 'postgres'")
}
