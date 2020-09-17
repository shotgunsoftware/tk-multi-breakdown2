# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

from .item import FileItem
from ..framework_qtwidgets import ShotgunListWidget


class BreakdownManager(object):
    """
    This class is used for managing and executing file updates.
    """

    SG_FIELDS = ["id", "project", "entity", "name", "task", "published_file_type"]

    def __init__(self):
        """
        Initialize the manager.
        """

        self._bundle = sgtk.platform.current_bundle()

    def scan_scene(self):
        """
        """

        fields = list(BreakdownManager.SG_FIELDS)
        file_items = []

        # todo: see if we need to execute this action in the main thread using engine.execute_in_main_thread()
        scene_objects = self._bundle.execute_hook_method("hook_scene_operations", "scan_scene")

        file_item_config = self._bundle.execute_hook_method("hook_ui_configurations", "file_item_details")

        fields += ShotgunListWidget.resolve_sg_fields(file_item_config.get("top_left"))
        fields += ShotgunListWidget.resolve_sg_fields(file_item_config.get("top_right"))
        fields += ShotgunListWidget.resolve_sg_fields(file_item_config.get("body"))
        if file_item_config["thumbnail"]:
            fields.append("image")

        # only keep the files corresponding to Shotgun Published Files. As some files can come from other projects, we
        # cannot rely on templates so we have to query SG instead
        file_paths = [o["path"] for o in scene_objects]
        published_files = sgtk.util.find_publish(
            self._bundle.sgtk,
            file_paths,
            fields=fields,
            only_current_project=False
        )

        for obj in scene_objects:
            file_item = FileItem(obj["node_name"], obj["node_type"], obj["path"])
            file_item.extra_data = obj.get("extra_data")
            if obj["path"] in published_files.keys():
                file_item.sg_data = published_files[obj["path"]]
            file_items.append(file_item)

        return file_items

    def get_file_history(self, item):
        """
        :param item:
        :return:
        """

        file_history = self._bundle.execute_hook("hook_get_file_history", item=item)
        item.file_history = file_history

        return item.file_history

    def update_to_latest_version(self, item):
        """
        :param item:
        :return:
        """

        latest_published_file = item.file_history[0]
        item.path = latest_published_file["path"]["local_path"]

        # self._bundle.execute_hook_method("hook_scene_operations", "update", item=item.to_dict())
