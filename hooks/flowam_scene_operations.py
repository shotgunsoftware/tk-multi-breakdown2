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

                if asset_id not in processed_assets:
                    try:
                        asset = objects.FlowAsset(asset_id)
                        versions = list(asset.iterate_versions())
                        processed_assets[asset_id] = (asset, versions)
                    except exceptions.FlowError:
                        self.logger.error(
                            f"Failed to query versions for asset {asset_id}"
                        )
                        continue

                asset, versions = processed_assets[asset_id]
                published_file_type = self.parent.flowam.get_published_file_type(asset)

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
                        self.logger.error(
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
                                published_file_type["code"]
                                if published_file_type
                                else None
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
                raise exceptions.FlowError("No asset ID found for item")

            project = self.parent.context.project

            try:
                asset = objects.FlowAsset(asset_id)
                latest_revision = asset.get_latest_revision()
                if not latest_revision:
                    self.logger.warning(
                        f"No latest revision found for asset {asset_id}"
                    )
                    raise exceptions.FlowError(
                        f"No latest revision found for asset {asset_id}"
                    )
            except exceptions.FlowError as e:
                self.logger.error(
                    f"Failed to get latest revision for asset {asset_id}: {e}"
                )
                raise

            published_file_type = self.parent.flowam.get_published_file_type(asset)

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
