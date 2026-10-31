# Trivy misconfig ignore-policy for the helm-config-scan target (DD-282).
#
# Trivy queries data.trivy.ignore over each finding, so this file must stay in
# `package trivy` and the rule must be named `ignore`. Keep it minimal: silence
# only verified false positives, never a whole rule.
package trivy

default ignore = false

# KSV-0109 flags "secrets" stored in ConfigMaps. The metrics-puller ConfigMaps
# hold prometheus oauth2 client-secret / basic-auth password entries whose
# values are `${env:...}` placeholders resolved from mounted secrets at runtime
# (DD-282 R5) - no secret material is in the chart. Scoped to those two
# ConfigMaps by name; KSV-0109 stays live for everything else.
ignore {
	input.ID == "KSV-0109"
	contains(input.Message, "-metrics-puller' in ")
}
