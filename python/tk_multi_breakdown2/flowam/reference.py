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

import sgtk
from tank_vendor.flow_integration_sdk import (
    dependency,
    exceptions,
    globals,
    objects,
    schema,
    utils,
)


def get_dependencies() -> list[dependency.DependencyData]:
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


def update_dependency(
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
    new_rev.fetch()

    file_seq_comp = new_rev.find_component(
        type_id=schema.get_schema_id(globals.FILE_SEQ_TYPE)
    )
    if file_seq_comp:
        # Return a file path with embedded frame padding
        new_path = utils.cleanpath(
            new_rev.get_storage_dir(), file_seq_comp.properties["fileFormat"]
        )
    else:
        new_path = new_rev.get_storage_source_path()

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
