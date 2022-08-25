# Copyright (c) 2020 Autodesk Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Software Inc.

import os
import sys

import sgtk
from tank_test.tank_test_base import TankTestBase


class AppTestBase(TankTestBase):
    """
    Base class for scene breakdown API functionality.
    """

    def setUp(self):
        """
        Set up before any tests are executed.
        """

        # First call the parent TankTestBase constructor to set up the tests base
        super(AppTestBase, self).setUp()
        self.setup_fixtures()

        # Set up the python path to import required modules
        base_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "python",
            )
        )
        app_dir = os.path.abspath(os.path.join(base_dir, "tk_multi_breakdown2"))
        api_dir = os.path.abspath(os.path.join(app_dir, "api"))
        sys.path.extend([base_dir, app_dir, api_dir])

        from tk_multi_breakdown2 import constants
        from tk_multi_breakdown2.api import BreakdownManager
        from tk_multi_breakdown2.api.item import FileItem

        self.constants = constants
        self._manager_class = BreakdownManager
        self._file_item_class = FileItem

        self.project_name = os.path.basename(self.project_root)
        context = self.tk.context_from_entity(self.project["type"], self.project["id"])

        engine_name = os.environ.get("TEST_ENGINE", "tk-testengine")
        self._engine = sgtk.platform.start_engine(engine_name, self.tk, context)
        self._app = self._engine.apps["tk-multi-breakdown2"]

        self._manager = None
        self._bg_task_manager = None

        self.published_file_type = sgtk.util.get_published_file_entity_type(
            self._app.sgtk
        )

    def tearDown(self):
        """
        Clean up after all tests have been executed.
        """

        if self.engine:
            self.engine.destroy()

        super(AppTestBase, self).tearDown()

    @property
    def engine(self):
        """
        The engine running the Breadkwon2 Application.
        """

        return self._engine

    @property
    def app(self):
        """
        The Breakdown2 Application.
        """

        return self._app

    @property
    def bg_task_manager(self):
        """Get the background task manager."""

        if not self._bg_task_manager:
            # Create it if this is the first time requesting it
            self._bg_task_manager = (
                self.app.frameworks["tk-framework-shotgunutils"]
                .import_module("task_manager")
                .BackgroundTaskManager(parent=None, start_processing=True)
            )
            self.addCleanup(self._bg_task_manager.shut_down)

        return self._bg_task_manager

    @property
    def manager(self):
        """
        The Breakdown2 Manager object.
        """

        if not self._manager:
            if self.app:
                self._manager = self._app.create_breakdown_manager()
            elif self._manager_class:
                self._manager = self._manager_class(self.app)

        return self._manager

    def create_manager(self):
        """
        Convenience method to create a new Breakdown2 Manager object.
        """

        if self.app:
            return self._app.create_breakdown_manager()

        if self._manager_class:
            return self._manager_class(self.app)

        return None

    def create_version(self, **kwargs):
        """
        Create a new (mock) Version entity.
        """

        data = {"project": self.project}
        data.update(**kwargs)
        return self.create_entity("Version", data)

    def create_task(self, **kwargs):
        """
        Convenience method to create a new (mock) Task entity.
        """

        data = {"project": self.project}
        data.update(**kwargs)
        return self.create_entity("Task", data)

    def create_published_file(self, **kwargs):
        """
        Convenience method to create a new (mock) Published File entity.
        """

        data = {"project": self.project}
        data.update(**kwargs)
        return self.create_entity("PublishedFile", data)

    def create_entity(self, entity_type, entity_data):
        """
        Convenience method to create a new (mock) Entity for the project.
        """

        return self.mockgun.create(entity_type, entity_data)
