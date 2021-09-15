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
    The FileModel maintains a model of all the files found when parsing the current scene. Details
    of each file are contained in a FileItem instance and presented as a single model item.

    File items are grouped into groups defined by the app configuration.
    """

    UI_CONFIG_ADV_HOOK_PATH = "hook_ui_config_advanced"

    # Additional data roles defined for the model
    _BASE_ROLE = QtCore.Qt.UserRole + 32
    (
        STATUS_ROLE,  # The item status
        STATUS_FILTER_DATA_ROLE,  # The item status data used for filtering
        REFERENCE_LOADED,  # True if the reference associated with the item is loaded by the DCC
        FILE_ITEM_ROLE,  # The file item object
        FILE_ITEM_NODE_NAME_ROLE,  # Convenience role for the file item node_name field
        FILE_ITEM_NODE_TYPE_ROLE,  # Convenience role for the file item node_type field
        FILE_ITEM_PATH_ROLE,  # Convenience role for the file item path field
        FILE_ITEM_SG_DATA_ROLE,  # Convenience role for the file item sg_data field
        FILE_ITEM_EXTRA_DATA_ROLE,  # Convenience role for the file item extra_data field
        FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE,  # Convenience role for the file item latest_published_file field
        FILE_ITEM_CREATED_AT_ROLE,  # Convenience method to extract the created at datetime from the file item shotgun data
        FILE_ITEM_TAGS_ROLE,  # Convenience method to extract the file item tags from the shotgun data
        NEXT_AVAILABLE_ROLE,  # Keep track of the next available custome role. Insert new roles above.
    ) = range(_BASE_ROLE, _BASE_ROLE + 13)

    # File item status enum
    (
        STATUS_NONE,  # Status is none when the necessary data has not all loaded yet to determine the status
        STATUS_UP_TO_DATE,
        STATUS_OUT_OF_SYNC,
        STATUS_LOCKED,
    ) = range(4)

    FILE_ITEM_STATUS_ICON_PATHS = {
        STATUS_UP_TO_DATE: ":/tk-multi-breakdown2/icons/main-uptodate.png",
        STATUS_OUT_OF_SYNC: ":/tk-multi-breakdown2/icons/main-outofdate.png",
        STATUS_LOCKED: ":/tk-multi-breakdown2/icons/main-override.png",
    }
    FILE_ITEM_STATUS_ICONS = {
        STATUS_UP_TO_DATE: QtGui.QIcon(
            FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_UP_TO_DATE)
        ),
        STATUS_OUT_OF_SYNC: QtGui.QIcon(
            FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_OUT_OF_SYNC)
        ),
        STATUS_LOCKED: QtGui.QIcon(FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_LOCKED)),
    }

    FILE_ITEM_STATUS_NAMES = {
        STATUS_UP_TO_DATE: "Up to Date",
        STATUS_OUT_OF_SYNC: "Out of Date",
        STATUS_LOCKED: "Locked",
    }

    # The group identifier for background tasks created when processing files.
    TASK_GROUP_PROCESSED_FILES = "process_files"

    # signal emitted once all the files have been processed
    files_processed = QtCore.Signal()
    # signal emitted specifically when the data changed for the FILE_ITEM_ROLE
    file_item_data_changed = QtCore.Signal(QtGui.QStandardItem)

    class BaseModelItem(QtGui.QStandardItem):
        """
        The base model item class for the FileModel.
        """

        def __eq__(self, other):
            """
            Overload the equality comparison operator to allow comparing BaseModelItem objects.
            Model items are compared by their model index; e.g. two indexes are equivalent if
            they have the same index.

            :param other: The other model item to compare this one to.
            :type other: BaseModelItem
            """

            return self.index() == other.index()

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
                    result = data_method(self.index())
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

        def data(self, role):
            """
            Override the :class:`sgtk.platform.qt.QtGui.QStandardItem` method.

            Return the data for the item for the specified role.

            :param role: The :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole` role.
            :return: The data for the specified roel.
            """

            if role in (
                FileModel.STATUS_FILTER_DATA_ROLE,
                FileModel.REFERENCE_LOADED,
                FileModel.FILE_ITEM_ROLE,
                FileModel.FILE_ITEM_NODE_NAME_ROLE,
                FileModel.FILE_ITEM_NODE_TYPE_ROLE,
                FileModel.FILE_ITEM_PATH_ROLE,
                FileModel.FILE_ITEM_SG_DATA_ROLE,
                FileModel.FILE_ITEM_EXTRA_DATA_ROLE,
                FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE,
                FileModel.FILE_ITEM_CREATED_AT_ROLE,
                FileModel.FILE_ITEM_TAGS_ROLE,
            ):
                # File item specific roles, just return None.
                return None

            if role == FileModel.VIEW_ITEM_HEIGHT_ROLE:
                # Group item height always adjusts to content size
                return -1

            if role == FileModel.VIEW_ITEM_LOADING_ROLE:
                # Do not show a loading icon for the group item (loading status will be
                # shown in the subtitle)
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

                return (
                    FileModel.STATUS_LOCKED if locked else FileModel.STATUS_UP_TO_DATE
                )

            return super(FileModel.GroupModelItem, self).data(role)

    class FileModelItem(BaseModelItem):
        """
        Model item that represents a single FileItem in the model.
        """

        def __init__(self, *args, **kwargs):
            """
            Constructor. Initialize the file item data to None, the file item data will be
            set in the setData method using the FileModel.FILE_ITEM_ROLE.
            """

            super(FileModel.FileModelItem, self).__init__(*args, **kwargs)
            self._file_item = None

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

                if role == FileModel.FILE_ITEM_EXTRA_DATA_ROLE:
                    return self._file_item.extra_data

                if role == FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE:
                    return self._file_item.latest_published_file

                if role == FileModel.FILE_ITEM_SG_DATA_ROLE:
                    return self._file_item.sg_data

                if role == FileModel.FILE_ITEM_CREATED_AT_ROLE:
                    return self._file_item.sg_data.get("created_at")

                if role == FileModel.FILE_ITEM_TAGS_ROLE:
                    return self._file_item.sg_data.get(
                        "tags"
                    ) or self._file_item.sg_data.get("tag_list")

                if role == FileModel.STATUS_ROLE:
                    # NOTE if we ever need to know if the file is up to date or not, while
                    # it is also locked, we would need to create a separate role to determine
                    # if the file is locked or not, in addition to this status role that would
                    # then not check if the file is locked.
                    if self._file_item.locked:
                        return FileModel.STATUS_LOCKED

                    if self.data(FileModel.VIEW_ITEM_LOADING_ROLE):
                        # Item is still loading, too early to determine the status.
                        return FileModel.STATUS_NONE

                    if (
                        not self._file_item.highest_version_number
                        or self._file_item.sg_data["version_number"]
                        < self._file_item.highest_version_number
                    ):
                        return FileModel.STATUS_OUT_OF_SYNC

                    return FileModel.STATUS_UP_TO_DATE

                if role == FileModel.STATUS_FILTER_DATA_ROLE:
                    status_value = self.data(FileModel.STATUS_ROLE)
                    status_name = FileModel.FILE_ITEM_STATUS_NAMES.get(status_value)
                    return {
                        "status": {
                            "name": status_name,
                            "value": status_value,
                            "icon": FileModel.FILE_ITEM_STATUS_ICON_PATHS.get(
                                status_value
                            ),
                        }
                    }

                if role == FileModel.VIEW_ITEM_LOADING_ROLE:
                    # Check the model is loading this item or not.
                    return self.model().is_loading(self)

                if role == FileModel.REFERENCE_LOADED:
                    # TODO call a hook method per DCC to check if the reference associated with this
                    # file item has been loaded into the scene (if the DCC supports loading and
                    # unloading references, e.g. Maya).
                    #
                    # For now, we'll just say everything is loaded unless told otherwise.
                    return True

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
        self._bg_task_manager.task_group_finished.connect(
            self._on_background_task_group_finished
        )

        # sg data retriever is used to download thumbnails in the background
        self._sg_data_retriever = ShotgunDataRetriever(bg_task_manager=bg_task_manager)
        self._sg_data_retriever.work_completed.connect(
            self._on_data_retriever_work_completed
        )
        self._sg_data_retriever.work_failure.connect(
            self._on_data_retriever_work_failed
        )

        # Get all the required fields when querying for published files. Call the hook to get
        # them once and store them, since they are not expected to not change within this session.
        self._published_file_fields = get_ui_published_file_fields(self._app)

        # Add additional roles defined by the ViewItemRolesMixin class.
        self.NEXT_AVAILABLE_ROLE = self.initialize_roles(self.NEXT_AVAILABLE_ROLE)

        # Get the hook instance for configuring the display for model view items.
        ui_config_adv_hook_path = self._app.get_setting(self.UI_CONFIG_ADV_HOOK_PATH)
        ui_config_adv_hook = self._app.create_hook_instance(ui_config_adv_hook_path)

        # Create a mapping of model item data roles to the method that will be called to retrieve
        # the data for the item. The methods defined for each role must accept two parameters:
        # (1) QStandardItem (2) dict
        self.role_methods = {
            self.VIEW_ITEM_THUMBNAIL_ROLE: ui_config_adv_hook.get_item_thumbnail,
            self.VIEW_ITEM_HEADER_ROLE: ui_config_adv_hook.get_item_title,
            self.VIEW_ITEM_SUBTITLE_ROLE: ui_config_adv_hook.get_item_subtitle,
            self.VIEW_ITEM_TEXT_ROLE: ui_config_adv_hook.get_item_details,
            self.VIEW_ITEM_SHORT_TEXT_ROLE: ui_config_adv_hook.get_item_short_text,
            self.VIEW_ITEM_ICON_ROLE: ui_config_adv_hook.get_item_icons,
            self.VIEW_ITEM_SEPARATOR_ROLE: ui_config_adv_hook.get_item_separator,
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
        Scan the current scene to get all the items we could perform actions on and for each item,
        build a model item and a data structure to represent them.
        """

        self.beginResetModel()
        self.clear()

        # scan the current scene
        file_items = self._manager.scan_scene(extra_fields=self._published_file_fields)

        for file_item in file_items:
            # if the item doesn't have any associated shotgun data, it means that the file is not a
            # Published File so skip it
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

            file_model_item = FileModel.FileModelItem()
            # Add the model item to the group before setting and data on the item, to ensure it has
            # a model associated with it.
            group_item.appendRow(file_model_item)
            # Set a placeholder icon, until the thumbnail is loaded.
            file_model_item.setIcon(QtGui.QIcon())
            # Set the file item data, an async request will be made to get the thumbnail.
            file_model_item.setData(file_item, FileModel.FILE_ITEM_ROLE)

            # for each item, we need to determine the latest version in order to know if the file
            # is up-to-date or not
            task_id = self._bg_task_manager.add_task(
                self._manager.get_latest_published_file,
                task_kwargs={"item": file_item},
                group=self.TASK_GROUP_PROCESSED_FILES,
            )
            self._pending_version_requests[task_id] = file_model_item

        self.endResetModel()

    def is_loading(self, model_item):
        """
        Return True if the item in the model is in a loading state. An item is considered to be
        loading if the model item is found in the `_pending_version_requests` or
        `_pending_thumbnail_requests`.

        :param model_item: The item in the model.
        :type model_item: :class:`sgtk.platform.qt.QtGui.QStandardItem`

        :return: True if model is loading the item, else False.
        :rtype: bool
        """

        # items_loading = list(self._pending_version_requests.values()) + list(
        # self._pending_thumbnail_requests.values()
        # )
        items_loading = (
            self._pending_version_requests.values()
            + self._pending_thumbnail_requests.values()
        )
        return model_item in items_loading

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

    def _on_background_task_group_finished(self, group_id):
        """
        Slot triggered when the background manager finishes all tasks within a group.

        :param group_id: The group that has finished
        :type group_id: This will be whatever the group_id was set as on 'add_task'.
        """

        if group_id == self.TASK_GROUP_PROCESSED_FILES:
            # Emit signal now that all files have been processed.
            self.files_processed.emit()
