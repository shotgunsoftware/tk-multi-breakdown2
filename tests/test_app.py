# Copyright (c) 2020 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import datetime
import os
import pytest

from app_test_base import AppTestBase

from tank.errors import TankHookMethodDoesNotExistError
from tank_test.tank_test_base import setUpModule  # noqa


class TestApplication(AppTestBase):
    """
    Test the SceneBreakdown2 Application class methods. Note that
    this test module is a subclass of TankTestBase, which makes it
    a unittest.TestCase, which means we cannot use some pytest
    functionality, like parametrization and pytest fixtures.
    """

    def setUp(self):
        """
        Set up before any tests are executed.
        """

        os.environ["TEST_ENVIRONMENT"] = "test"
        super(TestApplication, self).setUp()

    def test_init_app(self):
        """
        Test initializing the application.
        """

        assert self.app is not None
        assert self.app._manager_class is not None
        assert self.engine is not None

        # Ensure that the engine has the app command registered with
        # the correct properties
        app_cmd = self.engine.commands.get("Scene Breakdown2...", None)
        assert app_cmd is not None
        cmd_props = app_cmd.get("properties", None)
        assert cmd_props is not None
        assert cmd_props.get("short_name", "") == "breakdown2"

    def test_app_hooks_exist(self):
        """
        Test that the Application has the required hooks set up.
        """

        required_hooks = {
            "hook_scene_operations": [
                {
                    "method": "scan_scene",
                    "kwargs": {},
                },
                {
                    "method": "update",
                    "kwargs": {"item": {}},
                },
            ],
            "hook_get_published_files": [
                {
                    "method": "get_latest_published_file",
                    "kwargs": {"item": {}},
                }
            ],
            "hook_ui_configurations": [
                {
                    "method": "file_item_details",
                    "kwargs": {},
                },
                {
                    "method": "main_file_history_details",
                    "kwargs": {},
                },
                {
                    "method": "file_history_details",
                    "kwargs": {},
                },
            ],
        }
        for hook_key, hook_data in required_hooks.items():
            hook_name = self.app.get_setting(hook_key, None)
            assert hook_name is not None

            for hook in hook_data:
                try:
                    self.app.execute_hook_method(
                        hook_key, hook["method"], **hook["kwargs"]
                    )

                except TankHookMethodDoesNotExistError as tank_error:
                    pytest.fail(
                        "Hook not found: {key}\n{error}".format(
                            key=hook_key, error=tank_error
                        )
                    )

                except Exception as error:
                    # Hook executed but had an exception. This is OK since this is just a test of existence.
                    pass

    def test_create_breakdown_manager(self):
        """
        Test creating and returning a :class:`tk_multi_breakdown2.BreakdownManager` instance.
        """

        manager = self.app.create_breakdown_manager()
        assert manager is not None
        assert manager._bundle == self.app
