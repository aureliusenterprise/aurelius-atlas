# aurelius-atlas-server

The Aurelius Atlas server: the Apache Atlas 2.4.0 REST API on Elasticsearch.

## Usage

```
npx nx serve aurelius-atlas-server
```

This starts the dev Elasticsearch store and the observability stack, then the server at [https://localhost:21000](<https://localhost:21000>), the port Apache Atlas uses.

## Deployment

Deploy the image built from the provided Dockerfile. It listens on port 21000 and needs the Elasticsearch settings; it does not start without its store.

## Configuration

> [!NOTE]
>
> **Settings**
>
> ## aurelius\_atlas\_server.settings.ServerSettings
>
> Bases: `StoreAccessSettings`
>
> How the server runs and where its store is.
>
> **Show JSON schema:**
>
> ```
> {
>   "$defs": {
>     "LogLevel": {
>       "enum": [
>         "trace",
>         "debug",
>         "info",
>         "warning",
>         "error"
>       ],
>       "type": "string"
>     }
>   },
>   "description": "How the server runs and where its store is.",
>   "properties": {
>     "elasticsearch_hosts": {
>       "items": {
>         "format": "uri",
>         "maxLength": 2083,
>         "minLength": 1,
>         "type": "string"
>       },
>       "minItems": 1,
>       "title": "Elasticsearch Hosts",
>       "type": "array"
>     },
>     "elasticsearch_username": {
>       "default": "elastic",
>       "title": "Elasticsearch Username",
>       "type": "string"
>     },
>     "elasticsearch_password": {
>       "format": "password",
>       "title": "Elasticsearch Password",
>       "type": "string",
>       "writeOnly": true
>     },
>     "elasticsearch_ca_certs": {
>       "format": "file-path",
>       "title": "Elasticsearch Ca Certs",
>       "type": "string"
>     },
>     "snapshot_location": {
>       "default": "aurelius-atlas",
>       "title": "Snapshot Location",
>       "type": "string"
>     },
>     "host": {
>       "default": "localhost",
>       "title": "Host",
>       "type": "string"
>     },
>     "port": {
>       "default": 21000,
>       "maximum": 65535,
>       "minimum": 1,
>       "title": "Port",
>       "type": "integer"
>     },
>     "log_level": {
>       "$ref": "#/$defs/LogLevel",
>       "default": "info"
>     },
>     "tls_cert_file": {
>       "format": "file-path",
>       "title": "Tls Cert File",
>       "type": "string"
>     },
>     "tls_key_file": {
>       "format": "file-path",
>       "title": "Tls Key File",
>       "type": "string"
>     },
>     "hsts_enabled": {
>       "default": true,
>       "title": "Hsts Enabled",
>       "type": "boolean"
>     },
>     "root_path": {
>       "default": "",
>       "pattern": "^(/[^/\\s]+)*$",
>       "title": "Root Path",
>       "type": "string"
>     },
>     "forwarded_allow_ips": {
>       "default": "127.0.0.1",
>       "title": "Forwarded Allow Ips",
>       "type": "string"
>     },
>     "dashboard_dir": {
>       "anyOf": [
>         {
>           "format": "directory-path",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Dashboard Dir"
>     },
>     "models_dir": {
>       "default": "/home/runner/work/aurelius-atlas/aurelius-atlas/libs/python/aurelius-atlas-core/aurelius_atlas_core/models",
>       "format": "path",
>       "title": "Models Dir",
>       "type": "string"
>     },
>     "m4i_models_enabled": {
>       "default": true,
>       "title": "M4I Models Enabled",
>       "type": "boolean"
>     },
>     "typedef_refresh_seconds": {
>       "default": 5.0,
>       "minimum": 0,
>       "title": "Typedef Refresh Seconds",
>       "type": "number"
>     },
>     "delete_type": {
>       "default": "soft",
>       "enum": [
>         "soft",
>         "hard"
>       ],
>       "title": "Delete Type",
>       "type": "string"
>     },
>     "delete_type_override": {
>       "default": false,
>       "title": "Delete Type Override",
>       "type": "boolean"
>     },
>     "tasks_enabled": {
>       "default": true,
>       "title": "Tasks Enabled",
>       "type": "boolean"
>     },
>     "task_poll_seconds": {
>       "default": 10.0,
>       "exclusiveMinimum": 0,
>       "title": "Task Poll Seconds",
>       "type": "number"
>     },
>     "import_folder": {
>       "anyOf": [
>         {
>           "format": "path",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Import Folder"
>     },
>     "cluster_name": {
>       "default": "default",
>       "title": "Cluster Name",
>       "type": "string"
>     },
>     "lineage_on_demand_enabled": {
>       "default": false,
>       "title": "Lineage On Demand Enabled",
>       "type": "boolean"
>     },
>     "lineage_on_demand_default_node_count": {
>       "default": 3,
>       "minimum": 1,
>       "title": "Lineage On Demand Default Node Count",
>       "type": "integer"
>     },
>     "lineage_max_node_count": {
>       "default": 9000,
>       "minimum": 1,
>       "title": "Lineage Max Node Count",
>       "type": "integer"
>     },
>     "metrics_persist_interval_minutes": {
>       "default": 60,
>       "minimum": 0,
>       "title": "Metrics Persist Interval Minutes",
>       "type": "integer"
>     },
>     "metrics_ttl_hours": {
>       "default": 336,
>       "minimum": 1,
>       "title": "Metrics Ttl Hours",
>       "type": "integer"
>     },
>     "audit_aging_enabled": {
>       "default": false,
>       "title": "Audit Aging Enabled",
>       "type": "boolean"
>     },
>     "audit_default_ageout_enabled": {
>       "default": true,
>       "title": "Audit Default Ageout Enabled",
>       "type": "boolean"
>     },
>     "audit_default_ageout_ttl_in_days": {
>       "default": 90,
>       "title": "Audit Default Ageout Ttl In Days",
>       "type": "integer"
>     },
>     "audit_default_ageout_count": {
>       "default": 0,
>       "title": "Audit Default Ageout Count",
>       "type": "integer"
>     },
>     "audit_default_ageout_ignore_ttl": {
>       "default": false,
>       "title": "Audit Default Ageout Ignore Ttl",
>       "type": "boolean"
>     },
>     "audit_custom_ageout_ttl_in_days": {
>       "default": 0,
>       "title": "Audit Custom Ageout Ttl In Days",
>       "type": "integer"
>     },
>     "audit_custom_ageout_count": {
>       "default": 0,
>       "title": "Audit Custom Ageout Count",
>       "type": "integer"
>     },
>     "audit_custom_ageout_entity_types": {
>       "anyOf": [
>         {
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Audit Custom Ageout Entity Types"
>     },
>     "audit_custom_ageout_action_types": {
>       "anyOf": [
>         {
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Audit Custom Ageout Action Types"
>     },
>     "audit_sweep_out_enabled": {
>       "default": false,
>       "title": "Audit Sweep Out Enabled",
>       "type": "boolean"
>     },
>     "audit_sweep_out_entity_types": {
>       "anyOf": [
>         {
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Audit Sweep Out Entity Types"
>     },
>     "audit_sweep_out_action_types": {
>       "anyOf": [
>         {
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Audit Sweep Out Action Types"
>     },
>     "audit_create_events_ageout_allowed": {
>       "default": false,
>       "title": "Audit Create Events Ageout Allowed",
>       "type": "boolean"
>     },
>     "audit_aging_subtypes_included": {
>       "default": true,
>       "title": "Audit Aging Subtypes Included",
>       "type": "boolean"
>     },
>     "audit_min_ttl_to_maintain": {
>       "default": 7,
>       "title": "Audit Min Ttl To Maintain",
>       "type": "integer"
>     },
>     "audit_min_count_to_maintain": {
>       "default": 50,
>       "title": "Audit Min Count To Maintain",
>       "type": "integer"
>     },
>     "audit_reduction_max_pending_tasks": {
>       "default": 50,
>       "title": "Audit Reduction Max Pending Tasks",
>       "type": "integer"
>     },
>     "audit_aging_scheduler_frequency_in_days": {
>       "default": 30,
>       "title": "Audit Aging Scheduler Frequency In Days",
>       "type": "integer"
>     },
>     "audit_aging_scheduler_initial_delay_in_min": {
>       "default": 1,
>       "title": "Audit Aging Scheduler Initial Delay In Min",
>       "type": "integer"
>     },
>     "snapshot_enabled": {
>       "default": false,
>       "title": "Snapshot Enabled",
>       "type": "boolean"
>     },
>     "snapshot_schedule": {
>       "default": "0 0 * * * ?",
>       "title": "Snapshot Schedule",
>       "type": "string"
>     },
>     "snapshot_retention": {
>       "default": "7d",
>       "title": "Snapshot Retention",
>       "type": "string"
>     },
>     "snapshot_check_minutes": {
>       "default": 15,
>       "minimum": 1,
>       "title": "Snapshot Check Minutes",
>       "type": "integer"
>     },
>     "revision": {
>       "default": "UNKNOWN",
>       "title": "Revision",
>       "type": "string"
>     },
>     "otel_token_url": {
>       "anyOf": [
>         {
>           "format": "uri",
>           "maxLength": 2083,
>           "minLength": 1,
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Otel Token Url"
>     },
>     "otel_client_id": {
>       "default": "otel-atlas-server",
>       "title": "Otel Client Id",
>       "type": "string"
>     },
>     "otel_client_secret": {
>       "anyOf": [
>         {
>           "format": "password",
>           "type": "string",
>           "writeOnly": true
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Otel Client Secret"
>     },
>     "otel_endpoint": {
>       "default": "https://localhost:4319",
>       "title": "Otel Endpoint",
>       "type": "string"
>     },
>     "otel_ca_file": {
>       "anyOf": [
>         {
>           "format": "file-path",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Otel Ca File"
>     },
>     "auth_server_url": {
>       "format": "uri",
>       "maxLength": 2083,
>       "minLength": 1,
>       "title": "Auth Server Url",
>       "type": "string"
>     },
>     "auth_realm": {
>       "default": "master",
>       "title": "Auth Realm",
>       "type": "string"
>     },
>     "auth_client_id": {
>       "default": "aurelius-atlas-server",
>       "title": "Auth Client Id",
>       "type": "string"
>     },
>     "auth_client_secret": {
>       "format": "password",
>       "title": "Auth Client Secret",
>       "type": "string",
>       "writeOnly": true
>     },
>     "auth_audiences": {
>       "items": {
>         "type": "string"
>       },
>       "title": "Auth Audiences",
>       "type": "array"
>     },
>     "auth_principal_claim": {
>       "default": "preferred_username",
>       "title": "Auth Principal Claim",
>       "type": "string"
>     },
>     "auth_groups_claim": {
>       "default": "groups",
>       "title": "Auth Groups Claim",
>       "type": "string"
>     },
>     "auth_ca_file": {
>       "anyOf": [
>         {
>           "format": "file-path",
>           "type": "string"
>         },
>         {
>           "type": "null"
>         }
>       ],
>       "default": null,
>       "title": "Auth Ca File"
>     },
>     "session_timeout_seconds": {
>       "default": 3600,
>       "exclusiveMinimum": 0,
>       "title": "Session Timeout Seconds",
>       "type": "integer"
>     }
>   },
>   "required": [
>     "elasticsearch_hosts",
>     "elasticsearch_password",
>     "elasticsearch_ca_certs",
>     "tls_cert_file",
>     "tls_key_file",
>     "auth_server_url",
>     "auth_client_secret"
>   ],
>   "title": "ServerSettings",
>   "type": "object"
> }
> ```
>
> Fields:
>
> - `elasticsearch_hosts` (`list[HttpUrl]`)
> - `elasticsearch_username` (`str`)
> - `elasticsearch_password` (`SecretStr`)
> - `elasticsearch_ca_certs` (`FilePath`)
> - `snapshot_location` (`str`)
> - `host` (`str`)
> - `port` (`int`)
> - `log_level` (`LogLevel`)
> - `tls_cert_file` (`FilePath`)
> - `tls_key_file` (`FilePath`)
> - `hsts_enabled` (`bool`)
> - `root_path` (`str`)
> - `forwarded_allow_ips` (`str`)
> - `dashboard_dir` (`DirectoryPath | None`)
> - `models_dir` (`Path`)
> - `m4i_models_enabled` (`bool`)
> - `typedef_refresh_seconds` (`float`)
> - `delete_type` (`Literal['soft', 'hard']`)
> - `delete_type_override` (`bool`)
> - `tasks_enabled` (`bool`)
> - `task_poll_seconds` (`float`)
> - `import_folder` (`Path | None`)
> - `cluster_name` (`str`)
> - `lineage_on_demand_enabled` (`bool`)
> - `lineage_on_demand_default_node_count` (`int`)
> - `lineage_max_node_count` (`int`)
> - `metrics_persist_interval_minutes` (`int`)
> - `metrics_ttl_hours` (`int`)
> - `audit_aging_enabled` (`bool`)
> - `audit_default_ageout_enabled` (`bool`)
> - `audit_default_ageout_ttl_in_days` (`int`)
> - `audit_default_ageout_count` (`int`)
> - `audit_default_ageout_ignore_ttl` (`bool`)
> - `audit_custom_ageout_ttl_in_days` (`int`)
> - `audit_custom_ageout_count` (`int`)
> - `audit_custom_ageout_entity_types` (`str | None`)
> - `audit_custom_ageout_action_types` (`str | None`)
> - `audit_sweep_out_enabled` (`bool`)
> - `audit_sweep_out_entity_types` (`str | None`)
> - `audit_sweep_out_action_types` (`str | None`)
> - `audit_create_events_ageout_allowed` (`bool`)
> - `audit_aging_subtypes_included` (`bool`)
> - `audit_min_ttl_to_maintain` (`int`)
> - `audit_min_count_to_maintain` (`int`)
> - `audit_reduction_max_pending_tasks` (`int`)
> - `audit_aging_scheduler_frequency_in_days` (`int`)
> - `audit_aging_scheduler_initial_delay_in_min` (`int`)
> - `snapshot_enabled` (`bool`)
> - `snapshot_schedule` (`str`)
> - `snapshot_retention` (`str`)
> - `snapshot_check_minutes` (`int`)
> - `revision` (`str`)
> - `otel_token_url` (`HttpUrl | None`)
> - `otel_client_id` (`str`)
> - `otel_client_secret` (`SecretStr | None`)
> - `otel_endpoint` (`str`)
> - `otel_ca_file` (`FilePath | None`)
> - `auth_server_url` (`HttpUrl`)
> - `auth_realm` (`str`)
> - `auth_client_id` (`str`)
> - `auth_client_secret` (`SecretStr`)
> - `auth_audiences` (`list[str]`)
> - `auth_principal_claim` (`str`)
> - `auth_groups_claim` (`str`)
> - `auth_ca_file` (`FilePath | None`)
> - `session_timeout_seconds` (`int`)
>
> ### audit\_aging\_enabled
>
> ```
> audit_aging_enabled: bool = False
> ```
>
> Whether the entity audits age out on a schedule, and `admin/audits/ageout?useAuditConfig` ages them: `atlas.audit.aging.enabled` (AGE-02, AGE-05).
>
> ### audit\_aging\_scheduler\_frequency\_in\_days
>
> ```
> audit_aging_scheduler_frequency_in_days: int = 30
> ```
>
> `atlas.audit.aging.scheduler.frequency.in.days`: at least 1 (AGE-05).
>
> ### audit\_aging\_scheduler\_initial\_delay\_in\_min
>
> ```
> audit_aging_scheduler_initial_delay_in_min: int = 1
> ```
>
> `atlas.audit.aging.scheduler.initial.delay.in.min`: at least 1 (AGE-05).
>
> ### audit\_aging\_subtypes\_included
>
> ```
> audit_aging_subtypes_included: bool = True
> ```
>
> `atlas.audit.aging.subtypes.included`: an aging's types take their sub types (AGE-04).
>
> ### audit\_create\_events\_ageout\_allowed
>
> ```
> audit_create_events_ageout_allowed: bool = False
> ```
>
> `atlas.audit.create.events.ageout.allowed`: creations may age out too (AGE-04).
>
> ### audit\_custom\_ageout\_action\_types
>
> ```
> audit_custom_ageout_action_types: str | None = None
> ```
>
> `atlas.audit.custom.ageout.action.types`: comma-separated action names or prefixes (AGE-02).
>
> ### audit\_custom\_ageout\_count
>
> ```
> audit_custom_ageout_count: int = 0
> ```
>
> `atlas.audit.custom.ageout.count` (AGE-02).
>
> ### audit\_custom\_ageout\_entity\_types
>
> ```
> audit_custom_ageout_entity_types: str | None = None
> ```
>
> `atlas.audit.custom.ageout.entity.types`: comma-separated, `<prefix>*` for all that start so (AGE-02).
>
> ### audit\_custom\_ageout\_ttl\_in\_days
>
> ```
> audit_custom_ageout_ttl_in_days: int = 0
> ```
>
> `atlas.audit.custom.ageout.ttl.in.days` (AGE-02).
>
> ### audit\_default\_ageout\_count
>
> ```
> audit_default_ageout_count: int = 0
> ```
>
> `atlas.audit.default.ageout.count`: the newest audits each entity keeps; 0 for no count (AGE-02).
>
> ### audit\_default\_ageout\_enabled
>
> ```
> audit_default_ageout_enabled: bool = True
> ```
>
> `atlas.audit.default.ageout.enabled`: the default aging, of the types no other aging names (AGE-02).
>
> ### audit\_default\_ageout\_ignore\_ttl
>
> ```
> audit_default_ageout_ignore_ttl: bool = False
> ```
>
> `atlas.audit.default.ageout.ignore.ttl`: the default aging by count alone (AGE-02).
>
> ### audit\_default\_ageout\_ttl\_in\_days
>
> ```
> audit_default_ageout_ttl_in_days: int = 90
> ```
>
> `atlas.audit.default.ageout.ttl.in.days`: at least `audit_min_ttl_to_maintain` (AGE-02).
>
> ### audit\_min\_count\_to\_maintain
>
> ```
> audit_min_count_to_maintain: int = 50
> ```
>
> `atlas.audit.min.count.to.maintain`: the least count an aging may keep (AGE-02).
>
> ### audit\_min\_ttl\_to\_maintain
>
> ```
> audit_min_ttl_to_maintain: int = 7
> ```
>
> `atlas.audit.min.ttl.to.maintain`: the least TTL, in days, an aging may have (AGE-02).
>
> ### audit\_reduction\_max\_pending\_tasks
>
> ```
> audit_reduction_max_pending_tasks: int = 50
> ```
>
> `atlas.audit.reduction.max.pending.tasks`: past it no aging is queued (AGE-03).
>
> ### audit\_sweep\_out\_action\_types
>
> ```
> audit_sweep_out_action_types: str | None = None
> ```
>
> `atlas.audit.sweep.out.action.types` (AGE-02).
>
> ### audit\_sweep\_out\_enabled
>
> ```
> audit_sweep_out_enabled: bool = False
> ```
>
> `atlas.audit.sweep.out.enabled`: every audit of the sweep's types and actions removed (AGE-02).
>
> ### audit\_sweep\_out\_entity\_types
>
> ```
> audit_sweep_out_entity_types: str | None = None
> ```
>
> `atlas.audit.sweep.out.entity.types` (AGE-02).
>
> ### auth\_audiences
>
> ```
> auth_audiences: list[str]
> ```
>
> Further clients whose tokens the server accepts: the webapp's, which the auxiliary APIs forward (AUT-02, AUT-10).
>
> ### auth\_ca\_file
>
> ```
> auth_ca_file: FilePath | None = None
> ```
>
> PEM CA verifying the provider's TLS; unset uses the system trust store.
>
> ### auth\_client\_id
>
> ```
> auth_client_id: str = 'aurelius-atlas-server'
> ```
>
> The server's confidential client: browsers sign in with it, and its tokens are accepted (AUT-05).
>
> ### auth\_client\_secret
>
> ```
> auth_client_secret: SecretStr
> ```
>
> The secret of `auth_client_id`; never shown in logs.
>
> ### auth\_groups\_claim
>
> ```
> auth_groups_claim: str = 'groups'
> ```
>
> The claim a user's groups are read from, else the realm roles: `atlas.authentication.method.keycloak .groups_claim` (AUT-03).
>
> ### auth\_principal\_claim
>
> ```
> auth_principal_claim: str = 'preferred_username'
> ```
>
> The claim a user's name is read from: Atlas's Keycloak `principal-attribute` (AUT-03, DD-250).
>
> ### auth\_realm
>
> ```
> auth_realm: str = 'master'
> ```
>
> The realm the tokens are issued from.
>
> ### auth\_server\_url
>
> ```
> auth_server_url: HttpUrl
> ```
>
> The identity provider's root (Keycloak), which tokens are verified against and browsers sign in at (AUT-02, AUT-05; ADR 007).
>
> ### cluster\_name
>
> ```
> cluster_name: str = 'default'
> ```
>
> The cluster an export says it comes from: `atlas.metadata.namespace`, else `atlas.cluster.name` (EXP-06).
>
> ### dashboard\_dir
>
> ```
> dashboard_dir: DirectoryPath | None = None
> ```
>
> The built dashboards: `dashboardv2` at its root and `dashboardv3` in `n/`; None serves the API only (DSH-04).
>
> ### delete\_type
>
> ```
> delete_type: Literal['soft', 'hard'] = 'soft'
> ```
>
> How entities are deleted unless a request chooses: `atlas.DeleteHandlerV1.impl` (EDL-04, DD-059).
>
> ### delete\_type\_override
>
> ```
> delete_type_override: bool = False
> ```
>
> Whether a request's `deleteType` chooses: `atlas.rest.enable.delete.type.override` (EDL-04, DD-059).
>
> ### elasticsearch\_ca\_certs
>
> ```
> elasticsearch_ca_certs: FilePath
> ```
>
> PEM file with the certificate authority of the Elasticsearch server certificate.
>
> ### elasticsearch\_hosts
>
> ```
> elasticsearch_hosts: list[HttpUrl]
> ```
>
> Base URLs of the Elasticsearch nodes, as a JSON list: `["https://localhost:9200"]`.
>
> ### elasticsearch\_password
>
> ```
> elasticsearch_password: SecretStr
> ```
>
> Password for the store; never shown in logs.
>
> ### elasticsearch\_username
>
> ```
> elasticsearch_username: str = 'elastic'
> ```
>
> User for the store.
>
> ### forwarded\_allow\_ips
>
> ```
> forwarded_allow_ips: str = '127.0.0.1'
> ```
>
> Which peers may rewrite the client address through `X-Forwarded-For` (SRV-10, DD-238), passed to uvicorn. The default trusts only the loopback; behind a proxy the arrangement names the proxy network, so the access log and OTel peer attributes key on the browser's address, not the proxy's. The rate limit itself lives at the webapp's nginx edge, not here (SRV-09, DD-238).
>
> ### host
>
> ```
> host: str = 'localhost'
> ```
>
> The interface to listen on; the container image sets `0.0.0.0`.
>
> ### hsts\_enabled
>
> ```
> hsts_enabled: bool = True
> ```
>
> Whether responses carry `Strict-Transport-Security` (SRV-08, DD-236). The image ships True; the dev arrangement turns it off so a browser that visited the mkcert server is not pinned to HTTPS on the plaintext dev surfaces (ADR 039's named relaxations).
>
> ### import\_folder
>
> ```
> import_folder: Path | None = None
> ```
>
> The one folder `admin/importfile` reads export ZIPs from; none refuses every file (IMS-06, DV-125).
>
> ### lineage\_max\_node\_count
>
> ```
> lineage_max_node_count: int = 9000
> ```
>
> The relations past which lineage adds none (at most 9,000): `atlas.lineage.max.node.count` (LIN-04).
>
> ### lineage\_on\_demand\_default\_node\_count
>
> ```
> lineage_on_demand_default_node_count: int = 3
> ```
>
> The relations each way lineage on demand takes by default: `atlas.lineage.on.demand.default.node.count` (LIN-06).
>
> ### lineage\_on\_demand\_enabled
>
> ```
> lineage_on_demand_enabled: bool = False
> ```
>
> Whether `POST v2/lineage/{guid}` answers lineage on demand: `atlas.lineage.on.demand.enabled` (LIN-06).
>
> ### log\_level
>
> ```
> log_level: LogLevel = 'info'
> ```
>
> The lowest level of log record the server and uvicorn emit.
>
> ### m4i\_models\_enabled
>
> ```
> m4i_models_enabled: bool = True
> ```
>
> Whether the m4i data dictionary types are loaded at start-up too, after `models_dir`; off loads none and leaves those stored as they are (MDD-01, MDD-03, ADR 058).
>
> ### metrics\_persist\_interval\_minutes
>
> ```
> metrics_persist_interval_minutes: int = 60
> ```
>
> How often the metrics are stored, in minutes on their multiples since the epoch; 0 stores none: `atlas.metrics.persist.schedule` (MHS-05, DV-137).
>
> ### metrics\_ttl\_hours
>
> ```
> metrics_ttl_hours: int = 336
> ```
>
> How long a stored metric is kept: `atlas.metrics.ttl.hours` (MHS-01, MHS-05).
>
> ### model\_config
>
> ```
> model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra='ignore')
> ```
>
> ### model\_dirs
>
> ```
> model_dirs: list[Path]
> ```
>
> The models directories loaded at start-up, in order (MDD-01).
>
> ### models\_dir
>
> ```
> models_dir: Path = BUILTIN_MODELS_DIR
> ```
>
> The models loaded at start-up: by default `addons/models` of Apache Atlas 2.4.0; a missing directory loads none (MDL-01, MDL-16, DD-032).
>
> ### otel\_ca\_file
>
> ```
> otel_ca_file: FilePath | None = None
> ```
>
> PEM CA verifying the collector's TLS for the OTLP export; unset uses the system trust store (the dev stack's mkcert CA is not system-wide).
>
> ### otel\_client\_id
>
> ```
> otel_client_id: str = 'otel-atlas-server'
> ```
>
> The ingest realm client the server mints for (7.18, DD-196).
>
> ### otel\_client\_secret
>
> ```
> otel_client_secret: SecretStr | None = None
> ```
>
> The secret of `otel_client_id`; never shown in logs.
>
> ### otel\_endpoint
>
> ```
> otel_endpoint: str = 'https://localhost:4319'
> ```
>
> The collector's per-service-leg HTTP base for the OTLP export (7.18, DD-196); the dev compose overrides with the service DNS name.
>
> ### otel\_token\_url
>
> ```
> otel_token_url: HttpUrl | None = None
> ```
>
> The issuer's token endpoint for the OTLP ingest credential (7.18, DD-196): with `otel_client_secret` set, the server exports OTLP through the app-owned pipeline (the collector's per-service leg accepts only client-credentials JWTs); unset, the server exports no OTLP (console only). The OTel env vars (`OTEL_EXPORTER_OTLP_*`) are deliberately not read: the 60s dev token cannot ride a static header (DD-196).
>
> ### port
>
> ```
> port: int = DEFAULT_PORT
> ```
>
> The port to listen on (SRV-03).
>
> ### revision
>
> ```
> revision: str = 'UNKNOWN'
> ```
>
> The source revision the server was built from, reported by `admin/version` (ADM-01).
>
> ### root\_path
>
> ```
> root_path: str = ''
> ```
>
> The path a proxy serves the server under, such as `/atlas2`, passed to uvicorn: the server's redirects and its sign-in's return lead there; empty serves it at the root (PFX-01, DD-363).
>
> ### session\_timeout\_seconds
>
> ```
> session_timeout_seconds: int = 3600
> ```
>
> How long a browser session lasts unused: Atlas's `web.xml` session timeout, 60 minutes (AUT-06).
>
> ### snapshot\_check\_minutes
>
> ```
> snapshot_check_minutes: int = 15
> ```
>
> How often the server reads how the policy's last runs went (SNP-03).
>
> ### snapshot\_enabled
>
> ```
> snapshot_enabled: bool = False
> ```
>
> Whether the server puts the store's snapshot policy at start and watches its runs (SNP-01 to SNP-03). The chart turns it on; the dev store's data is disposable.
>
> ### snapshot\_location
>
> ```
> snapshot_location: str = 'aurelius-atlas'
> ```
>
> The repository's directory, below the store's `path.repo` (SNP-01).
>
> ### snapshot\_retention
>
> ```
> snapshot_retention: str = '7d'
> ```
>
> How long a snapshot is kept, as an Elasticsearch time unit (SNP-02).
>
> ### snapshot\_schedule
>
> ```
> snapshot_schedule: str = '0 0 * * * ?'
> ```
>
> When a snapshot is taken, as an Elasticsearch cron expression in UTC: every hour on the hour (SNP-02).
>
> ### task\_poll\_seconds
>
> ```
> task_poll_seconds: float = 10.0
> ```
>
> How often the worker looks for tasks other processes recorded or left behind (DD-080).
>
> ### tasks\_enabled
>
> ```
> tasks_enabled: bool = True
> ```
>
> Whether propagation is deferred to tasks a worker runs after the request: `atlas.tasks.enabled` (TSK-02, DD-081).
>
> ### tls
>
> ```
> tls: tuple[Path, Path]
> ```
>
> The certificate and key to serve HTTPS with (SRV-03, SRV-06, DD-234).
>
> ### tls\_cert\_file
>
> ```
> tls_cert_file: FilePath
> ```
>
> PEM certificate to serve HTTPS with (SRV-06, DD-234): required — the server never serves plaintext, the way the store's password is required (SRV-01, SRV-02).
>
> ### tls\_key\_file
>
> ```
> tls_key_file: FilePath
> ```
>
> PEM private key of `tls_cert_file` (SRV-06).
>
> ### typedef\_refresh\_seconds
>
> ```
> typedef_refresh_seconds: float = 5.0
> ```
>
> How long the server answers from its type registry before it checks for another process's type change (TDS-13, DD-029).
>
> ### audit\_aging\_config
>
> ```
> audit_aging_config() -> AuditAgingConfig
> ```
>
> The `atlas.audit.*` aging settings of the core's aging (AGE-02).
>
> ### snapshot\_policy
>
> ```
> snapshot_policy() -> SnapshotPolicy
> ```
>
> The snapshot policy of the server's indices, every index of `INDEX_PREFIX` (SNP-01, SNP-02).
>
> ### store\_settings
>
> ```
> store_settings() -> StoreSettings
> ```
>
> The settings of the Elasticsearch store.

