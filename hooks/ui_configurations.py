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


class UIConfiguration(HookBaseClass):
    """
    """

    def file_item_details(self):
        """
        """
        return {
            "top_left": "<b>{name}</b>",
            "top_right": "",
            "body": "<b style='color:#18A7E3;'>Node</b> {<NODE_NAME>}<br/>"
                    "<b style='color:#18A7E3;'>Version</b> {version_number}<br/>"
                    "<b style='color:#18A7E3;'>Entity</b> {entity::showtype}<br/>"
                    "<b style='color:#18A7E3;'>Type</b> {published_file_type.PublishedFileType.code}",
            "thumbnail": True
        }
