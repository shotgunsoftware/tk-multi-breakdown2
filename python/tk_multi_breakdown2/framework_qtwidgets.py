# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Wrapper for the various widgets used from frameworks so that they can be used
easily from within Qt Designer
"""

import sgtk

# Grouped list view, widget base class and delegates
views = sgtk.platform.import_framework("tk-framework-qtwidgets", "views")
GroupedItemView = views.GroupedItemView

delegates = sgtk.platform.import_framework("tk-framework-qtwidgets", "delegates")
ViewItemDelegate = delegates.ViewItemDelegate

# Shotgun formatted widget
shotgun_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_widget"
)
ShotgunFolderWidget = shotgun_widget.ShotgunFolderWidget

# Overlay widget
overlay_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "overlay_widget"
)
ShotgunOverlayWidget = overlay_widget.ShotgunOverlayWidget

utils = sgtk.platform.import_framework("tk-framework-qtwidgets", "utils")
