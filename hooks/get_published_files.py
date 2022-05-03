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

HookBaseClass = sgtk.get_hook_baseclass()


class GetPublishedFiles(HookBaseClass):
    """"""

    def get_latest_published_file(self, item, **kwargs):
        """
        Query ShotGrid to get the latest published file for the given item.

        :param item: :class`FileItem` object we want to get the latest published file for
        :return: The published file as a ShotGrid dictionary
        """

        filters = [
            ["entity", "is", item.sg_data["entity"]],
            ["name", "is", item.sg_data["name"]],
            ["task", "is", item.sg_data["task"]],
            ["published_file_type", "is", item.sg_data["published_file_type"]],
        ]
        fields = list(item.sg_data.keys()) + ["version_number", "path"]
        order = [{"field_name": "version_number", "direction": "desc"}]

        # todo: check if this work with url published files
        # todo: need to check for path comparison?
        published_file = self.sgtk.shotgun.find_one(
            "PublishedFile",
            filters=filters,
            fields=fields,
            order=order,
        )

        return published_file
