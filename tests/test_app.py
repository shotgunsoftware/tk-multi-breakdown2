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
    Test the SceneBreakdown2 Application class methods.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor
        """

        super(TestApplication, self).__init__(*args, **kwargs)

    def setUp(self):
        """
        Set up before any tests are executed.
        """

        os.environ["TEST_ENVIRONMENT"] = "app_test"
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

        # Validate that the required hooks are set up
        required_hooks = {
            "hook_scene_operations": [
                {"method": "scan_scene", "kwargs": {},},
                {"method": "update", "kwargs": {"item": {}},},
            ],
            "hook_get_published_files": [
                {"method": "get_latest_published_file", "kwargs": {"item": {}},}
            ],
            "hook_ui_configurations": [
                {"method": "file_item_details", "kwargs": {},},
                {"method": "main_file_history_details", "kwargs": {},},
                {"method": "file_history_details", "kwargs": {},},
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

    def test_scan_scene(self):
        """
        Test scanning the current scene.
        """

        # manager = self.app.create_breakdown_manager()
        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)

        # FIXME do better
        # Scene items returned are hard coded in tests/fixtures/config/hooks/scene_operations_test.py
        assert len(scene_items) == 3

        fields = self.constants.PUBLISHED_FILES_FIELDS + self.app.get_setting(
            "published_file_fields", []
        )

        for item in scene_items:
            assert hasattr(item, "sg_data")
            assert isinstance(item.sg_data, dict)
            assert item.sg_data is not None

            sg_data_keys = item.sg_data.keys()
            for field in fields:
                assert field in sg_data_keys

    def test_get_latest_published_file(self):
        """
        Test getting the latest available published file according to the current item context.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)
        assert len(scene_items) > 0

        item = scene_items[0]
        latest = self.manager.get_latest_published_file(item)
        assert item.latest_published_file == latest

        # FIXME
        assert latest.get("version_number", None) == 2

    def test_get_published_file_history(self):
        """
        Test getting the published history for the selected item.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)
        assert len(scene_items) > 0

        item = scene_items[0]

        extra_fields = ["another_field"]
        history_items = self.manager.get_published_file_history(item, extra_fields)

        fields = (
            self.constants.PUBLISHED_FILES_FIELDS
            + self.app.get_setting("published_file_fields", [])
            + extra_fields
        )

        latest = -1
        for history_item in history_items:
            if history_item["version_number"] > latest:
                latest = history_item["version_number"]

            history_item_fields = history_item.keys()
            for field in fields:
                assert field in history_item_fields

        assert item.latest_published_file is not None
        assert item.latest_published_file["version_number"] == latest

    def test_breakdown_manager_workflow(self):
        """
        Run through the API BreakdownManager tests using the BreakdownManager created
        from this Application.
        """

        manager = self.app.create_breakdown_manager()

        scene_items = manager.scan_scene()
        assert isinstance(scene_items, list)
        assert len(scene_items) > 0

        item_to_update = scene_items[0]
        latest_published_file = manager.get_latest_published_file(item_to_update)
        assert latest_published_file is not None

        file_history = manager.get_published_file_history(item_to_update)
        assert isinstance(file_history, list)
        assert len(file_history) > 0

        for history in file_history:
            # FIXME failing on sg_data["path"] is none but should be a dictionary containing file path info
            manager.update_to_specific_version(item_to_update, history)

        manager.update_to_latest_version(item_to_update)
