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


def show_dialog(app):
    """
    Show the main dialog ui

    :param app: The parent App
    """

    # defer imports so that the app works gracefully in batch modes
    from .dialog import AppDialog

    app.engine.show_dialog("Breakdown2", app, AppDialog)
