{{/*
atlas-keycloak helpers. Chart-local by design (DD-247): every chart carries the
helpers it uses, the way the Helm ecosystem's own scaffolding does — no shared
library chart to version, publish, or keep in sync. The shared shape these
encode (the global.* contract, the label set, the ADR 018 guard) is a
convention the charts follow, not code they share.
*/}}

{{- define "atlas-keycloak.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-keycloak.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-keycloak.getValueAt" -}}
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

{{- define "atlas-keycloak.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-keycloak.fullname" -}}
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

{{/* The RSS headless Service JGroups discovers through (CHT-16). */}}
{{- define "atlas-keycloak.rssName" -}}
{{- printf "%s-rss" (include "atlas-keycloak.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* The bundled Postgres (a chart section, CHT-17). */}}
{{- define "atlas-keycloak.pgFullname" -}}
{{- printf "%s-postgres" (include "atlas-keycloak.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-keycloak.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-keycloak.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-keycloak.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-keycloak.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-keycloak.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-keycloak.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "atlas-keycloak.labelsPG" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-keycloak.pgFullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-keycloak.versionLabel" . | quote }}
app.kubernetes.io/component: postgres
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "atlas-keycloak.selectorLabelsPG" -}}
app.kubernetes.io/name: {{ include "atlas-keycloak.pgFullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "atlas-keycloak.image" -}}
{{- $name := required "image.repository is required (the Keycloak image)" .Values.image.repository -}}
{{- $tag := required "image.tag is required (the Keycloak image tag travels with the chart)" .Values.image.tag -}}
{{- printf "%s:%s" $name $tag -}}
{{- end -}}

{{- define "atlas-keycloak.pgImage" -}}
{{- $name := required "postgres.image.repository is required" .Values.postgres.image.repository -}}
{{- $tag := required "postgres.image.tag is required" .Values.postgres.image.tag -}}
{{- printf "%s:%s" $name $tag -}}
{{- end -}}

{{/*
The browser hostname KC_HOSTNAME pins (CHT-16 — the issuer-immutability
warning lives with this value). Precedence: hostname value, then the host
part of global.issuer.url, then keycloak.<domain> — the umbrella's host.
The last-resort <release>.localhost exists only so the bare `helm lint`/
`helm template` renders (helm.ts runs them without values) succeed; the
umbrella always sets global.domain, and the chart-contract suite pins each
chain step. A deploy without any of the three is caught by the 10.5 smoke,
not here.
*/}}
{{- define "atlas-keycloak.host" -}}
{{- if .Values.hostname -}}
{{- .Values.hostname -}}
{{- else if .Values.global.issuer.url -}}
{{- $u := trimSuffix "/" (trimPrefix "https://" (trimPrefix "http://" .Values.global.issuer.url)) -}}
{{- $u | trimSuffix "/" | splitList "/" | first -}}
{{- else if .Values.global.domain -}}
{{- printf "keycloak.%s" .Values.global.domain -}}
{{- else -}}
{{- printf "%s.localhost" .Release.Name -}}
{{- end -}}
{{- end -}}

{{/* The issuer root Keycloak must embed in tokens (CHT-16). Keycloak builds
it from KC_HOSTNAME + the proxy scheme; the umbrella's issuer.url must equal
https://<host> — validate.yaml guards it. */}}

{{/* Generated credential Secret names (CHT-19, DD-254) — <release>-<purpose>. */}}
{{- define "atlas-keycloak.adminSecretName" -}}
{{- default (printf "%s-keycloak-admin" .Release.Name) .Values.bootstrap.adminSecretName -}}
{{- end -}}

{{- define "atlas-keycloak.dbSecretName" -}}
{{- default (printf "%s-keycloak-database" .Release.Name) .Values.database.secretName -}}
{{- end -}}

{{- define "atlas-keycloak.usersSecretName" -}}
{{- default (printf "%s-keycloak-users" .Release.Name) .Values.realm.usersSecretName -}}
{{- end -}}

{{- define "atlas-keycloak.otelClientsSecretName" -}}
{{- default (printf "%s-otel-clients" .Release.Name) .Values.realm.otelClientsSecretName -}}
{{- end -}}

{{- define "atlas-keycloak.legacyTokenSecretName" -}}
{{- default (printf "%s-collector-legacy" .Release.Name) .Values.telemetry.tokenSecretName -}}
{{- end -}}

{{/* The TLS Secret carrying this pod's certificate + the issuer CA (CHT-16). */}}
{{- define "atlas-keycloak.tlsSecretName" -}}
{{- default (printf "%s-tls" (include "atlas-keycloak.fullname" .)) .Values.tls.secretName -}}
{{- end -}}

{{- define "atlas-keycloak.pgTlsSecretName" -}}
{{- printf "%s-tls" (include "atlas-keycloak.pgFullname" .) -}}
{{- end -}}

{{- define "atlas-keycloak.caPath" -}}
{{- printf "%s/ca.crt" (trimSuffix "/" .Values.tls.mountPath) -}}
{{- end -}}

{{/* The JDBC URL (CHT-17): bundled takes the in-cluster service + the
verify-full pin to the issuer CA; external supplies its own. */}}
{{- define "atlas-keycloak.jdbcUrl" -}}
{{- if .Values.database.url -}}
{{- .Values.database.url -}}
{{- else -}}
{{- printf "jdbc:postgresql://%s:%d/%s?sslmode=verify-full&sslrootcert=%s" (include "atlas-keycloak.pgFullname" .) (int .Values.postgres.service.port) .Values.postgres.auth.database (include "atlas-keycloak.caPath" .) -}}
{{- end -}}
{{- end -}}

{{/* JAVA_OPTS: the pinned heap (the dev compose's CI-cap lesson), the realm
placeholder resolution (DD-256), then extras. No truststore flags — the CA
mount is the trust path (CHT-16). */}}
{{- define "atlas-keycloak.javaOpts" -}}
{{- $opts := printf "-Xms%s -Xmx%s -Dkeycloak.migration.replace-placeholders=true" .Values.heap .Values.heap -}}
{{- with .Values.extraJavaOpts -}}
{{- $opts = printf "%s %s" $opts . -}}
{{- end -}}
{{- $opts -}}
{{- end -}}
