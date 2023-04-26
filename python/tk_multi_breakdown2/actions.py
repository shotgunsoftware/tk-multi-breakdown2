# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import copy

import sgtk
from sgtk.platform.qt import QtCore, QtGui

from .decorators import wait_cursor


class ActionManager(object):
    """Class to gather all the possible actions we can run inside the Scene Breakdown 2."""

    @staticmethod
    def add_update_to_latest_action(file_items, model, parent=None):
        """
        Build a QAction for the "Update to latest" menu item.

        :param file_items: List of items to update to their latest versions
        :type file_items: List<FileItem>
        :parma model: The Qt model that the may need to be updated after the action executes.
        :type model: QtGui.QStandardItemModel
        :param parent: Parent widget
        :type parent: QtGui.QWidget

        :return: The QAction representing the menu item.
        :rtype: QtGui.QAction
        """

        action = UpdateToLatestVersionAction("Update to latest", file_items, model)

        q_action = QtGui.QAction(action.label, parent)
        q_action.triggered[()].connect(lambda checked=False: action.execute())

        return q_action

    @staticmethod
    def add_update_to_specific_version_action(file_item, model, sg_data, parent=None):
        """
        Build a QAction for the "Update to vxx" menu item.

        :param file_item: The file item to update to a specific version.
        :type file_item: FileItem
        :parma model: The Qt model that the may need to be updated after the action executes.
        :type model: QtGui.QStandardItemModel
        :param sg_data: Dictionary of ShotGrid data representing the published file we want to update the item to
        :type sg_data: dict
        :param parent: Parent widget
        :type parent: QtGui.QWidget

        :return: The QAction representing the menu item.
        :rtype: QtGui.QAction
        """

        if not sg_data.get("version_number"):
            return

        action = UpdateToSpecificVersionAction(
            "Override current reference with Version {version}".format(
                version=sg_data["version_number"]
            ),
            file_item,
            sg_data,
            model,
        )

        q_action = QtGui.QAction(action.label, parent)
        q_action.triggered[()].connect(lambda checked=False: action.execute())

        return q_action

    @staticmethod
    def execute_update_to_latest_action(file_items, model):
        """
        Execute the "Update to latest" action.

        :param file_items: List of file items to update to their latest versions.
        :type file_items: list<FileItem>
        :param model: The Qt model that may need to be updated after the action executes.
        :type model: QtGui.QStandardItemModel

        :return: The value returned by action method executed.
        """

        action = UpdateToLatestVersionAction("Update to latest", file_items, model)
        return action.execute()


class Action(object):
    """Base class for Actions."""

    def __init__(self, label, file_items, model):
        """
        Constructor.

        :param label: Name of the action.
        :type label: str
        :param file_items: File items to perform the actions on.
        :type file_items: list<FileItem>
        :param model: The Qt model that may need to be updated after the action executes.
        :type model: QtGui.QStandardItemModel
        """

        self._app = sgtk.platform.current_bundle()
        self._manager = self._app.create_breakdown_manager()
        self.label = label

        self._file_items = file_items
        self._model = model

    def execute(self):
        """
        Called when the user executes a given action. The default implementation raises a NotImplementedError.

        :raises NotImplementedError: Thrown if a derived class doesn't implement this method and the client invokes it.
        """

        raise NotImplementedError(
            "Implementation of execute() method missing for action '%s'" % self.label
        )

    def _get_index_for_item(self, file_item):
        """
        Find the model item corresponding to the given file item data.

        :param file_item: The file item data.
        :type file_item: FileItem

        :return: The model index for the file item.
        :rtype: QtCore.QModelIndex
        """

        # Get the model item for the FileItem
        file_model_item = self._model.item_from_file(file_item)
        if not file_model_item:
            return

        # Get the index and parent index from the model item, to use to emit the model data
        # changed signal
        if file_model_item.parent_item:
            parent_index = self._model.index(file_model_item.parent_item.row(), 0)
        else:
            parent_index = QtCore.QModelIndex()

        return self._model.index(file_model_item.row(), 0, parent_index)


class UpdateToLatestVersionAction(Action):
    """Update items to their latest version."""

    def __init__(self, label, file_items, model):
        """
        Class constructor

        :param label: Name of the action.
        :type label: str
        :param items: The list of file items to perform the action on.
        :type items: list<FileItem>
        :param model: The Qt model that may need to be updated after the action executes.
        :type model: QtGui.QStandardItemModel
        """

        super(UpdateToLatestVersionAction, self).__init__(label, file_items, model)

    @wait_cursor
    def execute(self):
        """Update a list of items to their latest version."""

        if not self._file_items:
            return

        for file_item in self._file_items:
            # Call the manager to update the file item object to the latest version.
            do_update = self._manager.update_to_latest_version(file_item)

            if do_update:
                # The file item object that the model holds was updated by the manager.
                # Emit a signal that the data has changed.
                index = self._get_index_for_item(file_item)
                self._model.dataChanged.emit(
                    index,
                    index,
                    [self._model.FILE_ITEM_ROLE, self._model.FILE_ITEM_SG_DATA_ROLE],
                )


class UpdateToSpecificVersionAction(Action):
    """Update an item to a specific version."""

    def __init__(self, label, file_item, sg_data, model):
        """
        Class constructor

        :param label: Name of the action.
        :type label: str
        :param item: The file item to perform the action on.
        :type item: FileItem
        :param sg_data: Dictionary of ShotGrid data representing the Published File we want to update the item to
        :type sg_data: dict
        :param model: The Qt model that may need to be updated after the action executes.
        :type model: QtGui.QStandardItemModel
        """

        super(UpdateToSpecificVersionAction, self).__init__(label, [file_item], model)
        self._sg_data = sg_data

    @wait_cursor
    def execute(self):
        """Update an item to a specific version."""

        file_item = self._file_items[0]

        # Call the manager to update the file item to the specific version.
        do_update = self._manager.update_to_specific_version(file_item, self._sg_data)

        if do_update:
            # The file item object that the model holds was updated by the manager.
            # Emit a signal that the data has changed.
            index = self._get_index_for_item(file_item)
            self._model.dataChanged.emit(
                index,
                index,
                [self._model.FILE_ITEM_ROLE, self._model.FILE_ITEM_SG_DATA_ROLE],
            )
