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

from .file_model import FileModel
from .framework_qtwidgets import GroupedListViewItemDelegate, GroupWidgetBase, ShotgunListWidget
from .ui.file_group_widget import Ui_FileGroupWidget
from .ui.file_widget import Ui_FileWidget

shotgun_model = sgtk.platform.import_framework("tk-framework-shotgunutils", "shotgun_model")


class FileWidget(QtGui.QWidget):
    """
    """

    def __init__(self, parent):
        """
        :param parent:
        """
        QtGui.QWidget.__init__(self, parent)

        self._bundle = sgtk.platform.current_bundle()

        # setup the ui
        self._ui = Ui_FileWidget()
        self._ui.setupUi(self)

        self._ui.shotgun_widget._ui.box.setFrameShape(QtGui.QFrame.NoFrame)
        self._ui.shotgun_widget._ui.box.setFrameShadow(QtGui.QFrame.Raised)

    def set_formatting(self):
        """
        :return:
        """
        file_item_config = self._bundle.execute_hook_method("hook_ui_configurations", "file_item_details")
        self._ui.shotgun_widget.set_formatting(
            file_item_config.get("top_left"),
            file_item_config.get("top_right"),
            file_item_config.get("body"),
            file_item_config.get("thumbnail")
        )

    def set_thumbnail(self, thumbnail):
        """
        :return:
        """
        self._ui.shotgun_widget.set_thumbnail(thumbnail)

    def set_text(self, sg_data):
        """
        :param text:
        :return:
        """
        self._ui.shotgun_widget.set_text(sg_data)

    def replace_extra_key(self, key_name, key_value):
        """
        :return:
        """
        self._ui.shotgun_widget.replace_extra_key(key_name, key_value)

    def set_selected(self, selected):
        """
        :param selected:
        :return:
        """
        if selected:
            self._ui.frame.setStyleSheet(
                """#frame {border-width: 2px;
                                                 border-color: %s;
                                                 border-style: solid;
                                                 background-color: %s}
                                      """
                % (self._ui.shotgun_widget._highlight_str, self._ui.shotgun_widget._transp_highlight_str)
            )
        else:
            self._ui.frame.setStyleSheet("")

    def set_state(self, up_to_date):
        """
        :param up_to_date:
        :return:
        """
        if up_to_date:
            self._ui.icon.setPixmap(QtGui.QPixmap(":/tk-multi-breakdown2/green_bullet.png"))
        else:
            self._ui.icon.setPixmap(QtGui.QPixmap(":/tk-multi-breakdown2/red_bullet.png"))


class FileGroupWidget(GroupWidgetBase):
    """
    """

    def __init__(self, parent):
        """
        """
        GroupWidgetBase.__init__(self, parent)

        # setup the UI
        self._ui = Ui_FileGroupWidget()
        self._ui.setupUi(self)

        # widget signal/slot connections
        self._ui.expand_check_box.stateChanged.connect(
            self._on_expand_checkbox_state_changed
        )

    def set_item(self, model_idx):
        """
        """
        group_name = str(model_idx.data(QtCore.Qt.DisplayRole))
        self._ui.header.setText(group_name)

    def set_expanded(self, expand=True):
        """
        """
        if (self._ui.expand_check_box.checkState() == QtCore.Qt.Checked) != expand:
            self._ui.expand_check_box.setCheckState(
                QtCore.Qt.Checked if expand else QtCore.Qt.Unchecked
            )

    def _on_expand_checkbox_state_changed(self, state):
        """
        """
        self.toggle_expanded.emit(state != QtCore.Qt.Unchecked)


class FileGroupDelegate(GroupedListViewItemDelegate):
    """
    """

    def __init__(self, view):
        """
        :param view:
        """
        GroupedListViewItemDelegate.__init__(self, view)

        self._item_widget = None

    def create_group_widget(self, parent):
        """
        :param parent:
        :return:
        """
        return FileGroupWidget(parent)

    def _get_painter_widget(self, model_index, parent):
        """
        """
        if not model_index.isValid():
            return None
        if not self._item_widget:
            self._item_widget = FileWidget(parent)
            self._item_widget.set_formatting()
        return self._item_widget

    def _on_before_paint(self, widget, model_index, style_options):
        """
        Overriden method called before painting to allow the delegate to set up the
        widget for the specified model index.

        :param widget:          The widget that will be used to paint with
        :param model_index:     The QModelIndex representing the index in the model that is
                                being painted
        :param style_options:   The style options that should be used to paint the widget for
                                the index
        """

        if not isinstance(widget, FileWidget):
            # this class only paints ShotgunListWidget widgets
            return

        thumbnail = model_index.data(QtCore.Qt.DecorationRole)
        widget.set_thumbnail(thumbnail)

        item_data = model_index.data(FileModel.FILE_ITEM_ROLE)

        widget.set_text(item_data.sg_data)

        # here is a special case where we need to replace some app settings by their values
        for n in ["NODE_NAME", "PATH"]:
            widget.replace_extra_key(n, getattr(item_data, n.lower()))

        # apply widget selection style
        widget.set_selected(
            (
                style_options.state & QtGui.QStyle.State_Selected
            ) == QtGui.QStyle.State_Selected
        )

        # update icon
        if item_data.highest_version:
            widget.set_state(item_data.sg_data["version_number"] >= item_data.highest_version)
        else:
            widget.set_state(False)

    def sizeHint(self, style_options, model_index):
        """
        """
        if not model_index.isValid():
            return QtCore.QSize()

        if model_index.parent() != self.view.rootIndex():
            return self._get_painter_widget(model_index, self.view).size()
        else:
            # call base class:
            return GroupedListViewItemDelegate.sizeHint(
                self, style_options, model_index
            )
