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
