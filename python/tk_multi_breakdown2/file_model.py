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
from sgtk import TankError
from sgtk.platform.qt import QtGui, QtCore

from .utils import get_ui_published_file_fields

shotgun_data = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_data"
)
ShotgunDataRetriever = shotgun_data.ShotgunDataRetriever

shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model"
)

delegates = sgtk.platform.import_framework("tk-framework-qtwidgets", "delegates")
ViewItemRolesMixin = delegates.ViewItemRolesMixin


class FileModel(QtGui.QStandardItemModel, ViewItemRolesMixin):
    """
    The FileModel maintains a model of all the files found when parsing the current scene. Details of each file are
    contained in a FileItem instance and presented as a single model item.

    File items are grouped into groups defined by the app configuration.
    """

    VIEW_ITEM_CONFIG_HOOK_PATH = "view_item_configuration_hook"

    # Additional data roles defined for the model
    _BASE_ROLE = QtCore.Qt.UserRole + 32
    (
        STATUS_ROLE,  # The item status
        FILE_ITEM_ROLE,  # The file item object
        FILE_ITEM_NODE_NAME_ROLE,  # Convenience role for the file item node_name field
        FILE_ITEM_NODE_TYPE_ROLE,  # Convenience role for the file item node_type field
        FILE_ITEM_PATH_ROLE,  # Convenience role for the file item path field
        FILE_ITEM_SG_DATA_ROLE,  # Convenience role for the file item sg_data field
        FILE_ITEM_EXTRA_DATA_ROLE,  # Convenience role for the file item extra_data field
        FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE,  # Convenience role for the file item latest_published_file field
        FILE_ITEM_CREATED_AT_ROLE,  # Convenience method to extract the created at datetime from the file item shotgun data
        NEXT_AVAILABLE_ROLE,  # Keep track of the next available custome role. Insert new roles above.
    ) = range(_BASE_ROLE, _BASE_ROLE + 10)

    # File item status enum
    (
        STATUS_OK,
        STATUS_OUT_OF_SYNC,
        STATUS_LOCKED,
    ) = range(3)

    FILE_ITEM_STATUS_ICONS = {
        STATUS_OK: QtGui.QIcon(":/tk-multi-breakdown2/main-uptodate.png"),
        STATUS_OUT_OF_SYNC: QtGui.QIcon(":/tk-multi-breakdown2/main-outofdate.png"),
        STATUS_LOCKED: QtGui.QIcon(":/tk-multi-breakdown2/main-override.png"),
    }

    # signal emitted once all the files have been processed
    files_processed = QtCore.Signal()
    # signal emitted specifically when the data changed for the FILE_ITEM_ROLE
    file_item_data_changed = QtCore.Signal(QtGui.QStandardItem)

    class BaseModelItem(QtGui.QStandardItem):
        """
        The base model item class for the FileModel.
        """

        def __init__(self, *args, **kwargs):
            """
            Constructor

            :param args: The positional arguments to pass to the :class:`sgtk.platform.qt.QtGui.QStandardItem` constructor.
            :pram kwargs: The keyword arguments to the pass to the :class:`sgtk.platform.qt.QtGui.QStandardItem` constructor.
            """

            QtGui.QStandardItem.__init__(self, *args, **kwargs)

        def data(self, role):
            """
            Override the :class:`sgtk.platform.qt.QtGui.QStandardItem` method.

            Return the data for the item for the specified role.

            :param role: The :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole` role.
            :return: The data for the specified roel.
            """

            result = None

            # Check if the model has a method defined for retrieving the item data for this role.
            data_method = self.model().get_method_for_role(role)
            if data_method:
                try:
                    result = data_method(self, self.data(FileModel.FILE_ITEM_ROLE))
                except TypeError as error:
                    raise TankError(
                        "Failed to execute the method defined to retrieve item data for role `{role}`.\nError: {msg}".format(
                            role=role, msg=error
                        )
                    )

            else:
                # Default to the base implementation
                result = super(FileModel.BaseModelItem, self).data(role)

            return shotgun_model.util.sanitize_qt(result)

    class GroupModelItem(BaseModelItem):
        """
        Model item that represents a group in the model.
        """

        def __init__(self, text):
            """
            :param text: String used for the label/display role for this item
            """
            QtGui.QStandardItem.__init__(self, text)

        def data(self, role):
            """
            Override the :class:`sgtk.platform.qt.QtGui.QStandardItem` method.

            Return the data for the item for the specified role.

            :param role: The :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole` role.
            :return: The data for the specified roel.
            """

            if role in (
                FileModel.FILE_ITEM_ROLE,
                FileModel.FILE_ITEM_NODE_NAME_ROLE,
                FileModel.FILE_ITEM_NODE_TYPE_ROLE,
                FileModel.FILE_ITEM_PATH_ROLE,
                FileModel.FILE_ITEM_SG_DATA_ROLE,
                FileModel.FILE_ITEM_EXTRA_DATA_ROLE,
                FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE,
            ):
                # File item specific roles, just return None.
                return None

            if role == FileModel.VIEW_ITEM_HEIGHT_ROLE:
                # Group item height always adjusts to content size
                return -1

            if role == FileModel.VIEW_ITEM_LOADING_ROLE:
                # The group header will indicate a loading state if any of the children are loading.
                if self.hasChildren():
                    for row in range(self.rowCount()):
                        if self.child(row).data(role):
                            return True
                return False

            if role == FileModel.STATUS_ROLE:
                if self.hasChildren():
                    locked = True
                    for row in range(self.rowCount()):
                        child_status = self.child(row).data(role)
                        if child_status == FileModel.STATUS_OUT_OF_SYNC:
                            # The group status is out of sync if any children are out of sync.
                            return FileModel.STATUS_OUT_OF_SYNC

                        if child_status != FileModel.STATUS_LOCKED:
                            # The group status is locked only if all children are locked.
                            locked = False

                return FileModel.STATUS_LOCKED if locked else FileModel.STATUS_OK

            return super(FileModel.GroupModelItem, self).data(role)

    class FileModelItem(BaseModelItem):
        """
        Model item that represents a single FileItem in the model.
        """

        def __init__(self, text, file_item=None):
            """
            :param text: String used for the label/display role for this item
            :param file_item: The file item data for this item
            """

            QtGui.QStandardItem.__init__(self, text)

            self._file_item = file_item

        def data(self, role):
            """
            Override the :class:`sgtk.platform.qt.QtGui.QStandardItem` method.

            Return the data for the item for the specified role.

            :param role: The :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole` role.
            :return: The data for the specified role.
            """

            if role == QtCore.Qt.BackgroundRole:
                return QtGui.QApplication.palette().midlight()

            if role == FileModel.FILE_ITEM_ROLE:
                return self._file_item

            if self._file_item:
                if role == FileModel.FILE_ITEM_NODE_NAME_ROLE:
                    return self._file_item.node_name

                if role == FileModel.FILE_ITEM_NODE_TYPE_ROLE:
                    return self._file_item.node_type

                if role == FileModel.FILE_ITEM_PATH_ROLE:
                    return self._file_item.path

                if role == FileModel.FILE_ITEM_SG_DATA_ROLE:
                    return self._file_item.sg_data

                if role == FileModel.FILE_ITEM_EXTRA_DATA_ROLE:
                    return self._file_item.extra_data

                if role == FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE:
                    return self._file_item.latest_published_file

                if role == FileModel.FILE_ITEM_CREATED_AT_ROLE:
                    return self._file_item.sg_data.get("created_at")

                if role == FileModel.STATUS_ROLE:
                    if self._file_item.locked:
                        return FileModel.STATUS_LOCKED

                    if (
                        not self._file_item.highest_version_number
                        or self._file_item.sg_data["version_number"]
                        < self._file_item.highest_version_number
                    ):
                        return FileModel.STATUS_OUT_OF_SYNC

                    return FileModel.STATUS_OK

                if role == FileModel.VIEW_ITEM_LOADING_ROLE:
                    return (
                        self._file_item and not self._file_item.highest_version_number
                    )

            return super(FileModel.FileModelItem, self).data(role)

        def setData(self, value, role):
            """
            Override teh :class:`sgtk.platform.qt.QtGui.QStandardItem` method.

            Set the data for the item and role.

            :param value: The data value to set for the item's role.
            :param role: The :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole` role.
            """

            if role == FileModel.FILE_ITEM_ROLE:
                # Send a request to retrieve and update the file item's thumbnail
                self.model().request_thumbnail(self, value)
                self._file_item = value

                # Emit a specific signal for the FILE_ITEM_ROLE
                self.model().file_item_data_changed.emit(self)

                # Emit the standard model data changed
                self.emitDataChanged()

            else:
                super(FileModel.FileModelItem, self).setData(value, role)

    def __init__(self, parent, bg_task_manager):
        """
        Class constructor

        :param parent:          The parent QObject for this instance
        :param bg_task_manager: A BackgroundTaskManager instance that will be used for all background/threaded
                                work that needs undertaking
        """

        QtGui.QStandardItemModel.__init__(self, parent)

        self._app = sgtk.platform.current_bundle()

        self._group_items = {}
        self._pending_thumbnail_requests = {}
        self._pending_version_requests = {}

        self._manager = self._app.create_breakdown_manager()

        self._bg_task_manager = bg_task_manager
        self._bg_task_manager.task_completed.connect(self._on_background_task_completed)
        self._bg_task_manager.task_failed.connect(self._on_background_task_failed)

        # sg data retriever is used to download thumbnails in the background
        self._sg_data_retriever = ShotgunDataRetriever(bg_task_manager=bg_task_manager)
        self._sg_data_retriever.work_completed.connect(
            self._on_data_retriever_work_completed
        )
        self._sg_data_retriever.work_failure.connect(
            self._on_data_retriever_work_failed
        )

        # Add additional roles defined by the ViewItemRolesMixin class.
        self.NEXT_AVAILABLE_ROLE = self.initialize_roles(self.NEXT_AVAILABLE_ROLE)

        # Get the hook instance for configuring the display for model view items.
        view_item_config_hook_path = self._app.get_setting(
            self.VIEW_ITEM_CONFIG_HOOK_PATH
        )
        view_item_config_hook = self._app.create_hook_instance(
            view_item_config_hook_path
        )

        # Create a mapping of model item data roles to the method that will be called to retrieve
        # the data for the item. The methods defined for each role must accept two parameters:
        # (1) QStandardItem (2) dict
        self.role_methods = {
            self.VIEW_ITEM_THUMBNAIL_ROLE: view_item_config_hook.get_item_thumbnail,
            self.VIEW_ITEM_HEADER_ROLE: view_item_config_hook.get_item_title,
            self.VIEW_ITEM_SUBTITLE_ROLE: view_item_config_hook.get_item_subtitle,
            self.VIEW_ITEM_TEXT_ROLE: view_item_config_hook.get_item_details,
            self.VIEW_ITEM_SHORT_TEXT_ROLE: view_item_config_hook.get_item_short_text,
            self.VIEW_ITEM_ICON_ROLE: view_item_config_hook.get_item_icons,
            self.VIEW_ITEM_WIDTH_ROLE: view_item_config_hook.get_item_width,
            self.VIEW_ITEM_SEPARATOR_ROLE: view_item_config_hook.get_item_separator,
        }

    @classmethod
    def get_status_icon(cls, status):
        """
        Return the icon for the status.
        """

        return cls.FILE_ITEM_STATUS_ICONS.get(status, QtGui.QIcon())

    def destroy(self):
        """
        Called to clean-up and shutdown any internal objects when the model has been finished
        with. Failure to call this may result in instability or unexpected behaviour!
        """

        # clear the model
        self.clear()

        # stop the data retriever
        if self._sg_data_retriever:
            self._sg_data_retriever.stop()
            self._sg_data_retriever.deleteLater()
            self._sg_data_retriever = None

        # shut down the task manager
        if self._bg_task_manager:
            self._bg_task_manager.task_completed.disconnect(
                self._on_background_task_completed
            )
            self._bg_task_manager.task_failed.disconnect(
                self._on_background_task_failed
            )

    def process_files(self):
        """
        Scan the current scene to get all the items we could perform actions on and for each item, build a model item
        and a data structure to represent them.
        """

        # scan the current scene
        extra_fields = get_ui_published_file_fields(self._app)
        file_items = self._manager.scan_scene(extra_fields=extra_fields)

        for file_item in file_items:

            # if the item doesn't have any associated shotgun data, it means that the file is not a Published File so
            # skip it
            if not file_item.sg_data:
                continue

            # group scene object by project
            # todo: use an app setting to be able to group scene object by another Shotgun field
            project = file_item.sg_data["project"]
            if project["id"] not in self._group_items.keys():
                group_item = FileModel.GroupModelItem(project["name"])
                self.invisibleRootItem().appendRow(group_item)
                self._group_items[project["id"]] = group_item
            else:
                group_item = self._group_items[project["id"]]

            file_model_item = FileModel.FileModelItem("", file_item)
            group_item.appendRow(file_model_item)

            # for each item, we need to determine the latest version in order to know if the file is up-to-date or not
            task_id = self._bg_task_manager.add_task(
                self._manager.get_latest_published_file,
                task_kwargs={"item": file_item},
            )
            self._pending_version_requests[task_id] = file_model_item

            # finally, download the file thumbnail
            self.request_thumbnail(file_model_item, file_item)

        self.files_processed.emit()

    def _on_data_retriever_work_completed(self, uid, request_type, data):
        """
        Slot triggered when the data-retriever has finished doing some work. The data retriever is currently
        just used to download thumbnails for published files so this will be triggered when a new thumbnail
        has been downloaded and loaded from disk.

        :param uid:             The unique id representing a task being executed by the data retriever
        :param request_type:    A string representing the type of request that has been completed
        :param data:            The result from completing the work
        """
        if uid not in self._pending_thumbnail_requests:
            return

        file_model_item = self._pending_thumbnail_requests[uid]
        del self._pending_thumbnail_requests[uid]

        thumb_path = data.get("thumb_path")
        if thumb_path:
            file_model_item.setIcon(QtGui.QPixmap(thumb_path))

    def _on_data_retriever_work_failed(self, uid, error_msg):
        """
        Slot triggered when the data retriever fails to do some work!

        :param uid:         The unique id representing the task that the data retriever failed on
        :param error_msg:   The error message for the failed task
        """
        if uid in self._pending_thumbnail_requests:
            del self._pending_thumbnail_requests[uid]
        self._app.logger.debug(
            "File Model: Failed to find thumbnail for id %s: %s" % (uid, error_msg)
        )

    def _on_background_task_completed(self, uid, group_id, result):
        """
        Slot triggered when the background manager has finished doing some task. The only task we're asking the manager
        to do is to find the latest published file associated to the current item.

        :param uid:      Unique id associated with the task
        :param group_id: The group the task is associated with
        :param result:   The data returned by the task
        """
        if uid not in self._pending_version_requests:
            return
        file_model_item = self._pending_version_requests[uid]
        del self._pending_version_requests[uid]

        file_model_item.emitDataChanged()

    def _on_background_task_failed(self, uid, group_id, msg, stack_trace):
        """
        Slot triggered when the background manager fails to do some task.

        :param uid:         Unique id associated with the task
        :param group_id:    The group the task is associated with
        :param msg:         Short error message
        :param stack_trace: Full error traceback
        """
        if uid in self._pending_version_requests:
            del self._pending_version_requests[uid]
        self._app.logger.error(
            "File Model: Failed to find the latest published file for id %s: %s"
            % (uid, msg)
        )

    def request_thumbnail(self, model_item, file_item):
        """
        Make an async request for the file item thumbnail, to set for the model item.

        :param model_item: The model item object
        :type model_item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param file_item: The file item data object
        :type file_item: FileItem

        :return: None
        """

        if not file_item.sg_data.get("image"):
            return

        request_id = self._sg_data_retriever.request_thumbnail(
            file_item.sg_data["image"],
            file_item.sg_data["type"],
            file_item.sg_data["id"],
            "image",
        )

        # Store the model item with the request id, so that the model item can be retrieved
        # to update when the async request completes.
        self._pending_thumbnail_requests[request_id] = model_item