## Design

The technology-specific detail of how the server runs. The properties it must keep are in the architecture: [Configuration Management](<https://aureliusenterprise.github.io/feat-root-path-proxy/architecture/platform/delivery/configuration-management/index.md>) (ADR 018), [Components &amp; Interfaces](<https://aureliusenterprise.github.io/feat-root-path-proxy/architecture/platform/components-and-interfaces/index.md>).

**Settings.** Read once at start-up into a frozen `ServerSettings`; a validation failure (missing key, bad scheme, missing TLS material) stops start-up with a message naming the variable (SRV-01, SRV-02, SRV-06). All names carry the `AURELIUS_ATLAS_SERVER_` prefix. What a deployment must supply, with no defaults:

| Variable | Purpose |
| --- | --- |
| `..._ELASTICSEARCH_HOSTS` | JSON list of store node URLs, e.g. `["https://es-0:9200"]` — `https` only |
| `..._ELASTICSEARCH_PASSWORD` | Store password — a `SecretStr`, never shown in logs |
| `..._ELASTICSEARCH_CA_CERTS` | PEM CA of the store certificate; the store link is https-only (ADR 039) |
| `..._TLS_CERT_FILE` + `..._TLS_KEY_FILE` | PEM pair for serving HTTPS: both required — the server never serves plaintext (SRV-06, DD-234) |

With defaults: `HOST` (`0.0.0.0` in the image), `PORT` (21000, Atlas's port — kept so existing clients find the catalogue where Atlas was, ADR 046), `LOG_LEVEL`, `REVISION` (reported by `admin/version`, ADM-01), `HSTS_ENABLED` (true — the dev arrangement sets it false, SRV-08/DD-236), `DASHBOARD_DIR` (None serves the API only, DSH-04), `MODELS_DIR` (default: the vendored Atlas 2.4.0 `addons/models`, MDL-16/DD-032), `TYPEDEF_REFRESH_SECONDS` (5.0 — how long the server answers from its type registry before checking for another process's type change, TDS-13/DD-029).

> [!WARNING]
>
> **The server does not start without TLS material**
>
> `TLS_CERT_FILE` and `TLS_KEY_FILE` are required settings — there is no plaintext mode (SRV-06, DD-234, superseding the both-or-neither rule of SRV-03). A container that mounts no material exits with a message naming the missing variable; this is the design working, not a broken image. The image's `ENV` names where the pair lives (`/certs/server.pem`, `/certs/server-key.pem` — DD-216's stack-owned mount).

