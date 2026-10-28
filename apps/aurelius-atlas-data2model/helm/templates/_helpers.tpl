{{/*
atlas-data2model helpers. Chart-local by design (DD-247): every chart carries the
helpers it uses, the way the Helm ecosystem's own scaffolding does — no shared
library chart to version, publish, or keep in sync. The shared shape these
encode (the global.* contract, the label set, the ADR 018 guard) is a
convention the charts follow, not code they share.
*/}}

{{- define "atlas-data2model.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-data2model.fullname" -}}
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

{{- define "atlas-data2model.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-data2model.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-data2model.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-data2model.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-data2model.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-data2model.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "atlas-data2model.image" -}}
{{- $registry := default "ghcr.io" .Values.global.image.registry -}}
{{- $namespace := default "aureliusenterprise" .Values.global.image.namespace -}}
{{- $name := required "image.name is required (the published image name, e.g. aurelius-atlas-server)" .Values.image.name -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s/%s/%s:%s" $registry $namespace $name $tag -}}
{{- end -}}

{{- define "atlas-data2model.issuerUrl" -}}
{{- $issuer := trimSuffix "/" (default "" .Values.global.issuer.url) -}}
{{- if not $issuer -}}
{{- $domain := trimSuffix "/" (default "" .Values.global.domain) -}}
{{- if $domain -}}
{{- $issuer = printf "https://keycloak.%s" $domain -}}
{{- end -}}
{{- end -}}
{{- $issuer -}}
{{- end -}}

{{- define "atlas-data2model.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-data2model.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-data2model.getValueAt" -}}
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
