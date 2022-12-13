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
from .decorators import wait_cursor

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
        """The base model item class for the FileModel."""

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

        def __init__(self, file_item=None):
            """
            Constructor. Initialize the file item data to None, the file item data will be
            set in the setData method using the FileModel.FILE_ITEM_ROLE.

            :param file_item: The file item data to initialize the model item with.
            :type file_item: FileItem
            """

            # Call the base QStandardItem constructor
            super(FileModel.FileModelItem, self).__init__()

            # Initialize our file mode item data.
            self._file_item = file_item

            # Create the item icon from the thumbnail data
            if self._file_item:
                self.__thumbnail_icon = QtGui.QIcon(self._file_item.thumbnail_path)

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

        def data(self, role):
            """
            Override the :class:`sgtk.platform.qt.QtGui.QStandardItem` method.

            Return the data for the item for the specified role.

            :param role: The :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole` role.
            :return: The data for the specified role.
            """

            if role == QtCore.Qt.BackgroundRole:
                return QtGui.QApplication.palette().midlight()

            if role == QtCore.Qt.DecorationRole:
                if not self.__thumbnail_icon:
                    self.__thumbnail_icon = QtGui.QIcon(self._file_item.thumbnail_path)
                return self.__thumbnail_icon

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

                self._file_item = value

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

        def set_thumbnail(self, thumbnail_path):
            """Custom method to set the thumbnail data to avoid emitting data changed signals."""

            self.__thumbnail = QtGui.QIcon(thumbnail_path)

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

        # Flag indicating if the model is in the middle of a reload
        self.__is_reloading = False

        # Flag indicating if the model will poll for published file updates async.
        self._polling = polling

        # Get the app setting for the timeout interval length for polling file item statuses.
        self._timeout_interval = self._app.get_setting("file_status_check_interval")
        # Create a timer that checks the latest published file every X seconds
        self._file_status_check_timer = QtCore.QTimer()
        self._file_status_check_timer.timeout.connect(
            lambda s=self: self.check_published_file_status()
        )

        # The list of file item data that currently populates the model.
        self.__file_items = []
        # The list of current group items in the model to easily change groupings.
        self._group_items = {}

        # Keep track of pending background tasks.
        self.__pending_published_file_data_request = None
        self.__pending_version_requests = {}
        self.__pending_thumbnail_requests = {}

        if group_by and isinstance(group_by, six.string_types):
            self._group_by = group_by
        else:
            self._group_by = "project"

        self._manager = self._app.create_breakdown_manager()

        self._bg_task_manager = bg_task_manager
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

    @property
    def polling(self):
        """Get or set the property indicating if the model is polling for published file updates."""
        return self._polling
    
    @polling.setter
    def polling(self, value):
        self._polling = value
        self.start_timer() if self._polling else self.stop_timer()

    #########################################################################################################
    # Override base FileModel class methods

    def destroy(self):
        """
        Override the base method.

        Called to clean-up and shutdown any internal objects when the model has been finished
        with. Failure to call this may result in instability or unexpected behaviour!
        """

        self.clear()
        self.stop_timer()

        if self._sg_data_retriever:
            self._sg_data_retriever.stop()
            self._sg_data_retriever.work_completed.disconnect(
                self._on_data_retriever_work_completed
            )
            self._sg_data_retriever.work_failure.disconnect(
                self._on_data_retriever_work_failed
            )
            self._sg_data_retriever.deleteLater()
            self._sg_data_retriever = None

        if self._bg_task_manager:
            self._bg_task_manager.task_group_finished.disconnect(
                self._on_background_task_group_finished
            )

    def clear(self):
        """
        Override the base method.

        Clean up the data that this model owns and call the base class method to finish the
        clean up.
        """

        self.__file_items = []
        self._group_items = {}

        # Stop any background tasks currently running
        self._bg_task_manager.stop_task(self.__pending_published_file_data_request)

        for version_request_id in self.__pending_version_requests:
            self._bg_task_manager.stop_task(version_request_id)

        for thumbnail_request_id in self.__pending_thumbnail_requests:
            self._bg_task_manager.stop_task(thumbnail_request_id)

        # Clear request ids
        self.__pending_published_file_data_request = None
        self.__pending_version_requests.clear()
        self.__pending_thumbnail_requests.clear()

        super(FileModel, self).clear()

    #########################################################################################################
    # Public FileModel methods

    @wait_cursor
    def reload(self):
        """
        Reload the data in the model.

        Fire off a background task that scans the current scene to get all the file items. Once
        the background task is complete, the file items will be processed to rebuild the model.

        This method will emit the signal that the model is resetting but does not call the
        signal to end the model reset. The slot called when the scan scene task is complete
        is responsible for emitting the end model reset signal.
        """

        self.beginResetModel()
        self.__is_reloading = True

        try:
            restore_state = self.blockSignals(True)
            self.clear()
            # Pause polling for updates while the model reloads. This will start again once
            # all async tasks are complete to reload the model.
            self.stop_timer()

            # Run the scan scene method in the main thread (not a background task) since this
            # may cause issues for certain DCCs
            self.__file_items = self._manager.scan_scene(extra_fields=self._published_file_fields)

            # Run the api call to get all published file data necessary to determine the
            # latest published file per file item. Get all info in a single request and
            # execute the request async.
            self.__pending_published_file_data_request = self._get_published_files_for_items(self.__file_items, self._sg_data_retriever)
        except:
            # Reset on failure to reload
            self.__pending_published_file_data_request = None
        finally:
            # Restore block siganls state, but do not emit endResetModel signal yet, this will
            # be done when the background tasks have completed to load the model data.
            self.blockSignals(restore_state)

        # If there was no data to fetch, then the model is done reloading (async tasks will
        # not emit signals to finish model reload).
        if self.__pending_published_file_data_request is None:
            self.__is_reloading = False
            self.endResetModel()

    @sgtk.LogManager.log_timing
    @wait_cursor
    def refresh(self):
        """
        Refresh the model internal data layout.

        This method should be called if the model grouping (parent/child relationships) have
        been changed.
        """

        # Do not refresh if the model is in the middle of a reload already
        if self.__is_reloading:
            return

        self.layoutAboutToBeChanged.emit()

        try:
            restore_state = self.blockSignals(True)

            # Save the current file items to refresh with (these will be lost on clear)
            file_items = self.__file_items

            # Clear the current model and pause the timer polling for updates.
            self.clear()
            self.stop_timer()

            # Restore the file items
            self.__file_items = file_items

            # Rebuild the model without refreshing the current model data. Only the model
            # structure has chagned.
            self._build_model_from_file_items(refresh_thumbnails=False)

            self.start_timer()
        finally:
            self.blockSignals(restore_state)
            self.layoutChanged.emit()

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

    @sgtk.LogManager.log_timing
    def _build_model_from_file_items(self, published_files_mapping=None, refresh_thumbnails=True):
        """
        Process the current file items data in the model to create and add the model items.

        A model item will be created for each of the given file items, and will be added to
        the model.

        This method does not clear the current model items, the clear method, in most cases,
        should be called before this method.

        :param published_files_mapping: A dictionary mapping a list of published files by
            their entity, task, published file type, and name. This is used to set the file
            items' latest published file field. It is assumed that the list of published files
            in this mapping are already sorted from highest version number to lowest. If not
            provided, the latest published file data will not be updated.
        :type published_files_mapping: dict
        :param refresh_thumbnails: True will fetch thumbnails for file items async, else False
            will not update the thumbnail data for file items. Default is True.
        :type refresh_thumbnails: bool
        """

        # Keep track of file items by grouping to add all at once at the end of processing. It
        # is more efficient to call appendRows rather than appendRow for each item.
        file_items_by_group = {}

        for file_item in self.__file_items:
            # if the item doesn't have any associated shotgun data, it means that the file is not a
            # Published File so skip it
            if not file_item.sg_data:
                continue

            group_by_id, group_by_display = self._get_file_group_info(file_item)
            if self._group_items.get(group_by_id) is None:
                group_item = FileModel.GroupModelItem(group_by_id, group_by_display)
                self._group_items[group_by_id] = group_item
            else:
                group_item = self._group_items[group_by_id]

            if published_files_mapping:
                file_item.latest_published_file = self._get_latest_published_file_for_item(file_item, published_files_mapping)

            file_model_item = FileModel.FileModelItem(file_item=file_item)

            # Make async requests to get the item thumbnail data while the model data is being
            # processed.
            if refresh_thumbnails:
                self._request_thumbnail(file_model_item, file_item)

            # Add the file item to the grouping
            file_items_by_group.setdefault(group_by_id, []).append(file_model_item)

        # Add all model items (by their parent) at once to improve performance.
        group_items = list(self._group_items.values())
        self.invisibleRootItem().appendRows(group_items)
        for group_id, file_items in file_items_by_group.items():
            group_item = self._group_items[group_id]
            group_item.appendRows(file_items)

    @sgtk.LogManager.log_timing
    def _update_latest_published_files(self, published_files_mapping):
        """
        Update the current model data to reflect the latest published file data.
        
        :param published_files_mapping: A dictionary mapping a list of published files by
            their entity, task, published file type, and name which is used to determine
            the latest published file for the given item. This param is expected to be the
            result returned by the method `_get_published_files_mapping`.
        :type published_files_mapping: dict
        """

        # NOTE: watch performance here. If many items update their published files at once,
        # this causes many consecutive data changed signals per item, which could make the
        # UI sluggish.

        for row in range(self.rowCount()):
            group_item = self.item(row)
            for child_row in range(group_item.rowCount()):
                child = group_item.child(child_row)
                file_item = child.data(self.FILE_ITEM_ROLE)
                latest_published_file = self._get_latest_published_file_for_item(file_item, published_files_mapping)
                child.setData(latest_published_file, FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE)

    # ----------------------------------------------------------------------------------------
    # Methods to retrieving and handling published file data

    def _get_published_files_for_items(self, file_items, data_retriever=None):
        """
        Make an api request to get the published file data for the given file items.
        
        If a data retreiver is given, then the api request will be executed async, else it
        will execute synchronously. For async requests, the background task id will be
        returned, else the published file data will be returned for synchronous requests.

        :param file_items: The file item objects to get the published file data for.
        :type file_items: List[FileItem]
        :param data_retriever: The Shotgun data retriever to make the api request async, if
            not provided then the request will be synchronous.
        :type data_retriever: ShotgunDataRetriever

        :return: If executed async, the background task id for the api request, else the
            published file data for the file items is returned.
        :rtype: str | dict
        """

        return self._manager.get_published_files_for_items(file_items, data_retriever=data_retriever)

    def _get_published_files_mapping(self, published_file_data):
        """
        Return a mapping of published files by their entity, name, task and type.

        The published file data passed in is a list of published file data (dictionaries). A
        mapping is created where the published files are indexed by their entity, name, task, 
        and published file type.

        :param published_file_data: The list of published file data to map.
        :type published_file_data: List[dict]

        :return: The dictionary mapping for published files.
        :rtype: dict
        """

        published_files_mapping = {}

        for pf_data in published_file_data:
            name = pf_data.get("name")

            if not pf_data.get("entity"):
                entity_id = None
                entity_type = None
            else:
                entity_id = pf_data["entity"]["id"]
                entity_type = pf_data["entity"]["type"]

            if not pf_data.get("task"):
                task_id = None
            else:
                task_id = pf_data["task"]["id"]

            if not pf_data.get("published_file_type"):
                pf_type_id = None
            else:
                pf_type_id = pf_data["published_file_type"]["id"]

            published_files_mapping.setdefault(entity_type, {}).setdefault(entity_id, {}).setdefault(task_id, {}).setdefault(pf_type_id, {}).setdefault(name, []).append(pf_data)

        return published_files_mapping
    
    def _get_latest_published_file_for_item(self, file_item, published_files_mapping):
        """
        Return the latest published file for the given file item and published file data.

        :param file_item: The file item to get the latest published file for.
        :type file_item: FileItem
        :param published_files_mapping: A dictionary mapping a list of published files by
            their entity, task, published file type, and name which is used to determine
            the latest published file for the given item. This param is expected to be the
            result returned by the method `_get_published_files_mapping`.
        :type published_files_mapping: dict

        :return: The latest published file.
        :rtype: dict
        """

        name = file_item.sg_data.get("name")

        if not file_item.sg_data.get("entity"):
            entity_id = None
            entity_type = None
        else:
            entity_id = file_item.sg_data["entity"]["id"]
            entity_type = file_item.sg_data["entity"]["type"]

        if not file_item.sg_data.get("task"):
            task_id = None
        else:
            task_id = file_item.sg_data["task"]["id"]

        if not file_item.sg_data.get("published_file_type"):
            pf_type_id = None
        else:
            pf_type_id = file_item.sg_data["published_file_type"]["id"]

        # Look up the published files for this item by the entity, task, published file type,
        # and name
        publish_files = published_files_mapping[entity_type][entity_id][task_id][pf_type_id][name]

        # The published files are assumed to be in order of highest to lowest by version
        # number. Thus the latest, is the first item in the list.
        return publish_files[0]

    def _request_thumbnail(self, model_item, file_item):
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
        self.__pending_thumbnail_requests[request_id] = file_item

    # ----------------------------------------------------------------------------------------
    # File grouping methods

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

    # ----------------------------------------------------------------------------------------
    # Polling methods

    def start_timer(self):
        """Start the file status check timer to poll for status updates."""

        if not self.polling:
            return

        # Only start the timer if a valid interval was given
        if self._timeout_interval and self._timeout_interval > 0:
            self._file_status_check_timer.start(self._timeout_interval)

    def stop_timer(self):
        """Stop the file status check timer to prevent any more calls to update the status."""

        self._file_status_check_timer.stop()

    def check_published_file_status(self):
        """
        Slot triggered on the file status check timeout.

        Make an async request to get the latest published file for this file model item,
        such that the file item status can be updated to show if the item is out of date
        or not.
        """

        if not self.polling or self.__is_reloading or self.__pending_published_file_data_request or self.rowCount() <= 0:
            return

        self.__pending_published_file_data_request = self._get_published_files_for_items(self.__file_items, self._sg_data_retriever)

    # ----------------------------------------------------------------------------------------
    # Background task and Data Retriever callbacks

    def _on_data_retriever_work_completed(self, uid, request_type, data):
        """
        Slot triggered when the data-retriever has finished doing some work. The data retriever is currently
        just used to download thumbnails for published files so this will be triggered when a new thumbnail
        has been downloaded and loaded from disk.

        :param uid:             The unique id representing a task being executed by the data retriever
        :param request_type:    A string representing the type of request that has been completed
        :param data:            The result from completing the work
        """

        if uid in self.__pending_thumbnail_requests:
            # Get the file item pertaining to this thumbnail request
            file_item = self.__pending_thumbnail_requests[uid]
            del self.__pending_thumbnail_requests[uid]

            # Update the file item's thumbnail from the data returned by the request. The
            # model item will get this data and create the QIcon to display.
            file_item.thumbnail_path = data.get("thumb_path")
        
        elif uid in self.__pending_version_requests:
            file_model_item = self.__pending_version_requests[uid]
            del self.__pending_version_requests[uid]

            latest_pf_data = data.get("sg")
            file_model_item.setData(
                latest_pf_data, FileModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE
            )

        elif uid == self.__pending_published_file_data_request:
            self.__pending_published_file_data_request = None
            published_files_mapping = self._get_published_files_mapping(data.get("sg", []))

            if self.__is_reloading:
                self._build_model_from_file_items(published_files_mapping)
            else:
                # Only update the latest published file data
                self._update_latest_published_files(published_files_mapping)

    def _on_data_retriever_work_failed(self, uid, error_msg):
        """
        Slot triggered when the data retriever fails to do some work!

        :param uid:         The unique id representing the task that the data retriever failed on
        :param error_msg:   The error message for the failed task
        """

        if uid in self.__pending_thumbnail_requests:
            del self.__pending_thumbnail_requests[uid]

        elif uid in self.__pending_version_requests:
            del self.__pending_version_requests[uid]

        elif uid == self.__pending_published_file_data_request:
            self.__pending_published_file_data_request = None

    def _on_background_task_group_finished(self, group_id):
        """
        Slot triggered when the background manager finishes all tasks within a group.

        :param group_id: The group that has finished
        :type group_id: This will be whatever the group_id was set as on 'add_task'.
        """

        # We cannot check the specific group id since we are using the data retriever
        # to initiate the background tasks, so instead we know we're done with the model
        # reload when all our pending requets are empty.
        if self.__is_reloading and self.__pending_published_file_data_request is None and not self.__pending_thumbnail_requests:
            self.__is_reloading = False
            self.start_timer()
            self.endResetModel()
