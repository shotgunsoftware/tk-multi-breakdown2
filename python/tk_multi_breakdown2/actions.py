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

from .file_model import FileModel


class Action(object):
    """
    """

    def __init__(self, label, items):
        """
        Constructor.

        :param label: Name of the action.
        """
        self._app = sgtk.platform.current_bundle()
        self._manager = self._app.create_breakdown_manager()
        self.label = label
        self._items = items

    def execute(self):
        """
        Called when the user executes a given action. The default implementation raises a NotImplementedError.

        :raises NotImplementedError: Thrown if a derived class doesn't implement this method and the client invokes it.
        """
        raise NotImplementedError(
            "Implementation of _execute() method missing for action '%s'" % self.label
        )


class UpdateVersionAction(Action):
    """
    """

    def __init__(self, label, items):
        """
        """
        Action.__init__(self, label, items)

    def execute(self):
        """
        :return:
        """

        for i in self._items:

            file_item_model = i[0]
            file_item = i[1]

            self._manager.update_to_latest_version(file_item)

            # update the UI
            file_item.sg_data = file_item.file_history[0]
