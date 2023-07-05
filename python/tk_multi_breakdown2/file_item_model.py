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


class FileTreeItemModel(QtCore.QAbstractItemModel, ViewItemRolesMixin):
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
        GROUP_ID_ROLE,  # The id of the group for this item
        GROUP_DISPLAY_ROLE,  # The id of the group for this item
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
    ) = range(_BASE_ROLE, _BASE_ROLE + 15)

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

    def __init__(
        self,
        parent,
        bg_task_manager,
        group_by=None,
        polling=False,
        dynamic_loading=True,
    ):
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
        :param dynamic_loading: True will populate the model as the data is loaded
            asynchronously, else False will populate the model once all data has finished
            loading. The data is loaded async, in the same way, whether this param is True or
            False, the difference is when the view is updated to reflect the model data
            changes. When True, the UI may be slower to respond while loading, though the
            benefit is that the user can see data as is comes in and can interact with the
            data that has already loaded. When False, the UI will not be available until all
            data has loaded, which may speed up the model load and the UI will not be slowed
            down.
        :type dynamic_loading: bool
        """

        super(FileTreeItemModel, self).__init__(parent)

        # The model data
        # Create the (invisible) tree root item. All top level layer item will be added as
        # children to this root item.
        self.__root_item = FileTreeModelItem(None)

        # Keep a list of all the layer item objects. This is a workaround to not being able
        # to use the QModelIndex.internalPointer data storage (in Python, the internal pointer
        # object is garbage collected and crashes when trying to acces it)
        self.__data = {id(None): self.__root_item}

        # ------------------------------------------------------------------------------------

        self._app = sgtk.platform.current_bundle()

        # Flag indicating if the model is dynamically loaded as it is retrieved async. False
        # will show a loader until all data is loaded in.
        self.__dynamic_loading = dynamic_loading

        # Flag indicating if the model is in the middle of a reload
        self.__is_reloading = False

        # Flag indicating if the model will poll for published file updates async.
        self.__polling = polling

        # Get the app setting for the timeout interval length for polling file item statuses.
        self._timeout_interval = self._app.get_setting("file_status_check_interval")
        # Create a timer that checks the latest published file every X seconds
        self._file_status_check_timer = QtCore.QTimer()
        self._file_status_check_timer.timeout.connect(
            lambda s=self: self.check_published_files_status()
        )

        # The list of scene objects last found by the scan_scene method. These objects
        # determine the file items shown in the app.
        self.__scene_objects = []
        # The list of file item data that currently populates the model.
        self.__file_items = []
        # The list of current group items in the model to easily change groupings.
        self._group_items = {}

        # Keep track of pending background tasks.
        self.__pending_published_file_data_request = None
        self.__pending_latest_published_files_data_request = None
        self.__pending_version_requests = {}
        self.__pending_thumbnail_requests = {}

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
        # the data for the item. The methods defined for each role must accept one parameter:
        # (1) The model item index
        self.role_methods = {
            self.VIEW_ITEM_THUMBNAIL_ROLE: ui_config_adv_hook.get_item_thumbnail,
            self.VIEW_ITEM_HEADER_ROLE: ui_config_adv_hook.get_item_title,
            self.VIEW_ITEM_SUBTITLE_ROLE: ui_config_adv_hook.get_item_subtitle,
            self.VIEW_ITEM_TEXT_ROLE: ui_config_adv_hook.get_item_details,
            self.VIEW_ITEM_SHORT_TEXT_ROLE: ui_config_adv_hook.get_item_short_text,
            self.VIEW_ITEM_ICON_ROLE: ui_config_adv_hook.get_item_icons,
            self.VIEW_ITEM_SEPARATOR_ROLE: ui_config_adv_hook.get_item_separator,
            QtCore.Qt.BackgroundRole: ui_config_adv_hook.get_item_background_color,
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
        return self.__polling

    @polling.setter
    def polling(self, value):
        self.__polling = value
        self.start_timer() if self.__polling else self.stop_timer()

    @property
    def dynamic_loading(self):
        """Get or set the property indicating if the model dynamicly loads data or not."""
        return self.__dynamic_loading

    @dynamic_loading.setter
    def dynamic_loading(self, value):
        self.__dynamic_loading = value

    # ----------------------------------------------------------------------
    # Helper functions to work around not being able to use QModelIndex.internalPointer

    def __get_ptr_id(self, file_item):
        """
        Return a unique id the layer item object to pass to the createIndex method.

        :param layer_item: The layer item to get the id for.
        :type layer_item: LayerTreeItem

        :return: The id for the layer item.
        :rtype: int
        """

        if file_item:
            ptr_id = file_item
        else:
            ptr_id = None

        return id(ptr_id)

    def __get_internal_data(self, index):
        """
        Return the layer item object for the index.

        :param index: The index to get the internal data for.
        :type index: QtCore.QModelIndex

        :return: The layer item object at the specifed index.
        :rtype: LayerTreeItem
        """

        ptr_id = index.internalId()
        return self.__data.get(ptr_id)

    def __set_internal_data(self, file_item):
        """
        Store the layer item object data in the model's internal data storage.

        :param layer_item: The layer item obejct to store.
        :type layer_item: LayerTreeItem
        """

        ptr_id = self.__get_ptr_id(file_item)
        self.__data[ptr_id] = file_item

    def __remove_internal_data(self, index):
        """
        Store the layer item object data in the model's internal data storage.

        :param layer_item: The layer item obejct to store.
        :type layer_item: LayerTreeItem
        """

        ptr_id = index.internalId()
        del self.__data[ptr_id]

    # ----------------------------------------------------------------------
    # Implement required base QAbstractItemModel methods

    def createIndex(self, row, column, ptr):
        """
        Override the base QAbstractItemModel method.

        Intercept the createIndex method to get the id for the ptr and pass this id
        instead of the ptr itself. This is a workaround to not being able to use the
        QModelIndex.internalPointer object storage.
        """

        ptr_id = self.__get_ptr_id(ptr)
        return super(FileTreeItemModel, self).createIndex(row, column, ptr_id)

    def index(self, row, column=0, parent=QtCore.QModelIndex()):
        """Return the index of hte item in the model specified by the given row, column and parent index."""

        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parent_item = self.__root_item
        else:
            parent_item = self.__get_internal_data(parent)

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)

        return self.createIndex(row, column, None)

    def parent(self, index):
        """Return the parent of the model item with the given index."""

        if not index.isValid():
            return QtCore.QModelIndex()

        child_item = self.__get_internal_data(index)
        if not child_item:
            return QtCore.QModelIndex()

        parent_item = child_item.parent_item
        if not parent_item or parent_item is self.__root_item:
            return QtCore.QModelIndex()

        row = parent_item.row()
        return self.createIndex(row, 0, parent_item)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """Returns the number of columns for the children of the given parent."""

        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        """Returns the number of rows under the given parent."""

        if not parent.isValid():
            parent_item = self.__root_item
        else:
            parent_item = self.__get_internal_data(parent)

        return parent_item.child_count()

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Returns the data stored under the given role for the item referred to by the index."""

        if not index.isValid():
            return None

        model_item = self.__get_internal_data(index)
        if not model_item:
            return None

        if model_item.file_item:
            # It is a file item
            file_item = model_item.file_item

            if role == QtCore.Qt.DisplayRole:
                return file_item.sg_data.get("name") or file_item.node_name

            if role == QtCore.Qt.DecorationRole:
                if not model_item.thumbnail_icon:
                    model_item.set_thumbnail(file_item.thumbnail_path)
                return model_item.thumbnail_icon

            if role == FileTreeItemModel.GROUP_ID_ROLE:
                return model_item.group_id

            if role == FileTreeItemModel.GROUP_DISPLAY_ROLE:
                return model_item.group_display

            if role == FileTreeItemModel.FILE_ITEM_ROLE:
                return file_item

            if role == FileTreeItemModel.FILE_ITEM_NODE_NAME_ROLE:
                return file_item.node_name

            if role == FileTreeItemModel.FILE_ITEM_NODE_TYPE_ROLE:
                return file_item.node_type

            if role == FileTreeItemModel.FILE_ITEM_PATH_ROLE:
                return file_item.path

            if role == FileTreeItemModel.FILE_ITEM_EXTRA_DATA_ROLE:
                return file_item.extra_data

            if role == FileTreeItemModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE:
                return file_item.latest_published_file

            if role == FileTreeItemModel.FILE_ITEM_SG_DATA_ROLE:
                return file_item.sg_data

            if role == FileTreeItemModel.FILE_ITEM_CREATED_AT_ROLE:
                return file_item.sg_data.get("created_at")

            if role == FileTreeItemModel.FILE_ITEM_TAGS_ROLE:
                return file_item.sg_data.get("tags") or file_item.sg_data.get(
                    "tag_list"
                )

            if role == FileTreeItemModel.STATUS_ROLE:
                # NOTE if we ever need to know if the file is up to date or not, while
                # it is also locked, we would need to create a separate role to determine
                # if the file is locked or not, in addition to this status role that would
                # then not check if the file is locked.
                if file_item.locked:
                    return FileTreeItemModel.STATUS_LOCKED

                if file_item.highest_version_number:
                    if (
                        file_item.sg_data["version_number"]
                        < file_item.highest_version_number
                    ):
                        return FileTreeItemModel.STATUS_OUT_OF_SYNC
                    return FileTreeItemModel.STATUS_UP_TO_DATE

                # Item may still loading, too early to determine the status.
                return FileTreeItemModel.STATUS_NONE

            if role == FileTreeItemModel.STATUS_FILTER_DATA_ROLE:
                status_value = self.data(index, FileTreeItemModel.STATUS_ROLE)
                status_name = FileTreeItemModel.FILE_ITEM_STATUS_NAMES.get(status_value)
                return {
                    "status": {
                        "name": status_name,
                        "value": status_value,
                        "icon": FileTreeItemModel.FILE_ITEM_STATUS_ICON_PATHS.get(
                            status_value
                        ),
                    }
                }

            if role == FileTreeItemModel.VIEW_ITEM_LOADING_ROLE:
                return self.is_loading(index)

            if role == FileTreeItemModel.REFERENCE_LOADED:
                # TODO call a hook method per DCC to check if the reference associated with this
                # file item has been loaded into the scene (if the DCC supports loading and
                # unloading references, e.g. Maya).
                #
                # For now, we'll just say everything is loaded unless told otherwise.
                return True
        else:
            # It is a group for file items
            if role in (
                FileTreeItemModel.STATUS_FILTER_DATA_ROLE,
                FileTreeItemModel.REFERENCE_LOADED,
                FileTreeItemModel.FILE_ITEM_ROLE,
                FileTreeItemModel.FILE_ITEM_NODE_NAME_ROLE,
                FileTreeItemModel.FILE_ITEM_NODE_TYPE_ROLE,
                FileTreeItemModel.FILE_ITEM_PATH_ROLE,
                FileTreeItemModel.FILE_ITEM_SG_DATA_ROLE,
                FileTreeItemModel.FILE_ITEM_EXTRA_DATA_ROLE,
                FileTreeItemModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE,
                FileTreeItemModel.FILE_ITEM_CREATED_AT_ROLE,
                FileTreeItemModel.FILE_ITEM_TAGS_ROLE,
            ):
                # File item specific roles, just return None.
                return None

            if role == QtCore.Qt.DisplayRole:
                return model_item.group_display

            if role == FileTreeItemModel.GROUP_ID_ROLE:
                return model_item.group_id

            if role == FileTreeItemModel.GROUP_DISPLAY_ROLE:
                return model_item.group_display

            if role == FileTreeItemModel.VIEW_ITEM_HEIGHT_ROLE:
                # Group item height always adjusts to content size
                return -1

            if role == FileTreeItemModel.VIEW_ITEM_LOADING_ROLE:
                # Do not show a loading icon for the group item (loading status will be
                # shown in the subtitle)
                return False

            if role == FileTreeItemModel.STATUS_ROLE:
                num_children = model_item.child_count()
                if num_children > 0:
                    locked = True
                    for row in range(num_children):
                        child_index = self.index(row, 0, index)
                        child_status = self.data(child_index, role)

                        if child_status == FileTreeItemModel.STATUS_OUT_OF_SYNC:
                            # The group status is out of sync if any children are out of sync.
                            return FileTreeItemModel.STATUS_OUT_OF_SYNC

                        if child_status != FileTreeItemModel.STATUS_LOCKED:
                            # The group status is locked only if all children are locked.
                            locked = False

                    return (
                        FileTreeItemModel.STATUS_LOCKED
                        if locked
                        else FileTreeItemModel.STATUS_UP_TO_DATE
                    )

                # Group has no children, it should not exist.
                return None

        # base model item handling here for role methods
        result = None

        # Check if the model has a method defined for retrieving the item data for this role.
        data_method = self.get_method_for_role(role)
        if data_method:
            try:
                result = data_method(index)
            except TypeError as error:
                raise TankError(
                    "Failed to execute the method defined to retrieve item data for role `{role}`.\nError: {msg}".format(
                        role=role, msg=error
                    )
                )
        else:
            result = None

        return shotgun_model.util.sanitize_qt(result)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Sets the role data for the item at index to value."""

        if not index.isValid():
            return False

        model_item = self.__get_internal_data(index)
        if not model_item:
            return False

        changed = False
        change_roles = [role]

        if role == QtCore.Qt.DecorationRole:
            model_item.set_thumbnail(value)
            changed = True

        elif role == FileTreeItemModel.GROUP_ID_ROLE:
            model_item.group_id = value
            changed = True

        elif role == FileTreeItemModel.GROUP_DISPLAY_ROLE:
            model_item.group_display = value
            changed = True

        elif role == FileTreeItemModel.FILE_ITEM_ROLE:
            file_item = model_item.file_item
            if file_item:
                cur_group_value = file_item.sg_data.get(self.group_by)
                updated_group_value = value.sg_data.get(self.group_by)
                if cur_group_value != updated_group_value:
                    # Update the grouping of this file item now that its data has changed
                    # and it no longer belongs in its current group
                    self.update_file_group(index.row(), file_item, value)

            model_item.set_file_item(value)
            changed = True

        elif role == FileTreeItemModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE:
            file_item = model_item.file_item
            if file_item:
                if (
                    not file_item.latest_published_file
                    or not value
                    or file_item.latest_published_file.get("id") != value.get("id")
                ):
                    file_item.latest_published_file = value
                    changed = True

        if changed:
            self.dataChanged.emit(index, index, change_roles)
            return True

        return False

    # ----------------------------------------------------------------------
    # Override base QAbstractItemModel methods

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        """Insert count rows starting with the given row under parent from the model."""

        self.beginInsertRows(parent, row, row + count - 1)

        # First get the parent to insert the rows under
        if not parent.isValid():
            parent_item = self.__root_item
        else:
            parent_item = self.__get_internal_data(parent)

        # Insert the rows now
        if row == parent_item.child_count():
            # Append to the parent item
            for _ in range(count):
                item = FileTreeModelItem()
                parent_item.append_child(item)
                item.parent_item = parent_item
                self.__set_internal_data(item)
        else:
            for i in range(count):
                item = FileTreeModelItem()
                parent_item.child_items.insert(row + i, item)
                item.parent_item = parent_item
                self.__set_internal_data(item)

        self.endInsertRows()

        return True

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        """Removes count rows starting with the given row under parent from the model."""

        self.beginRemoveRows(parent, row, row + count - 1)

        index = self.index(row, 0, parent)
        if index.isValid():
            if not parent.isValid():
                parent_item = self.__root_item
            else:
                parent_item = self.__get_internal_data(parent)

            # Update the model internal data
            del parent_item.child_items[row : row + count]
            self.__remove_internal_data(index)

            success = True
        else:
            success = False

        self.endRemoveRows()

        return success

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
            self._bg_task_manager.task_completed.disconnect(
                self._on_background_task_completed
            )
            self._bg_task_manager.task_failed.disconnect(
                self._on_background_task_failed
            )
            self._bg_task_manager.task_group_finished.disconnect(
                self._on_background_task_group_finished
            )

    def clear(self):
        """
        Override the base method.

        Clean up the data that this model owns and call the base class method to finish the
        clean up.
        """

        self.__root_item.reset()
        self.__data = {id(None): self.__root_item}

        self.__scene_objects = []
        self.__file_items = []
        self._group_items = {}

        # Stop any background tasks currently running
        self._bg_task_manager.stop_task(self.__pending_published_file_data_request)
        self._bg_task_manager.stop_task(
            self.__pending_latest_published_files_data_request
        )

        for version_request_id in self.__pending_version_requests:
            self._bg_task_manager.stop_task(version_request_id)

        for thumbnail_request_id in self.__pending_thumbnail_requests:
            self._bg_task_manager.stop_task(thumbnail_request_id)

        # Clear request ids
        self.__pending_published_file_data_request = None
        self.__pending_latest_published_files_data_request = None
        self.__pending_version_requests.clear()
        self.__pending_thumbnail_requests.clear()

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
            self.__scene_objects = self._manager.scan_scene()

            # Make an async request to get the published files for the references in the scene.
            # This will omit any objects from the scene that do not have a ShotGrid Published
            # File. Some files can come from other projects so we cannot rely on templates,
            # and instead need to query ShotGrid.
            file_paths = [o["path"] for o in self.__scene_objects]
            self.__pending_published_file_data_request = (
                self._manager.get_published_files_from_file_paths(
                    file_paths,
                    extra_fields=self._published_file_fields,
                    bg_task_manager=self._bg_task_manager,
                )
            )
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
            self._finish_reload(start_timer=False)

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

            if self.__pending_thumbnail_requests:
                request_thumbnails = True
            else:
                request_thumbnails = False

            # Clear the current model and pause the timer polling for updates.
            self.clear()
            self.stop_timer()

            # Restore the file items
            self.__file_items = file_items

            # Rebuild the model without refreshing the current model data. Only the model
            # structure has chagned.
            self._build_model_from_file_items(refresh_thumbnails=request_thumbnails)

            self.start_timer()
        finally:
            self.blockSignals(restore_state)
            self.layoutChanged.emit()

    @sgtk.LogManager.log_timing
    @wait_cursor
    def add_item(self, file_item_data):
        """
        Add a new file item to the model from the given data.

        :param file_item_data: The data to create the new file item.
        :type file_item_data: dict

        :return: True if the item was added successfully, else False.
        :rtype: bool
        """

        if self.__is_reloading:
            return

        # Query for the published file for the new file item and create the FileItem object.
        published_files = self._manager.get_published_files_from_file_paths(
            [file_item_data["path"]],
            extra_fields=self._published_file_fields,
        )

        # Get the FileItem object from the published file data
        file_items = self._manager.get_file_items([file_item_data], published_files)
        if not file_items:
            return False

        file_item = file_items[0]
        if not file_item.sg_data:
            # Invalid file item, cannot continue.
            return False

        # Get the latest published file for the new item.
        item_published_files = self._get_published_files_for_items(file_items)
        file_item.latest_published_file = item_published_files[0]

        # Now we have all the data necessary to add the new file item to the model.
        group_by_id, group_by_display = self._get_file_group_info(file_item)
        if self._group_items.get(group_by_id) is None:
            # Insert a new row in the model for the new file item grouping
            group_row = self.__root_item.child_count()
            success = self.insertRows(group_row, 1)
            if not success:
                return False

            group_index = self.index(group_row)
            self.setData(group_index, group_by_id, self.GROUP_ID_ROLE)
            self.setData(group_index, group_by_display, self.GROUP_DISPLAY_ROLE)

            group_item = self.__get_internal_data(group_index)
            self._group_items[group_by_id] = group_item
        else:
            # Get the existing group item to add the new file model item to.
            group_item = self._group_items[group_by_id]
            group_index = self.index(group_item.row(), 0)

        # Insert the row in the model to hold the new file item data
        item_row = group_item.child_count()
        success = self.insertRows(item_row, 1, group_index)
        if success:
            item_index = self.index(item_row, 0, group_index)
            self.setData(item_index, file_item, self.FILE_ITEM_ROLE)

            # Request the thumbnail data
            file_model_item = self.__get_internal_data(item_index)
            self._request_thumbnail(file_model_item, file_item)

            # Update the internal data with the new file item.
            self.__scene_objects.append(file_item_data)
            self.__file_items.append(file_item)

        return success

    @sgtk.LogManager.log_timing
    @wait_cursor
    def remove_item_by_file_path(self, file_path):
        """
        Find the model item corresponding to the given file path and remove it from the model.

        :param file_path: The file path to look up the model item to remove.
        :type file_path: str

        :return: True if the item was successfully removed, else False.
        :rtype: bool
        """

        if self.__is_reloading:
            return

        index = self.index_from_file_path(file_path, check_old_path=True)
        if not index.isValid():
            return False

        file_item_to_remove = self.data(index, self.FILE_ITEM_ROLE)
        if not file_item_to_remove:
            # Invalid index data
            return False

        file_path = file_item_to_remove.path
        for i, obj in enumerate(self.__scene_objects):
            if obj["path"] == file_path:
                del self.__scene_objects[i]
                break

        for i, fi in enumerate(self.__file_items):
            if fi == file_item_to_remove:
                del self.__file_items[i]
                break

        parent_index = index.parent()
        success = self.removeRows(index.row(), 1, parent_index)

        if not success:
            # Failed to remove item, return failure.
            return False

        # Check if by remove this item, the item's group is now empty. If so, remove the group
        if not parent_index.isValid():
            # No parent group to check, return success.
            return True

        if not self.rowCount(parent_index):
            # Remove the group from the internal data list
            group_id = self.data(parent_index, self.GROUP_ID_ROLE)
            del self._group_items[group_id]

            # Remove the group since it is now empty. Return the result of removing the group.
            return self.removeRows(parent_index.row(), 1, parent_index.parent())

        # Item removed successfully.
        return True

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
        Traverse the model to get the model item that matches the given file item data.

        :param file_item: The file item data to find the model item by.
        :type file_item: FileItem

        :return: The model item.
        :rtype: FileModelItem
        """

        row_count = self.__root_item.child_count()

        for group_row in range(row_count):
            group_index = self.index(group_row, 0)
            group_item = self.__get_internal_data(group_index)

            num_children = group_item.child_count()
            for child_row in range(num_children):
                child_index = self.index(child_row, 0, group_index)

                if (
                    self.data(child_index, FileTreeItemModel.FILE_ITEM_ROLE)
                    == file_item
                ):
                    child_item = self.__get_internal_data(child_index)
                    return child_item

        return None

    def index_from_file_path(self, file_path, check_old_path=False):
        """
        Traverse the model to get the model item index that matches the given file path.

        :param file_path: The file path to find the model index by.
        :type file_path: str
        :param check_old_path: True will check the item extra data for the old path, which is
            the path before it was updated. For removing indexes, the path may have been
            updated before the index could be removed.
        :type check_old_path: bool

        :return: The model index.
        :rtype: QtCore.QModelIndex
        """

        row_count = self.__root_item.child_count()

        for group_row in range(row_count):
            group_index = self.index(group_row, 0)
            group_item = self.__get_internal_data(group_index)

            num_children = group_item.child_count()
            for child_row in range(num_children):
                child_index = self.index(child_row, 0, group_index)
                file_item = self.data(child_index, FileTreeItemModel.FILE_ITEM_ROLE)

                if file_item.path == file_path:
                    return child_index

                if (
                    check_old_path
                    and file_item.extra_data
                    and file_item.extra_data.get("old_path") == file_path
                ):
                    return child_index

        return QtCore.QModelIndex()

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
            new_group_item = FileTreeModelItem(
                group_id=new_group_id, group_display=new_group_display
            )
            self._group_items[new_group_id] = new_group_item
            self.__root_item.append_child(new_group_item)
            self.appendRow(new_group_item)

        new_group_item.append_child(file_model_item)

    #########################################################################################################
    # Protected FileModel methods

    def _finish_reload(self, start_timer=True):
        """
        Model has finished reloading.

        Emit the Qt signal for model reset and reset the reloading flag.

        :param start_timer: True will start the timer to poll for published file updates.
        :type start_time: bool
        """

        if start_timer:
            self.start_timer()

        self.__is_reloading = False
        self.endResetModel()

    @sgtk.LogManager.log_timing
    def _build_model_from_file_items(
        self, published_files_mapping=None, refresh_thumbnails=True
    ):
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
                group_item = FileTreeModelItem(
                    group_id=group_by_id, group_display=group_by_display
                )
                self._group_items[group_by_id] = group_item
                self.__set_internal_data(group_item)
            else:
                group_item = self._group_items[group_by_id]

            if published_files_mapping:
                file_item.latest_published_file = (
                    self._get_latest_published_file_for_item(
                        file_item, published_files_mapping
                    )
                )

            file_model_item = FileTreeModelItem(file_item=file_item)
            self.__set_internal_data(file_model_item)

            # Make async requests to get the item thumbnail data while the model data is being
            # processed.
            if refresh_thumbnails:
                self._request_thumbnail(file_model_item, file_item)

            # Add the file item to the grouping
            file_items_by_group.setdefault(group_by_id, []).append(file_model_item)

        # Add all model items (by their parent) at once to improve performance.
        group_items = list(self._group_items.values())

        for group_item in group_items:
            group_item.parent_item = self.__root_item
            self.__root_item.append_child(group_item)

        for group_id, file_items in file_items_by_group.items():
            group_item = self._group_items[group_id]
            for file_item in file_items:
                file_item.parent_item = group_item
                group_item.append_child(file_item)

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

        row_count = self.__root_item.child_count()

        for row in range(row_count):
            group_index = self.index(row, 0)
            group_item = self.__get_internal_data(group_index)
            child_row_count = group_item.child_count()

            for child_row in range(child_row_count):
                child_index = self.index(child_row, 0, group_index)
                file_item = self.data(child_index, self.FILE_ITEM_ROLE)
                latest_published_file = self._get_latest_published_file_for_item(
                    file_item, published_files_mapping
                )
                self.setData(
                    child_index,
                    latest_published_file,
                    FileTreeItemModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE,
                )

    def is_loading(self, index=None):
        """Return True if the model item is currently being loaded."""

        if (
            self.__pending_published_file_data_request
            or self.__pending_latest_published_files_data_request
        ):
            return True

        if index:
            if not index.isValid():
                return False

            model_item = self.__get_internal_data(index)
            if model_item in [v[1] for v in self.__pending_thumbnail_requests.values()]:
                return True

            if model_item in self.__pending_version_requests.values():
                return True
        else:
            if self.__pending_thumbnail_requests:
                return True

            if self.__pending_version_requests.values():
                return True

        return False

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

        return self._manager.get_published_files_for_items(
            file_items, data_retriever=data_retriever
        )

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

            published_files_mapping.setdefault(entity_type, {}).setdefault(
                entity_id, {}
            ).setdefault(task_id, {}).setdefault(pf_type_id, {}).setdefault(
                name, []
            ).append(
                pf_data
            )

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
        publish_files = published_files_mapping[entity_type][entity_id][task_id][
            pf_type_id
        ][name]

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
        self.__pending_thumbnail_requests[request_id] = (file_item, model_item)

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

    def check_published_files_status(self):
        """
        Slot triggered on the file status check timeout.

        Make an async request to get the latest published file for this file model item,
        such that the file item status can be updated to show if the item is out of date
        or not.
        """

        if (
            not self.polling
            or self.__is_reloading
            or self.__pending_published_file_data_request
            or self.__pending_latest_published_files_data_request
            or self.rowCount() <= 0
        ):
            return

        self.__pending_latest_published_files_data_request = (
            self._get_published_files_for_items(
                self.__file_items, self._sg_data_retriever
            )
        )

    def __get_index_from_item(self, item):
        """Return the index for the FileTreeModelItem."""

        parent_item = item.parent_item
        if parent_item:
            parent_index = self.index(parent_item.row(), 0)
        else:
            parent_index = QtCore.QModelIndex()

        file_item_row = item.row()
        return self.index(file_item_row, 0, parent_index)

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
            file_item, file_model_item = self.__pending_thumbnail_requests[uid]
            del self.__pending_thumbnail_requests[uid]

            # Update the thumbnail path without emitting any signals. For non-dynamic loading,
            # the thumbnail udpate will be reflected once all data has been retrieved (not
            # just thumbnails).
            # For dynamic loading, we will emit one data changed signal once all thumbnails are
            # retrieved. Ideally, we would emit a signal as each thumbnail is loaded but tree
            # views do not handle single updates efficiently (e.g. the whole tree is painted
            # on each single index update).
            file_item.thumbnail_path = data.get("thumb_path")
            if self.dynamic_loading and not self.__pending_thumbnail_requests:
                top_left = self.index(0, 0)
                bottom_right = self.index(self.rowCount() - 1, 0)
                self.dataChanged.emit(top_left, bottom_right)

        elif uid in self.__pending_version_requests:
            file_model_item = self.__pending_version_requests[uid]
            del self.__pending_version_requests[uid]

            latest_pf_data = data.get("sg")
            file_item_index = self.__get_index_from_item(file_model_item)
            self.setData(
                file_item_index,
                latest_pf_data,
                FileTreeItemModel.FILE_ITEM_LATEST_PUBLISHED_FILE_ROLE,
            )

        elif uid == self.__pending_latest_published_files_data_request:
            self.__pending_latest_published_files_data_request = None
            published_files_mapping = self._get_published_files_mapping(
                data.get("sg", [])
            )

            if self.__is_reloading:
                self._build_model_from_file_items(published_files_mapping)
                if self.dynamic_loading:
                    # Emit signals that data has finished loading. Any data still loading will
                    # be dynamically populated as it is retrieved (e.g. thumbnails).
                    self._finish_reload()
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

        elif uid == self.__pending_latest_published_files_data_request:
            self.__pending_latest_published_files_data_request = None

    def _on_background_task_completed(self, uid, group_id, result):
        """
        Callback triggered when the background manager has finished doing some task. The only
        task we're asking the manager to do is to find the latest published file associated
        to the current item.

        :param uid: Unique id associated with the task
        :param group_id: The group the task is associated with
        :param result: The data returned by the task
        """

        if uid == self.__pending_published_file_data_request:
            self.__pending_published_file_data_request = None

            # Get the list of FileItem objects representing the objects in the scene
            self.__file_items = self._manager.get_file_items(
                self.__scene_objects, result
            )

            # Make an async request to get all published file data necessary to determine the
            # latest published file per file item. Get all info in a single request.
            self.__pending_latest_published_files_data_request = (
                self._get_published_files_for_items(
                    self.__file_items, self._sg_data_retriever
                )
            )

    def _on_background_task_failed(self, uid, group_id, msg, stack_trace):
        """
        Callback triggered when the background manager failed to complete a task.

        :param uid: Unique id associated with the task
        :param group_id: The group the task is associated with
        :param msg: Short error message
        :param stack_trace: Full error traceback
        """

        if uid == self.__pending_published_file_data_request:
            self.__pending_published_file_data_request = None
            self._finish_reload()

    def _on_background_task_group_finished(self, group_id):
        """
        Slot triggered when the background manager finishes all tasks within a group.

        :param group_id: The group that has finished
        :type group_id: This will be whatever the group_id was set as on 'add_task'.
        """

        # We cannot check the specific group id since we are using the data retriever to
        # initiate the reload background tasks, so instead we know we're done with the model
        # reload when all our pending requets are empty.
        if (
            self.__is_reloading
            and self.__pending_published_file_data_request is None
            and self.__pending_latest_published_files_data_request is None
            and not self.__pending_thumbnail_requests
        ):
            self._finish_reload()


