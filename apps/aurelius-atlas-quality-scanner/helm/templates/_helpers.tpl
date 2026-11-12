{{/*
atlas-quality-scanner helpers. Chart-local by design (DD-290): every chart
carries the helpers it uses; the convention is the dedupe, not a shared library
(the tree rejects a library chart, DD-290). The batch shape (DD-508): this
chart installs standalone, never through the umbrella, so it derives its
identity from its own values with the same name rules the umbrella charts use.
*/}}

{{- define "atlas-quality-scanner.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-quality-scanner.fullname" -}}
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

{{- define "atlas-quality-scanner.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-quality-scanner.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-quality-scanner.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-quality-scanner.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-quality-scanner.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-quality-scanner.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "atlas-quality-scanner.image" -}}
{{- $registry := default "ghcr.io" .Values.global.image.registry -}}
{{- $namespace := default "aureliusenterprise" .Values.global.image.namespace -}}
{{- $name := required "image.name is required (the published image name, e.g. aurelius-atlas-quality-scanner)" .Values.image.name -}}
{{- $base := printf "%s/%s/%s" $registry $namespace $name -}}
{{- with .Values.image.digest -}}
{{- printf "%s@%s" $base . -}}
{{- else -}}
{{- printf "%s:%s" $base (default .Chart.AppVersion $.Values.image.tag) -}}
{{- end -}}
{{- end -}}

{{/* The Keycloak realm the mint URL names (CHT-74): global.realm, whose chart
default is the production realm. */}}
{{- define "atlas-quality-scanner.realm" -}}
{{- default "aurelius-atlas" .Values.global.realm -}}
{{- end -}}

{{/* The issuer root the job mints against (CHT-116): global.issuer.url, whose
fallback derives from global.domain exactly as the service charts derive it. */}}
{{- define "atlas-quality-scanner.issuerUrl" -}}
{{- $issuer := trimSuffix "/" (default "" .Values.global.issuer.url) -}}
{{- if not $issuer -}}
{{- $domain := trimSuffix "/" (default "" .Values.global.domain) -}}
{{- if $domain -}}
{{- $issuer = printf "https://keycloak.%s" $domain -}}
{{- end -}}
{{- end -}}
{{- $issuer -}}
{{- end -}}

{{/* The token endpoint (the mint the client credentials go to, CHT-116). */}}
{{- define "atlas-quality-scanner.tokenUrl" -}}
{{- printf "%s/realms/%s/protocol/openid-connect/token" (include "atlas-quality-scanner.issuerUrl" .) (include "atlas-quality-scanner.realm" .) -}}
{{- end -}}

{{/* The identity Secret and its key (CHT-116, DD-509): "" derives
<release>-scanner-clients and the client id — the deployment's own Secret. */}}
{{- define "atlas-quality-scanner.secretName" -}}
{{- default (printf "%s-scanner-clients" .Release.Name) .Values.auth.secretName -}}
{{- end -}}

{{- define "atlas-quality-scanner.secretKey" -}}
{{- default .Values.auth.clientId .Values.auth.secretKey -}}
{{- end -}}

{{/* The ingest client the OTLP mint names (CHT-125, DD-511): "" reuses the
job's own catalogue client — one registered client, two audiences (DD-514's
reuse rule). */}}
{{- define "atlas-quality-scanner.otelClientId" -}}
{{- default .Values.auth.clientId .Values.telemetry.auth.clientId -}}
{{- end -}}

{{/* The Secret holding the ingest client's secret (CHT-125): "" reuses the
identity Secret the job reads (CHT-116's join), key defaulting to the ingest
client id. */}}
{{- define "atlas-quality-scanner.otelSecretName" -}}
{{- default (include "atlas-quality-scanner.secretName" .) .Values.telemetry.auth.secretName -}}
{{- end -}}

{{- define "atlas-quality-scanner.otelSecretKey" -}}
{{- default (include "atlas-quality-scanner.otelClientId" .) .Values.telemetry.auth.secretKey -}}
{{- end -}}

{{/* The CA Secret to mount, if any (CHT-117): chart value over global. ""
means "system trust", and no volume renders. */}}
{{- define "atlas-quality-scanner.caSecretName" -}}
{{- default .Values.global.trust.caSecretName .Values.trust.caSecretName -}}
{{- end -}}

{{- define "atlas-quality-scanner.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-quality-scanner.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-quality-scanner.getValueAt" -}}
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
