"""The server's settings, read once at start-up from the environment (SRV-01, SRV-03, SRV-06)."""

from pathlib import Path
from typing import Literal

from aurelius_atlas_core.audit_reduction_service import AuditAgingConfig
from aurelius_atlas_core.entity_documents import INDEX_PREFIX
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR
from aurelius_atlas_store_es import StoreSettings
from aurelius_atlas_store_es.snapshots import SnapshotPolicy
from pydantic import DirectoryPath, Field, FilePath, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_SERVER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_PORT = 21000
"""The port Apache Atlas listens on."""

SNAPSHOT_INDICES = (f"{INDEX_PREFIX}-*",)
"""The indices a snapshot holds and a restore brings back: all the server's (SNP-01, SNP-05)."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels both uvicorn and the OTel console accept."""


class StoreAccessSettings(BaseSettings):
    """Where the store is and where its snapshots are: all the snapshot command needs (SNP-04, SNP-05)."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    elasticsearch_hosts: list[HttpUrl] = Field(min_length=1)
    """Base URLs of the Elasticsearch nodes, as a JSON list: ``["https://localhost:9200"]``."""

    elasticsearch_username: str = "elastic"
    """User for the store."""

    elasticsearch_password: SecretStr
    """Password for the store; never shown in logs."""

    elasticsearch_ca_certs: FilePath
    """PEM file with the certificate authority of the Elasticsearch server certificate."""

    snapshot_location: str = "aurelius-atlas"
    """The repository's directory, below the store's ``path.repo`` (SNP-01)."""

    def store_settings(self) -> StoreSettings:
        """The settings of the Elasticsearch store."""
        return StoreSettings(
            hosts=self.elasticsearch_hosts,
            username=self.elasticsearch_username,
            password=self.elasticsearch_password,
            ca_certs=self.elasticsearch_ca_certs,
        )


class ServerSettings(StoreAccessSettings):
    """How the server runs and where its store is."""

    host: str = "localhost"
    """The interface to listen on; the container image sets ``0.0.0.0``."""

    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    """The port to listen on (SRV-03)."""

    log_level: LogLevel = "info"
    """The lowest level of log record the server and uvicorn emit."""

    tls_cert_file: FilePath
    """PEM certificate to serve HTTPS with (SRV-06, DD-234): required — the server never serves plaintext,
    the way the store's password is required (SRV-01, SRV-02)."""

    tls_key_file: FilePath
    """PEM private key of ``tls_cert_file`` (SRV-06)."""

    hsts_enabled: bool = True
    """Whether responses carry ``Strict-Transport-Security`` (SRV-08, DD-236). The image ships True; the dev
    arrangement turns it off so a browser that visited the mkcert server is not pinned to HTTPS on the
    plaintext dev surfaces (ADR 039's named relaxations)."""

    root_path: str = Field(default="", pattern=r"^(/[^/\s]+)*$")
    """The path a proxy serves the server under, such as ``/atlas2``, passed to uvicorn: the server's redirects
    and its sign-in's return lead there; empty serves it at the root (PFX-01, DD-363)."""

    forwarded_allow_ips: str = "127.0.0.1"
    """Which peers may rewrite the client address through ``X-Forwarded-For`` (SRV-10, DD-238), passed to
    uvicorn. The default trusts only the loopback; behind a proxy the arrangement names the proxy network,
    so the access log and OTel peer attributes key on the browser's address, not the proxy's. The rate
    limit itself lives at the webapp's nginx edge, not here (SRV-09, DD-238)."""

    dashboard_dir: DirectoryPath | None = None
    """The built dashboards: ``dashboardv2`` at its root and ``dashboardv3`` in ``n/``; None serves the API only
    (DSH-04)."""

    models_dir: Path = BUILTIN_MODELS_DIR
    """The models loaded at start-up: by default ``addons/models`` of Apache Atlas 2.4.0; a missing directory loads
    none (MDL-01, MDL-16, DD-032)."""

    m4i_models_enabled: bool = True
    """Whether the m4i data dictionary types are loaded at start-up too, after ``models_dir``; off loads none and
    leaves those stored as they are (MDD-01, MDD-03, ADR 058)."""

    @property
    def model_dirs(self) -> list[Path]:
        """The models directories loaded at start-up, in order (MDD-01)."""
        return [self.models_dir, *([M4I_MODELS_DIR] if self.m4i_models_enabled else [])]

    typedef_refresh_seconds: float = Field(default=5.0, ge=0)
    """How long the server answers from its type registry before it checks for another process's type change
    (TDS-13, DD-029)."""

    delete_type: Literal["soft", "hard"] = "soft"
    """How entities are deleted unless a request chooses: ``atlas.DeleteHandlerV1.impl`` (EDL-04, DD-059)."""

    delete_type_override: bool = False
    """Whether a request's ``deleteType`` chooses: ``atlas.rest.enable.delete.type.override`` (EDL-04, DD-059)."""

    tasks_enabled: bool = True
    """Whether propagation is deferred to tasks a worker runs after the request: ``atlas.tasks.enabled`` (TSK-02,
    DD-081)."""

    task_poll_seconds: float = Field(default=10.0, gt=0)
    """How often the worker looks for tasks other processes recorded or left behind (DD-080)."""

    embedding_url: HttpUrl | None = None
    """The base of an OpenAI-compatible embeddings API, as the embedder of 11.2 serves one; unset, embedding is
    off: no vectors are mapped or computed (VEC-08, ADR 059)."""

    embedding_model: str = "intfloat/multilingual-e5-small"
    """The model the embeddings are computed with, sent with every request and recorded with each embedding."""

    embedding_dimensions: int = Field(default=384, gt=0)
    """The model's vectors' dimensions, as the entity index maps them (VEC-03, DD-438)."""

    embedding_ca_file: FilePath | None = None
    """PEM CA verifying the embedder's TLS; unset uses the system trust store."""

    embedding_batch_size: int = Field(default=32, gt=0, le=256)
    """Entities per page of the indexer and per request to the embedder, which takes 256 at most (EMB-01)."""

    embedding_poll_seconds: float = Field(default=10.0, gt=0)
    """How often the indexer looks for entities without a current embedding (VEC-07, DD-436)."""

    hybrid_vector_weight: float = Field(default=10.0, ge=0)
    """What a hybrid search multiplies an entity's vector score by before adding its text score (SBM-03, DD-442)."""

    import_folder: Path | None = None
    """The one folder ``admin/importfile`` reads export ZIPs from; none refuses every file (IMS-06, DV-125)."""

    cluster_name: str = "default"
    """The cluster an export says it comes from: ``atlas.metadata.namespace``, else ``atlas.cluster.name`` (EXP-06)."""

    lineage_on_demand_enabled: bool = False
    """Whether ``POST v2/lineage/{guid}`` answers lineage on demand: ``atlas.lineage.on.demand.enabled`` (LIN-06)."""

    lineage_on_demand_default_node_count: int = Field(default=3, ge=1)
    """The relations each way lineage on demand takes by default: ``atlas.lineage.on.demand.default.node.count``
    (LIN-06)."""

    lineage_max_node_count: int = Field(default=9000, ge=1)
    """The relations past which lineage adds none (at most 9,000): ``atlas.lineage.max.node.count`` (LIN-04)."""

    metrics_persist_interval_minutes: int = Field(default=60, ge=0)
    """How often the metrics are stored, in minutes on their multiples since the epoch; 0 stores none:
    ``atlas.metrics.persist.schedule`` (MHS-05, DV-137)."""

    metrics_ttl_hours: int = Field(default=336, ge=1)
    """How long a stored metric is kept: ``atlas.metrics.ttl.hours`` (MHS-01, MHS-05)."""

    audit_aging_enabled: bool = False
    """Whether the entity audits age out on a schedule, and ``admin/audits/ageout?useAuditConfig`` ages them:
    ``atlas.audit.aging.enabled`` (AGE-02, AGE-05)."""

    audit_default_ageout_enabled: bool = True
    """``atlas.audit.default.ageout.enabled``: the default aging, of the types no other aging names (AGE-02)."""

    audit_default_ageout_ttl_in_days: int = 90
    """``atlas.audit.default.ageout.ttl.in.days``: at least ``audit_min_ttl_to_maintain`` (AGE-02)."""

    audit_default_ageout_count: int = 0
    """``atlas.audit.default.ageout.count``: the newest audits each entity keeps; 0 for no count (AGE-02)."""

    audit_default_ageout_ignore_ttl: bool = False
    """``atlas.audit.default.ageout.ignore.ttl``: the default aging by count alone (AGE-02)."""

    audit_custom_ageout_ttl_in_days: int = 0
    """``atlas.audit.custom.ageout.ttl.in.days`` (AGE-02)."""

    audit_custom_ageout_count: int = 0
    """``atlas.audit.custom.ageout.count`` (AGE-02)."""

    audit_custom_ageout_entity_types: str | None = None
    """``atlas.audit.custom.ageout.entity.types``: comma-separated, ``<prefix>*`` for all that start so (AGE-02)."""

    audit_custom_ageout_action_types: str | None = None
    """``atlas.audit.custom.ageout.action.types``: comma-separated action names or prefixes (AGE-02)."""

    audit_sweep_out_enabled: bool = False
    """``atlas.audit.sweep.out.enabled``: every audit of the sweep's types and actions removed (AGE-02)."""

    audit_sweep_out_entity_types: str | None = None
    """``atlas.audit.sweep.out.entity.types`` (AGE-02)."""

    audit_sweep_out_action_types: str | None = None
    """``atlas.audit.sweep.out.action.types`` (AGE-02)."""

    audit_create_events_ageout_allowed: bool = False
    """``atlas.audit.create.events.ageout.allowed``: creations may age out too (AGE-04)."""

    audit_aging_subtypes_included: bool = True
    """``atlas.audit.aging.subtypes.included``: an aging's types take their sub types (AGE-04)."""

    audit_min_ttl_to_maintain: int = 7
    """``atlas.audit.min.ttl.to.maintain``: the least TTL, in days, an aging may have (AGE-02)."""

    audit_min_count_to_maintain: int = 50
    """``atlas.audit.min.count.to.maintain``: the least count an aging may keep (AGE-02)."""

    audit_reduction_max_pending_tasks: int = 50
    """``atlas.audit.reduction.max.pending.tasks``: past it no aging is queued (AGE-03)."""

    audit_aging_scheduler_frequency_in_days: int = 30
    """``atlas.audit.aging.scheduler.frequency.in.days``: at least 1 (AGE-05)."""

    audit_aging_scheduler_initial_delay_in_min: int = 1
    """``atlas.audit.aging.scheduler.initial.delay.in.min``: at least 1 (AGE-05)."""

    snapshot_enabled: bool = False
    """Whether the server puts the store's snapshot policy at start and watches its runs (SNP-01 to SNP-03). The
    chart turns it on; the dev store's data is disposable."""

    snapshot_schedule: str = "0 0 * * * ?"
    """When a snapshot is taken, as an Elasticsearch cron expression in UTC: every hour on the hour (SNP-02)."""

    snapshot_retention: str = "7d"
    """How long a snapshot is kept, as an Elasticsearch time unit (SNP-02)."""

    snapshot_check_minutes: int = Field(default=15, ge=1)
    """How often the server reads how the policy's last runs went (SNP-03)."""

    revision: str = "UNKNOWN"
    """The source revision the server was built from, reported by ``admin/version`` (ADM-01)."""

    otel_token_url: HttpUrl | None = None
    """The issuer's token endpoint for the OTLP ingest credential (7.18,
    DD-196): with ``otel_client_secret`` set, the server exports OTLP through
    the app-owned pipeline (the collector's per-service leg accepts only
    client-credentials JWTs); unset, the server exports no OTLP (console
    only). The OTel env vars (``OTEL_EXPORTER_OTLP_*``) are deliberately not
    read: the 60s dev token cannot ride a static header (DD-196)."""

    otel_client_id: str = "otel-atlas-server"
    """The ingest realm client the server mints for (7.18, DD-196)."""

    otel_client_secret: SecretStr | None = None
    """The secret of ``otel_client_id``; never shown in logs."""

    otel_endpoint: str = "https://localhost:4319"
    """The collector's per-service-leg HTTP base for the OTLP export
    (7.18, DD-196); the dev compose overrides with the service DNS name."""

    otel_ca_file: FilePath | None = None
    """PEM CA verifying the collector's TLS for the OTLP export; unset uses
    the system trust store (the dev stack's mkcert CA is not system-wide)."""

    auth_server_url: HttpUrl
    """The identity provider's root (Keycloak), which tokens are verified against and browsers sign in at
    (AUT-02, AUT-05; ADR 007)."""

    auth_realm: str = "master"
    """The realm the tokens are issued from."""

    auth_client_id: str = "aurelius-atlas-server"
    """The server's confidential client: browsers sign in with it, and its tokens are accepted (AUT-05)."""

    auth_client_secret: SecretStr
    """The secret of ``auth_client_id``; never shown in logs."""

    auth_audiences: list[str] = Field(default_factory=list)
    """Further clients whose tokens the server accepts: the webapp's, which the auxiliary APIs forward
    (AUT-02, AUT-10)."""

    auth_principal_claim: str = "preferred_username"
    """The claim a user's name is read from: Atlas's Keycloak ``principal-attribute`` (AUT-03, DD-250)."""

    auth_groups_claim: str = "groups"
    """The claim a user's groups are read from, else the realm roles: ``atlas.authentication.method.keycloak
    .groups_claim`` (AUT-03)."""

    auth_ca_file: FilePath | None = None
    """PEM CA verifying the provider's TLS; unset uses the system trust store."""

    session_timeout_seconds: int = Field(default=3600, gt=0)
    """How long a browser session lasts unused: Atlas's ``web.xml`` session timeout, 60 minutes (AUT-06)."""

    @property
    def tls(self) -> tuple[Path, Path]:
        """The certificate and key to serve HTTPS with (SRV-03, SRV-06, DD-234)."""
        return Path(self.tls_cert_file), Path(self.tls_key_file)

    def snapshot_policy(self) -> SnapshotPolicy:
        """The snapshot policy of the server's indices, every index of ``INDEX_PREFIX`` (SNP-01, SNP-02)."""
        return SnapshotPolicy(
            indices=SNAPSHOT_INDICES,
            location=self.snapshot_location,
            schedule=self.snapshot_schedule,
            expire_after=self.snapshot_retention,
        )

    def audit_aging_config(self) -> AuditAgingConfig:
        """The ``atlas.audit.*`` aging settings of the core's aging (AGE-02)."""
        return AuditAgingConfig(
            aging_enabled=self.audit_aging_enabled,
            default_ageout_enabled=self.audit_default_ageout_enabled,
            default_ageout_ttl_in_days=self.audit_default_ageout_ttl_in_days,
            default_ageout_count=self.audit_default_ageout_count,
            default_ageout_ignore_ttl=self.audit_default_ageout_ignore_ttl,
            custom_ageout_ttl_in_days=self.audit_custom_ageout_ttl_in_days,
            custom_ageout_count=self.audit_custom_ageout_count,
            custom_ageout_entity_types=self.audit_custom_ageout_entity_types,
            custom_ageout_action_types=self.audit_custom_ageout_action_types,
            sweep_out_enabled=self.audit_sweep_out_enabled,
            sweep_out_entity_types=self.audit_sweep_out_entity_types,
            sweep_out_action_types=self.audit_sweep_out_action_types,
            create_events_ageout_allowed=self.audit_create_events_ageout_allowed,
            subtypes_included=self.audit_aging_subtypes_included,
            min_ttl_to_maintain=self.audit_min_ttl_to_maintain,
            min_count_to_maintain=self.audit_min_count_to_maintain,
            max_pending_tasks=self.audit_reduction_max_pending_tasks,
        )
