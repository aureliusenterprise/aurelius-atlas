{{/*
atlas-observability helpers. Chart-local by design (DD-247): every chart carries the
helpers it uses, the way the Helm ecosystem's own scaffolding does — no shared
library chart to version, publish, or keep in sync. The shared shape these
encode (the global.* contract, the label set, the ADR 018 guard) is a
convention the charts follow, not code they share.
*/}}

{{- define "atlas-observability.requireValues" -}}
{{- $missing := list -}}
{{- with .values.required }}
{{- range . }}
{{- $value := include "atlas-observability.getValueAt" (dict "root" $.values "path" .key) -}}
{{- if not $value -}}
{{- $missing = append $missing .message -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- with $missing -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " .)) -}}
{{- end -}}
{{- end -}}

{{- define "atlas-observability.getValueAt" -}}
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

{{- define "atlas-observability.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "atlas-observability.fullname" -}}
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

{{- define "atlas-observability.versionLabel" -}}
{{- default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* A component image: <registry>/<name>:<tag> with the dhi.io defaults the
values file names. Unlike the app images (global.image), these are upstream
hardened images and travel under their own repository (the store chart's
rule). */}}
{{/* A chart-pinned component image (CHT-92): repository + tag (or the
helper's defaultTag), with the digest winning when set (CHT-93). */}}
{{- define "atlas-observability.componentImage" -}}
{{- if .digest -}}
{{- printf "%s@%s" .repository .digest -}}
{{- else -}}
{{- printf "%s:%s" .repository (default .defaultTag .tag) -}}
{{- end -}}
{{- end -}}

{{/* The browser host Keycloak answers on; mirrors the umbrella's helper so a
standalone render derives the same name (CHT-03). */}}
{{- define "atlas-observability.keycloakHost" -}}
{{- if .Values.global.issuer.url -}}
{{- $u := trimSuffix "/" (trimPrefix "https://" (trimPrefix "http://" .Values.global.issuer.url)) -}}
{{- $u | trimSuffix "/" | splitList "/" | first -}}
{{- else -}}
{{- printf "keycloak.%s" (required "global.domain or global.issuer.url is required (the issuer the collector validates ingest tokens against)" .Values.global.domain) -}}
{{- end -}}
{{- end -}}

{{/* The issuer root the collector's oidc extension validates against
(CHT-34): the public URL (DD-265 — in-cluster DNS resolves it too). */}}
{{- define "atlas-observability.issuerUrl" -}}
{{- $url := default (printf "https://%s" (include "atlas-observability.keycloakHost" .)) .Values.global.issuer.url -}}
{{- trimSuffix "/" $url -}}
{{- end -}}

{{/* The realm the ingest audience mints in (CHT-74): global.realm, whose
chart default is the production realm. */}}
{{- define "atlas-observability.realm" -}}
{{- default "aurelius-atlas" .Values.global.realm -}}
{{- end -}}

{{/* The namespace this chart's resources land in. */}}
{{- define "atlas-observability.namespace" -}}
{{- default .Release.Namespace .Values.global.namespace -}}
{{- end -}}

{{/* The legacy-leg token Secret (CHT-35): <release>-collector-legacy, the
umbrella's generated credential (DD-244); secrets.collectorLegacy brings
your own. */}}
{{- define "atlas-observability.legacySecretName" -}}
{{- default (printf "%s-collector-legacy" .Release.Name) .Values.secrets.collectorLegacy -}}
{{- end -}}

{{/* The Grafana admin Secret (DD-267): <release>-grafana-admin, the
umbrella's generated credential; grafana.adminPasswordSecret brings your
own. */}}
{{- define "atlas-observability.grafanaAdminSecretName" -}}
{{- default (printf "%s-grafana-admin" .Release.Name) .Values.grafana.adminPasswordSecret -}}
{{- end -}}

{{/* The Grafana OAuth client Secret (CHT-83/84, DD-275):
<release>-grafana-oauth, the umbrella's generated credential the realm
import reads too (its key is the ${GRAFANA_CLIENT_SECRET} placeholder);
grafana.oauthSecretName brings your own. */}}
{{- define "atlas-observability.grafanaOauthSecretName" -}}
{{- default (printf "%s-grafana-oauth" .Release.Name) .Values.grafana.oauthSecretName -}}
{{- end -}}

{{/* The collector's TLS Secret (CHT-36): its own Certificate's output;
tls.secretName brings your own. */}}
{{- define "atlas-observability.tlsSecretName" -}}
{{- default (printf "%s-tls" (include "atlas-observability.fullname" .)) .Values.tls.secretName -}}
{{- end -}}

{{- define "atlas-observability.selectorLabels" -}}
app.kubernetes.io/name: {{ include "atlas-observability.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
A peer's pod name for NetworkPolicy selectors (CHT-70, DD-271). External
workload pods carry their chart name as app.kubernetes.io/name (a constant),
but another chart's fullname-derived workloads (its metrics pullers) carry
<fullname>-suffix — the same release-prefix rule as every sibling join, so
this helper is the CHT-13 name rule speaking about pods instead of Services.
An override renames the peer (networkPolicy.peers.<peer>).
*/}}
{{- define "atlas-observability.peerName" -}}
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

{{/* One peer's podSelector block (name = chart-name constant or fullname-
derived puller name; component only where a chart shares one name, CHT-70). */}}
{{- define "atlas-observability.peerFrom" -}}
-   podSelector:
        matchLabels:
            app.kubernetes.io/name: {{ .name | quote }}
            app.kubernetes.io/instance: {{ .release | quote }}
            {{- with .component }}
            app.kubernetes.io/component: {{ . | quote }}
            {{- end }}
{{- end -}}

{{/* A list of peers, each rendered by peerFrom (concatenated — the caller
nindents the whole run). */}}
{{- define "atlas-observability.peerFromList" -}}
{{- $out := "" -}}
{{- range $p := . -}}
{{- $out = printf "%s\n%s" $out (include "atlas-observability.peerFrom" $p) -}}
{{- end -}}
{{- trim $out -}}
{{- end -}}

{{- define "atlas-observability.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "atlas-observability.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ include "atlas-observability.versionLabel" . | quote }}
app.kubernetes.io/component: {{ default .Chart.Name .Values.component }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}
