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

from . import constants
from .framework_qtwidgets import ShotgunListWidget

shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model"
)
ShotgunModel = shotgun_model.ShotgunModel


class FileHistoryModel(ShotgunModel):
    """
    """

    def __init__(self, parent, bg_task_manager):
        """
        Class constructor

        :param parent:
        :param bg_task_manager:
        """

        ShotgunModel.__init__(
            self,
            parent,
            bg_task_manager=bg_task_manager
        )

    def load_data(self, sg_data):
        """
        """

        fields = [] + constants.PUBLISHED_FILES_FIELDS

        # query the configuration hook to add some additional shotgun fields
        app = sgtk.platform.current_bundle()
        file_history_config = app.execute_hook_method("hook_ui_configurations", "file_history_details")

        fields += ShotgunListWidget.resolve_sg_fields(file_history_config.get("top_left"))
        fields += ShotgunListWidget.resolve_sg_fields(file_history_config.get("top_right"))
        fields += ShotgunListWidget.resolve_sg_fields(file_history_config.get("body"))
        if file_history_config["thumbnail"] and "image" not in fields:
            fields.append("image")

        # remove all duplicates
        fields = list(set(fields))

        filters = [
            ["project", "is", sg_data["project"]],
            ["name", "is", sg_data["name"]],
            ["task", "is", sg_data["task"]],
            ["entity", "is", sg_data["entity"]],
            ["published_file_type", "is", sg_data["published_file_type"]],
        ]

        ShotgunModel._load_data(
            self,
            entity_type="PublishedFile",
            filters=filters,
            hierarchy=["version_number"],
            fields=fields,
        )

        self._refresh_data()
