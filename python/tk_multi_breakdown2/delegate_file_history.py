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
from sgtk.platform.qt import QtCore, QtGui

from .actions import ActionManager
from .file_model import FileModel
from .framework_qtwidgets import EditSelectedWidgetDelegate, ShotgunListWidget

# import the shotgun_model module from shotgunutils framework
shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model"
)


class FileHistoryDelegate(EditSelectedWidgetDelegate):
    """
    Delegate which 'glues up' the Details Widget with a QT View.
    """

    def __init__(self, view, file_view, file_model):
        """
        Class constructor.

        :param view:       The view where this delegate is being used
        :param file_view:  Main file view
        :param file_model: Model used by the main file view
        """
        self._left_corner = None
        self._right_corner = None
        self._body = None
        self._thumbnail = None
        self._file_view = file_view
        self._file_model = file_model

        EditSelectedWidgetDelegate.__init__(self, view)

    def set_formatting(
        self, left_corner=None, right_corner=None, body=None, thumbnail=True
    ):
        """
        Format the delegate to be able to render the data at the right place

        :param left_corner:  Content to display in the top left area of the item
        :param right_corner: Content to display in the top right area of the item
        :param body:         Content to display in the main area of the item
        :param thumbnail:    If True, the widget will display a thumbnail. If False, no thumbnail will be displayed
        """
        self._left_corner = left_corner
        self._right_corner = right_corner
        self._body = body
        self._thumbnail = thumbnail

    def _create_widget(self, parent):
        """
        Widget factory as required by base class. The base class will call this
        when a widget is needed and then pass this widget in to the various callbacks.

        :param parent: Parent object for the widget
        """
        widget = ShotgunListWidget(parent)
        widget.set_formatting(
            top_left=self._left_corner,
            top_right=self._right_corner,
            body=self._body,
            thumbnail=self._thumbnail,
        )
        return widget

    def _on_before_selection(self, widget, model_index, style_options):
        """
        Called when the associated widget is selected. This method
        implements all the setting up and initialization of the widget
        that needs to take place prior to a user starting to interact with it.

        :param widget: The widget to operate on (created via _create_widget)
        :param model_index: The model index to operate on
        :param style_options: QT style options
        """
        # do std drawing first
        self._on_before_paint(widget, model_index, style_options)

        # indicate to the widget that it is in a selected state
        widget.set_selected(True)

    def _on_before_paint(self, widget, model_index, style_options):
        """
        Called by the base class when the associated widget should be
        painted in the view. This method should implement setting of all
        static elements (labels, pixmaps etc) but not dynamic ones (e.g. buttons)

        :param widget: The widget to operate on (created via _create_widget)
        :param model_index: The model index to operate on
        :param style_options: QT style options
        """
        icon = shotgun_model.get_sanitized_data(model_index, QtCore.Qt.DecorationRole)
        widget.set_thumbnail(icon)

        # get the shotgun data
        sg_item = shotgun_model.get_sg_data(model_index)

        # fill the content of the widget with the data of the loaded Shotgun
        # item
        widget.set_text(sg_item)

        # add an action to update the file to this version
        selected_indexes = self._file_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            return
        model_index = selected_indexes[0]
        file_item_model = self._file_model.itemFromIndex(model_index)
        file_item = model_index.data(FileModel.FILE_ITEM_ROLE)
        q_action = ActionManager.add_update_to_specific_version_action((file_item, file_item_model), sg_item, None)
        widget.set_actions([q_action])

    def sizeHint(self, style_options, model_index):
        """
        Specify the size of the item.

        :param style_options: QT style options
        :param model_index: Model item to operate on
        """
        # ask the widget what size it takes
        return ShotgunListWidget.calculate_size()
