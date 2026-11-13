"""The administrative answers: what ``admin/version``, ``admin/status`` and ``admin/session`` write.

ADM-01, ADM-02, ADM-05. Apache Atlas builds each one inline — the version map of
``AtlasVersion.asMap()``, the status map of ``AdminResource#getStatus``, and the session's JSON object of
``AdminResource`` — so each keeps its Java key names, the dotted settings names included.
"""

from typing import Any

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel, JavaBool, JavaInt


class AtlasVersionInfo(AtlasModel):
    """``AtlasVersion.asMap()``: the four strings of ``admin/version`` (ADM-01, DV-03).

    ``webapp/src/main/java/org/apache/atlas/web/resources/AdminResource.java#getVersion`` puts them under
    ``Version``, ``Revision``, ``Name`` and ``Description`` — capitalized, unlike the JSON names elsewhere.
    """

    version: str = Field(default="", alias="Version")
    revision: str = Field(default="", alias="Revision")
    name: str = Field(default="", alias="Name")
    description: str = Field(default="", alias="Description")


class AtlasServiceStatus(AtlasModel):
    """The map of ``admin/status`` (ADM-02): ``webapp/.../AdminResource.java#getStatus``.

    Aurelius Atlas has no high-availability states, so ``Status`` is always ``ACTIVE`` while it runs.
    """

    status: str = Field(default="ACTIVE", alias="Status")


class AtlasSessionProfile(AtlasModel):
    """The session object of ``admin/session`` (ADM-05).

    ``webapp/src/main/java/org/apache/atlas/web/resources/AdminResource.java#AdminResource`` (the session
    defaults), ``webapp/.../AtlasCSRFPreventionFilter.java`` (the CSRF defaults) and
    ``intg/src/main/java/org/apache/atlas/AtlasConfiguration.java`` (the feature switches). The settings
    carry their ``atlas.`` names as they are; ``userName`` is null for a request without a user.

    ``to_json`` is overridden: Java writes every key of this object, the null ``userName``
    included, so unlike the other models no key may drop out of the answer (ADM-05).
    """

    csrf_enabled: bool = Field(default=True, alias="atlas.rest-csrf.enabled")
    csrf_useragents_regex: str = Field(
        default="^Mozilla.*,^Opera.*,^Chrome", alias="atlas.rest-csrf.browser-useragents-regex"
    )
    csrf_methods_to_ignore: str = Field(default="GET,OPTIONS,HEAD,TRACE", alias="atlas.rest-csrf.methods-to-ignore")
    csrf_custom_header: str = Field(default="X-XSRF-HEADER", alias="atlas.rest-csrf.custom-header")
    ui_editable_entity_types: str = Field(default="hdfs_path", alias="atlas.ui.editable.entity.types")
    ui_default_version: str = Field(default="v2", alias="atlas.ui.default.version")
    ui_date_timezone_format_enabled: bool = Field(default=True, alias="atlas.ui.date.timezone.format.enabled")
    ui_date_format: str = Field(default="MM/DD/YYYY hh:mm:ss A", alias="atlas.ui.date.format")
    debug_metrics_enabled: bool = Field(default=False, alias="atlas.debug.metrics.enabled")
    tasks_enabled: JavaBool = Field(default=True, alias="atlas.tasks.enabled")
    tasks_ui_tab_enabled: bool = Field(default=False, alias="atlas.tasks.ui.tab.enabled")
    lineage_on_demand_enabled: bool = Field(default=False, alias="atlas.lineage.on.demand.enabled")
    lineage_on_demand_default_node_count: JavaInt = Field(default=3, alias="atlas.lineage.on.demand.default.node.count")
    relationship_search_enabled: bool = Field(default=False, alias="atlas.relationship.search.enabled")
    entity_update_allowed: JavaBool = Field(default=False, alias="atlas.entity.update.allowed")
    entity_create_allowed: JavaBool = Field(default=False, alias="atlas.entity.create.allowed")
    user_name: str | None = Field(default=None, alias="userName")
    groups: list[str] = Field(default_factory=list, alias="groups")
    timezones: list[str] = Field(default_factory=list, alias="timezones")
    csrf_token: str = Field(default="", alias="_csrfToken")

    def to_json(self) -> dict[str, Any]:
        """The session object with every key, a null ``userName`` kept (ADM-05)."""
        return self.model_dump(mode="python", by_alias=True)
