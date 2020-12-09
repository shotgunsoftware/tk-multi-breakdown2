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

from .utils import get_ui_published_file_fields
from . import constants


shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model"
)
ShotgunModel = shotgun_model.ShotgunModel


class FileHistoryModel(ShotgunModel):
    """
    This model represents the version history for a file.
    """

    def __init__(self, parent, bg_task_manager):
        """
        Class constructor

        :param parent:          The parent QObject for this instance
        :param bg_task_manager: A BackgroundTaskManager instance that will be used for all background/threaded
                                work that needs undertaking
        """

        ShotgunModel.__init__(
            self,
            parent,
            bg_task_manager=bg_task_manager
        )

    def load_data(self, sg_data):
        """
        Load the details for the shotgun publish entity described by sg_data.

        :param sg_data: Dictionary describing a publish in shotgun, including all the common
                        publish fields.
        """

        app = sgtk.platform.current_bundle()

        fields = constants.PUBLISHED_FILES_FIELDS + app.get_setting("published_file_fields", [])
        fields += get_ui_published_file_fields(app)
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
