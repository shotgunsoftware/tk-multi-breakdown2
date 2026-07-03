# Copyright (c) 2026 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import sgtk
from tank_vendor.flow_integration_sdk import (
    dependency,
    exceptions,
    globals,
    objects,
    schema,
    utils,
)

if TYPE_CHECKING:
    from ..api import FileItem


def get_scene_objects(
    bg_task_manager: Optional[Any],
) -> tuple[list[dict[str, Any]], Any]:
    """
    Retrieve the scene objects and their associated published files
    using Flow Asset Manager integration.

    Each dependency is mapped to a stub entry shaped like a SG PublishedFile
    but populated with MEDM data (asset_id, revision_id, version_number, etc.)
    so the breakdown app can build its file item model and determine statuses.

    Args:
        bg_task_manager: Background task manager for async operations. If None, execute synchronously.
    Returns:
        A tuple of (scene_objects, published_file_data) where:
            - scene_objects is a list of dictionaries with keys: node_name, node_type, path
            - published_file_data is either a background task id or a dictionary mapping
              file paths to a stub PublishedFile dict populated with MEDM data.
    """

    flow_dependencies = _get_dependencies()

    scene_objects = [
        {
            "node_name": dep_info.node_handle,
            "node_type": dep_info.node_type,
            "path": dep_info.file_path,
        }
        for dep_info in flow_dependencies
    ]

    def build_published_file_stubs():
        result = {}
        for dep_info in flow_dependencies:
            version_number = None
            created_at = None
            if dep_info.version_id:
                version_number = dep_info.version_num

            thumbnail_path = None
            if dep_info.revision_id:
                rev = objects.FlowRevision.get_revision(dep_info.revision_id)
                thumbnail_path = rev.get_thumbnail_file()

            entity = None
            published_file_type = None
            if dep_info.asset_id:
                asset = objects.FlowAsset(dep_info.asset_id)
                entity = {
                    "type": "Asset",
                    "id": dep_info.asset_id,
                    "name": asset.name,
                }
                revision = objects.FlowRevision.get_revision(dep_info.revision_id)
                type_comps = revision.find_components(type_id=globals.BASE_TYPE_ID)
                type_ids = [c.type_id for c in type_comps]
                published_file_type = None
                created_at = asset.created_at
                if type_ids:
                    try:
                        display_name = schema.get_schema_display_name(type_ids[0])
                    except exceptions.FlowError:
                        display_name = type_ids[0]
                    published_file_type = {
                        "type": "PublishedFileType",
                        "id": None,
                        "code": display_name,
                    }

            stub = {
                "type": "PublishedFile",
                "id": None,
                "project": sgtk.platform.current_engine().context.project,
                "entity": entity,
                "name": dep_info.component_name or dep_info.node_handle,
                "created_at": created_at,
                "created_by.HumanUser.name": asset.created_by,
                "description": asset.description,
                "task": None,
                "task.Task.sg_status_list": "No Status",
                "tags": "No Tags",
                "published_file_type": published_file_type,
                "published_file_type.PublishedFileType.code": (
                    published_file_type["code"] if published_file_type else None
                ),
                "path": {"local_path": dep_info.file_path},
                "version_number": version_number,
                "sg_flow_revision_id": dep_info.revision_id,
                "sg_flow_asset_id": dep_info.asset_id,
                "sg_flow_version_id": dep_info.version_id,
                "sg_flow_blob_index": dep_info.blob_index,
                "sg_flow_thumbnail_path": thumbnail_path,
            }
            result[dep_info.file_path] = stub
        return result

    if bg_task_manager:
        return scene_objects, bg_task_manager.add_task(build_published_file_stubs)

    return scene_objects, build_published_file_stubs()