**The image** (`apps/aurelius-atlas-server/Dockerfile`: hardened base, runs as `nonroot`) bakes in the production defaults — listen on `0.0.0.0:21000`, dashboards served from `/application/dashboard` — and a liveness healthcheck against `/api/atlas/admin/liveness` over HTTPS, verifying the served certificate (SRV-06). Liveness is the probe a restart decision uses; readiness also fails while the store is away (DD-016).

**Security headers.** Every answer carries them (SRV-08, DD-236): `security_headers.py` stamps the JSON API with no-store/nosniff/framing-closed headers and a documents-free CSP, the dashboards with a same-origin CSP (DV-86) and immutable caching on bust-versioned assets, and HSTS when `HSTS_ENABLED`.

**Parity scenarios.** `scenarios/<resource>/*.scenario.yaml` state each expectation as Atlas's own answer — e.g. `scenarios/admin/version.scenario.yaml` expects `Version: "2.4.0"`, `Name: apache-atlas`, the exact content type — each cited to the Java source that produces it. Build-varying fields are marked volatile; the two places Aurelius Atlas must answer differently (name, description) carry a `deviations: DV-03` entry. Anything else that differs fails the scenario (ADR 052).

## Documentation

## aurelius\_atlas\_server.app

The FastAPI application: settings, the store's lifetime, error handling and routers (DD-015, DD-016).

