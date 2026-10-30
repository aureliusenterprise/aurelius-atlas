{{/*
atlas-server helpers. Chart-local by design (DD-247): every chart carries the
helpers it uses, the way the Helm ecosystem's own scaffolding does — no shared
library chart to version, publish, or keep in sync. The shared shape these
encode (the global.* contract, the label set, the ADR 018 guard) is a
convention the charts follow, not code they share.
*/}}

{{- define "atlas-server.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-server.fullname" -}}
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

{{- define "atlas-server.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* The image reference (CHT-21): <registry>/<namespace>/<name>:<tag>; the tag
defaults to the chart's appVersion, which the release sets to the image tag
(DD-245). */}}
{{- define "atlas-server.image" -}}
{{- $registry := default "ghcr.io" .Values.global.image.registry -}}
{{- $namespace := default "aureliusenterprise" .Values.global.image.namespace -}}
{{- $name := required "image.name is required (the published image name, e.g. aurelius-atlas-server)" .Values.image.name -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s/%s/%s:%s" $registry $namespace $name $tag -}}
{{- end -}}

{{/* The browser host Keycloak answers on; mirrors the umbrella's helper so a
standalone render derives the same name (CHT-03). */}}
{{- define "atlas-server.keycloakHost" -}}
{{- if .Values.global.issuer.url -}}
{{- $u := trimSuffix "/" (trimPrefix "https://" (trimPrefix "http://" .Values.global.issuer.url)) -}}
{{- $u | trimSuffix "/" | splitList "/" | first -}}
{{- else -}}
{{- printf "keycloak.%s" (required "global.domain or global.issuer.url is required (the issuer the server verifies tokens against)" .Values.global.domain) -}}
{{- end -}}
{{- end -}}

{{/* The Keycloak issuer root (CHT-03): an explicit URL wins, else the derived
keycloak host. */}}
{{- define "atlas-server.issuerUrl" -}}
{{- $url := default (printf "https://%s" (include "atlas-server.keycloakHost" .)) .Values.global.issuer.url -}}
{{- trimSuffix "/" $url -}}
{{- end -}}

{{/* The Keycloak realm the OTLP mint URL names (CHT-74): global.realm, whose
chart default is the production realm. */}}
{{- define "atlas-server.realm" -}}
{{- default "aurelius-atlas" .Values.global.realm -}}
{{- end -}}

{{/*
The Elasticsearch Service this server dials (CHT-21). "" derives the sibling
chart's name in this release — the store chart's fullname rule (its
atlas-elasticsearch.fullname), duplicated per DD-247 (chart-local helpers):
a release name that prefixes the chart name yields the bare chart name.
*/}}
{{- define "atlas-server.storeService" -}}
{{- if .Values.store.service -}}
{{- .Values.store.service -}}
{{- else -}}
{{- $name := "atlas-elasticsearch" -}}
{{- if hasPrefix (lower .Release.Name) (lower $name) -}}
{{- lower $name -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* A sibling chart's Service by chart name (the collector, 10.3b) — the same
fullname rule as storeService. */}}
{{- define "atlas-server.siblingService" -}}
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

{{/* The TLS Secret this server mounts (CHT-21/22): its own Certificate's
output; tls.secretName brings your own. */}}
{{- define "atlas-server.tlsSecretName" -}}
{{- default (printf "%s-tls" (include "atlas-server.fullname" .)) .Values.tls.secretName -}}
{{- end -}}

{{- define "atlas-server.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-server.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "atlas-server.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-server.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-server.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-server.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-server.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-server.getValueAt" -}}
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
