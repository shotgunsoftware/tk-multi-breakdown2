# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import sgtk

from .item import FileItem
from .. import constants


class BreakdownManager(object):
    """This class is used for managing and executing file updates."""

    def __init__(self, bundle):
        """Initialize the manager."""

        self._bundle = bundle

    @sgtk.LogManager.log_timing
    def scan_scene(self, extra_fields=None):
        """
        Scan the current scene to return a list of object we could perform actions on.

        :param extra_fields: A list of ShotGrid fields to append to the ShotGrid query
                             for published files.
        :return: A list of :class`FileItem` objects containing the file data.
        """

        file_items = []

        # todo: see if we need to execute this action in the main thread using engine.execute_in_main_thread()
        scene_objects = self._bundle.execute_hook_method(
            "hook_scene_operations", "scan_scene"
        )

        # only keep the files corresponding to Shotgun Published Files. As some files can come from other projects, we
        # cannot rely on templates so we have to query SG instead
        file_paths = [o["path"] for o in scene_objects]

        fields = self.get_published_file_fields()
        if extra_fields is not None:
            fields += extra_fields

        published_files = sgtk.util.find_publish(
            self._bundle.sgtk, file_paths, fields=fields, only_current_project=False
        )

        for obj in scene_objects:
            if obj["path"] in published_files.keys():
                file_item = FileItem(obj["node_name"], obj["node_type"], obj["path"])
                file_item.extra_data = obj.get("extra_data")
                file_item.sg_data = published_files[obj["path"]]
                file_items.append(file_item)

        return file_items

    def get_published_file_fields(self):
        """
        Get the fields to pass to the query to retrieve the published files when scanning the
        scene.

        :return: The published file fields.
        :rtype: list<str>
        """

        return constants.PUBLISHED_FILES_FIELDS + self._bundle.get_setting(
            "published_file_fields", []
        )

    def get_latest_published_file(self, item):
        """
        Get the latest available published file according to the current item context.

        :param item: :class`FileItem` object we want to get the latest published file
        :return:  The latest published file as a ShotGrid entity dictionary
        """

        if not item.sg_data:
            return {}

        latest_published_file = self._bundle.execute_hook_method(
            "hook_get_published_files", "get_latest_published_file", item=item
        )
        item.latest_published_file = latest_published_file

        return latest_published_file

    def get_published_file_history(self, item, extra_fields=None):
        """
        Get the published history for the selected item. It will gather all the published files with the same context
        than the current item (project, name, task, ...)

        :param extra_fields: A list of ShotGrid fields to append to the ShotGrid query fields.
        :param item: :class`FileItem` object we want to get the published file history
        :param extra_fields: A list of ShotGrid fields to append to the ShotGrid query
                             for published files.

        :returns: A list of ShotGrid published file dictionary
        """

        if not item.sg_data:
            return []

        fields = constants.PUBLISHED_FILES_FIELDS + self._bundle.get_setting(
            "published_file_fields", []
        )
        if extra_fields is not None:
            fields += extra_fields

        filters = [
            ["project", "is", item.sg_data["project"]],
            ["name", "is", item.sg_data["name"]],
            ["task", "is", item.sg_data["task"]],
            ["entity", "is", item.sg_data["entity"]],
            ["published_file_type", "is", item.sg_data["published_file_type"]],
        ]

        pfs = self._bundle.shotgun.find(
            "PublishedFile",
            filters=filters,
            fields=fields,
            order=[{"direction": "desc", "field_name": "version_number"}],
        )

        if pfs:
            item.latest_published_file = pfs[0]
            return pfs

        # Return empty list indicating no publish file history was found.
        return []

    def update_to_latest_version(self, item):
        """
        Update the item to its latest version.

        :param item: Item to update
        """

        if not item.latest_published_file:
            return

        self.update_to_specific_version(item, item.latest_published_file)

    def update_to_specific_version(self, item, sg_data):
        """
        Update the item to a specific version.

        :param item: Item to update
        :param sg_data: Dictionary of ShotGrid data representing the published file we want to update the item to
        """

        if not sg_data or not sg_data.get("path", {}).get("local_path", None):
            return

        # store the current path into the extra_data in case we need to access it later in the hook
        if not item.extra_data:
            item.extra_data = {"old_path": item.path}
        else:
            item.extra_data["old_path"] = item.path

        item.path = sg_data["path"]["local_path"]
        self._bundle.execute_hook_method(
            "hook_scene_operations", "update", item=item.to_dict()
        )
        item.sg_data = sg_data