Functions:

- **`build_auth`** –

  The token verifier: the provider's tokens for the server's client and the further audiences (AUT-02).
- **`build_oidc`** –

  The server's client at the provider, which browsers sign in with (AUT-05).
- **`create_app`** –

  Build the application.
- **`mount_dashboards`** –

  Serve `dashboardv3` at `/n/` and `dashboardv2` at `/` (DSH-01, DSH-02; DD-018).

Attributes:

- **`BRIDGED_LOGGERS`** –

  The loggers whose records the collector receives (OBS-01): the server's, its libraries' and uvicorn's errors.
- **`DASHBOARD_V3_DIR`** –

  Where `dashboardv3` sits in the dashboard directory, and below which path it is served.
- **`LOGGER`** –
- **`NAME`** –

### BRIDGED\_LOGGERS

```
BRIDGED_LOGGERS = (NAME, 'aurelius_atlas_core', 'aurelius_atlas_store_es', 'uvicorn.error')
```

The loggers whose records the collector receives (OBS-01): the server's, its libraries' and uvicorn's errors.

### DASHBOARD\_V3\_DIR

```
DASHBOARD_V3_DIR = 'n'
```

Where `dashboardv3` sits in the dashboard directory, and below which path it is served.

### LOGGER

```
LOGGER = logging.getLogger(NAME)
```

