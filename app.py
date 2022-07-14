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
    This is the :class:`sgtk.platform.Application` subclass that defines the
    top-level scenebreakdown2 interface.
    """

    def init_app(self):
        """
        Called as the application is being initialized
        """

        tk_multi_breakdown2 = self.import_module("tk_multi_breakdown2")

        # the manager class provides the interface for publishing. We store a
        # reference to it to enable the create_publish_manager method exposed on
        # the application itself
        self._manager_class = tk_multi_breakdown2.BreakdownManager

        cb = lambda: tk_multi_breakdown2.show_dialog(self)
        self.engine.register_command(
            "Scene Breakdown...", cb, {"short_name": "breakdown"}
        )

    def show_dialog(self):
        """Show the Scene Breakdown 2 App dialog."""

        tk_multi_breakdown2 = self.import_module("tk_multi_breakdown2")
        tk_multi_breakdown2.show_dialog(self)

    def create_breakdown_manager(self):
        """
        Create and return a :class:`tk_multi_breakdown2.BreakdownManager` instance.

        :returns: A :class:`tk_multi_breakdown2.BreakdownManager` instance
        """

        return self._manager_class(self)

    def _log_metric_viewed_app(self):
        """
        Module local metric logging helper method for the "Logged In" metric.
        """

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
