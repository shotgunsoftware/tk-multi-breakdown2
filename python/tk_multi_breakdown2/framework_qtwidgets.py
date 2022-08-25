# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

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
ThumbnailViewItemDelegate = delegates.ThumbnailViewItemDelegate

shotgun_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_widget"
)
ShotgunFolderWidget = shotgun_widget.ShotgunFolderWidget

overlay_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "overlay_widget"
)
ShotgunOverlayWidget = overlay_widget.ShotgunOverlayWidget

utils = sgtk.platform.import_framework("tk-framework-qtwidgets", "utils")

search_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "search_widget"
)
SearchWidget = search_widget.SearchWidget

models = sgtk.platform.import_framework("tk-framework-qtwidgets", "models")
HierarchicalFilteringProxyModel = models.HierarchicalFilteringProxyModel

filtering = sgtk.platform.import_framework("tk-framework-qtwidgets", "filtering")
FilterItem = filtering.FilterItem
FilterMenu = filtering.FilterMenu
FilterMenuButton = filtering.FilterMenuButton
FilterItemTreeProxyModel = filtering.FilterItemTreeProxyModel

sg_qicons = sgtk.platform.import_framework("tk-framework-qtwidgets", "sg_qicons")
SGQIcon = sg_qicons.SGQIcon
