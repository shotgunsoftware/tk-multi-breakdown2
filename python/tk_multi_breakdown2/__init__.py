# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from .api import BreakdownManager

# For unit tests to access the app modules
from .file_model import FileModel
from .file_proxy_model import FileProxyModel
from .file_history_model import FileHistoryModel

try:
    # Attempt to import the AppDialog
    from .dialog import AppDialog
except:
    # Ignore import error for AppDialog so that the app works gracefully in batch modes
    pass


def show_dialog(app):
    """
    Show the main dialog ui

    :param app: The parent App
    :type app: Application

    :return: The dialog widget.
    :rtype: AppDialog
    """

    return app.engine.show_dialog("Scene Breakdown", app, AppDialog)


def show_as_panel(app):
    """
    Return True if the App should be shown as a panel, instead of a dialog.

    To be shown as a panel, the App should be set up to refresh on scene change events, such
    as file open/new, reference files added/removed, etc. It does not make sense for the App
    to be a dockable panel if it needs to be clsoed and re-opened to get updates.

    :param app: The parent App
    :type app: Application

    :return: True if App should be a dockable panel, else False if it should be a dialog.
    :rtype: bool
    """

    scene_operations_hook_path = app.get_setting("hook_scene_operations")
    scene_operations_hook = app.create_hook_instance(scene_operations_hook_path)

    return hasattr(scene_operations_hook, "register_scene_change_callback")
