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
            "Scene Breakdown2...", cb, {"short_name": "breakdown2"}
        )

    def create_breakdown_manager(self):
        """
        Create and return a :class:`tk_multi_breakdown2.BreakdownManager` instance.

        :returns: A :class:`tk_multi_breakdown2.BreakdownManager` instance
        """
        return self._manager_class()
