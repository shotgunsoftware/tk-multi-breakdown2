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
from sgtk.platform.qt import QtGui


class ActionManager(object):
    """
    Class to gather all the possible actions we can run inside the Scene Breakdown 2.
    """

    @staticmethod
    def add_update_to_latest_action(items, parent=None):
        """
        Build a QAction for the "Update to latest" menu item.

        :param items: List of items to update to their latest versions
        :param parent: Parent widget
        :returns: The QAction representing the menu item
        """

        action = UpdateToLatestVersionAction("Update to latest", items)

        q_action = QtGui.QAction(action.label, parent)
        q_action.triggered[()].connect(lambda checked=False: action.execute())

        return q_action

    @staticmethod
    def add_update_to_specific_version_action(item, sg_data, parent=None):
        """
        Build a QAction for the "Update to vxx" menu item.

        :param item: Item to update to a specific version
        :param sg_data: Dictionary of Shotgun data representing the published file we want to update the item to
        :param parent: Parent widget
        :returns: The QAction representing the menu item
        """
        if not sg_data.get("version_number"):
            return

        action = UpdateToSpecificVersionAction(
            "Override current reference with Version {version}".format(
                version=sg_data["version_number"]
            ),
            item,
            sg_data,
        )

        q_action = QtGui.QAction(action.label, parent)
        q_action.triggered[()].connect(lambda checked=False: action.execute())

        return q_action

    @staticmethod
    def execute_update_to_latest_action(items):
        """
        Execute the "Update to latest" action.

        :param items: List of items to update to their latest versions
        :type items: list<FileItem>
        :return: The value returned by action method executed.
        """

        action = UpdateToLatestVersionAction("Update to latest", items)
        return action.execute()


class Action(object):
    """
    Base class for Actions.
    """

    def __init__(self, label, items):
        """
        Constructor.

        :param label: Name of the action.
        :param items: Items to perform the actions on
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
            "Implementation of execute() method missing for action '%s'" % self.label
        )


class UpdateToLatestVersionAction(Action):
    """
    Update items to their latest version
    """

    def __init__(self, label, items):
        """
        Class constructor

        :param label: Name of the action.
        :param items: Items to perform the action on
        """
        Action.__init__(self, label, items)

    def execute(self):
        """
        Update a list of items to their latest version.
        """
        for file_item, file_model_item in self._items:
            self._manager.update_to_latest_version(file_item)
            file_model_item.emitDataChanged()


class UpdateToSpecificVersionAction(Action):
    """
    Update an item to a specific version.
    """

    def __init__(self, label, item, sg_data):
        """
        Class constructor

        :param label: Name of the action.
        :param item: Item to perform the action on
        :param sg_data: Dictionary of Shotgun data representing the Published File we want to update the item to
        """
        Action.__init__(self, label, item)
        self._sg_data = sg_data

    def execute(self):
        """
        Update an item to a specific version.
        """
        file_item = self._items[0]
        file_model_item = self._items[1]
        self._manager.update_to_specific_version(file_item, self._sg_data)
        file_model_item.emitDataChanged()
