{{/*
atlas-elasticsearch helpers. Chart-local by design (DD-247): every chart carries the
helpers it uses, the way the Helm ecosystem's own scaffolding does — no shared
library chart to version, publish, or keep in sync. The shared shape these
encode (the global.* contract, the label set, the ADR 018 guard) is a
convention the charts follow, not code they share.
*/}}

{{- define "atlas-elasticsearch.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-elasticsearch.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if hasPrefix (lower .Release.Name) (lower $name) -}}
{{- printf "%s" (lower $name) | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* The headless Service that governs the StatefulSet (CHT-10). */}}
{{- define "atlas-elasticsearch.headlessName" -}}
{{- printf "%s-headless" (include "atlas-elasticsearch.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* The generated credential Secret (DD-244/DD-254); the umbrella names it
<release>-elasticsearch. auth.secretName brings your own. */}}
{{- define "atlas-elasticsearch.authSecretName" -}}
{{- $default := printf "%s-%s" .Release.Name (default "elasticsearch" .Values.component) -}}
{{- default $default .Values.auth.secretName -}}
{{- end -}}

{{/* The sibling chart's Service in this release (CHT-43, name rule per
DD-247 — each chart duplicates the join it makes): "" derives
<release>-<name>, shortened when the release name already prefixes it. */}}
{{- define "atlas-elasticsearch.siblingService" -}}
{{- if .override -}}
{{- .override -}}
{{- else -}}
{{- $name := .name -}}
{{- if hasPrefix (lower .release) (lower $name) -}}
{{- lower $name -}}
{{- else -}}
{{- printf "%s-%s" .release $name -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* The issuer root the puller mints its ingest JWT against (CHT-41,
DD-265): the public name, split-horizon-resolved in-cluster. */}}
{{- define "atlas-elasticsearch.keycloakHost" -}}
{{- if .Values.global.issuer.url -}}
{{- $u := trimSuffix "/" (trimPrefix "https://" (trimPrefix "http://" .Values.global.issuer.url)) -}}
{{- $u | trimSuffix "/" | splitList "/" | first -}}
{{- else -}}
{{- printf "keycloak.%s" (required "global.domain or global.issuer.url is required (the puller mints ingest tokens against the issuer)" .Values.global.domain) -}}
{{- end -}}
{{- end -}}
{{- define "atlas-elasticsearch.issuerUrl" -}}
{{- $url := default (printf "https://%s" (include "atlas-elasticsearch.keycloakHost" .)) .Values.global.issuer.url -}}
{{- trimSuffix "/" $url -}}
{{- end -}}

{{/* The metrics puller (CHT-43, DD-266): its name, and its own label pair —
the store's selectorLabels would also match the puller's pods, so the
puller carries its own name/instance pair (the labelsPG pattern). */}}
{{- define "atlas-elasticsearch.pullerName" -}}
{{- printf "%s-metrics-puller" (include "atlas-elasticsearch.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "atlas-elasticsearch.pullerSelectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-elasticsearch.pullerName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "atlas-elasticsearch.pullerLabels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-elasticsearch.pullerName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-elasticsearch.versionLabel" . | quote }}
app.kubernetes.io/component: metrics-puller
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-elasticsearch.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-elasticsearch.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-elasticsearch.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-elasticsearch.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-elasticsearch.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-elasticsearch.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* The store image (upstream dhi.io mirror, chart-pinned — not global.image). */}}
{{- define "atlas-elasticsearch.image" -}}
{{- $name := required "image.repository is required (the store image)" .Values.image.repository -}}
{{- $tag := required "image.tag is required (the store image tag travels with the chart)" .Values.image.tag -}}
{{- printf "%s:%s" $name $tag -}}
{{- end -}}

{{/* The coredump-agent image (an Aurelius image: global.image registry/namespace,
DD-255). tag "" takes the chart appVersion the release sets. */}}
{{- define "atlas-elasticsearch.agentImage" -}}
{{- $registry := default "ghcr.io" .Values.global.image.registry -}}
{{- $namespace := default "aureliusenterprise" .Values.global.image.namespace -}}
{{- $name := required "agent.image.name is required" .Values.agent.image.name -}}
{{- $tag := default .Chart.AppVersion .Values.agent.image.tag -}}
{{- printf "%s/%s/%s:%s" $registry $namespace $name $tag -}}
{{- end -}}

{{/* ES_JAVA_OPTS (CHT-15): the heap flags, the coredump javaagent, then extras. */}}
{{- define "atlas-elasticsearch.javaOpts" -}}
{{- $opts := printf "-Xms%s -Xmx%s -javaagent:/agent/coredump-noop.jar" .Values.heap .Values.heap -}}
{{- with .Values.extraJavaOpts -}}
{{- $opts = printf "%s %s" $opts . -}}
{{- end -}}
{{- $opts -}}
{{- end -}}

{{/*
The healthcheck command (CHT-14, DD-008): the compose healthcheck's shape as a
shell one-liner — openssl over TLS, CA-pinned, authenticated as elastic; a
green-or-yellow cluster health answers healthy. The hardened image has no curl.
*/}}
{{- define "atlas-elasticsearch.healthcheck" -}}
printf 'GET /_cluster/health HTTP/1.1\r\nHost: localhost\r\nAuthorization: Basic %s\r\nConnection: close\r\n\r\n' "$(printf 'elastic:%s' "$ELASTIC_PASSWORD" | base64 -w0)" | timeout {{ int .Values.probes.timeoutSeconds }} openssl s_client -quiet -verify_return_error -CAfile {{ .Values.tls.mountPath }}/ca.pem -connect localhost:{{ int .Values.service.port }} 2>/dev/null | grep -qE '"status":"(green|yellow)"'
{{- end -}}

{{- define "atlas-elasticsearch.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-elasticsearch.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-elasticsearch.getValueAt" -}}
{{- $parts := splitList "." .path -}}
{{- $node := .root -}}
{{- range $parts -}}
{{- if kindIs "map" $node -}}
{{- $node = get $node . -}}
{{- else -}}
{{- /* The Go template parser has no nil literal (helm 4): "" marks absent. */ -}}
{{- $node = "" -}}
{{- end -}}
{{- end -}}
{{- if or (kindIs "string" $node) (kindIs "numeric" $node) (kindIs "bool" $node) -}}
{{- $node -}}
{{- end -}}
{{- end -}}