def _get_published_file_type(asset: objects.FlowAsset) -> Optional[dict[str, Any]]:
    """Return a PublishedFileType-shaped stub derived from the asset's type_ids.

    Uses the first type_id in asset.type_ids and resolves its display name via
    schema.get_schema_display_name. Returns None if no type is available.

    Args:
        asset: A Flow Asset object exposing a type_ids attribute (list of str).
    Returns:
        A dict shaped like a SG PublishedFileType entity.
    """
    if not asset or not getattr(asset, "type_ids", None):
        return None
    type_id = asset.type_ids[0]
    try:
        display_name = schema.get_schema_display_name(type_id)
    except exceptions.FlowError:
        display_name = type_id
    return {"type": "PublishedFileType", "id": None, "code": display_name}


def _get_dependencies() -> list[dependency.DependencyData]:
    """Return the list of asset dependencies found in current scene.
    List will contain DependencyData objects which contain pertinent info
    about each asset dependency instance found.

    The DependencyData node contains detailed information of the dependency such as
        * node_handle (node name)
        * node_type (e.g. "reference")
        * file_path (local file path of dependency)

    Only the top level asset dependencies will be returned.
    """
    # Introspect current scene and get dependency tree
    # (this will include asset and local dependencies together)
    dep_tree = sgtk.platform.current_engine().flow_host.get_dependency_tree()

    # Filter out only the top-level asset (internal) dependencies
    asset_deps = dep_tree.get_internal_dependencies(top_level=True)

    return asset_deps


# ============================
# Get revisions in FPT format
# ============================
def get_latest_revision(
    item: FileItem,
    bg_task_manager: Optional[Any] = None,
) -> dict[str, Any] | "BackgroundTaskManager":
    """
    Get the latest published file (revision) for a single item using MEDM.

    Args:
        item: FileItem to get the latest revision for.
        bg_task_manager: If provided, the query runs async and the task id
            is returned. Otherwise executes synchronously.
    Returns:
        If async, the background task id. Otherwise a dict shaped like a
        SG PublishedFile entity representing the latest revision.
    """
    _bundle = sgtk.platform.current_bundle()

    def _fetch_latest():
        item_data = item.sg_data or {}
        asset_id = item_data.get("sg_flow_asset_id")
        if not asset_id:
            raise exceptions.FlowError("No asset ID found for item")

        project = _bundle.context.project

        try:
            asset = objects.FlowAsset(asset_id)
            latest_revision = asset.get_latest_revision()
            if not latest_revision:
                _bundle.logger.warning(f"No latest revision found for asset {asset_id}")
                raise exceptions.FlowError(
                    f"No latest revision found for asset {asset_id}"
                )
        except exceptions.FlowError as e:
            _bundle.logger.error(
                f"Failed to get latest revision for asset {asset_id}: {e}"
            )
            raise

        published_file_type = _get_published_file_type(asset)

        local_path = latest_revision.get_storage_component_path(
            component_purpose=globals.SOURCE_PURPOSE
        )

        created_at = asset.created_at

        return {
            "type": "PublishedFile",
            "id": None,
            "project": project,
            "entity": {
                "type": "Asset",
                "id": asset_id,
                "name": asset.name,
            },
            "name": item_data.get("name"),
            "task": None,
            "task.Task.sg_status_list": "No Status",
            "tags": "No Tags",
            "published_file_type": published_file_type,
            "published_file_type.PublishedFileType.code": (
                published_file_type["code"] if published_file_type else None
            ),
            "path": {"local_path": local_path} if local_path else None,
            "version_number": asset.version_number,
            "created_at": created_at,
            "created_by.HumanUser.name": asset.created_by,
            "description": asset.description,
            "sg_flow_revision_id": latest_revision.id,
            "sg_flow_asset_id": asset_id,
            "sg_flow_version_id": asset.version_id,
        }

    if bg_task_manager:
        return bg_task_manager.add_task(_fetch_latest)
    return _fetch_latest()