class FileModelItem:
    """Data structure to hold information about an item in the Layer model."""

    def __init__(self, file_item):
        """Initialize the file item."""

        self.set_file_item(file_item)

    def __eq__(self, other):
        """
        Override the base method.

        File model items are equal if their FileItem objects are equal. Note that this
        means each file model item should refer to a unique file item.

        :param other: The FileModelItem to compare with.
        :type other: FileModelItem

        :return: True if this model item is equal to the other item.
        :rtype: bool
        """

        if not isinstance(other, FileModelItem):
            return False

        return self.file_item_id == other.file_item_id

    # ----------------------------------------------------------------------
    # Properties

    @property
    def file_item_id(self):
        return self.__file_item_id

    @property
    def file_item(self):
        return self.__file_item

    @property
    def thumbnail_icon(self):
        return self.__thumbnail_icon

    # ----------------------------------------------------------------------
    # Public methods

    def set_file_item(self, file_item):
        """Set the file item data for this model item."""

        self.__file_item = file_item

        if self.__file_item:
            # File item path should be unique
            self.__file_item_id = self.__file_item.path
            self.__thumbnail_icon = QtGui.QIcon(self.__file_item.thumbnail_path)
        else:
            self.__file_item_id = None
            self.__thumbnail_icon = QtGui.QIcon()

    def set_thumbnail(self, thumbnail_path):
        """Custom method to set the thumbnail data to avoid emitting data changed signals."""

        self.__file_item.thumbnail_path = thumbnail_path
        self.__thumbnail_icon = QtGui.QIcon(thumbnail_path)


