{{/*
Umbrella helpers: the derived names every template and subchart reads.
The subcharts default these identically for a standalone render; the umbrella
is the source of truth (CHT-03).
*/}}

{{/* Shared labels every umbrella-owned resource carries. */}}
{{- define "aurelius-atlas.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ default "undefined" .Chart.AppVersion | toString | trunc 63 | trimSuffix "-" | quote }}
app.kubernetes.io/part-of: aurelius-atlas
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{/* The namespace the system installs into. */}}
{{- define "aurelius-atlas.namespace" -}}
{{- required "global.namespace is required (the values file ships a default)" .Values.global.namespace -}}
{{- end -}}

{{/* Browser base domain (one value retargets a cluster). */}}
{{- define "aurelius-atlas.domain" -}}
{{- required "global.domain is required (the base domain the hosts derive from)" .Values.global.domain -}}
{{- end -}}

{{/* The Keycloak issuer root the components verify tokens against. */}}
{{- define "aurelius-atlas.issuerUrl" -}}
{{- $url := default (printf "https://%s" (include "aurelius-atlas.keycloakHost" .)) .Values.global.issuer.url -}}
{{- trimSuffix "/" $url -}}
{{- end -}}

{{/* Browser hosts (CHT-03). A host set in values wins; the default derives from the domain. */}}
{{- define "aurelius-atlas.atlasHost" -}}
{{- default (printf "atlas.%s" (include "aurelius-atlas.domain" .)) .Values.global.hosts.atlas.host -}}
{{- end -}}

{{- define "aurelius-atlas.keycloakHost" -}}
{{- default (printf "keycloak.%s" (include "aurelius-atlas.domain" .)) .Values.global.hosts.keycloak.host -}}
{{- end -}}

{{- define "aurelius-atlas.dashboardHost" -}}
{{- default (printf "dashboard.%s" (include "aurelius-atlas.domain" .)) .Values.global.hosts.dashboard.host -}}
{{- end -}}

{{- define "aurelius-atlas.grafanaHost" -}}
{{- default (printf "grafana.%s" (include "aurelius-atlas.domain" .)) .Values.global.hosts.grafana.host -}}
{{- end -}}

{{/*
The Secret carrying the trust root (key: ca.crt) the components pin by file
(DD-243). Explicit value wins; cert-manager's self-signed issuer names its CA
secret "<issuer>-ca".
*/}}
{{- define "aurelius-atlas.caSecretName" -}}
{{- default (printf "%s-ca" .Values.global.trust.issuerRef.name) .Values.global.trust.caSecretName -}}
{{- end -}}

{{/* Shared credential Secret names (DD-244); component charts consume by name. */}}
{{- define "aurelius-atlas.secretName" -}}
{{- printf "%s-%s" .Release.Name .purpose -}}
{{- end -}}

{{/*
A co-deployed component's Service name, from the release-prefix rule the
component charts use for their own names (CHT-13): release `atlas` +
component `atlas-server` → `atlas-server`; release `atlas-prod` + the same
component → `atlas-prod-atlas-server`. The umbrella owns the edge and joins
routes to services by this name; each chart names itself identically, so the
two sides of the join cannot drift while the rule is the same. `override`
(a values knob) short-circuits.
*/}}
{{- define "aurelius-atlas.componentService" -}}
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

{{/*
The edge listener set (CHT-29/30) as JSON, so gateway.yaml, httproutes.yaml,
and certificate-edge.yaml share one derivation. One entry per enabled browser
host whose component is also enabled — a route to a disabled backend is a
404-generating corpse. secret = the listener's termination Secret;
backend/port = the single coarse backend (DD-242: routing is host-level, the
webapp's /api and /otel proxy is the tested data path); tlsBackend = the
backend speaks TLS and gets the BackendTLSPolicy trust pin (CHT-30).
*/}}
{{- define "aurelius-atlas.edge.listeners" -}}
{{- $l := list -}}
{{- $webapp := index .Values "atlas-webapp" | default dict -}}
{{- $keycloak := index .Values "atlas-keycloak" | default dict -}}
{{- $server := index .Values "atlas-server" | default dict -}}
{{- $obs := index .Values "atlas-observability" | default dict -}}
{{- if and .Values.global.hosts.atlas.enabled $webapp.enabled -}}
{{- $l = append $l (dict "name" "atlas" "host" (include "aurelius-atlas.atlasHost" .) "secret" (printf "%s-edge-tls" .Release.Name) "backend" (include "aurelius-atlas.componentService" (dict "name" "atlas-webapp" "release" .Release.Name "override" .Values.global.hosts.atlas.service)) "port" (int .Values.global.hosts.atlas.port) "tlsBackend" true) -}}
{{- end -}}
{{- if and .Values.global.hosts.keycloak.enabled $keycloak.enabled -}}
{{- $kc := include "aurelius-atlas.componentService" (dict "name" "atlas-keycloak" "release" .Release.Name "override" .Values.global.hosts.keycloak.service) -}}
{{- $l = append $l (dict "name" "keycloak" "host" (include "aurelius-atlas.keycloakHost" .) "secret" (printf "%s-tls" $kc) "backend" $kc "port" (int .Values.global.hosts.keycloak.port) "tlsBackend" true) -}}
{{- end -}}
{{- if and .Values.global.hosts.dashboard.enabled $server.enabled -}}
{{- $srv := include "aurelius-atlas.componentService" (dict "name" "atlas-server" "release" .Release.Name "override" .Values.global.hosts.dashboard.service) -}}
{{- $l = append $l (dict "name" "dashboard" "host" (include "aurelius-atlas.dashboardHost" .) "secret" (printf "%s-edge-tls" .Release.Name) "backend" $srv "port" (int .Values.global.hosts.dashboard.port) "tlsBackend" true) -}}
{{- end -}}
{{- if and .Values.global.hosts.grafana.enabled $obs.enabled -}}
{{- $l = append $l (dict "name" "grafana" "host" (include "aurelius-atlas.grafanaHost" .) "secret" (printf "%s-edge-tls" .Release.Name) "backend" (include "aurelius-atlas.componentService" (dict "name" "atlas-observability-grafana" "release" .Release.Name "override" .Values.global.hosts.grafana.service)) "port" (int .Values.global.hosts.grafana.port) "tlsBackend" false) -}}
{{- end -}}
{{- toJson $l -}}
{{- end -}}

{{/*
Render-time value validation (ADR 018's spirit: a bad deployment fails at
install, loudly, not at first request). Renders nothing; fails the render.
*/}}
{{- define "aurelius-atlas.validate" -}}
{{- $e := list -}}
{{- if not .Values.global.domain -}}
{{- $e = append $e "global.domain is required (the base domain the browser hosts derive from)" -}}
{{- end -}}
{{- if not .Values.global.namespace -}}
{{- $e = append $e "global.namespace is required" -}}
{{- end -}}
{{- if not .Values.global.trust.issuerRef.name -}}
{{- $e = append $e "global.trust.issuerRef.name is required (the issuer signing every certificate, DD-243)" -}}
{{- end -}}
{{- if and .Values.global.hosts.atlas.enabled (not (include "aurelius-atlas.atlasHost" .)) -}}
{{- $e = append $e "global.hosts.atlas.host resolves empty — set global.domain or the host" -}}
{{- end -}}
{{- if $e -}}
{{- fail (printf "Invalid values:\n  - %s" (join "\n  - " $e)) -}}
{{- end -}}
{{- end -}}
