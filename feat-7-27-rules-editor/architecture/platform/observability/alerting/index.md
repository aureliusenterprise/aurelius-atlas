# Alerting

The conditions worth announcing, where they are sent, and how to see one fire (ADR 040). The rules are Grafana-managed: `dev/observability/config/grafana/alerting/rules.yaml`, byte-copied into the observability chart. Every rule is labelled `team: maintainers`, the owner of the response ([Operations Ownership](<https://aureliusenterprise.github.io/feat-7-27-rules-editor/contributor-guide/operations-ownership/index.md>)).

## The conditions

| Rule | Severity | Fires when | For |
| --- | --- | --- | --- |
| Server silent | critical | the server sent no metrics in the last 5 minutes | 1m |
| Part silent | warning | a part sent signals in the last 6 hours and none in the last 10 minutes | — |
| Server errors | critical | more than 5% of the server's answers over 5 minutes are 5xx | 5m |
| Server slow | warning | the server's 95th-percentile latency over 5 minutes is above 2 seconds | 10m |
| Store red or silent | critical | Elasticsearch reports red, or its metrics stop | 2m |
| Collector down | critical | Prometheus cannot scrape the collector | 2m |
| Collector export failures | warning | the collector failed to deliver to Tempo, Prometheus or Loki | 5m |
| Snapshot overdue | critical | the store's last successful snapshot is more than two hours old | 15m |

Three of them watch silence: the server, every other part, and the collector itself. A part added later inherits "Part silent" as soon as it exports through the collector. Each rule's description in Grafana says what to check first, and its runbook link opens its section of [Incident Management](<https://aureliusenterprise.github.io/feat-7-27-rules-editor/architecture/platform/resilience/incident-management/index.md>), with the steps that follow. The [Monitoring](<https://aureliusenterprise.github.io/feat-7-27-rules-editor/architecture/platform/observability/monitoring/index.md>) dashboards hold the evidence.

## The destination

A cluster names its destination in the observability chart's values: a Secret whose key `url` is a webhook, such as a Slack or Teams incoming webhook or an incident tool's endpoint.

```
grafana:
    alerting:
        webhookSecret: atlas-alert-webhook
        repeatInterval: 4h
```

The chart then provisions the contact point `maintainers`, and a notification policy that sends every rule to it, grouped by rule and repeated every `repeatInterval` while it fires. Without the Secret, as in dev, no contact point exists: the rules fire in Grafana's alert list only (Alerting \> Alert rules).

## See one fire

In dev, with no server running, "Server silent" turns pending at its first evaluation and firing a minute later:

```
npx nx serve aurelius-atlas-dev-observability
```

Open Grafana on [http://localhost:3000](<http://localhost:3000>), Alerting \> Alert rules, folder Aurelius. Start the server (`npx nx serve aurelius-atlas-server`) and the rule returns to normal within a minute.

## Not yet watched

No rule watches the free space of Prometheus, Loki or Tempo: they do not report it. Their retention is increment 6.4d's.
