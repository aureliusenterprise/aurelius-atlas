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

{{/* The realm this chart imports (CHT-74): realm.name, then global.realm,
then the chart default (the hardened production realm). The asset
files/<name>.json must exist or the realm ConfigMap's render fails
(CHT-78). */}}
{{- define "atlas-keycloak.realmName" -}}
{{- $name := default .Values.global.realm .Values.realm.name -}}
{{- default "aurelius-atlas" $name -}}
{{- end -}}

{{/*
The browser hosts the realm asset's redirect URIs / web origins substitute
for (CHT-77). They mirror the umbrella's host rule (its
aurelius-atlas.atlasHost/dashboardHost) so a standalone render derives the
same hosts: an explicit host wins, else <name>.<domain>; the last-resort
<release>.localhost exists only so the bare helm lint/template renders
succeed — the realm ConfigMap itself fails render when no domain, issuer
URL, or host is set anywhere and the asset needs one.
*/}}
{{- define "atlas-keycloak.atlasHost" -}}
{{- if .Values.global.hosts.atlas.host -}}
{{- .Values.global.hosts.atlas.host -}}
{{- else if .Values.global.domain -}}
{{- printf "atlas.%s" .Values.global.domain -}}
{{- else -}}
{{- printf "%s.localhost" .Release.Name -}}
{{- end -}}
{{- end -}}

{{- define "atlas-keycloak.dashboardHost" -}}
{{- if .Values.global.hosts.dashboard.host -}}
{{- .Values.global.hosts.dashboard.host -}}
{{- else if .Values.global.domain -}}
{{- printf "dashboard.%s" .Values.global.domain -}}
{{- else -}}
{{- printf "%s.localhost" .Release.Name -}}
{{- end -}}
{{- end -}}

{{/* The Grafana host the grafana client's redirect URIs substitute for
(CHT-82): same rule as the browser hosts above, so a standalone render
derives what the umbrella's aurelius-atlas.grafanaHost would. */}}
{{- define "atlas-keycloak.grafanaHost" -}}
{{- if .Values.global.hosts.grafana.host -}}
{{- .Values.global.hosts.grafana.host -}}
{{- else if .Values.global.domain -}}
{{- printf "grafana.%s" .Values.global.domain -}}
{{- else -}}
{{- printf "%s.localhost" .Release.Name -}}
{{- end -}}
{{- end -}}

{{- define "atlas-keycloak.otelClientsSecretName" -}}
{{- default (printf "%s-otel-clients" .Release.Name) .Values.realm.otelClientsSecretName -}}
{{- end -}}

{{/* The otel-* ingest clients (CHT-87/89 roster) as a JSON array: each
carries its own placeholder ${<ID upper, - → _>_CLIENT_SECRET} in the prod
asset and its own Secret key/env. Chart-local copy (DD-247); the
chart-contract suite pins it against files/aurelius-atlas.json. */}}
{{- define "atlas-keycloak.otelClients" -}}
{{- `["otel-atlas-server","otel-data2model","otel-elasticsearch","otel-keycloak","otel-lineage-model","otel-postgres","otel-validate-entity"]` -}}
{{- end -}}

{{- define "atlas-keycloak.grafanaOauthSecretName" -}}
{{- default (printf "%s-grafana-oauth" .Release.Name) .Values.realm.grafanaOauthSecretName -}}
{{- end -}}

{{- define "atlas-keycloak.legacyTokenSecretName" -}}
{{- default (printf "%s-collector-legacy" .Release.Name) .Values.telemetry.tokenSecretName -}}
{{- end -}}

{{/* The sibling chart's Service in this release (CHT-42, name rule per
DD-247 — each chart duplicates the join it makes): "" derives
<release>-<name>, shortened when the release name already prefixes it. */}}
{{- define "atlas-keycloak.siblingService" -}}
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

{{/* The collector legacy-leg endpoint Keycloak exports to (CHT-42): the
explicit value wins, else the derived sibling name + port when enabled. */}}
{{- define "atlas-keycloak.telemetryEndpoint" -}}
{{- if .Values.telemetry.endpoint -}}
{{- .Values.telemetry.endpoint -}}
{{- else if .Values.telemetry.enabled -}}
{{- $collector := include "atlas-keycloak.siblingService" (dict "name" "atlas-observability" "release" .Release.Name "override" .Values.telemetry.service) -}}
{{- printf "https://%s:%d" $collector (int .Values.telemetry.port) -}}
{{- end -}}
{{- end -}}

{{/* The issuer root in-cluster producers reach by public name (DD-265 —
CoreDNS resolves it to this Service, :443 answers). */}}
{{- define "atlas-keycloak.issuerUrl" -}}
{{- $url := default (printf "https://%s" (include "atlas-keycloak.host" .)) .Values.global.issuer.url -}}
{{- trimSuffix "/" $url -}}
{{- end -}}

{{/* The metrics puller (CHT-43, DD-266): its name, and its own label pair —
the server's selectorLabels would also match the puller's pods, so the
puller carries its own name/instance pair (the labelsPG pattern). */}}
{{- define "atlas-keycloak.pullerName" -}}
{{- printf "%s-metrics-puller" (include "atlas-keycloak.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "atlas-keycloak.pullerSelectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-keycloak.pullerName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "atlas-keycloak.pullerLabels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-keycloak.pullerName" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-keycloak.versionLabel" . | quote }}
app.kubernetes.io/component: metrics-puller
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
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
