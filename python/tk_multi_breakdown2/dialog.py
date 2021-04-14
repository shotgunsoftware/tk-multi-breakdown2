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
from .ui import resources_rc  # Required for creating icons

from .file_model import FileModel
from .file_history_model import FileHistoryModel
from .actions import ActionManager
from .framework_qtwidgets import (
    ShotgunOverlayWidget,
    ViewItemDelegate,
    ThumbnailViewItemDelegate,
    utils,
)
from .tree_proxy_model import TreeProxyModel, FilterItem

task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager"
)
BackgroundTaskManager = task_manager.BackgroundTaskManager

shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)

settings = sgtk.platform.import_framework("tk-framework-shotgunutils", "settings")


class AppDialog(QtGui.QWidget):
    """
    The main App dialog.
    """

    # Settings keys
    VIEW_MODE_SETTING = "view_mode"
    LIST_SIZE_SCALE_VALUE = "view_item_list_size_scale"
    GRID_SIZE_SCALE_VALUE = "view_item_grid_size_scale"
    THUMBNAIL_SIZE_SCALE_VALUE = "view_item_thumb_size_scale"
    DETAILS_PANEL_VISIBILITY_SETTING = "details_panel_visibility"

    (
        THUMBNAIL_VIEW_MODE,
        LIST_VIEW_MODE,
        GRID_VIEW_MODE,
    ) = range(3)

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
        self._file_proxy_model = TreeProxyModel(self)
        self._file_proxy_model.setSourceModel(self._file_model)
        self._ui.file_view.setModel(self._file_proxy_model)

        # Filter Items
        self._node_name_filter = FilterItem(
            FilterItem.TYPE_REGEX_STR,
            FilterItem.OP_IN,
            FileModel.FILE_ITEM_NODE_NAME_ROLE,
        )

        self._file_model_overlay = ShotgunOverlayWidget(self._ui.file_view)
        self._file_model_overlay.start_spin()
        self._file_model.files_processed.connect(self._file_model_overlay.hide)

        list_view_icon = QtGui.QIcon(":/tk-multi-breakdown2/mode_switch_card.png")
        list_view_icon.addPixmap(
            QtGui.QPixmap(":/tk-multi-breakdown2/mode_switch_card_active.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On,
        )
        self._ui.list_view_btn.setIcon(list_view_icon)

        grid_view_icon = QtGui.QIcon(":/tk-multi-breakdown2/mode_switch_thumb.png")
        grid_view_icon.addPixmap(
            QtGui.QPixmap(":/tk-multi-breakdown2/mode_switch_thumb_active.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On,
        )
        self._ui.grid_view_btn.setIcon(grid_view_icon)

        file_view_icon = QtGui.QIcon(":/tk-multi-breakdown2/mode_switch_thumb.png")
        file_view_icon.addPixmap(
            QtGui.QPixmap(":/tk-multi-breakdown2/mode_switch_thumb_active.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On,
        )
        self._ui.file_view_btn.setIcon(file_view_icon)

        # Enable mouse tracking to allow the delegate to receive mouse events
        self._ui.file_view.setMouseTracking(True)

        # Create a delegate for the file view. Set the row width to None
        file_item_delegate = self._create_file_item_delegate(
            set_delegate=False, thumbnail=True
        )
        # Create a delegate for the list view. Set the row width to -1 will expand each item row
        # to the full available width and thus display one item per row in a "list" view.
        list_item_delegate = self._create_file_item_delegate(set_delegate=False)

        # TODO: more advanced filtering - for now there is only a simple text filter on the item's displayed text
        self._display_text_filter = FilterItem(
            FilterItem.TYPE_REGEX_STR,
            FilterItem.OP_IN,
            data_func=list_item_delegate.get_displayed_text,
        )

        # Set up the view modes
        self.view_modes = [
            {
                "mode": self.THUMBNAIL_VIEW_MODE,
                "button": self._ui.file_view_btn,
                "delegate": file_item_delegate,
                "slider_value": self._settings_manager.retrieve(
                    self.THUMBNAIL_SIZE_SCALE_VALUE, 100
                ),
            },
            {
                "mode": self.GRID_VIEW_MODE,
                "button": self._ui.grid_view_btn,
                "delegate": list_item_delegate,
                "slider_value": self._settings_manager.retrieve(
                    self.GRID_SIZE_SCALE_VALUE, 100
                ),
            },
            {
                "mode": self.LIST_VIEW_MODE,
                "button": self._ui.list_view_btn,
                "delegate": list_item_delegate,
                "slider_value": self._settings_manager.retrieve(
                    self.LIST_SIZE_SCALE_VALUE, 100
                ),
            },
        ]
        for i, view_mode in enumerate(self.view_modes):
            view_mode["button"].clicked.connect(
                lambda checked=False, mode=i: self._set_view_mode(mode)
            )

        self._ui.size_slider.valueChanged.connect(self._on_view_item_size_slider_change)

        self._ui.select_all_outdated_button.clicked.connect(
            self._on_select_all_outdated
        )
        self._ui.update_selected_button.clicked.connect(self._on_update_selected)

        self._ui.search_widget.set_placeholder_text("Search Files")
        self._ui.search_widget.search_edited.connect(self._on_search_widget_edited)

        # Get the last view mode used from the settings manager, default to the first view if
        # no settings found
        cur_view_mode = self._settings_manager.retrieve(self.VIEW_MODE_SETTING, 0)
        self._set_view_mode(cur_view_mode)

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

        self._create_file_history_item_delegate()
        self._ui.file_history_view.setMouseTracking(True)

        details_icon = QtGui.QIcon(":/tk-multi-breakdown2/info-inactive@2x.png")
        details_icon.addPixmap(
            QtGui.QPixmap(":/tk-multi-breakdown2/info-active@2x.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On,
        )
        self._ui.details_button.setIcon(details_icon)
        self._ui.details_button.clicked.connect(self._toggle_details_panel)
        details_panel_visibility = self._settings_manager.retrieve(
            self.DETAILS_PANEL_VISIBILITY_SETTING, False
        )
        self._set_details_panel_visibility(details_panel_visibility)

        # -----------------------------------------------------

        # finally, update the UI by processing the files of the current scene
        self._file_model.process_files()

        # make this slot connection once the model has started processing files otherwise the
        # selection model doesn't exist
        file_view_selection_model = self._ui.file_view.selectionModel()
        if file_view_selection_model:
            file_view_selection_model.selectionChanged.connect(self._on_file_selection)

        # -----------------------------------------------------
        # Log metric for app usage
        self._bundle._log_metric_viewed_app()

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

        self._ui.file_view.setItemDelegate(None)
        for view_mode in self.view_modes:
            delegate = view_mode.get("delegate")
            if delegate:
                delegate.setParent(None)
                delegate.deleteLater()
                delegate = None

        file_history_delegate = self._ui.file_history_view.itemDelegate()
        self._ui.file_history_view.setItemDelegate(None)
        file_history_delegate.setParent(None)
        file_history_delegate.deleteLater()
        file_history_delegate = None

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

    def _on_view_item_size_slider_change(self, value):
        """
        Slot triggered on the view item size slider value changed.

        :param value: The value of the slider.
        :return: None
        """

        for view_mode in self.view_modes:
            delegate = view_mode["delegate"]

            if view_mode["button"].isChecked():
                view_mode["slider_value"] = value

                if view_mode["mode"] == self.THUMBNAIL_VIEW_MODE:
                    width = value * (16 / 9.0)
                    delegate.thumbnail_size = QtCore.QSize(width, value)
                    self._settings_manager.store(self.THUMBNAIL_SIZE_SCALE_VALUE, value)

                elif view_mode["mode"] == self.LIST_VIEW_MODE:
                    delegate.item_height = value
                    delegate.item_width = -1
                    self._settings_manager.store(self.LIST_SIZE_SCALE_VALUE, value)

                elif view_mode["mode"] == self.GRID_VIEW_MODE:
                    delegate.item_height = None
                    delegate.item_width = value * 2
                    self._settings_manager.store(self.GRID_SIZE_SCALE_VALUE, value)

        self._ui.file_view._update_all_item_info = True
        self._ui.file_view.viewport().update()

    def _on_context_menu_requested(self, pnt):
        """
        Slot triggered when a context menu has been requested from one of the file views.
        Call the method to show the context menu.

        :param pnt: The position for the context menu relative to the source widget.
        """

        self._show_context_menu(self.sender(), pnt)

    def _actions_menu_requested(self, view, index, pos):
        """
        Callback triggered when a view item's action menu is requested to be shown.
        This will clear and select the given index, and show the item's actions menu.

        :param view: The view the item belongs to.
        :type view: :class:`GroupItemView`
        :param index: The index of the item.
        :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`
        :param pos: The position that the menu should be displayed at.
        :type pos: :class:`sgtk.platform.qt.QtCore.QPoint`

        :return: None
        """

        selection_model = view.selectionModel()
        if selection_model:
            view.selectionModel().select(
                index, QtGui.QItemSelectionModel.ClearAndSelect
            )

        self._show_context_menu(view, pos)

    def _show_context_menu(self, widget, pnt):
        """
        Show a context menu for the selected items.

        :param widget: The source widget.
        :param pnt: The position for the context menu relative to the source widget.
        """

        # get all the selected items
        selection_model = self._ui.file_view.selectionModel()
        if not selection_model:
            return

        indexes = selection_model.selectedIndexes()
        if not indexes:
            return

        items = []
        for index in indexes:
            if isinstance(index.model(), QtGui.QSortFilterProxyModel):
                index = index.model().mapToSource(index)

            file_model_item = index.model().itemFromIndex(index)
            file_item = index.data(FileModel.FILE_ITEM_ROLE)
            items.append((file_item, file_model_item))

        # map the point to a global position:
        pnt = widget.mapToGlobal(pnt)

        # build the context menu
        context_menu = QtGui.QMenu(self)

        # build the actions
        q_action = ActionManager.add_update_to_latest_action(items, context_menu)
        context_menu.addAction(q_action)

        context_menu.exec_(pnt)

    def _show_history_item_context_menu(self, view, index, pos):
        """
        Create and show the menu item actions for a history file item.

        :param index: The file history item model index.
        :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`
        :param pos: The mouse position, relative to the view, when the action was triggered.
        :type pos: :class:`sgtk.platform.qt.QtCore.QPoint`.
        :param view: The view (self._ui.file_history_view) that this index belongs to.
        :type view: :class:`sgtk.platform.qt.QtGui.QListView`
        :return: None
        """

        actions = []

        # Clear and set the current selection
        self._ui.file_history_view.selectionModel().select(
            index, QtGui.QItemSelectionModel.ClearAndSelect
        )

        # Get the selected file items from the main view
        selected_indexes = self._ui.file_view.selectionModel().selectedIndexes()

        if selected_indexes:
            # Get the currently selected file item to be updated.
            update_item_index = selected_indexes[0]
            if isinstance(update_item_index.model(), QtGui.QSortFilterProxyModel):
                update_item_index = update_item_index.model().mapToSource(
                    update_item_index
                )
            item_to_update = update_item_index.model().itemFromIndex(update_item_index)
            file_item_to_update = update_item_index.data(FileModel.FILE_ITEM_ROLE)

            # Get the data from the file history item to update the selected file item with. The index
            # passed in references the file history item.
            if isinstance(index.model(), QtGui.QSortFilterProxyModel):
                index = index.model().mapToSource(index)
            history_item = index.model().itemFromIndex(index)
            sg_data = history_item.get_sg_data()

            update_action = ActionManager.add_update_to_specific_version_action(
                (file_item_to_update, item_to_update), sg_data, None
            )
            actions.append(update_action)

        if not actions:
            no_action = QtGui.QAction("No Actions")
            no_action.setEnabled(False)
            actions.append(no_action)

        menu = QtGui.QMenu()
        menu.addActions(actions)
        menu.exec_(view.mapToGlobal(pos))

    def _on_file_selection(self):
        """
        Slot triggered when selection changed in the main view. This will collect details about
        the selected file in order to display them in the details panel.
        """

        selected_indexes = self._ui.file_view.selectionModel().selectedIndexes()
        self._setup_details_panel(selected_indexes)

    def _set_details_panel_visibility(self, visible):
        """
        Specifies if the details panel should be visible or not

        :param visible: Boolean to indicate whether the details panel should be visible or not
        """

        self._details_panel_visible = visible
        self._ui.details_panel.setVisible(visible)
        self._ui.details_button.setChecked(visible)

        if visible:
            # Set up the details panel with the current selection.
            selection_model = self._ui.file_view.selectionModel()
            self._setup_details_panel(selection_model.selectedIndexes())

        self._settings_manager.store(self.DETAILS_PANEL_VISIBILITY_SETTING, visible)

    def _setup_details_panel(self, selected_items):
        """
        Set up the details panel according to the selected items.

        :param selected_items:  Model indexes of the selected items.
        """

        if not selected_items or len(selected_items) > 1:
            # Clear the details when there is no selection, or multiple items selected.
            self._clear_details_panel()

        else:
            model_index = selected_items[0]
            file_item = model_index.data(FileModel.FILE_ITEM_ROLE)
            thumbnail = model_index.data(QtCore.Qt.DecorationRole)

            # display file item details
            self._ui.file_details.set_text(file_item.sg_data)
            self._ui.file_details.set_thumbnail(thumbnail)

            # load file history
            self._file_history_model.load_data(file_item)

    def _clear_details_panel(self):
        """
        Clear the details panel.
        """

        self._file_history_model.clear()
        self._ui.file_details.clear()

    def _set_view_mode(self, mode_index):
        """
        Sets up the view mode for the UI `file_view`.

        :param mode_index: The view mode index to set the view to.
        :type mode_index: int
        :return: None
        """

        assert 0 <= mode_index < len(self.view_modes), "Undefined view mode"

        for i, view_mode in enumerate(self.view_modes):
            is_cur_mode = i == mode_index
            view_mode["button"].setChecked(is_cur_mode)

            if is_cur_mode:
                delegate = view_mode["delegate"]
                self._ui.file_view.setItemDelegate(view_mode["delegate"])

                if view_mode["mode"] == self.LIST_VIEW_MODE:
                    delegate.scale_thumbnail_to_item_height(2.0)
                    delegate.text_role = FileModel.VIEW_ITEM_TEXT_ROLE

                elif view_mode["mode"] == self.GRID_VIEW_MODE:
                    delegate.thumbnail_width = 164
                    delegate.scale_thumbnail_to_item_height(None)
                    delegate.text_role = FileModel.VIEW_ITEM_TEXT_ROLE

                elif view_mode["mode"] == self.THUMBNAIL_VIEW_MODE:
                    delegate.text_role = FileModel.VIEW_ITEM_SHORT_TEXT_ROLE

                # Get the value to set the slider to, once all views have been updated.
                slider_value = view_mode.get(
                    "slider_value", self._ui.size_slider.value()
                )

        # Set the slider value for the current view, this will also update the viewport.
        self._ui.size_slider.setValue(slider_value)

        self._settings_manager.store(self.VIEW_MODE_SETTING, mode_index)

    def _on_select_all_outdated(self):
        """
        Callback triggered when the "Select all Outdated" button is clicked. This will
        select all items in the file view that are not using the latest version.
        """

        selection_model = self._ui.file_view.selectionModel()
        if not selection_model:
            return

        selection_model.clearSelection()

        outdated_selection = QtGui.QItemSelection()
        group_rows = self._file_model.rowCount()

        for group_row in range(group_rows):
            group_item = self._file_model.item(group_row, 0)
            file_item_rows = group_item.rowCount()
            for file_item_row in range(file_item_rows):
                file_item = group_item.child(file_item_row)

                if (
                    file_item.data(FileModel.STATUS_ROLE)
                    == FileModel.STATUS_OUT_OF_SYNC
                ):
                    index = file_item.index()
                    proxy_index = self._file_proxy_model.mapFromSource(index)
                    outdated_selection.select(proxy_index, proxy_index)

        if outdated_selection.indexes():
            selection_model.select(outdated_selection, QtGui.QItemSelectionModel.Select)
            self._ui.file_view.scrollTo(outdated_selection.indexes()[0])

    def _on_update_selected(self):
        """
        Callback triggere when the "Update Selected" button is clicked. This will update
        all selected items to the latest version.
        """

        selection_model = self._ui.file_view.selectionModel()
        if not selection_model:
            return

        file_items = []
        indexes = selection_model.selectedIndexes()
        for index in indexes:
            if isinstance(index.model(), QtGui.QSortFilterProxyModel):
                index = index.model().mapToSource(index)
            file_item = index.data(FileModel.FILE_ITEM_ROLE)
            file_model_item = index.model().itemFromIndex(index)
            file_items.append((file_item, file_model_item))

        ActionManager.execute_update_to_latest_action(file_items)

    def _on_search_widget_edited(self, search_text):
        """
        Slot triggered when the search text has been changed.

        :param search_text: The new search text
        """

        self._display_text_filter.filter_value = QtCore.QRegularExpression(
            search_text, QtCore.QRegularExpression.CaseInsensitiveOption
        )
        self._file_proxy_model.filter_items = [self._display_text_filter]

    def _create_file_item_delegate(self, set_delegate=True, thumbnail=False):
        """
        Create and set up a :class:`ViewItemDelegate` object for the File view.

        :return: The created delegate.
        :rtype: :class:`ViewItemDelegate`
        """

        # The view (self._ui.file_view) passed to the ViewItemDelegate constructor must be a
        # instance of subclass QAbstractItemView.
        if thumbnail:
            delegate = ThumbnailViewItemDelegate(self._ui.file_view)
            delegate.thumbnail_size = QtCore.QSize(164, 128)
            delegate.text_padding = ViewItemDelegate.Padding(4, 7, 4, 7)

        else:
            delegate = ViewItemDelegate(self._ui.file_view)
            delegate.text_padding = ViewItemDelegate.Padding(5, 7, 7, 7)

        # Set the delegate model data roles
        delegate.thumbnail_role = FileModel.VIEW_ITEM_THUMBNAIL_ROLE
        delegate.header_role = FileModel.VIEW_ITEM_HEADER_ROLE
        delegate.subtitle_role = FileModel.VIEW_ITEM_SUBTITLE_ROLE
        delegate.text_role = FileModel.VIEW_ITEM_TEXT_ROLE
        delegate.expand_role = FileModel.VIEW_ITEM_EXPAND_ROLE
        delegate.width_role = FileModel.VIEW_ITEM_WIDTH_ROLE
        delegate.height_role = FileModel.VIEW_ITEM_HEIGHT_ROLE
        delegate.loading_role = FileModel.VIEW_ITEM_LOADING_ROLE
        delegate.separator_role = FileModel.VIEW_ITEM_SEPARATOR_ROLE

        # Create an icon for the expand header action
        expand_icon = QtGui.QIcon(":/tk-multi-breakdown2/tree_arrow_expanded.png")
        expand_icon.addPixmap(
            QtGui.QPixmap(":/tk-multi-breakdown2/tree_arrow_collapsed.png"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On,
        )

        # Add LEFT side actions: group header expand and status icon
        delegate.add_actions(
            [
                {
                    "icon": expand_icon,
                    "show_always": True,
                    "padding": 0,
                    "features": QtGui.QStyleOptionButton.Flat,
                    "get_data": get_expand_action_data,
                    "callback": lambda view, index, pos: view.toggle_expand(index),
                },
                {
                    "icon": QtGui.QIcon(),  # The get_data callback will set the icon based on status.
                    "icon_size": QtCore.QSize(20, 20),
                    "show_always": True,
                    "padding": 0,
                    "features": QtGui.QStyleOptionButton.Flat,
                    "get_data": get_thumbnail_header_status_action_data
                    if thumbnail
                    else get_status_action_data,
                },
            ],
            ViewItemDelegate.LEFT,
        )
        # Add the menu actions buton on top right
        delegate.add_action(
            {
                "icon": QtGui.QIcon(":/tk-multi-breakdown2/tree_arrow_expanded.png"),
                "padding": 0,
                "callback": self._actions_menu_requested,
            },
            ViewItemDelegate.TOP_RIGHT,
        )
        if thumbnail:
            # Thumbnail delegate specifc actions
            # Add status icon to top left for non gorup header items
            delegate.add_action(
                {
                    "icon": QtGui.QIcon(),  # The get_data callback will set the icon based on status.
                    "icon_size": QtCore.QSize(20, 20),
                    "show_always": True,
                    "padding": 0,
                    "features": QtGui.QStyleOptionButton.Flat,
                    "get_data": get_thumbnail_status_action_data,
                },
                ViewItemDelegate.TOP_LEFT,
            )
        else:
            # Non-thumbnail specific actions
            # Add non-actionable item to display the created timestamp
            delegate.add_action(
                {
                    "name": "",  # The get_data callback will set the text.
                    "show_always": True,
                    "features": QtGui.QStyleOptionButton.Flat,
                    "get_data": get_timestamp_action_data,
                },
                ViewItemDelegate.RIGHT,
            )

        if set_delegate:
            self._ui.file_view.setItemDelegate(delegate)

        return delegate

    def _create_file_history_item_delegate(self, set_delegate=True):
        """
        Create and set up a :class:`ViewItemDelegate` object for the File History view.

        :param set_delegate: If True, set the delegate on the file history view.
        :type set_delegate: bool (default=True)
        :return: The created delegate.
        :rtype: :class:`ViewItemDelegate`
        """

        # The view (self._ui.file_history_view) passed to the ViewItemDelegate constructor must be a
        # instance of subclass QAbstractItemView.
        delegate = ViewItemDelegate(self._ui.file_history_view)

        # Set the delegate model data roles
        delegate.thumbnail_role = FileHistoryModel.VIEW_ITEM_THUMBNAIL_ROLE
        delegate.header_role = FileHistoryModel.VIEW_ITEM_HEADER_ROLE
        delegate.subtitle_role = FileHistoryModel.VIEW_ITEM_SUBTITLE_ROLE
        delegate.text_role = FileHistoryModel.VIEW_ITEM_TEXT_ROLE
        delegate.icon_role = FileHistoryModel.VIEW_ITEM_ICON_ROLE
        delegate.separator_role = FileHistoryModel.VIEW_ITEM_SEPARATOR_ROLE

        # Override tooltips applied to model items outside of the delegate.
        delegate.override_item_tooltip = True

        # Set up delegaet styling
        delegate.item_padding = 4
        delegate.text_padding = ViewItemDelegate.Padding(4, 4, 4, 7)
        delegate.thumbnail_padding = ViewItemDelegate.Padding(4, 0, 4, 4)
        # Set the thumbnail width to ensure text aligns between rows.
        delegate.thumbnail_width = 64

        # Add the menu actions button.
        delegate.add_action(
            {
                "icon": QtGui.QIcon(":/tk-multi-breakdown2/tree_arrow_expanded.png"),
                "padding": 0,
                "callback": self._show_history_item_context_menu,
            },
            ViewItemDelegate.FLOAT_TOP_RIGHT,
        )

        if set_delegate:
            self._ui.file_history_view.setItemDelegate(delegate)

        return delegate


######################################################################################################
# ViewItemDelegate action callbacks


def get_expand_action_data(parent, index):
    """
    Return the action data for the group header expand action, and for the given index.
    This data will determine how the action is displayed for the index.

    :param parent: This is the parent of the :class:`ViewItemDelegate`, which is the file view.
    :type parent: :class:`GroupItemView`
    :param index: The index the action is for.
    :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`
    :return: The data for the action and index.
    :rtype: dict, e.g.:
        {
            "visible": bool  # Flag indicating whether the action is displayed or not
            "state": :class:`sgtk.platform.qt.QtGui.QStyle.StateFlag`  # Flag indicating state of the icon
                                                                       # e.g. enabled/disabled, on/off, etc.
            "name": str # Override the default action name for this index
        }
    """

    visible = not index.parent().isValid()
    state = QtGui.QStyle.State_Active | QtGui.QStyle.State_Enabled

    if parent.is_expanded(index):
        state |= QtGui.QStyle.State_Off
    else:
        state |= QtGui.QStyle.State_On

    return {"visible": visible, "state": state}


def get_thumbnail_header_status_action_data(parent, index):
    """
    Return the action data for the status action icon, and for the given index.
    This data will determine how the action icon is displayed for the index.

    :param parent: This is the parent of the :class:`ViewItemDelegate`, which is the file view.
    :type parent: :class:`GroupItemView`
    :param index: The index the action is for.
    :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`
    :return: The data for the action and index.
    :rtype: dict, e.g.:
    """

    visible = index.data(FileModel.FILE_ITEM_ROLE) is None
    status = index.data(FileModel.STATUS_ROLE)
    status_icon = FileModel.get_status_icon(status)

    return {
        "visible": visible,
        "icon": status_icon,
    }


def get_thumbnail_status_action_data(parent, index):
    """
    Return the action data for the status action icon, and for the given index.
    This data will determine how the action icon is displayed for the index.

    :param parent: This is the parent of the :class:`ViewItemDelegate`, which is the file view.
    :type parent: :class:`GroupItemView`
    :param index: The index the action is for.
    :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`
    :return: The data for the action and index.
    :rtype: dict, e.g.:
    """

    visible = index.data(FileModel.FILE_ITEM_ROLE) is not None
    status = index.data(FileModel.STATUS_ROLE)
    status_icon = FileModel.get_status_icon(status)

    return {
        "visible": visible,
        "icon": status_icon,
    }


def get_status_action_data(parent, index):
    """
    Return the action data for the status action icon, and for the given index.
    This data will determine how the action icon is displayed for the index.

    :param parent: This is the parent of the :class:`ViewItemDelegate`, which is the file view.
    :type parent: :class:`GroupItemView`
    :param index: The index the action is for.
    :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`
    :return: The data for the action and index.
    :rtype: dict, e.g.:
    """

    status = index.data(FileModel.STATUS_ROLE)
    status_icon = FileModel.get_status_icon(status)

    return {
        "icon": status_icon,
    }


def get_timestamp_action_data(parent, index):
    """
    Return the action data for the status action icon, and for the given index.
    This data will determine how the action icon is displayed for the index.

    :param parent: This is the parent of the :class:`ViewItemDelegate`, which is the file view.
    :type parent: :class:`GroupItemView`
    :param index: The index the action is for.
    :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`
    :return: The data for the action and index.
    :rtype: dict, e.g.:
    """

    visible = index.parent().isValid()
    datetime_obj = index.data(FileModel.FILE_ITEM_CREATED_AT_ROLE)
    timestamp, _ = utils.create_human_readable_timestamp(
        datetime_obj, "short_timestamp"
    )
    return {
        "visible": visible,
        "name": timestamp,
    }