class FileTreeModelItem(FileModelItem):
    """Data structure to hold information about a file item in a tree model."""

    def __init__(self, file_item=None, group_id=None, group_display=None):
        """Initialize the file tree item."""

        super(FileTreeModelItem, self).__init__(file_item)

        self.__group_id = group_id
        self.__group_display = group_display

        self.__child_items = []
        self.__parent_item = None

    def __eq__(self, other):
        """
        Override the base method.

        File tree model items are equal if their FileItem objects are equal. Note that this
        means each file model item should refer to a unique file item.

        :param other: The FileTreeModelItem to compare with.
        :type other: FileTreeModelItem

        :return: True if this model item is equal to the other item.
        :rtype: bool
        """

        if not isinstance(other, FileTreeModelItem):
            return False

        if self.file_item_id is None or other.file_item_id is None:
            # One of the items are a group

            if self.file_item_id != other.file_item_id:
                # One item is a group, while the other is a file, thus they are not equal.
                return False

            # Both items are groups, compare their group ids.
            return self.group_id == other.group_id

        # They are both file items, compare their file ids.
        return self.file_item_id == other.file_item_id

    # ----------------------------------------------------------------------
    # Properties

    @property
    def group_id(self):
        """Get or set the unique group id for this item."""
        return self.__group_id

    @group_id.setter
    def group_id(self, value):
        self.__group_id = value

    @property
    def group_display(self):
        """Get or set the group display value for this item."""
        return self.__group_display

    @group_display.setter
    def group_display(self, value):
        self.__group_display = value

    @property
    def child_items(self):
        """Get the layer tree item's child items."""
        return self.__child_items

    @property
    def parent_item(self):
        """Get or set the layer tree item's paretn item."""
        return self.__parent_item

    @parent_item.setter
    def parent_item(self, value):
        self.__parent_item = value

    # ----------------------------------------------------------------------
    # Public methods

    def append_child(self, child_item):
        """
        Add a child item to this item.

        :param child_item: The child item to add.
        :type child_item: LayerTreeItem
        """

        self.__child_items.append(child_item)

    def child(self, row):
        """
        Return the child item at the specified row.

        :parm row: The row of the child to get.
        :type row: int

        :return: The child item.
        :rtype: LayerTreeItem
        """
        if row < 0 or row >= len(self.__child_items):
            return None
        return self.__child_items[row]

    def child_count(self):
        """Return the number of children under this item."""

        return len(self.__child_items)

    def row(self):
        """Return the item's location within its parent's list of items."""

        if self.parent_item is None:
            return 0

        return self.__parent_item.child_items.index(self)

    def reset(self):
        """Reset the tree item data."""

        self.__parent_item = None
        self.__child_items = []