### NAME

```
NAME = 'aurelius-atlas-server'
```

### build\_auth

```
build_auth(settings: ServerSettings, http: Client | None = None) -> KeycloakAuth
```

The token verifier: the provider's tokens for the server's client and the further audiences (AUT-02).

### build\_oidc

```
build_oidc(settings: ServerSettings, auth: KeycloakAuth, http: AsyncClient | None = None) -> OidcClient
```

The server's client at the provider, which browsers sign in with (AUT-05).

### create\_app

```
create_app(
    settings: ServerSettings,
    store: ElasticsearchStore | None = None,
    *,
    auth: KeycloakAuth | None = None,
    oidc_http: AsyncClient | None = None,
) -> FastAPI
```

Build the application.

Parameters:

- #### **`settings`**

  (`ServerSettings`) –

  The server's settings.
- #### **`store`**

  (`ElasticsearchStore | None`, default: `None` ) –

  The store to use; by default one built from the settings. It is opened when the application starts, which fails when the store cannot be opened (SRV-02), and closed when it stops.
- #### **`auth`**

  (`KeycloakAuth | None`, default: `None` ) –

  The token verifier; by default one for the settings' provider (AUT-02).
- #### **`oidc_http`**

  (`AsyncClient | None`, default: `None` ) –

  The HTTP client the sign-in calls the provider with; by default one of its own (AUT-05).

