"""The per-request services the entity endpoints build from their dependencies (SVC-03, DD-795).

``routes/entity.py`` holds handlers and nothing else: every per-request service, and the store helpers
every family shares, live here. A sibling route imports the module that owns the service instead of the
entity hub (SVC-04), and the helpers that find or check an entity by its ``attr:`` values live here
because every family that names an entity that way needs the same read (ERD-08, CLS-06).
"""

from collections.abc import Mapping
from typing import Annotated, Any

from aurelius_atlas_core.classification_associator import ClassificationAssociator
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_business_metadata import EntityBusinessMetadata
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_labels import EntityLabels
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.import_writer import ImportWriter
from aurelius_atlas_model.errors import java_string, validate_param_length
from aurelius_atlas_model.params import (
    EntityDeleteParams,
    EntityReadParams,
    EntityWriteParams,
    UniqueAttributeParams,
    first_value,
    parse_flag,
    read_params,
)
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.entity_type import EntityType
from fastapi import Depends, Request
from pydantic import BaseModel

from aurelius_atlas_server.authentication import acting_user
from aurelius_atlas_server.deps import Authorizer, Settings, StoreSet
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode

READ_ENTITY_GUID = "read entity: guid="
"""The action text every entity read audits under (AUZ-11)."""


async def entity_store(found: StoreSet) -> EntityStore:
    """The entity store of the request's tenant, its registry refreshed when due (ERD-10, TDS-13, TSS-06).

    The store set arrives as a dependency, so a request that needs both resolves it once (DD-794, DD-799).
    """
    await found.typedef_store.refresh()
    return found.entity_store


type Store = Annotated[EntityStore, Depends(entity_store)]


def read_query[M: BaseModel](model: type[M], request: Request) -> M:
    """A query-parameter model read from a request, its own checks applied (DV-39, TYR-04).

    Raises:
        AtlasError: the model's refusal of a parameter it cannot take.
    """
    return read_params(model, request.query_params)


def flag(request: Request, name: str) -> bool:
    """A boolean query parameter as JAX-RS reads one: its first value, true only for ``true`` in any case."""
    return parse_flag(first_value(request.query_params, name))


def unique_attributes(request: Request) -> dict[str, Any]:
    """``getAttributes``: each ``attr:<name>`` parameter with its first value (ERD-08)."""
    return read_query(UniqueAttributeParams, request).attributes


def unique_attribute_sets(request: Request) -> list[dict[str, Any]]:
    """``getAttributesList``: one set per index of ``attr_<n>:<name>``, in the order indices appear (ERD-08, DV-19)."""
    return read_query(UniqueAttributeParams, request).attribute_sets


def ensure_entity_type(store: EntityStore, type_name: str) -> EntityType:
    """``ensureEntityType``: the entity type named ``type_name`` (ERD-08).

    Raises:
        AtlasError: ``TYPE_NAME_INVALID`` when there is no such entity type.
    """
    entity_type = store.registry.entity_type(type_name)
    if entity_type is None:
        raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, TypeCategory.ENTITY.value, type_name)
    return entity_type


def validate_unique_attributes(entity_type: EntityType, attributes: Mapping[str, Any]) -> None:
    """``validateUniqueAttribute``: at least one attribute, each a unique one of the type (ERD-08).

    Raises:
        AtlasError: ``ATTRIBUTE_UNIQUE_INVALID`` naming the type and the attribute, or ``""`` for none.
    """
    if not attributes:
        raise AtlasError(AtlasErrorCode.ATTRIBUTE_UNIQUE_INVALID, entity_type.type_name, "")
    for name in attributes:
        attribute = entity_type.attribute(name)
        if attribute is None or not attribute.attribute_def.is_unique:
            raise AtlasError(AtlasErrorCode.ATTRIBUTE_UNIQUE_INVALID, entity_type.type_name, name)


def ensure_classification_type(store: EntityStore, name: str) -> None:
    """``ensureClassificationType``: a classification type is named ``name`` (CLS-03, CLS-09).

    Raises:
        AtlasError: ``TYPE_NAME_INVALID`` (``CLASSIFICATION``) when there is none.
    """
    if store.registry.classification_type(name) is None:
        raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, TypeCategory.CLASSIFICATION.value, name)


async def guid_by_unique_attributes(store: EntityStore, type_name: str, request: Request) -> str:
    """``getGuidByUniqueAttributes`` of the ``attr:`` values (CLS-06).

    Raises:
        AtlasError: ``TYPE_NAME_INVALID``, ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND``.
    """
    validate_param_length("typeName", type_name)
    entity_type = ensure_entity_type(store, type_name)
    attributes = unique_attributes(request)
    found = await store.find_by_unique_attributes(entity_type, attributes)
    if found is None:
        raise AtlasError(AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND, type_name, java_string(attributes))
    return found.entity.guid


