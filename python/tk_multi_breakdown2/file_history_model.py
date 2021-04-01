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
from sgtk.platform.qt import QtCore

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

    VIEW_ITEM_CONFIG_HOOK_PATH = "view_item_configuration_hook"

    # Additional data roles defined for the model
    _BASE_ROLE = QtCore.Qt.UserRole + 32
    (
        ENTITY_DATA_ROLE,  # The entity that this model data records are 'history' of.
        NEXT_AVAILABLE_ROLE,  # Keep track of the next available custome role. Insert new roles above.
    ) = range(_BASE_ROLE, _BASE_ROLE + 2)

    def __init__(self, parent, bg_task_manager):
        """
        Class constructor

        :param parent:          The parent QObject for this instance
        :param bg_task_manager: A BackgroundTaskManager instance that will be used for all background/threaded
                                work that needs undertaking
        """

        ShotgunModel.__init__(self, parent, bg_task_manager=bg_task_manager)

        self._entity = None
        self._app = sgtk.platform.current_bundle()

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
            FileHistoryModel.VIEW_ITEM_THUMBNAIL_ROLE: view_item_config_hook.get_history_item_thumbnail,
            FileHistoryModel.VIEW_ITEM_HEADER_ROLE: view_item_config_hook.get_history_item_title,
            FileHistoryModel.VIEW_ITEM_SUBTITLE_ROLE: view_item_config_hook.get_history_item_subtitle,
            FileHistoryModel.VIEW_ITEM_TEXT_ROLE: view_item_config_hook.get_history_item_details,
            FileHistoryModel.VIEW_ITEM_ICON_ROLE: view_item_config_hook.get_history_item_icons,
        }

    @property
    def entity(self):
        """
        Get the entity whose history records make up this model (the data in this model are the
        history records for this entity).
        """
        return self._entity

    def load_data(self, sg_data):
        """
        Load the details for the shotgun publish entity described by sg_data.

        :param sg_data: Dictionary describing a publish in shotgun, including all the common
                        publish fields.
        """

        # Set the entity property to the new entity that this model will contain history records for.
        self._entity = sg_data

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
        :param sg_data: Shotgun data dictionary that was received from Shotgun given the fields
                        and other settings specified in load_data()
        """

        self.set_data_for_role_methods(item, sg_data)

    def _get_args_for_role_method(self, item, role):
        """
        Override the :class:`ViewItemRolesMixin` method.

        This method will be called before executing the method to retrieve the item
        data for a given role.

        Return any additional positional or keyword arguments to pass along to the
        method executed for a role.staticmethod

        :param item: The model item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param role: The item role.
        :type role: :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole`

        :return: Positional or keyword arguments to pass to a method executed to retreive
                 item data for a role.
        :rtype: tuple(list, dict)
        """

        args = ()
        kwargs = {"entity": self.entity}
        return (args, kwargs)