def get_assets_for_items(
    items: list[FileItem],
    bg_task_manager: Optional[Any] = None,
) -> list[dict[str, Any]] | "BackgroundTaskManager":
    """
    Get all published file revisions for the given items using FlowAM.

    Queries FlowAM for all numbered versions of each item's asset, returning
    them as PublishedFile-shaped dicts so the breakdown model can build its
    version mapping and determine statuses.

    Args:
        items: List of FileItem objects to get published files for.
        bg_task_manager: If provided, the query runs async and the task id
            is returned. Otherwise executes synchronously.
    Returns:
        If async, the background task id. Otherwise a list of dicts shaped
        like SG PublishedFile entities, sorted newest-first per asset.
    """

    _bundle = sgtk.platform.current_bundle()

    def _fetch_all_versions():
        project = _bundle.context.project
        result = []
        processed_assets = {}

        for item in items:
            item_data = item.sg_data or {}
            asset_id = item_data.get("sg_flow_asset_id")
            if not asset_id:
                continue

            name = item_data.get("name")

            if asset_id not in processed_assets:
                try:
                    asset = objects.FlowAsset(asset_id)
                    versions = list(asset.iterate_versions())
                    processed_assets[asset_id] = (asset, versions)
                except exceptions.FlowError:
                    _bundle.logger.error(
                        f"Failed to query versions for asset {asset_id}"
                    )
                    continue

            asset, versions = processed_assets[asset_id]
            published_file_type = _get_published_file_type(asset)

            for version in versions:
                revision = version.revision
                local_path = revision.get_storage_component_path(
                    component_purpose=globals.SOURCE_PURPOSE
                )

                created_at = version.created_at

                thumbnail_path = None
                try:
                    thumbnail_path = revision.get_thumbnail_file()
                except exceptions.FlowError:
                    _bundle.logger.error(
                        f"Failed to get thumbnail path for revision {revision.id}"
                    )

                result.append(
                    {
                        "type": "PublishedFile",
                        "id": None,
                        "project": project,
                        "entity": {
                            "type": "Asset",
                            "id": asset_id,
                            "name": asset.name,
                        },
                        "name": name,
                        "task": None,
                        "task.Task.sg_status_list": "No Status",
                        "tags": "No Tags",
                        "published_file_type": published_file_type,
                        "published_file_type.PublishedFileType.code": (
                            published_file_type["code"] if published_file_type else None
                        ),
                        "path": {"local_path": local_path} if local_path else None,
                        "version_number": version.version_number,
                        "created_at": created_at,
                        "created_by.HumanUser.name": version.created_by,
                        "description": revision.comment,
                        "sg_flow_revision_id": revision.id,
                        "sg_flow_asset_id": asset_id,
                        "sg_flow_version_id": version.id,
                        "sg_flow_thumbnail_path": thumbnail_path,
                    }
                )

        return result

    if bg_task_manager:
        return bg_task_manager.add_task(_fetch_all_versions)
    return _fetch_all_versions()


# ============================
# Update depdendencies methods
# ============================
def update_to_latest(items: list[FileItem]) -> list[FileItem]:
    """Update the given items in the scene.

    Args:
        items: list of file item object to update
    Returns:
        list of file item that were updated
    """
    items_to_update = []
    for file_item in items:
        res = _update_dependency(
            file_item.sg_data["sg_flow_revision_id"],
            node_handle=file_item.node_name,
        )
        if res:
            items_to_update.append(file_item)

    return items_to_update


