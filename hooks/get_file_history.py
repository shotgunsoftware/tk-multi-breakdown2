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

HookBaseClass = sgtk.get_hook_baseclass()


class GetVersionNumber(HookBaseClass):
    """
    """

    def execute(self, item, **kwargs):
        """
        :param item:
        :param kwargs:
        :return:
        """

        max_history = self.parent.get_setting("version_history")

        filters = [
            ["entity", "is", item.sg_data["entity"]],
            ["name", "is", item.sg_data["name"]],
            ["task", "is", item.sg_data["task"]],
            ["published_file_type", "is", item.sg_data["published_file_type"]],
        ]
        fields = item.sg_data.keys() + ["version_number", "path"]
        order = [{"field_name": "version_number", "direction": "desc"}]

        # todo: check if this work with url published files
        # todo: need to check for path comparison?
        published_files = self.sgtk.shotgun.find(
            "PublishedFile",
            filters=filters,
            fields=fields,
            order=order,
            limit=max_history
        )

        return published_files
