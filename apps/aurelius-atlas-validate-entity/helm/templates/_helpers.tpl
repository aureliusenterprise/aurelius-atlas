{{/*
atlas-validate-entity helpers. Chart-local by design (DD-247): every chart carries the
helpers it uses, the way the Helm ecosystem's own scaffolding does — no shared
library chart to version, publish, or keep in sync. The shared shape these
encode (the global.* contract, the label set, the ADR 018 guard) is a
convention the charts follow, not code they share.
*/}}

{{- define "atlas-validate-entity.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-validate-entity.fullname" -}}
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

{{- define "atlas-validate-entity.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-validate-entity.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-validate-entity.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-validate-entity.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-validate-entity.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-validate-entity.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "atlas-validate-entity.image" -}}
{{- $registry := default "ghcr.io" .Values.global.image.registry -}}
{{- $namespace := default "aureliusenterprise" .Values.global.image.namespace -}}
{{- $name := required "image.name is required (the published image name, e.g. aurelius-atlas-server)" .Values.image.name -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s/%s/%s:%s" $registry $namespace $name $tag -}}
{{- end -}}

{{/* The sibling chart's Service in this release (CHT-42, name rule per
DD-247 — each chart duplicates the join it makes): "" derives
<release>-<name>, shortened when the release name already prefixes it. */}}
{{- define "atlas-validate-entity.siblingService" -}}
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

{{- define "atlas-validate-entity.issuerUrl" -}}
{{- $issuer := trimSuffix "/" (default "" .Values.global.issuer.url) -}}
{{- if not $issuer -}}
{{- $domain := trimSuffix "/" (default "" .Values.global.domain) -}}
{{- if $domain -}}
{{- $issuer = printf "https://keycloak.%s" $domain -}}
{{- end -}}
{{- end -}}
{{- $issuer -}}
{{- end -}}

{{- define "atlas-validate-entity.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-validate-entity.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-validate-entity.getValueAt" -}}
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