The type registry is loaded from the stored type definitions when the application starts (TDS-12), then the models are loaded and patched (MDL-16); the entity store's indices are created and interrupted writes recovered (ENS-01, ENS-07), and the audit index (DD-082). With tasks enabled, a worker runs the tasks requests record (TSK-04, DD-080). With snapshots enabled, the store's snapshot policy is put and its runs watched (SNP-01 to SNP-03).

### mount\_dashboards

```
mount_dashboards(app: FastAPI, directory: Path) -> None
```

Serve `dashboardv3` at `/n/` and `dashboardv2` at `/` (DSH-01, DSH-02; DD-018).

Mounted after the API routes, so the API takes precedence (DSH-03).

## aurelius\_atlas\_server.errors

The body Atlas errors are answered with (SRV-04, SRV-05, SRV-07), as `AtlasBaseExceptionMapper` does.

The errors themselves live in `aurelius_atlas_model.errors` (DD-023) and are re-exported here. 5xx bodies are opaque: the cause is logged, and the trace id rides along for correlation (DD-235, DV-85).

Classes:

- **`AtlasJSONResponse`** –

  A JSON response with the Atlas media type (SRV-05), written by Atlas's JSON codec (VAL-01, DD-039).

Functions:

- **`atlas_error_handler`** –

  Answer an `AtlasError` with its status and `{"errorCode", "errorMessage"[, "errorCause"]}` (SRV-04).

Attributes:

- **`ATLAS_JSON_MEDIA_TYPE`** –

  The media type of Atlas JSON responses (`Servlets.JSON_MEDIA_TYPE`).

### ATLAS\_JSON\_MEDIA\_TYPE

```
ATLAS_JSON_MEDIA_TYPE = 'application/json; charset=UTF-8'
```

The media type of Atlas JSON responses (`Servlets.JSON_MEDIA_TYPE`).

### LOGGER

```
LOGGER = logging.getLogger(__name__)
```

### \_\_all\_\_

```
__all__ = ['ATLAS_JSON_MEDIA_TYPE', 'AtlasError', 'AtlasErrorCode', 'AtlasJSONResponse', 'atlas_error_handler']
```

### AtlasJSONResponse

Bases: `JSONResponse`

A JSON response with the Atlas media type (SRV-05), written by Atlas's JSON codec (VAL-01, DD-039).

Methods:

- **`render`** –

  Decimals keep their digits and dates are epoch milliseconds, as Jackson writes them.

Attributes:

- **`media_type`** –

#### media\_type

```
media_type = ATLAS_JSON_MEDIA_TYPE
```

#### render

```
render(content: Any) -> bytes
```

Decimals keep their digits and dates are epoch milliseconds, as Jackson writes them.

### atlas\_error\_handler

```
atlas_error_handler(_request: Request, error: Exception) -> AtlasJSONResponse
```