def update_to_revision(
    item: Optional[FileItem],
    item_data: Optional[dict[str, Any]] = None,
) -> bool:
    """Update the item to a specific version.

    Args:
        item: Dictionary representation of the FileItem to update
        item_data: Dictionary of Flow Production Tracking data representing the target
                published file revision to update to.

    Returns:
        True if the item requires the data model to update, else False will not
        trigger a model update.
    """
    _bundle = sgtk.platform.current_bundle()
    # Validate item_data contains the required revision ID
    if not item_data or not item_data.get("sg_flow_revision_id"):
        _bundle.logger.warning(
            "Cannot update to revision: item_data is missing or lacks sg_flow_revision_id"
        )
        return False

    # Validate item structure
    flowam_data = item.get("sg_data") if item else None
    if not flowam_data or not flowam_data.get("sg_flow_revision_id"):
        _bundle.logger.warning(
            "Cannot update to revision: item sg_data is missing or lacks sg_flow_revision_id"
        )
        return False

    do_update = _update_dependency(
        revision_id=flowam_data["sg_flow_revision_id"],
        new_revision_id=item_data["sg_flow_revision_id"],
        node_handle=item.get("node_name"),
    )

    return do_update


def _update_dependency(
    revision_id: str,
    new_revision_id: str | None = None,
    node_handle: str | None = None,
) -> bool:
    """Given an asset dependency, update all relevant dependencies to that revision
    within the scene to the latest version of that asset or a specific version if provided.

    Args:
        revision_id: Revision id of original dependency. This can be a version id.
        new_revision_id: Revision id to change to. If None, update to latest revision
                         of the same asset. This can be a version id.
        node_handle: Unique dependency identifier. If not provided, all dependencies
                     of given revision id will be updated.

    Returns:
        True if dependency(ies) were updated.
        False if revision is already matching the specification and nothing was done.

    Raises:
        EntityNotFoundError
        FlowError
    """
    if sgtk.platform.current_engine().name == "tk-desktop":
        raise exceptions.FlowError(
            "Updating dependency is not relevant outside of a DCC context."
        )

    try:
        if objects.FlowVersion.is_version_id(revision_id):
            input_type = "version"
            rev = objects.FlowVersion(revision_id).revision
        else:
            input_type = "revision"
            rev = objects.FlowRevision.get_revision(revision_id)
    except exceptions.FlowError as exc:
        msg = f"Invalid {input_type} id provided: {revision_id}."
        raise exceptions.EntityNotFoundError(
            entity_id=revision_id, details=msg
        ) from exc

    if new_revision_id:
        try:
            if objects.FlowVersion.is_version_id(new_revision_id):
                input_type = "version"
                new_rev = objects.FlowVersion(new_revision_id).revision
            else:
                input_type = "revision"
                new_rev = objects.FlowRevision.get_revision(new_revision_id)
        except exceptions.FlowError as exc:
            msg = f"Invalid new {input_type} id provided: {new_revision_id}."
            raise exceptions.EntityNotFoundError(
                entity_id=new_revision_id, details=msg
            ) from exc
    else:
        # Determine the latest revision of same asset
        asset = objects.FlowAsset(rev.asset_id)
        new_rev = asset.get_latest_revision()

    if rev.revision_number == new_rev.revision_number:
        # Already matching the spec, so nothing to be done
        return False

    # Fetch source component of new revision
    new_rev.fetch(component_purpose=globals.SOURCE_PURPOSE)

    file_seq_comp = new_rev.find_component(
        type_id=schema.get_schema_id(globals.FILE_SEQ_TYPE)
    )
    if file_seq_comp:
        # Return a file path with embedded frame padding
        new_path = utils.cleanpath(
            new_rev.get_storage_dir(), file_seq_comp.properties["fileFormat"]
        )
    else:
        new_path = new_rev.get_storage_component_path(
            component_purpose=globals.SOURCE_PURPOSE
        )

    # Get list of top-level asset dependencies in scene
    orig_revision_id = rev.id
    host = sgtk.platform.current_engine().flow_host
    dep_tree = host.get_dependency_tree()
    asset_deps = dep_tree.get_internal_dependencies(top_level=True)
    for dep in asset_deps:
        if dep.revision_id == orig_revision_id:
            if node_handle and dep.node_handle != node_handle:
                continue  # skip if node handle doesn't match
            host.update_dependency(dep, new_path)

    return True
