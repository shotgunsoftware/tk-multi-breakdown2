# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import sgtk


class SceneBreakdown2(sgtk.platform.Application):
    """
    This is the :class:`sgtk.platform.Application` subclass that defines the top-level
    Scene Breakdown2 interface.
    """

    def init_app(self):
        """Called as the application is being initialized."""

        tk_multi_breakdown2 = self.import_module("tk_multi_breakdown2")

        # Store a reference to manager class to expose its functionality at the application level.
        self._manager_class = tk_multi_breakdown2.BreakdownManager

        # Keep track of the dialog and panel widgets for this app
        self._current_dialog = None
        self._current_panel = None

        # Register the app as a panel.
        self._unique_panel_id = self.engine.register_panel(self.create_panel)

        # Register a menu entry on the ShotGrid menu so that users can launch the panel.
        self.engine.register_command(
            "Scene Breakdown...",
            self.create_panel,
            {"type": "panel", "short_name": "breakdown"},
        )

    def show_dialog(self):
        """Show the Scene Breakdown 2 App dialog."""

        tk_multi_breakdown2 = self.import_module("tk_multi_breakdown2")
        return tk_multi_breakdown2.show_dialog(self)

    def create_dialog(self):
        """
        Show the app as a dialog.

        Contrary to the create_panel() method, multiple calls to this method will result in
        multiple windows appearing.

        :returns: The widget associated with the dialog.
        :rtype: AppDialog
        """

        widget = self.show_dialog()
        self._current_dialog = widget

        return widget

    def create_panel(self):
        """
        Shows the app as a panel.

        Note that since panels are singletons by nature, calling this more than once will only
        result in one panel.

        :returns: The widget associated with the panel.
        :rtype: AppDialog
        """

        tk_multi_breakdown2 = self.import_module("tk_multi_breakdown2")

        try:
            widget = self.engine.show_panel(
                self._unique_panel_id,
                "Scene Breakdown",
                self,
                tk_multi_breakdown2.AppDialog,
            )
        except AttributeError as e:
            self.log_warning(
                "Could not execute show_panel method - please upgrade "
                "to latest core and engine! Falling back on show_dialog. "
                "Error: %s" % e
            )
            widget = self.create_dialog()

        self._current_panel = widget
        return widget

    def create_breakdown_manager(self):
        """
        Create and return a BreakdownManager instance.

        :returns: A BreakdownManager instance.
        :rtype: BreakdownManager
        """

        return self._manager_class(self)

    def _log_metric_viewed_app(self):
        """Module local metric logging helper method for the "Logged In" metric."""

        try:
            from sgtk.util.metrics import EventMetric

            EventMetric.log(
                EventMetric.GROUP_TOOLKIT,
                "Opened Breakdown2 App",
                log_once=False,
                bundle=self,
            )
        except:
            # Ignore all errors, e.g. using a core that does not support metrics.
            pass

    def _on_dialog_close(self, dialog):
        """
        Callback called by the panel dialog whenever it is about to close.

        Clear the stored references to the dialog, if it is one of the app dialogs.

        :param dialog: The dialog that is about to close.
        :type dialog: QtGui.QDialog
        """

        if dialog == self._current_dialog:
            self.log_debug("Current dialog has been closed, clearing reference.")
            self._current_dialog = None

        elif dialog == self._current_panel:
            self.log_debug("Current panel has been closed, clearing reference.")
            self._current_panel = None
