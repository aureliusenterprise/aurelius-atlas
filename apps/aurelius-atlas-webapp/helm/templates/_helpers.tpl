{{/*
atlas-webapp helpers. Chart-local by design (DD-247): every chart carries the
helpers it uses, the way the Helm ecosystem's own scaffolding does — no shared
library chart to version, publish, or keep in sync. The shared shape these
encode (the global.* contract, the label set, the ADR 018 guard) is a
convention the charts follow, not code they share.
*/}}

{{- define "atlas-webapp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-webapp.fullname" -}}
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

{{- define "atlas-webapp.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-webapp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-webapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "atlas-webapp.image" -}}
{{- $registry := default "ghcr.io" .Values.global.image.registry -}}
{{- $namespace := default "aureliusenterprise" .Values.global.image.namespace -}}
{{- $name := required "image.name is required (the published image name, e.g. aurelius-atlas-webapp)" .Values.image.name -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s/%s/%s:%s" $registry $namespace $name $tag -}}
{{- end -}}

{{/* The browser host Keycloak answers on; mirrors the umbrella's helper so a
standalone render derives the same name (CHT-03). */}}
{{- define "atlas-webapp.keycloakHost" -}}
{{- if .Values.global.issuer.url -}}
{{- $u := trimSuffix "/" (trimPrefix "https://" (trimPrefix "http://" .Values.global.issuer.url)) -}}
{{- $u | trimSuffix "/" | splitList "/" | first -}}
{{- else -}}
{{- printf "keycloak.%s" (required "global.domain or global.issuer.url is required (the CSP needs the Keycloak origin)" .Values.global.domain) -}}
{{- end -}}
{{- end -}}

{{/* The Keycloak issuer root (CHT-03): an explicit URL wins, else the derived
keycloak host. */}}
{{- define "atlas-webapp.issuerUrl" -}}
{{- $url := default (printf "https://%s" (include "atlas-webapp.keycloakHost" .)) .Values.global.issuer.url -}}
{{- trimSuffix "/" $url -}}
{{- end -}}

{{/* The Keycloak realm /config.json names for the SPA (CHT-74): global.realm,
whose chart default is the production realm. */}}
{{- define "atlas-webapp.realm" -}}
{{- default "aurelius-atlas" .Values.global.realm -}}
{{- end -}}

{{/*
A sibling chart's Service by chart name (CHT-25): "override" wins, else this
release's name under the store chart's fullname rule (CHT-13) — a release name
that prefixes the chart name yields the bare chart name.
*/}}
{{- define "atlas-webapp.siblingService" -}}
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

{{/* The atlas-server Service this nginx proxies /api/ to (CHT-25). */}}
{{- define "atlas-webapp.serverService" -}}
{{- include "atlas-webapp.siblingService" (dict "name" "atlas-server" "release" .Release.Name "override" .Values.server.service) -}}
{{- end -}}

{{/* The collector Service this nginx proxies /otel/ to (CHT-25; the workload
itself is 10.3b). */}}
{{- define "atlas-webapp.collectorService" -}}
{{- include "atlas-webapp.siblingService" (dict "name" "atlas-observability" "release" .Release.Name "override" .Values.collector.service) -}}
{{- end -}}

{{/*
The Secret carrying the trust root (key: ca.crt) this nginx pins as a TLS
client (CHT-25, DD-259): explicit value wins, else the chain's CA named by the
issuer — the same default as the umbrella's helper.
*/}}
{{- define "atlas-webapp.caSecretName" -}}
{{- default (printf "%s-ca" .Values.global.trust.issuerRef.name) (default .Values.tls.secretName .Values.global.trust.caSecretName) -}}
{{- end -}}

{{/*
The leaf Secret this nginx serves its TLS listener with (DD-270): its own
Certificate's output; tls.certSecretName brings your own. tls.crt / tls.key,
the cert-manager convention (the server chart's rule).
*/}}
{{- define "atlas-webapp.tlsSecretName" -}}
{{- default (printf "%s-tls" (include "atlas-webapp.fullname" .)) .Values.tls.certSecretName -}}
{{- end -}}

{{- define "atlas-webapp.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-webapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-webapp.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-webapp.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-webapp.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-webapp.getValueAt" -}}
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
