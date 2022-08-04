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
from sgtk import TankError
from sgtk.platform.qt import QtGui, QtCore

from tank_vendor import six

from .ui import resources_rc  # Required for accessing icons
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
        # STATUS_UP_TO_DATE: QtGui.QIcon(
        #     FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_UP_TO_DATE)
        # ),
        # STATUS_OUT_OF_SYNC: QtGui.QIcon(
        #     FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_OUT_OF_SYNC)
        # ),
        # STATUS_LOCKED: QtGui.QIcon(FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_LOCKED)),
        STATUS_UP_TO_DATE: FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_UP_TO_DATE),
        STATUS_OUT_OF_SYNC: FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_OUT_OF_SYNC),
        STATUS_LOCKED: FILE_ITEM_STATUS_ICON_PATHS.get(STATUS_LOCKED),
    }

    FILE_ITEM_STATUS_NAMES = {
        STATUS_UP_TO_DATE: "Up to Date",
        STATUS_OUT_OF_SYNC: "Out of Date",
        STATUS_LOCKED: "Locked",
    }

    class BaseModelItem(QtGui.QStandardItem):
        """
        The base model item class for the FileModel.
        """

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
        """Model item that represents a group in the model."""

        def __init__(self, group_id, display_value):
            """Constructor"""

            super(FileModel.GroupModelItem, self).__init__(display_value)

            self._group_id = group_id
            self._display_value = display_value

        def __eq__(self, other):
            """
            Override the base method.

            Group model items are equal if ids are unique. Note that this means the
            group ids should be unique.

            :param other: The FileModelItem to compare with.
            :type other: FileModel.FileModelItem

            :return: True if this model item is equal to the other item.
            :rtype: bool
            """

            if not isinstance(other, FileModel.GroupModelItem):
                return False

            return self.group_id == other.group_id

        @property
        def group_id(self):
            """Get the unique id for this group model item."""
            return self._group_id

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
        """Model item that represents a single FileItem in the model."""

        def __init__(self, file_item=None, timeout_interval=None, polling=False):
            """
            Constructor. Initialize the file item data to None, the file item data will be
            set in the setData method using the FileModel.FILE_ITEM_ROLE.

            :param file_item: The file item data to initialize the model item with.
            :type file_item: FileItem
            :param timeout_interval: The timeout interval in milliseconds for polling the file
                item status. If None or not greater than 0, no polling will be performed.
            :type timeout_interval: int
            :param polling: True will start the item's timer to poll for automatic status
                updates, else False will not poll to get status updates.
            :type polling: bool
            """

            # Call the base QStandardItem constructor
            super(FileModel.FileModelItem, self).__init__()

            # Initialize our file mode item data. Deepcopy the data to ensure our file item
            # data cannot be modified outside of the model, or only using the setData method.
            self._file_item = copy.deepcopy(file_item)

            # Create a timer that checks the latest published file every X seconds
            self._file_status_check_timer = QtCore.QTimer()
            self._file_status_check_timer.timeout.connect(
                lambda s=self: self._check_file_status()
            )
            self._timeout_interval = timeout_interval

            if polling:
                self.start_timer()

        def __eq__(self, other):
            """
            Override the base method.

            File model items are equal if their FileItem objects are equal. Note that this
            means each file model item should refer to a unique file item.

            :param other: The FileModelItem to compare with.
            :type other: FileModel.FileModelItem

            :return: True if this model item is equal to the other item.
            :rtype: bool
            """

            if not isinstance(other, FileModel.FileModelItem):
                return False

            this_file_item = self.data(FileModel.FILE_ITEM_ROLE)
            other_file_item = other.data(FileModel.FILE_ITEM_ROLE)
            return this_file_item == other_file_item

        def __del__(self):
            """
            Override the base method.

            Ensure that the file status check timer has been stopped on deletion.
            """

            self.stop_timer()

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
                # Return a copy of the file item object so that the model data cannot be
                # modified without going through the setData method, so that the model
                # can emits the necessary signals
                return copy.deepcopy(self._file_item)

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

                    if self._file_item.highest_version_number:
                        if (
                            self._file_item.sg_data["version_number"]
                            < self._file_item.highest_version_number
                        ):
                            return FileModel.STATUS_OUT_OF_SYNC
                        return FileModel.STATUS_UP_TO_DATE

                    # Item may still loading, too early to determine the status.
                    return FileModel.STATUS_NONE

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
                    check_thumbnail_only = False

                    if (
                        self._file_item
                        and self._file_item.highest_version_number is not None
                    ):
                        check_thumbnail_only = True

                    return self.model().is_loading(
                        self, thumbnail_only=check_thumbnail_only
                    )

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
                if self.model():
                    cur_group_value = self._file_item.sg_data.get(self.model().group_by)
                    updated_group_value = value.sg_data.get(self.model().group_by)
                    if cur_group_value != updated_group_value:
                        # Update the grouping of this file item now that its data has changed
                        # and it no longer belongs in its current group
                        self.model().update_file_group(
                            self.row(), self._file_item, value
                        )

                # Deepcopy the value to ensure our file item data cannot be modified outside
                # of the model, or only using the setData method
                self._file_item = copy.deepcopy(value)

                # Emit the standard model data changed
                self.emitDataChanged()

            elif role == FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE:
                if (
                    not self._file_item.latest_published_file
                    or not value
                    or self._file_item.latest_published_file.get("id")
                    != value.get("id")
                ):
                    self._file_item.latest_published_file = value
                    self.emitDataChanged()

            else:
                super(FileModel.FileModelItem, self).setData(value, role)

        def start_timer(self):
            """Start the file status check timer to poll for status updates."""

            # Only start the timer if a valid interval was given
            if self._timeout_interval and self._timeout_interval > 0:
                self._file_status_check_timer.start(self._timeout_interval)

        def stop_timer(self):
            """Stop the file status check timer to prevent any more calls to update the status."""

            self._file_status_check_timer.stop()

        def _check_file_status(self):
            """
            Slot triggered on the file status check timeout.

            Make an async request to get the latest published file for this file model item,
            such that the file item status can be updated to show if the item is out of date
            or not.
            """

            if not self.model():
                return

            self.model().request_latest_published_file(self)

    def __init__(self, parent, bg_task_manager, group_by=None, polling=False):
        """
        Class constructor

        :param parent: The parent QObject for this instance
        :type parent: QtGui.QWidget
        :param bg_task_manager: A BackgroundTaskManager instance that will be used for all background/threaded
            work that needs undertaking
        :type bg_task_manager: BackgroundTaskManager
        :param group_by: The data defining how to create the file item grouping.
        :type group_by: dict
        :param polling: True will poll each file model item for status updates, else False
            will not poll to get automatic status updates.
        :type polling: bool
        """

        QtGui.QStandardItemModel.__init__(self, parent)

        self._app = sgtk.platform.current_bundle()

        self._polling = polling
        # Get the app setting for the timeout interval length for polling file item statuses.
        self._timeout_interval = self._app.get_setting("file_status_check_interval")

        self._group_items = {}
        self._pending_files_request = None
        self._pending_thumbnail_requests = {}
        self._pending_version_requests = {}

        if group_by and isinstance(group_by, six.string_types):
            self._group_by = group_by
        else:
            self._group_by = "project"

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

        icon = cls.FILE_ITEM_STATUS_ICONS.get(status, QtGui.QIcon())

        # The first time the status icon is accessed, it will provide the path to the icon.
        # Create it and set it in the status icon mapping to avoid creating it on each
        # access.
        if not isinstance(icon, QtGui.QIcon):
            icon = QtGui.QIcon(icon)
            cls.FILE_ITEM_STATUS_ICONS[status] = icon

        return icon

    @property
    def group_by(self):
        """Get or set the property defining the grouping of the file items."""
        return self._group_by

    @group_by.setter
    def group_by(self, value):
        self._group_by = value

    #########################################################################################################
    # Override base FileModel class methods

    def destroy(self):
        """
        Override the base method.

        Called to clean-up and shutdown any internal objects when the model has been finished
        with. Failure to call this may result in instability or unexpected behaviour!
        """

        self.clear()

        if self._sg_data_retriever:
            self._sg_data_retriever.stop()
            self._sg_data_retriever.deleteLater()
            self._sg_data_retriever = None

        if self._bg_task_manager:
            self._bg_task_manager.task_completed.disconnect(
                self._on_background_task_completed
            )
            self._bg_task_manager.task_failed.disconnect(
                self._on_background_task_failed
            )

    def clear(self):
        """
        Override the base method.

        Clean up the data that this model owns and call the base class method to finish the
        clean up.
        """

        self._group_items = {}

        # Save the current polling state to restore after stopping polling on file items that
        # will be removed on clearing the model.
        restore_polling = self._polling
        # Stop all the FileModelItem timers that are checking each item's status.
        self.poll_for_status_updates(False)
        # Restore the polling state.
        self._polling = restore_polling

        super(FileModel, self).clear()

    #########################################################################################################
    # Public FileModel methods

    def reload(self):
        """
        Reload the data in the model.

        Fire off a background task that scans the current scene to get all the file items. Once
        the background task is complete, the file items will be processed to rebuild the model.

        This method will emit the signal that the model is resetting but does not call the
        signal to end the model reset. The slot called when the scan scene task is complete
        is responsible for emitting the end model reset signal.
        """

        # First reset the pendings files request to ignore the current task that's in progress
        # once it completes, and so that we only populate the model once with the most recent
        # task result
        self._pending_files_request = None

        self.beginResetModel()

        try:
            restore_state = self.blockSignals(True)
            self.clear()

            # Fire off a background task to scan the current scene to get the file item data
            task_id = self._bg_task_manager.add_task(
                self._manager.scan_scene,
                task_kwargs={"extra_fields": self._published_file_fields},
            )
            self._pending_files_request = task_id

        finally:
            self.blockSignals(restore_state)

    def refresh(self):
        """
        Refresh the model internal data layout.

        This method should be called if the model grouping (parent/child relationships) have
        been changed.
        """

        # Do not refresh if the model is in the middle of a reload already
        if self._pending_files_request:
            return

        self.beginResetModel()

        try:
            restore_state = self.blockSignals(True)

            # Get the list of file item data to rebuild the model with. This is useful when
            # the model grouping has changed and the file model items will potentially all
            # need to be relocated to a differnt grouping
            file_items = []
            for row in range(self.rowCount()):
                group_item = self.item(row)
                for child_row in range(group_item.rowCount()):
                    child = group_item.child(child_row)
                    file_item = child.data(self.FILE_ITEM_ROLE)
                    file_items.append(file_item)

            # Clear the current model and rebuild it with our file item data
            self.clear()
            self._process_files(file_items)

        finally:
            self.blockSignals(restore_state)
            self.endResetModel()

            # Since the files are processed immediately (and not in background task), emit the
            # signal that they have bene fully processed - this must be emitted after signals
            # become unblocked
            self.files_processed.emit()

    def poll_for_status_updates(self, on):
        """
        Turn on polling for file item status udpates.

        This will start the timer on each item in the model to individually poll for updates
        on the file item. This will automatically refresh the item in the view when updates
        are found.

        :param on: True will turn on polling, else False will turn off polling.
        :type on: bool
        """

        self._polling = on

        for row in range(self.rowCount()):
            group_item = self.item(row)
            for child_row in range(group_item.rowCount()):
                child = group_item.child(child_row)
                if self._polling:
                    child.start_timer()
                else:
                    child.stop_timer()

    def get_group_by_fields(self):
        """
        Get the fields that are available to group the file items by.

        :return: The list of group by fields.
        :rtype: list<str>
        """

        return list(
            set(self._manager.get_published_file_fields() + self._published_file_fields)
        )

    def item_from_file(self, file_item):
        """
        Return the model item that matches the given file.

        :param file_item: The file item to find the model item by.
        :type file_item: FileItem

        :return: The model item.
        :rtype: QtGui.QStandardItem
        """

        for group_row in range(self.rowCount()):
            group_item = self.item(group_row)

            for child_row in range(group_item.rowCount()):
                child = group_item.child(child_row)
                if child.data(FileModel.FILE_ITEM_ROLE) == file_item:
                    return child

        return None

    def is_loading(self, model_item=None, thumbnail_only=False):
        """
        Return True if the whole model, or the individual model item is in a loading state.

        The model is loading when the current scene is being scanned and the model is
        waiting for the file items to be returned to create the items in the model. The
        model loading state will be returned if the `model_item` is not specified.

        A model item is loading when its data is being fetched. The model item loading state
        will be returned for the `model_item` specified.

        :param model_item: The item in the model, or None to check the loading status of the
            model as a whole.
        :type model_item: :class:`sgtk.platform.qt.QtGui.QStandardItem` | None
        :param thumbnail_only: Check specifically if the thumbnail is loading.
        :type thumbnail_only: bool

        :return: True if model or model item is loading the item, else False.
        :rtype: bool
        """

        if model_item is None:
            return self._pending_files_request is not None

        # Else return the loading state of the model item specified.
        if thumbnail_only:
            return model_item in list(self._pending_thumbnail_requests.values())

        items_loading = list(self._pending_version_requests.values()) + list(
            self._pending_thumbnail_requests.values()
        )
        return model_item in items_loading

    def request_latest_published_file(self, file_model_item, file_item=None):
        """
        Make an async request to retrieve the latest published file for the given file model
        item.

        :param file_model_item: The model item to get the latest published file for.
        :type file_model_item: FileModelItem
        :param file_item: The file item data for the model item (optional). If not provided
            the data will be fetched from the model item.
        :type file_item: FileItem
        """

        if not file_model_item:
            return

        file_item = file_item or file_model_item.data(FileModel.FILE_ITEM_ROLE)
        if not file_item:
            return

        # Retrieve the latest version in order to know if the file is up-to-date or not
        task_id = self._bg_task_manager.add_task(
            self._manager.get_latest_published_file,
            task_kwargs={"item": file_item},
        )

        self._pending_version_requests[task_id] = file_model_item

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

    def update_file_group(
        self, file_model_item_row, cur_file_item_data, new_file_item_data
    ):
        """
        Update the grouping that the file item belongs to.

        :param file_model_item_row: The row (relative to its grouping) that the file item is in.
        :type file_model_item_row: int
        :param cur_file_item_data: The current data of the file item.
        :type cur_file_item_data: FileItem
        :param new_file_item_data: The data that the file model item will be updated with.
        :type new_file_item_data: FileItem
        """

        # Get the current grouping and remove the file model item from it, and remove the
        # grouping totally if it becomes empty after removing the item.
        cur_group_id, _ = self._get_file_group_info(cur_file_item_data)
        cur_group_item = self._group_items.get(cur_group_id)
        file_model_item = cur_group_item.takeRow(file_model_item_row)
        if not cur_group_item.hasChildren():
            self.removeRow(cur_group_item.row())
            del self._group_items[cur_group_id]

        # Get the new grouping, create the group item if it does not yet exist, and add the
        # file model item to it
        new_group_id, new_group_display = self._get_file_group_info(new_file_item_data)
        new_group_item = self._group_items.get(new_group_id)
        if new_group_item is None:
            new_group_item = FileModel.GroupModelItem(new_group_id, new_group_display)
            self._group_items[new_group_id] = new_group_item
            self.appendRow(new_group_item)

        new_group_item.appendRows(file_model_item)

    #########################################################################################################
    # Protected FileModel methods

    def _process_files(self, file_items):
        """
        Process the file items given to add to the model.

        A model item will be created for each of the given file items, and will be added to
        the model.

        Note that this method does not clear the current model items, it just appends them to
        the current model.

        :param file_items: The file item data to create items in the model.
        :type file_items: list<FileItem>
        """

        for file_item in file_items:
            # if the item doesn't have any associated shotgun data, it means that the file is not a
            # Published File so skip it
            if not file_item.sg_data:
                continue

            group_by_id, group_by_display = self._get_file_group_info(file_item)
            if self._group_items.get(group_by_id) is None:
                group_item = FileModel.GroupModelItem(group_by_id, group_by_display)
                self.appendRow(group_item)
                self._group_items[group_by_id] = group_item
            else:
                group_item = self._group_items[group_by_id]

            file_model_item = FileModel.FileModelItem(
                file_item=file_item,
                timeout_interval=self._timeout_interval,
                polling=self._polling,
            )
            file_model_item.setIcon(QtGui.QIcon())
            # Send an async requests to retrieve additional data for the file item, and so
            # the model can continue on
            self.request_latest_published_file(file_model_item, file_item)
            self.request_thumbnail(file_model_item, file_item)

            # Add the file item to the grouping
            group_item.appendRow(file_model_item)

    def _get_file_group_info(self, file_item):
        """
        Get the group by information for the given file item.

        :param file_item: The file item to get the group by info from.
        :type file_item: FileItem

        :return: The group by information for the file item.
        :rtype: tuple<str, str>
        """

        if self.group_by not in file_item.sg_data:
            return ("", "")

        # Get the group by field data
        data = file_item.sg_data[self.group_by]

        # Attempt to construct the id for the grouping
        try:
            group_by_id = "{type}.{id}".format(
                type=data.get("type", "NoType"), id=data["id"]
            )
        except:
            # Fall back to just using the data itself as the id
            group_by_id = str(data)

        # Construct the group display value
        if not data:
            group_by_display = "None"

        elif isinstance(data, dict):
            group_by_display = data["name"]

        elif isinstance(data, (list, tuple)):
            item_strings = []
            for item in data:
                if isinstance(item, dict):
                    item_strings.append(item.get("name", str(item)))
                else:
                    item_strings.append(str(item))
            group_by_display = ", ".join(item_strings)

        else:
            group_by_display = str(data)

        return (group_by_id, group_by_display)

    def _on_data_retriever_work_completed(self, uid, request_type, data):
        """
        Slot triggered when the data-retriever has finished doing some work. The data retriever is currently
        just used to download thumbnails for published files so this will be triggered when a new thumbnail
        has been downloaded and loaded from disk.

        :param uid:             The unique id representing a task being executed by the data retriever
        :param request_type:    A string representing the type of request that has been completed
        :param data:            The result from completing the work
        """

        if uid in self._pending_thumbnail_requests:
            # Get the model item pertaining to this thumbnail request
            file_model_item = self._pending_thumbnail_requests[uid]

            # Remove the request id from the pending list
            del self._pending_thumbnail_requests[uid]

            # Update the model item's thumbnail from the data returned by the request
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

        if uid == self._pending_files_request:
            self._pending_files_request = None
            self._process_files(result)
            self.endResetModel()

        elif uid in self._pending_version_requests:
            file_model_item = self._pending_version_requests[uid]
            del self._pending_version_requests[uid]

            file_model_item.setData(
                result, FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE
            )

    def _on_background_task_failed(self, uid, group_id, msg, stack_trace):
        """
        Slot triggered when the background manager fails to do some task.

        :param uid:         Unique id associated with the task
        :param group_id:    The group the task is associated with
        :param msg:         Short error message
        :param stack_trace: Full error traceback
        """

        if uid == self._pending_files_request:
            self._pending_files_request = None
            self.endResetModel()

        elif uid in self._pending_version_requests:
            del self._pending_version_requests[uid]

        self._app.logger.error(
            "File Model: Failed to find the latest published file for id %s: %s"
            % (uid, msg)
        )

    def _on_background_task_group_finished(self, group_id):
        """
        Slot triggered when the background manager finishes all tasks within a group.

        Implement this functionality for this method if needed.

        :param group_id: The group that has finished
        :type group_id: This will be whatever the group_id was set as on 'add_task'.
        """