def retriever(request: Request, store: EntityStore) -> EntityRetriever:
    """A retriever with the request's ``minExtInfo`` and ``ignoreRelationships``."""
    given = read_query(EntityReadParams, request)
    return EntityRetriever(store, min_ext_info=given.min_ext_info, ignore_relationships=given.ignore_relationships)


def tasks_enabled(settings: Settings) -> bool:
    """Whether propagation is deferred to tasks: the server's ``tasks_enabled`` setting (TSK-02, DD-081)."""
    return bool(settings.tasks_enabled)


def notifier(store: Store, found: StoreSet) -> EntityChangeNotifier:
    """The change notifier of a request: its changes recorded in the server's audit (DD-084)."""
    return EntityChangeNotifier(store, [EntityAuditListener(found.entity_audits, store.now)])


def writer(request: Request, store: Store, found: StoreSet, settings: Settings, authorized: Authorizer) -> EntityWriter:
    """A writer deleting as the server's ``delete_type`` setting says unless a request chooses (EDL-04).

    Propagation is deferred as ``tasks_enabled`` says; the changes are audited (DD-084) and checked (AUZ-07).
    """
    return EntityWriter(
        store,
        delete_type=DeleteType.of(settings.delete_type),
        user=acting_user(request),
        tasks=tasks_enabled(settings),
        notifier=notifier(store, found),
        authorizer=authorized,
    )


type Writer = Annotated[EntityWriter, Depends(writer)]


def updater(
    request: Request, store: Store, found: StoreSet, settings: Settings, authorized: Authorizer
) -> EntityWriter:
    """A writer creating and updating as the request's user, audited and checked (EWR-02, AUZ-07).

    The request may opt in to moving a child it does not own with ``unsafeReparent`` (RPS-04, DD-756).
    """
    return EntityWriter(
        store,
        user=acting_user(request),
        tasks=tasks_enabled(settings),
        notifier=notifier(store, found),
        authorizer=authorized,
        unsafe_reparent=read_query(EntityWriteParams, request).unsafe_reparent,
    )


type Updater = Annotated[EntityWriter, Depends(updater)]


def importer(
    request: Request, store: Store, found: StoreSet, settings: Settings, authorized: Authorizer
) -> ImportWriter:
    """A writer creating entities as an import, as the request's user, audited (IMS-04, WRS-07).

    An import keeps the exported GUIDs and is checked against no privilege, so no delete type and no
    ``unsafeReparent`` choice apply (IMP-07).
    """
    return ImportWriter(
        store,
        user=acting_user(request),
        tasks=tasks_enabled(settings),
        notifier=notifier(store, found),
        authorizer=authorized,
    )


def classifications(
    request: Request, store: Store, found: StoreSet, settings: Settings, authorized: Authorizer
) -> EntityClassifications:
    """Classification changes, propagation deferred as the server's ``tasks_enabled`` setting says (TSK-02).

    Each read and change is checked (AUZ-08).
    """
    return EntityClassifications(
        store,
        user=acting_user(request),
        tasks=tasks_enabled(settings),
        notifier=notifier(store, found),
        authorizer=authorized,
    )


type Classifications = Annotated[EntityClassifications, Depends(classifications)]


def associator(
    request: Request, store: Store, found: StoreSet, settings: Settings, authorized: Authorizer
) -> ClassificationAssociator:
    """The bulk classifier of a request, its propagation deferred as ``tasks_enabled`` says (CLA-01).

    The changes are audited (DD-084) and each step checked (AUZ-08).
    """
    return ClassificationAssociator(
        store,
        user=acting_user(request),
        tasks=tasks_enabled(settings),
        notifier=notifier(store, found),
        authorizer=authorized,
    )


type Associator = Annotated[ClassificationAssociator, Depends(associator)]


def labels(request: Request, store: Store, found: StoreSet, authorized: Authorizer) -> EntityLabels:
    """Label changes as the request's user, audited (LBL-05) and checked (AUZ-16)."""
    return EntityLabels(store, user=acting_user(request), notifier=notifier(store, found), authorizer=authorized)


type LabelsService = Annotated[EntityLabels, Depends(labels)]


def business_metadata(
    request: Request, store: Store, found: StoreSet, authorized: Authorizer
) -> EntityBusinessMetadata:
    """Business attribute changes as the request's user, audited (BMD-06) and checked (AUZ-17)."""
    return EntityBusinessMetadata(
        store, user=acting_user(request), notifier=notifier(store, found), authorizer=authorized
    )


type BusinessMetadataService = Annotated[EntityBusinessMetadata, Depends(business_metadata)]


def delete_type(request: Request, settings: Settings) -> DeleteType:
    """The request's ``deleteType`` when the override is enabled, else ``DEFAULT`` (EDL-04, DD-059).

    The body asks for it rather than the signature: a bad ``deleteType`` is refused only after the GUID or
    type name it names, as Atlas's checks run in that order (EDL-04).
    """
    if not settings.delete_type_override:
        return DeleteType.DEFAULT
    return DeleteType.of(read_query(EntityDeleteParams, request).delete_type)