Answer an `AtlasError` with its status and `{"errorCode", "errorMessage"[, "errorCause"]}` (SRV-04).

A server error (5xx) keeps Atlas's two-field shape and adds the trace id of the request as `requestId` (SRV-07, DD-235): the cause's text goes to the log, never to the wire, so a wrapped store or transport failure cannot leak internals; the id ties the response to the logged stack and the trace. A client error (4xx) echoes the cause as Atlas does (SRV-04) — there the cause is the request's own defect, not server internals.

## aurelius\_atlas\_server.routes.admin

The admin endpoints of `AdminResource`: version, status, session, liveness, readiness, patches, metrics, purge, tasks, export, import, servers and their audit trail.

ADM-01 to ADM-05, ENS-10, EDL-01 to EDL-08, TSK-06, EXP-01, IMS-01 to IMS-06, REP-01 to REP-05, MET-01 to MET-04, MHS-01 to MHS-04.

Functions:

- **`ageout_audit_data`** –

  `ageoutAuditData`: the agings the criteria ask for, or with `useAuditConfig` the configuration's, queued
- **`delete_task`** –

  `deleteTask`: remove the tasks of the `guids` given (TSK-06).
- **`export`** –

  `export`: the entities the request reaches, with their types and the result, as a ZIP (EXP-01 to EXP-06).
- **`get_all_metrics`** –

  `getAllMetrics`: every stored metric, the latest first; with `mininfo`, the default, without the metrics
- **`get_atlas_audits`** –

  `getAtlasAudits`: the admin audits the search parameters find (ADA-04); it needs `ADMIN_AUDITS`.
- **`get_audit_details`** –

  `getAuditDetails`: the entity headers a purge's audit names, `limit` (10) from `offset` (ADA-05).
- **`get_cluster`** –

  `getCluster`: the server of the full name, with the replication it recorded (REP-01).
- **`get_export_import_audit`** –

  `getExportImportAudit`: the audit entries of the values given, the server either end (REP-05).
- **`get_liveness`** –

  Whether the server runs (ADM-03).
- **`get_metrics`** –

  `getMetrics`: the counts of the types, entities and classifications the user may read, the server's stats
- **`get_metrics_by_collection_time`** –

  `getMetricsByCollectionTime`: the metric stored at that time (MHS-02).
- **`get_metrics_for_chart_by_type_names`** –

  `getMetricsForChartByTypeNames`: per type name, its counts in the range by state (MHS-04).
- **`get_metrics_in_time_range`** –

  `getMetricsInTimeRange`: the metrics stored in the range, with the type data of the type names (MHS-03).
- **`get_patches`** –

  `getAtlasPatches`: the typedef patch records, sorted by id (ENS-10, DV-14).
- **`get_readiness`** –

  Whether the server can serve requests: its store must be healthy (ADM-04).
- **`get_session`** –

  The user interface settings and the user of this session (ADM-05, AUT-09).
- **`get_status`** –

  The service state, which is always `ACTIVE` while the server runs (ADM-02).
- **`get_task_status`** –

  `getTaskStatus`: the tasks of the `guids` given that exist, in their order, else every task (TSK-06).
- **`get_version`** –

  The server's name, release and revision (ADM-01, DV-03).
- **`import_data`** –

  `importData`: the form's `data`, an export ZIP, imported as its `request` asks (IMS-01 to IMS-05).
- **`import_file`** –

  `importFile`: the export ZIP its `fileName` option names, from the server's import folder (IMS-06, DV-125).
- **`purge_by_ids`** –

  `purgeByIds`: remove the `DELETED` entities of a JSON array of GUIDs (EDL-01 to EDL-03).
- **`time_zones`** –

  The IANA time zone ids, sorted (DV-05).

Attributes:

- **`ACTIVE`** –

  The only service state: Aurelius Atlas has no high-availability states.
- **`ADMIN`** –
- **`DESCRIPTION`** –

  What `admin/version` reports instead of Apache Atlas's name and description (DV-03).
- **`JAVA_LONG`** –
- **`LIVE`** –
- **`LONG_RANGE`** –
- **`NAME`** –
- **`NOT_READY`** –
- **`NO_CONTENT`** –
- **`OPERATION_STATUS`** –

  The option an export's or import's admin audit adds its status as (ADA-02).
- **`READY`** –
- **`UI_SETTINGS`** (`dict[str, Any]`) –

  The session's settings at the defaults of Atlas 2.4.0 (`AdminResource`, `AtlasCSRFPreventionFilter`,

### ACTIVE

```
ACTIVE = 'ACTIVE'
```

The only service state: Aurelius Atlas has no high-availability states.

### ADMIN

```
ADMIN = APIRouter(prefix='/api/atlas/admin', tags=['Admin'])
```

### DESCRIPTION

```
DESCRIPTION = 'Apache Atlas 2.4.0 REST API on Elasticsearch'
```

What `admin/version` reports instead of Apache Atlas's name and description (DV-03).

### JAVA\_LONG

```
JAVA_LONG = re.compile('[+-]?\\d+')
```

### LIVE

```
LIVE = 'Service is live'
```

### LONG\_RANGE

```
LONG_RANGE = (-2 ** 63, 2 ** 63 - 1)
```

### NAME

```
NAME = 'aurelius-atlas'
```

### NOT\_READY

```
NOT_READY = 'Service not ready to accept client requests'
```

### NO\_CONTENT

```
NO_CONTENT = 204
```

### OPERATION\_STATUS

```
OPERATION_STATUS = 'operationStatus'
```

The option an export's or import's admin audit adds its status as (ADA-02).

### READY

```
READY = 'Service is ready to accept requests'
```

### UI\_SETTINGS

```
UI_SETTINGS: dict[str, Any] = {
    "atlas.rest-csrf.enabled": True,
    "atlas.rest-csrf.browser-useragents-regex": "^Mozilla.*,^Opera.*,^Chrome",
    "atlas.rest-csrf.methods-to-ignore": "GET,OPTIONS,HEAD,TRACE",
    "atlas.rest-csrf.custom-header": "X-XSRF-HEADER",
    "atlas.ui.editable.entity.types": "hdfs_path",
    "atlas.ui.default.version": "v2",
    "atlas.ui.date.timezone.format.enabled": True,
    "atlas.ui.date.format": "MM/DD/YYYY hh:mm:ss A",
    "atlas.debug.metrics.enabled": False,
    "atlas.tasks.enabled": True,
    "atlas.tasks.ui.tab.enabled": False,
    "atlas.lineage.on.demand.enabled": False,
    "atlas.lineage.on.demand.default.node.count": 3,
    "atlas.relationship.search.enabled": False,
}
```

The session's settings at the defaults of Atlas 2.4.0 (`AdminResource`, `AtlasCSRFPreventionFilter`, `AtlasConfiguration`).

