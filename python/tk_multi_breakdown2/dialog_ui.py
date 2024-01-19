# Copyright (c) 2024 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from collections import namedtuple

from sgtk.platform.qt import QtCore, QtGui

from .framework_qtwidgets import (
    FilterMenuButton,
    GroupedItemView,
    ShotgunFolderWidget,
    SearchWidget,
    sg_qwidgets,
    SGQIcon,
)


class DialogUI:
    """The main App dialog UI."""

    ui_fields = [
        "file_view",
        "content_filter_widget",
        "content_filter_scroll_area",
        "details_splitter",
        "size_slider",
        "update_selected_button",
        "select_all_outdated_button",
        "details_panel",
        "file_details",
        "file_history_view",
        "details_button",
        "filter_btn",
        "thumbnail_view_btn",
        "list_view_btn",
        "grid_view_btn",
        "refresh_btn",
        "group_by_label",
        "group_by_combo_box",
        "search_widget",
    ]
    UI = namedtuple("UI", ui_fields)

    @staticmethod
    def ui(parent):
        """Return the UI components for the Dialog."""

        app_layout = QtGui.QVBoxLayout(parent)

        # Top toolbar
        top_toolbar_widget = QtGui.QWidget(parent)
        top_toolbar_layout = QtGui.QHBoxLayout(top_toolbar_widget)
        top_toolbar_layout.setSpacing(15)
        top_toolbar_layout.setContentsMargins(0, 0, 0, 5)
        # Refresh button
        refresh_btn = sg_qwidgets.SGQToolButton()
        refresh_btn.setObjectName("refresh_btn")
        refresh_btn.setIcon(SGQIcon.refresh())
        refresh_btn.setCheckable(True)
        top_toolbar_layout.addWidget(refresh_btn)
        # Group by label and combobox
        group_by_hlayout = QtGui.QHBoxLayout()
        group_by_hlayout.setSpacing(5)
        group_by_label = QtGui.QLabel("Group By:", top_toolbar_widget)
        group_by_hlayout.addWidget(group_by_label)
        group_by_combo_box = QtGui.QComboBox(top_toolbar_widget)
        group_by_hlayout.addWidget(group_by_combo_box)
        top_toolbar_layout.addLayout(group_by_hlayout)
        # Spacer
        spacer_item = QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum
        )
        top_toolbar_layout.addItem(spacer_item)
        # View mode buttons
        view_mode_hlayout = QtGui.QHBoxLayout()
        view_mode_hlayout.setSpacing(5)
        # Thumbnail
        thumbnail_view_btn = sg_qwidgets.SGQToolButton(top_toolbar_widget)
        thumbnail_view_btn.setObjectName("thumbnail_view_btn")
        thumbnail_view_btn.setIcon(SGQIcon.thumbnail_view_mode())
        thumbnail_view_btn.setCheckable(True)
        view_mode_hlayout.addWidget(thumbnail_view_btn)
        # List view
        list_view_btn = sg_qwidgets.SGQToolButton(top_toolbar_widget)
        list_view_btn.setObjectName("list_view_btn")
        list_view_btn.setIcon(SGQIcon.list_view_mode())
        list_view_btn.setCheckable(True)
        view_mode_hlayout.addWidget(list_view_btn)
        # Grid view
        grid_view_btn = sg_qwidgets.SGQToolButton(top_toolbar_widget)
        grid_view_btn.setObjectName("grid_view_btn")
        grid_view_btn.setIcon(SGQIcon.grid_view_mode())
        grid_view_btn.setCheckable(True)
        view_mode_hlayout.addWidget(grid_view_btn)
        # Add the button layout
        top_toolbar_layout.addLayout(view_mode_hlayout)
        # Search widget
        search_widget = SearchWidget(top_toolbar_widget)
        search_widget.setMaximumSize(QtCore.QSize(150, 16777215))
        top_toolbar_layout.addWidget(search_widget)
        # Filtering
        filter_btn = FilterMenuButton(top_toolbar_widget)
        filter_btn.setObjectName("filter_btn")
        filter_btn.setCheckable(True)
        filter_btn.setPopupMode(QtGui.QToolButton.InstantPopup)
        filter_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        top_toolbar_layout.addWidget(filter_btn)
        # Details
        details_button = sg_qwidgets.SGQToolButton(top_toolbar_widget)
        details_button.setObjectName("details_button")
        details_button.setText("")
        details_button.setIcon(SGQIcon.info())
        details_button.setCheckable(True)
        details_button.setAutoRaise(False)
        top_toolbar_layout.addWidget(details_button)
        #
        app_layout.addWidget(top_toolbar_widget)

        # Main content
        content_widget = QtGui.QWidget(parent)
        content_layout = QtGui.QVBoxLayout(content_widget)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        # content splitter
        details_splitter = QtGui.QSplitter(content_widget)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(details_splitter.sizePolicy().hasHeightForWidth())
        details_splitter.setSizePolicy(sizePolicy)
        details_splitter.setOrientation(QtCore.Qt.Horizontal)
        # filtering
        content_filter_widget = QtGui.QWidget()
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        content_filter_widget.setSizePolicy(sizePolicy)
        # filter widget layout
        content_filter_layout = QtGui.QVBoxLayout(content_filter_widget)
        content_filter_layout.setSpacing(0)
        content_filter_layout.setContentsMargins(0, 0, 0, 0)
        # filter scroll area
        content_filter_scroll_area = QtGui.QScrollArea(details_splitter)
        content_filter_scroll_area.setObjectName("content_filter_scroll_area")
        content_filter_scroll_area.setWidgetResizable(True)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        content_filter_scroll_area.setSizePolicy(sizePolicy)
        content_filter_scroll_area.setWidget(content_filter_widget)
        # list view
        file_view = GroupedItemView(details_splitter)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(file_view.sizePolicy().hasHeightForWidth())
        file_view.setSizePolicy(sizePolicy)
        # details
        details_panel = QtGui.QGroupBox(details_splitter)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(details_panel.sizePolicy().hasHeightForWidth())
        details_panel.setSizePolicy(sizePolicy)
        details_panel.setMinimumSize(QtCore.QSize(300, 0))
        details_panel.setMaximumSize(QtCore.QSize(16777215, 16777215))
        details_panel.setTitle("")
        details_vlayout = QtGui.QVBoxLayout(details_panel)
        details_vlayout.setContentsMargins(0, 0, 0, 0)
        details_vlayout.setSpacing(0)
        file_details = ShotgunFolderWidget(details_panel)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(file_details.sizePolicy().hasHeightForWidth())
        file_details.setSizePolicy(sizePolicy)
        file_details.setMinimumSize(QtCore.QSize(250, 0))
        details_vlayout.addWidget(file_details)
        file_history_view = QtGui.QListView(details_panel)
        file_history_view.setUniformItemSizes(True)
        file_history_view.setLayoutMode(QtGui.QListView.Batched)
        file_history_view.setBatchSize(25)
        file_history_view.setResizeMode(QtGui.QListView.Adjust)
        details_vlayout.addWidget(file_history_view)
        content_layout.addWidget(details_splitter)

        app_layout.addWidget(content_widget)

        # Bottom toolbar
        bottom_toolbar_widget = QtGui.QWidget(parent)
        bottom_toolbar_layout = QtGui.QHBoxLayout(bottom_toolbar_widget)

        # slider
        size_slider = QtGui.QSlider(bottom_toolbar_widget)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(size_slider.sizePolicy().hasHeightForWidth())
        size_slider.setSizePolicy(sizePolicy)
        size_slider.setMinimumSize(QtCore.QSize(150, 0))
        size_slider.setMinimum(20)
        size_slider.setMaximum(300)
        size_slider.setOrientation(QtCore.Qt.Horizontal)
        # TODO move to style sheet .qss
        size_slider.setStyleSheet(
            " QSlider::handle:horizontal {\n"
            # "    border: 1px solid palette(base);\n"
            # "     border-radius: 3px;\n"
            "     width: 8px;\n"
            # "     background: palette(light);\n"
            " }"
        )
        bottom_toolbar_layout.addWidget(size_slider)
        # spacer
        bottom_spacer_item = QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum
        )
        bottom_toolbar_layout.addItem(bottom_spacer_item)
        # select all outdated
        select_all_outdated_button = sg_qwidgets.SGQPushButton(
            "Select All Outdated", bottom_toolbar_widget
        )
        select_all_outdated_button.setMinimumSize(QtCore.QSize(125, 0))
        bottom_toolbar_layout.addWidget(select_all_outdated_button)
        # update selected
        update_selected_button = sg_qwidgets.SGQPushButton(
            "Update Selected", bottom_toolbar_widget
        )
        update_selected_button.setMinimumSize(QtCore.QSize(125, 0))
        bottom_toolbar_layout.addWidget(update_selected_button)

        app_layout.addWidget(bottom_toolbar_widget)

        return DialogUI.UI(
            file_view=file_view,
            content_filter_widget=content_filter_widget,
            content_filter_scroll_area=content_filter_scroll_area,
            details_splitter=details_splitter,
            thumbnail_view_btn=thumbnail_view_btn,
            grid_view_btn=grid_view_btn,
            list_view_btn=list_view_btn,
            filter_btn=filter_btn,
            details_button=details_button,
            details_panel=details_panel,
            file_details=file_details,
            file_history_view=file_history_view,
            size_slider=size_slider,
            update_selected_button=update_selected_button,
            select_all_outdated_button=select_all_outdated_button,
            refresh_btn=refresh_btn,
            group_by_label=group_by_label,
            group_by_combo_box=group_by_combo_box,
            search_widget=search_widget,
        )
