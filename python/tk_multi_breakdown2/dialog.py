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
from sgtk.platform.qt import QtGui, QtCore

from .ui.dialog import Ui_Dialog
from .file_model import FileModel
from .delegate_file_group import FileGroupDelegate
from .actions import UpdateVersionAction
from .framework_qtwidgets import ShotgunSpinningWidget

task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager"
)
BackgroundTaskManager = task_manager.BackgroundTaskManager

shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)


class AppDialog(QtGui.QWidget):

    def __init__(self, parent=None):
        """
        :param parent: The parent QWidget for this control
        """

        QtGui.QWidget.__init__(self, parent)

        # create a single instance of the task manager that manages all
        # asynchronous work/tasks
        self._bg_task_manager = BackgroundTaskManager(self, max_threads=8)
        self._bg_task_manager.start_processing()

        shotgun_globals.register_bg_task_manager(self._bg_task_manager)

        # now load in the UI that was created in the UI designer
        self._ui = Ui_Dialog()
        self._ui.setupUi(self)

        # -----------------------------------------------------
        # main file view

        self._ui.file_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self._ui.file_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._ui.file_view.customContextMenuRequested.connect(self._on_context_menu_requested)

        self._file_model = FileModel(self._bg_task_manager, self)
        self._ui.file_view.setModel(self._file_model)

        self._delegate = FileGroupDelegate(self._ui.file_view)
        self._ui.file_view.setItemDelegate(self._delegate)

        self._file_model_overlay = ShotgunSpinningWidget(self._ui.file_view)
        self._file_model_overlay.start_spin()
        self._file_model.files_processed.connect(self._file_model_overlay.hide)

        # finally, update the UI by processing the files of the current scene
        self._file_model.process_files()

    def closeEvent(self, event):
        """
        Overriden method triggered when the widget is closed.  Cleans up as much as possible
        to help the GC.

        :param event:   Close event
        """

        # clear up the various data models
        if self._file_model:
            self._file_model.destroy()

        # and shut down the task manager
        if self._bg_task_manager:
            shotgun_globals.unregister_bg_task_manager(self._bg_task_manager)
            self._bg_task_manager.shut_down()
            self._bg_task_manager = None

        return QtGui.QWidget.closeEvent(self, event)

    def _on_context_menu_requested(self, pnt):
        """
        Slot triggered when a context menu has been requested from one of the file views.  This
        will collect information about the item under the cursor and emit a file_context_menu_requested
        signal.

        :param pnt:
        :return:
        """

        # get all the selected items
        selection_model = self._ui.file_view.selectionModel()
        if not selection_model:
            return

        indexes = selection_model.selectedIndexes()
        if len(indexes) == 0:
            return

        items = []
        for i in indexes:
            file_item_model = self._file_model.itemFromIndex(i)
            file_item = i.data(FileModel.FILE_ITEM_ROLE)
            items.append((file_item_model, file_item))

        # map the point to a global position:
        pnt = self.sender().mapToGlobal(pnt)

        # build the context menu
        context_menu = QtGui.QMenu(self)

        # build the actions
        action = UpdateVersionAction("Update to latest", items)

        q_action = QtGui.QAction(action.label, context_menu)
        q_action.triggered[()].connect(lambda checked=False: action.execute())
        context_menu.addAction(q_action)

        context_menu.exec_(pnt)