### ageout\_audit\_data

```
ageout_audit_data(request: Request, store: Store, body: Body) -> Response
```

`ageoutAuditData`: the agings the criteria ask for, or with `useAuditConfig` the configuration's, queued as tasks and answered; none queued is 204 (AGE-01 to AGE-03). It needs `ADMIN_AUDITS`.

Raises:

- `AtlasError` –

  `UNAUTHORIZED_ACCESS`; `BAD_REQUEST` for a body that is no criteria (DV-10); `INTERNAL_ERROR` for action types of which none names an action.

### delete\_task

```
delete_task(request: Request) -> Response
```

`deleteTask`: remove the tasks of the `guids` given (TSK-06).

### export

```
export(request: Request, store: Store, body: Body) -> Response
```

`export`: the entities the request reaches, with their types and the result, as a ZIP (EXP-01 to EXP-06).

One export or import runs at a time unless the request's options name `skipLineage` or `replicatedTo`.

Raises:

- `AtlasError` –

  `UNAUTHORIZED_ACCESS`; `FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK` while another runs; `BAD_REQUEST` for a body that is no export request (DV-10).

### get\_all\_metrics

```
get_all_metrics(request: Request, store: Store) -> list[dict[str, Any]]
```

`getAllMetrics`: every stored metric, the latest first; with `mininfo`, the default, without the metrics (MHS-02).

### get\_atlas\_audits

```
get_atlas_audits(request: Request, store: Store, body: Body) -> AtlasJSONResponse
```

`getAtlasAudits`: the admin audits the search parameters find (ADA-04); it needs `ADMIN_AUDITS`.

Raises:

- `AtlasError` –

  `UNAUTHORIZED_ACCESS`; `INVALID_PARAMETERS` for no body; `UNKNOWN_ATTRIBUTE`; `BAD_REQUEST` for a body that is no search (DV-10).

### get\_audit\_details

```
get_audit_details(audit_guid: str, request: Request, store: Store) -> AtlasJSONResponse
```

`getAuditDetails`: the entity headers a purge's audit names, `limit` (10) from `offset` (ADA-05).

Atlas checks no admin privilege here, only the entity read of the entry.

Raises:

- `AtlasError` –

  `INSTANCE_GUID_NOT_FOUND`; `UNAUTHORIZED_ACCESS`; `INTERNAL_ERROR` for an audit other than a purge.

### get\_cluster

```
get_cluster(server_name: str, request: Request, store: Store) -> AtlasJSONResponse
```

`getCluster`: the server of the full name, with the replication it recorded (REP-01).

Atlas checks no admin privilege here, only the entity reads of its store (DD-307).

Raises:

- `AtlasError` –

  `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` for none.

### get\_export\_import\_audit

```
get_export_import_audit(request: Request, store: Store) -> AtlasJSONResponse
```

`getExportImportAudit`: the audit entries of the values given, the server either end (REP-05).

Query parameters `serverName`, `userName`, `operation`, `startTime`, `endTime`, `limit` and `offset`. Atlas checks no admin privilege here, only the entity reads of its search (DD-307).

### get\_liveness

```
get_liveness() -> str
```

Whether the server runs (ADM-03).

### get\_metrics

```
get_metrics(request: Request, store: Store) -> dict[str, Any]
```

`getMetrics`: the counts of the types, entities and classifications the user may read, the server's stats and its system details; a store that is not healthy is `not-connected` (MET-01 to MET-04).

### get\_metrics\_by\_collection\_time

```
get_metrics_by_collection_time(request: Request, store: Store, collection_time: str) -> dict[str, Any]
```

`getMetricsByCollectionTime`: the metric stored at that time (MHS-02).

### get\_metrics\_for\_chart\_by\_type\_names

```
get_metrics_for_chart_by_type_names(request: Request, store: Store) -> dict[str, list[dict[str, Any]]]
```

`getMetricsForChartByTypeNames`: per type name, its counts in the range by state (MHS-04).

### get\_metrics\_in\_time\_range

```
get_metrics_in_time_range(request: Request, store: Store) -> list[dict[str, Any]]
```

`getMetricsInTimeRange`: the metrics stored in the range, with the type data of the type names (MHS-03).

### get\_patches

```
get_patches(request: Request) -> dict[str, Any]
```

`getAtlasPatches`: the typedef patch records, sorted by id (ENS-10, DV-14).

### get\_readiness

```
get_readiness(request: Request) -> str
```

Whether the server can serve requests: its store must be healthy (ADM-04).

Raises:

- `AtlasError` –

  `INTERNAL_ERROR` when the store is not healthy.

### get\_session

```
get_session(request: Request) -> dict[str, Any]
```

The user interface settings and the user of this session (ADM-05, AUT-09).

The CSRF token is the session's, made on first ask; a request without a session gets a new one. The entity permissions are the user's (AUZ-06). `atlas.tasks.enabled` is the server's `tasks_enabled` setting (DD-081).

### get\_status

```
get_status() -> dict[str, str]
```

The service state, which is always `ACTIVE` while the server runs (ADM-02).

### get\_task\_status

```
get_task_status(request: Request) -> AtlasJSONResponse
```

`getTaskStatus`: the tasks of the `guids` given that exist, in their order, else every task (TSK-06).

### get\_version

```
get_version(request: Request) -> dict[str, str]
```

The server's name, release and revision (ADM-01, DV-03).

### import\_data

```
import_data(request: Request, store: Store) -> AtlasJSONResponse
```

`importData`: the form's `data`, an export ZIP, imported as its `request` asks (IMS-01 to IMS-05).

One export or import runs at a time unless the request names `replicatedFrom`; an empty ZIP answers an empty result.

Raises:

- `AtlasError` –

  `UNAUTHORIZED_ACCESS`; `FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK`; what the import fails with.

### import\_file

```
import_file(request: Request, store: Store, body: Body) -> AtlasJSONResponse
```

`importFile`: the export ZIP its `fileName` option names, from the server's import folder (IMS-06, DV-125).

It locks other exports and imports out only when the request names `replicatedFrom`, as Atlas does.

Raises:

- `AtlasError` –

  `UNAUTHORIZED_ACCESS`; `FAILED_TO_OBTAIN_IMPORT_EXPORT_LOCK`; `INVALID_PARAMETERS`; what the import fails with.

### purge\_by\_ids

```
purge_by_ids(request: Request, store: Store, body: Body) -> AtlasJSONResponse
```

`purgeByIds`: remove the `DELETED` entities of a JSON array of GUIDs (EDL-01 to EDL-03).

Raises:

- `AtlasError` –

  `BAD_REQUEST` for a body that is not an array of strings (DV-10).

### time\_zones

```
time_zones() -> list[str]
```

The IANA time zone ids, sorted (DV-05).
