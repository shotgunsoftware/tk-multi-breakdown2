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
from sgtk.platform.qt import QtCore, QtGui

from .ui import resources_rc  # Required for accessing icons
from .utils import get_ui_published_file_fields
from . import constants


shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model"
)
ShotgunModel = shotgun_model.ShotgunModel

delegates = sgtk.platform.import_framework("tk-framework-qtwidgets", "delegates")
ViewItemRolesMixin = delegates.ViewItemRolesMixin


class FileHistoryModel(ShotgunModel, ViewItemRolesMixin):
    """
    This model represents the version history for a file.
    """

    UI_CONFIG_ADV_HOOK_PATH = "hook_ui_config_advanced"

    # Additional data roles defined for the model
    _BASE_ROLE = QtCore.Qt.UserRole + 32
    (
        STATUS_ROLE,  # The item status, one of the status enums
        BADGE_ROLE,  # The badge to display for the item based on status
        SORT_ROLE,  # The history data to sort the items by
        NEXT_AVAILABLE_ROLE,  # Keep track of the next available custome role. Insert new roles above.
    ) = range(_BASE_ROLE, _BASE_ROLE + 4)

    (
        STATUS_UP_TO_DATE,
        STATUS_OUT_OF_DATE,
    ) = range(2)

    STATUS_BADGES = {
        STATUS_UP_TO_DATE: ":/tk-multi-breakdown2/icons/current-uptodate.png",
        STATUS_OUT_OF_DATE: ":/tk-multi-breakdown2/icons/current-outofdate.png",
    }
    LOCKED_ICON = ":/tk-multi-breakdown2/icons/current-override.png"

    def __init__(self, parent, bg_task_manager):
        """
        Class constructor

        :param parent:          The parent QObject for this instance
        :param bg_task_manager: A BackgroundTaskManager instance that will be used for all background/threaded
                                work that needs undertaking
        """

        ShotgunModel.__init__(self, parent, bg_task_manager=bg_task_manager)

        self._app = sgtk.platform.current_bundle()

        # Store parent file item of the items in this model.
        self._parent_file = None

        # Add additional roles defined by the ViewItemRolesMixin class.
        self.NEXT_AVAILABLE_ROLE = self.initialize_roles(self.NEXT_AVAILABLE_ROLE)

        # Get the hook instance for configuring the display for model view items.
        ui_config_adv_hook_path = self._app.get_setting(self.UI_CONFIG_ADV_HOOK_PATH)
        ui_config_adv_hook = self._app.create_hook_instance(ui_config_adv_hook_path)

        # Create a mapping of model item data roles to the method that will be called to retrieve
        # the data for the item. The methods defined for each role must accept two parameters:
        # (1) QStandardItem (2) dict
        self.role_methods = {
            self.VIEW_ITEM_THUMBNAIL_ROLE: ui_config_adv_hook.get_history_item_thumbnail,
            self.VIEW_ITEM_HEADER_ROLE: ui_config_adv_hook.get_history_item_title,
            self.VIEW_ITEM_SUBTITLE_ROLE: ui_config_adv_hook.get_history_item_subtitle,
            self.VIEW_ITEM_TEXT_ROLE: ui_config_adv_hook.get_history_item_details,
            self.VIEW_ITEM_ICON_ROLE: ui_config_adv_hook.get_history_item_icons,
            self.VIEW_ITEM_SEPARATOR_ROLE: ui_config_adv_hook.get_history_item_separator,
        }

    @property
    def parent_file(self):
        """
        Get or set the parent file of the items in this model. Setting the parent file will update
        the each item's data in the model based on the changes to the parent. If the parent file
        has changed to a new parent, the load_data method should be called instead of updating
        this property.
        """
        return self._parent_file

    @parent_file.setter
    def parent_file(self, parent):
        self._parent_file = parent

        # Update all items in the model. Note that this does not reload the data, it just updates
        # the history items based on the parent changes. If the parent has changed to a different
        # objects, then load_data should be called instead.
        for row in range(self.rowCount()):
            item = self.item(row)
            sg_data = item.get_sg_data()
            self._populate_item(item, sg_data)

    @property
    def parent_entity(self):
        """
        Get the ShotGrid entity data dictionary that the parent file item represents.
        """
        if not self.parent_file:
            return None

        return self.parent_file.sg_data

    @property
    def parent_locked(self):
        """
        Get whether or not the parent file is locked to its current version.
        """
        if not self.parent_file:
            return None

        return self.parent_file.locked

    @property
    def highest_version_number(self):
        """
        Get the highest version number that an item in this model can have. The highest version number
        is retrieved from the parent file.
        """
        if not self.parent_file:
            return None

        return self.parent_file.highest_version_number or -1

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        Override the base method.

        Returns the data stored under the given role for the item referred to by the index.

        :param index: The index to get the data for.
        :type index: QtCore.QModelIndex
        :param role: The role to get the data for.
        :type role: QtCore.Qt.ItemDataRole
        """

        if role == self.SORT_ROLE:
            sg_data = self.data(index, self.SG_DATA_ROLE)
            return sg_data.get("version_number", -1)

        return super(FileHistoryModel, self).data(index, role)

    def is_current(self, history_sg_data):
        """
        Return True if the history item represented by history_sg_data is the current version in use for
        the parent entity. This will compare the parent file entity to the history entity data.
        """

        if not self.parent_entity:
            return False

        return self.parent_entity.get("id") == history_sg_data.get("id")

    def load_data(self, parent_file):
        """
        Load the history details for the parent file item. The file item contains the ShotGrid data
        dictionary used to load the history data.

        :param sg_data: The parent file item to load history data for.
        :type sg_data: FileItem
        """

        # Store the parent file item. Do not use the property setter, since that will cause the
        # _populate_item to be unecessarily called twice per item.
        self._parent_file = parent_file
        sg_data = self._parent_file.sg_data

        app = sgtk.platform.current_bundle()

        fields = constants.PUBLISHED_FILES_FIELDS + app.get_setting(
            "published_file_fields", []
        )
        fields += get_ui_published_file_fields(app)
        filters = [
            ["project", "is", sg_data["project"]],
            ["name", "is", sg_data["name"]],
            ["task", "is", sg_data["task"]],
            ["entity", "is", sg_data["entity"]],
            ["published_file_type", "is", sg_data["published_file_type"]],
        ]

        ShotgunModel._load_data(
            self,
            entity_type="PublishedFile",
            filters=filters,
            hierarchy=["version_number"],
            fields=fields,
        )

        self._refresh_data()

    def _populate_item(self, item, sg_data):
        """
        Override the base :class:`ShotgunQueryModel` method.

        Whenever an item is constructed, this method is called. It allows subclasses to intercept
        the construction of a QStandardItem and add additional metadata or make other changes
        that may be useful. Nothing needs to be returned.

        :param item: QStandardItem that is about to be added to the model. This has been primed
                     with the standard settings that the ShotgunModel handles.
        :param sg_data: ShotGrid data dictionary that was received from ShotGrid given the fields
                        and other settings specified in load_data()
        """

        if self.is_current(sg_data):
            # This history item is the current item (e.g. the parent item is using this item).
            # Set the status and badge to indicate it is current
            history_item_version_number = sg_data.get("version_number", -1)
            if history_item_version_number < self.highest_version_number:
                status = self.STATUS_OUT_OF_DATE
            else:
                status = self.STATUS_UP_TO_DATE

            if self.parent_locked:
                badge = self.LOCKED_ICON
                # The first access will only provide the path to the icon. Create the icon
                # and set for next time.
                if not isinstance(badge, QtGui.QIcon):
                    badge = QtGui.QIcon(badge)
            else:
                badge = self.STATUS_BADGES.get(status, None)
                # The first icon access only the path will be provided. Create the icon and
                # set it in the status badge mapping for next time
                if badge and not isinstance(badge, QtGui.QIcon):
                    badge = QtGui.QIcon(badge)
                    self.STATUS_BADGES[status] = badge

        else:
            # No status or badge for non-current items
            status = None
            badge = None

        # Set the item data
        item.setData(status, self.STATUS_ROLE)
        item.setData(badge, self.BADGE_ROLE)
        # Set up the methods to call to retrieve the data for the specified role.
        self.set_data_for_role_methods(item, sg_data)

    def _set_tooltip(self, item, sg_item):
        """
        Override base method to ensure no tooltip is set from the model. Let the delegate
        take care of showing the tooltip.

        Sets a tooltip for this model item.

        :param item: ShotgunStandardItem associated with the publish.
        :param sg_item: Publish information from ShotGrid.
        """

        # Do nothing, let the delegate show the tooltip.
