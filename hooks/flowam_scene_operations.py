# Copyright (c) 2025 Autodesk, Inc.
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

from tank_vendor.flow_integration_sdk import exceptions, globals, objects, schema

if TYPE_CHECKING:
    from tk_multi_breakdown2.api.item import FileItem

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class FlowBreakdownSceneOperations(HookBaseClass):
    """
    Breakdown operations for Flow Asset Manager integration.

    This implementation handles detection of scene dependencies
    across different DCC applications.
    """

    def _get_published_file_type(
        self, asset: objects.FlowAsset
    ) -> Optional[dict[str, Any]]:
        """Return a PublishedFileType-shaped stub derived from the asset's type_ids.

        Uses the first type_id in asset.type_ids and resolves its display name via
        schema.get_schema_display_name. Returns None if no type is available.

        Args:
            asset: A Flow Asset object exposing a type_ids attribute (list of str).
        Returns:
            A dict shaped like a SG PublishedFileType entity, or None.
        """
        if not asset or not getattr(asset, "type_ids", None):
            return None
        type_id = asset.type_ids[0]
        try:
            display_name = schema.get_schema_display_name(type_id)
        except exceptions.FlowError:
            display_name = type_id
        return {"type": "PublishedFileType", "id": None, "code": display_name}

    def get_scene_objects_and_publishes(
        self,
        manager: Any,
        published_file_fields: list[str],
        bg_task_manager: Optional[Any],
    ) -> tuple[list[dict[str, Any]], Any]:
        """
        Retrieve the scene objects and their associated published files
        using Flow Asset Manager integration.

        Each dependency is mapped to a stub entry shaped like a SG PublishedFile
        but populated with MEDM data (asset_id, revision_id, version_number, etc.)
        so the breakdown app can build its file item model and determine statuses.

        Args:
            manager: The breakdown manager instance, used to get published file fields.
            published_file_fields: List of PublishedFile field names to query from Shotgun.
            bg_task_manager: Background task manager for async operations. If None, execute synchronously.
        Returns:
            A tuple of (scene_objects, published_file_data) where:
                - scene_objects is a list of dictionaries with keys: node_name, node_type, path
                - published_file_data is either a background task id or a dictionary mapping
                  file paths to a stub PublishedFile dict populated with MEDM data.
        """

        self.logger.debug(
            "=== FlowAM Scene Breakdown: get_scene_objects_and_publishes ==="
        )

        flow_dependencies = self.parent.flowam.get_dependencies()

        scene_objects = [
            {
                "node_name": dep_info.node_handle,
                "node_type": dep_info.node_type,
                "path": dep_info.file_path,
            }
            for dep_info in flow_dependencies
        ]

        project = self.parent.context.project

        def build_published_file_stubs():
            result = {}
            for dep_info in flow_dependencies:
                version_number = None
                created_at = None  # dep_info doesn't have it. Skip for now.
                if dep_info.version_id:
                    version_number = dep_info.version_num

                thumbnail_path = None
                if dep_info.revision_id:
                    try:
                        rev = objects.FlowRevision.get_revision(dep_info.revision_id)
                        thumbnail_path = rev.get_thumbnail_file()
                    except exceptions.FlowError:
                        self.logger.warning(
                            f"No thumbnail path found for revision {dep_info.revision_id}"
                        )

                entity = None
                published_file_type = None
                if dep_info.asset_id:
                    asset_name = objects.FlowAsset(dep_info.asset_id).name
                    entity = {
                        "type": "Asset",
                        "id": dep_info.asset_id,
                        "name": asset_name,
                    }
                    revision = objects.FlowRevision.get_revision(dep_info.revision_id)
                    type_comps = revision.find_components(type_id=globals.BASE_TYPE_ID)
                    type_ids = [c.type_id for c in type_comps]
                    published_file_type = None
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
                    "project": project,
                    "entity": entity,
                    "name": dep_info.component_name or dep_info.node_handle,
                    "task": None,
                    "published_file_type": published_file_type,
                    "published_file_type.PublishedFileType.code": (
                        published_file_type["code"] if published_file_type else None
                    ),
                    "path": {"local_path": dep_info.file_path},
                    "version_number": version_number,
                    "created_at": created_at,
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

    def get_published_files_for_items(
        self,
        items: list[FileItem],
        bg_task_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Get all published file revisions for the given items using MEDM.

        Queries MEDM for all numbered versions of each item's asset, returning
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

        def _fetch_all_versions():
            project = self.parent.context.project
            result = []
            processed_assets = {}

            for item in items:
                item_data = item.sg_data or {}
                asset_id = item_data.get("sg_flow_asset_id")
                if not asset_id:
                    continue

                name = item_data.get("name")
                blob_index = item_data.get("sg_flow_blob_index", 0)

                if asset_id not in processed_assets:
                    try:
                        asset = objects.FlowAsset(asset_id)
                        versions = list(asset.iterate_versions())
                        processed_assets[asset_id] = (asset, versions)
                    except exceptions.FlowError:
                        self.logger.warning(
                            f"Failed to query versions for asset {asset_id}"
                        )
                        continue

                asset, versions = processed_assets[asset_id]
                published_file_type = self._get_published_file_type(asset)

                for version in versions:
                    revision = version.revision
                    local_path = None
                    try:
                        local_path = revision.get_storage_component_path(
                            component_purpose=globals.SOURCE_PURPOSE
                        )
                    except exceptions.FlowError:
                        pass

                    created_at = version.created_at

                    thumbnail_path = None
                    try:
                        thumbnail_path = revision.get_thumbnail_file()
                    except exceptions.FlowError:
                        self.logger.warning(
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
                            "published_file_type": published_file_type,
                            "published_file_type.PublishedFileType.code": (
                                published_file_type["code"]
                                if published_file_type
                                else None
                            ),
                            "path": {"local_path": local_path} if local_path else None,
                            "version_number": version.version_number,
                            "created_at": created_at,
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

    def get_latest_published_file(
        self,
        item: FileItem,
        bg_task_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
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

        def _fetch_latest():
            item_data = item.sg_data or {}
            asset_id = item_data.get("sg_flow_asset_id")
            if not asset_id:
                return {}

            project = self.parent.context.project
            blob_index = item_data.get("sg_flow_blob_index", 0)

            try:
                asset = objects.FlowAsset(asset_id)
                latest_revision = asset.get_latest_revision()
                if not latest_revision:
                    self.logger.warning(
                        f"No latest revision found for asset {asset_id}"
                    )
                    return {}
            except exceptions.FlowError as e:
                self.logger.warning(
                    f"Failed to get latest revision for asset {asset_id}: {e}"
                )
                return {}

            published_file_type = self._get_published_file_type(asset)

            local_path = None
            try:
                local_path = latest_revision.get_storage_component_path(
                    component_purpose=globals.SOURCE_PURPOSE
                )
            except exceptions.FlowError:
                pass

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
                "published_file_type": published_file_type,
                "published_file_type.PublishedFileType.code": (
                    published_file_type["code"] if published_file_type else None
                ),
                "path": {"local_path": local_path} if local_path else None,
                "version_number": asset.version_number,
                "created_at": created_at,
                "sg_flow_revision_id": latest_revision.id,
                "sg_flow_asset_id": asset_id,
                "sg_flow_version_id": asset.version_id,
            }

        if bg_task_manager:
            return bg_task_manager.add_task(_fetch_latest)
        return _fetch_latest()

    def update_to_latest(self, items: list[FileItem]) -> list[FileItem]:
        """Update the given items in the scene.

        Args:
            items: list of file item object to update
        Returns:
            list of file item that were updated
        """
        items_to_update = []
        for file_item in items:
            res = self.parent.flowam.update_dependency(
                file_item.sg_data["sg_flow_revision_id"],
                node_handle=file_item.node_name,
            )
            if res:
                items_to_update.append(file_item)

        return items_to_update

    def update_to_revision(
        self,
        item: Optional[dict[str, Any]],
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
        # Validate item_data contains the required revision ID
        if not item_data or not item_data.get("sg_flow_revision_id"):
            self.logger.warning(
                "Cannot update to revision: item_data is missing or lacks sg_flow_revision_id"
            )
            return False

        # Validate item structure
        flowam_data = item.get("sg_data") if item else None
        if not flowam_data or not flowam_data.get("sg_flow_revision_id"):
            self.logger.warning(
                "Cannot update to revision: item sg_data is missing or lacks sg_flow_revision_id"
            )
            return False

        do_update = self.parent.flowam.update_dependency(
            revision_id=flowam_data["sg_flow_revision_id"],
            new_revision_id=item_data["sg_flow_revision_id"],
            node_handle=item.get("node_name"),
        )

        return do_update
