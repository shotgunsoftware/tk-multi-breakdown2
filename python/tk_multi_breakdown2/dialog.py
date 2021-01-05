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
from .file_history_model import FileHistoryModel
from .delegate_file_history import FileHistoryDelegate
from .actions import ActionManager
from .framework_qtwidgets import ShotgunOverlayWidget

task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager"
)
BackgroundTaskManager = task_manager.BackgroundTaskManager

shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)

settings = sgtk.platform.import_framework("tk-framework-shotgunutils", "settings")


class AppDialog(QtGui.QWidget):
    def __init__(self, parent=None):
        """
        :param parent: The parent QWidget for this control
        """

        QtGui.QWidget.__init__(self, parent)

        self._bundle = sgtk.platform.current_bundle()

        # create a single instance of the task manager that manages all
        # asynchronous work/tasks
        self._bg_task_manager = BackgroundTaskManager(self, max_threads=8)
        self._bg_task_manager.start_processing()

        shotgun_globals.register_bg_task_manager(self._bg_task_manager)

        # now load in the UI that was created in the UI designer
        self._ui = Ui_Dialog()
        self._ui.setupUi(self)

        # create a settings manager where we can pull and push prefs later
        # prefs in this manager are shared
        self._settings_manager = settings.UserSettings(self._bundle)

        # -----------------------------------------------------
        # main file view

        self._ui.file_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        self._ui.file_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._ui.file_view.customContextMenuRequested.connect(
            self._on_context_menu_requested
        )

        self._file_model = FileModel(self, self._bg_task_manager)
        self._ui.file_view.setModel(self._file_model)

        self._delegate = FileGroupDelegate(self._ui.file_view)
        self._ui.file_view.setItemDelegate(self._delegate)

        self._file_model_overlay = ShotgunOverlayWidget(self._ui.file_view)
        self._file_model_overlay.start_spin()
        self._file_model.files_processed.connect(self._file_model_overlay.hide)

        # -----------------------------------------------------
        # details view

        self._details_panel_visible = False

        # format the details main widget
        main_file_details_history_config = self._bundle.execute_hook_method(
            "hook_ui_configurations", "main_file_history_details"
        )
        self._ui.file_details.set_formatting(
            main_file_details_history_config.get("header"),
            main_file_details_history_config.get("body"),
            main_file_details_history_config.get("thumbnail"),
        )

        self._file_history_model = FileHistoryModel(self, self._bg_task_manager)

        self._file_history_proxy_model = QtGui.QSortFilterProxyModel(self)
        self._file_history_proxy_model.setSourceModel(self._file_history_model)

        # now use the proxy model to sort the data to ensure
        # higher version numbers appear earlier in the list
        # the history model is set up so that the default display
        # role contains the version number field in shotgun.
        # This field is what the proxy model sorts by default
        # We set the dynamic filter to true, meaning QT will keep
        # continously sorting. And then tell it to use column 0
        # (we only have one column in our models) and descending order.
        self._file_history_proxy_model.setDynamicSortFilter(True)
        self._file_history_proxy_model.sort(0, QtCore.Qt.DescendingOrder)

        self._ui.file_history_view.setModel(self._file_history_proxy_model)

        # setup a delegate
        self._file_history_delegate = FileHistoryDelegate(
            self._ui.file_history_view, self._ui.file_view, self._file_model
        )
        file_details_history_config = self._bundle.execute_hook_method(
            "hook_ui_configurations", "file_history_details"
        )
        self._file_history_delegate.set_formatting(
            file_details_history_config.get("top_left"),
            file_details_history_config.get("top_right"),
            file_details_history_config.get("body"),
            file_details_history_config.get("thumbnail"),
        )
        self._ui.file_history_view.setItemDelegate(self._file_history_delegate)

        self._ui.details_button.clicked.connect(self._toggle_details_panel)
        details_panel_visibility = self._settings_manager.retrieve(
            "details_panel_visibility", False
        )
        self._set_details_panel_visibility(details_panel_visibility)

        # -----------------------------------------------------

        # finally, update the UI by processing the files of the current scene
        self._file_model.process_files()

        # make this slot connection once the model has started processing files otherwise the selection model doesn't
        # exist
        file_view_selection_model = self._ui.file_view.selectionModel()
        if file_view_selection_model:
            file_view_selection_model.selectionChanged.connect(self._on_file_selection)

    def closeEvent(self, event):
        """
        Overriden method triggered when the widget is closed.  Cleans up as much as possible
        to help the GC.

        :param event: Close event
        """

        # clear the selection in the main views.
        # this is to avoid re-triggering selection
        # as items are being removed in the models
        #
        # note that we pull out a fresh handle to the selection model
        # as these objects sometimes are deleted internally in the view
        # and therefore persisting python handles may not be valid
        self._ui.file_view.selectionModel().clear()
        self._ui.file_history_view.selectionModel().clear()

        # clear up the various data models
        if self._file_model:
            self._file_model.destroy()

        if self._file_history_model:
            self._file_history_model.clear()

        # and shut down the task manager
        if self._bg_task_manager:
            shotgun_globals.unregister_bg_task_manager(self._bg_task_manager)
            self._bg_task_manager.shut_down()
            self._bg_task_manager = None

        return QtGui.QWidget.closeEvent(self, event)

    def _toggle_details_panel(self):
        """
        Slot triggered when someone clicks the show/hide details button
        """
        if self._ui.details_panel.isVisible():
            self._set_details_panel_visibility(False)
        else:
            self._set_details_panel_visibility(True)

    def _on_context_menu_requested(self, pnt):
        """
        Slot triggered when a context menu has been requested from one of the file views.  This
        will collect information about the item under the cursor and emit a file_context_menu_requested
        signal.

        :param pnt: The position for the context menu relative to the source widget
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
            file_model_item = self._file_model.itemFromIndex(i)
            file_item = i.data(FileModel.FILE_ITEM_ROLE)
            items.append((file_item, file_model_item))

        # map the point to a global position:
        pnt = self.sender().mapToGlobal(pnt)

        # build the context menu
        context_menu = QtGui.QMenu(self)

        # build the actions
        q_action = ActionManager.add_update_to_latest_action(items, context_menu)
        context_menu.addAction(q_action)

        context_menu.exec_(pnt)

    def _on_file_selection(self):
        """
        Slot triggered when a file is selected in the main view. This will collect details about the selected file in
        order to display them in the details panel.
        """

        selected_indexes = self._ui.file_view.selectionModel().selectedIndexes()
        self._setup_details_panel(selected_indexes)

    def _set_details_panel_visibility(self, visible):
        """
        Specifies if the details panel should be visible or not

        :param visible: Boolean to indicate whether the details panel should be visible or not
        """

        # hide details panel
        if not visible:
            self._details_panel_visible = False
            self._ui.details_panel.setVisible(False)
            self._ui.details_button.setText("Show Details")

        # show details panel
        else:

            self._details_panel_visible = True
            self._ui.details_panel.setVisible(True)
            self._ui.details_button.setText("Hide Details")

            # if there is something selected, make sure the detail
            # section is focused on this
            selection_model = self._ui.file_view.selectionModel()
            self._setup_details_panel(selection_model.selectedIndexes())

        self._settings_manager.store("details_panel_visibility", visible)

    def _setup_details_panel(self, selected_items):
        """
        Set up the details panel according to the selected items.

        :param selected_items:  Model indexes of the selected items.
        """

        def __clear_publish_history():
            """
            Helper method that clears the history view on the right hand side.
            """
            self._file_history_model.clear()
            self._ui.file_details.clear()

        if len(selected_items) != 1:
            __clear_publish_history()

        else:

            model_index = selected_items[0]
            file_item = model_index.data(FileModel.FILE_ITEM_ROLE)
            thumbnail = model_index.data(QtCore.Qt.DecorationRole)

            # display file item details
            self._ui.file_details.set_text(file_item.sg_data)
            self._ui.file_details.set_thumbnail(thumbnail)

            # load file history
            self._file_history_model.load_data(file_item.sg_data)
