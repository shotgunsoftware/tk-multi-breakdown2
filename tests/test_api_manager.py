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
import sys
import pytest
from mock import patch, MagicMock

from app_test_base import AppTestBase

from test_exceptions import InvalidTestData

from tank_test.tank_test_base import setUpModule  # noqa

# Manually add the app modules to the path in order to import them here.
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
app_dir = os.path.abspath(os.path.join(base_dir, "tk_multi_breakdown2"))
api_dir = os.path.abspath(os.path.join(app_dir, "api"))
sys.path.extend([base_dir, app_dir, api_dir])
from tk_multi_breakdown2 import constants
from tk_multi_breakdown2.api import BreakdownManager
from tk_multi_breakdown2.api.item import FileItem


"""
The purpose of set of tests below are to validate the BreakdownManager class functionality.
They are light-weight tests that do not use any other Toolkit functionality (e.g. sgtk,
Application, Engine, etc.), and strictly focus on testing the BreakdownManager class.
These tests are not a subclass of TankTestBase (unittest.TestCase) so that we can
leverage pytest's functionality, like parametrize and fixtures.

A set of fixtures are defined for these non unittest.TestCase functions. The fixtures
provide mock data for the BreakdownManager, so that the BreakdownManager methods can
execute without requiring additional Toolkit objects.
"""


@pytest.fixture(scope="module")
def find_publish_return_value(storage_root_path):
    """
    This is the return value for 'sgtk.util.find_publish' method call in
    BreakdownManager scan_scene method.
    """

    return {
        os.path.expandvars("%s/foo/bar/hello" % storage_root_path): {
            "id": 6,
            "type": "PublishedFile",
            "version_id": 2,
        },
        os.path.expandvars("%s/foo/bar/world" % storage_root_path): {
            "id": 2,
            "type": "PublishedFile",
            "version_id": 8,
        },
    }


@pytest.fixture(scope="module")
def bundle_hook_scan_scene_return_value(storage_root_path):
    """
    The return value for the BreakdownManager's class variable '_bundle' method
    call 'execute_hook_method("hook_scene_operation", "scan_scene")'.
    """

    return [
        {
            "node_name": "A reference node",
            "node_type": "reference",
            "path": "%s/foo/bar/hello" % storage_root_path,
        },
        {
            "node_name": "A file node",
            "node_type": "file",
            "path": "%s/foo/bar/world" % storage_root_path,
        },
        {
            "node_name": "An updated reference node",
            "node_type": "reference",
            "path": "%s/foo/bar/hello" % storage_root_path,
            "extra_data": {"field": "value", "another_field": "another value"},
        },
    ]


@pytest.fixture(scope="module")
def bundle_settings():
    """
    The settings for the BreakdownManager class variable '_bundle'.
    """

    return {"published_file_fields": ["test_field1", "test_field2", "test_field3"]}


@pytest.fixture(scope="module")
def bundle_hook_methods(bundle_hook_scan_scene_return_value, storage_root_path):
    """
    A mapping of hooks and their return value for the BreakdownManager's class
    variable '_bundle'. The return values do not necessarily match real production
    data, this is meant to be used to ensure the BreakdownManager can execute its
    methods without erring on hooks not found.
    """

    return {
        "hook_scene_operations": {
            "scan_scene": bundle_hook_scan_scene_return_value,
            "update": None,
        },
        "hook_get_published_files": {
            "get_latest_published_file": {
                "node_name": "A reference node",
                "node_type": "reference",
                "path": "%s/foo/bar/hello" % storage_root_path,
            },
        },
    }


@pytest.fixture
def bundle(bundle_settings, bundle_hook_methods):
    """
    A mock Application object to use to create the BreakdownManager object. Note that
    the mock Application does not provide the full functionality of the actual class
    it represents; any additional functionality required must be added here.
    """

    def mock_app_get_setting(name, default_value=None):
        """
        Mock the Application method 'get_settings'
        """
        return bundle_settings.get(name, default_value)

    def mock_app_execute_hook_method(hook_name, hook_method, **kwargs):
        """
        Mock the Application method 'execute_hook_method'.
        """
        return bundle_hook_methods.get(hook_name, {}).get(hook_method, None)

    def mock_app_shotgun_find(
        entity_type,
        filters,
        fields=None,
        order=None,
        filter_operator=None,
        limit=0,
        retired_only=False,
        page=0,
        include_archived_projects=True,
        additional_filter_presets=None,
    ):
        """
        Mock the Application method 'find' of it's 'shotgun' property.
        """

        # Currently this mock method only supports one level of sorting.
        order_by_field = order[0]["field_name"] if order else None
        result = []
        for i in range(5):
            item = {"id": i, "type": entity_type}
            for field in fields:
                item[field] = "dummy value"
            if order_by_field:
                item[order_by_field] = i
            result.append(item)

        if order_by_field:
            is_desc = order[0]["direction"] == "desc"
            return sorted(result, key=lambda k: k[order_by_field], reverse=is_desc)

        return result

    # Set up the mock Application
    app = MagicMock()
    app.get_setting = mock_app_get_setting
    app.execute_hook_method = mock_app_execute_hook_method
    app.sgtk = MagicMock()
    app.shotgun = MagicMock()
    app.shotgun.find = mock_app_shotgun_find

    return app


@pytest.mark.parametrize(
    "extra_fields",
    [
        None,
        [],
        ["one_field"],
        ["one_field", "two_field", "three_field"],
    ],
)
def test_scan_scene(
    bundle, find_publish_return_value, bundle_hook_scan_scene_return_value, extra_fields
):
    """
    Test the BreakdownManager 'scan_scene' method. This test case aims to strictly test
    the functionality of the BreakdownManager, and not the data returned by the hooks
    or Shotgun query.
    """

    manager = BreakdownManager(bundle)
    app = manager._bundle
    extra_fields = extra_fields or []

    # Patch the method call 'sgtk.util.find_publish' in the BreakdownManager scan_scene to
    # return the mock data 'find_publish_return_value'.
    with patch("sgtk.util.find_publish", return_value=find_publish_return_value):
        # Call the method that is to be tested.
        scene_items = manager.scan_scene(extra_fields=extra_fields)
        if extra_fields is None:
            # Assert that passing no param for extra_fields is the same as passing None.
            scene_items2 = manager.scan_scene()
            assert scene_items == scene_items2

    # Assert the result return type.
    assert isinstance(scene_items, list)

    # Assert that the scene items are of the right type and have the expected data.
    for index, item in enumerate(scene_items):
        assert isinstance(item, FileItem)

        expected_scene_item = bundle_hook_scan_scene_return_value[index]
        assert item.node_name == expected_scene_item["node_name"]
        assert item.node_type == expected_scene_item["node_type"]
        assert item.extra_data == expected_scene_item.get("extra_data")

        expected_publish_file = find_publish_return_value[item.path]
        assert expected_publish_file is not None
        assert item.sg_data == expected_publish_file


@pytest.mark.parametrize(
    "file_item_data",
    [(False, False), (True, False), (False, True), (True, True)],
    indirect=["file_item_data"],
)
def test_get_latest_published_file(bundle, file_item_data):
    """
    Test the BreakdownManager 'get_latest_publshed_file' method. This test case only
    validates the BreakdownManager's functionality, and assumes the latest published
    file returned by the bundle's hook method is correct.
    """

    manager = BreakdownManager(bundle)
    scene_item = FileItem(**file_item_data)
    # Remember the item's latest_published_file before calling get_latest_published_file,
    # in case we need to check it.
    latest_published_file_before_update = scene_item.latest_published_file

    # Call the method that is to be tested.
    latest = manager.get_latest_published_file(scene_item)

    # Assert the return value type is a dictionary
    assert isinstance(latest, dict)

    if not scene_item.sg_data:
        # Assert that an empty dictionary was returned, and the item's 'latest_published_file'
        # is unchanged, if hte item is invalid (e.g. has no 'sg_data')
        assert latest == {}
        assert scene_item.latest_published_file == latest_published_file_before_update
    else:
        # Assert that the item's latest_published_file property was updated correctly.
        assert scene_item.latest_published_file == latest


@pytest.mark.parametrize(
    "file_item_data",
    [
        (False, False),
        (
            {
                "project": "dummy project",
                "name": "some name",
                "task": "dummy task",
                "entity": "dummy entity",
                "published_file_type": "some type",
            },
            False,
        ),
        (False, True),
        (
            {
                "project": "dummy project",
                "name": "some name",
                "task": "dummy task",
                "entity": "dummy entity",
                "published_file_type": "some type",
            },
            True,
        ),
    ],
    indirect=["file_item_data"],
)
def test_get_published_file_history(bundle, file_item_data):
    """
    Test the BreakdownManager 'get_published_file_history' method. This test case
    only validates the BreakdownManager's functionality, and assume that the
    publish file history returned by the bundle's hook is correct.
    """

    manager = BreakdownManager(bundle)
    item = FileItem(**file_item_data)
    latest_published_file_before_update = item.latest_published_file
    extra_fields = ["another_field", "and another"]

    # Call the method that is to be tested.
    result = manager.get_published_file_history(item, extra_fields)

    # Get the expected latest published file to validate the result
    expected_latest = {"version_number": -1}
    for result_item in result:
        if result_item["version_number"] > expected_latest["version_number"]:
            expected_latest = result_item

    if not item.sg_data:
        # Assert the result is an empty list and that the latest published file
        # is unchanged, if the item is invalid (e.g. has no 'sg_data')
        assert result == []
        assert item.latest_published_file == latest_published_file_before_update

    else:
        if result:
            assert item.latest_published_file == expected_latest
        else:
            # No publish file history was found, assert that latest published file is unchanged
            assert item.latest_published_file == latest_published_file_before_update


@pytest.mark.parametrize(
    "file_item_data",
    [
        (False, False),
        ({"version_number": 1, "path": {"local_path": "some path"}}, False),
        (False, True),
        ({"version_number": 234, "path": {"local_path": "another path"}}, True),
        ({"version_number": 4}, True),
    ],
    indirect=["file_item_data"],
)
def test_update_to_latest_version(bundle, file_item_data):
    """
    Test the Breakdown Manager 'update_to_latest_version' method. This test case
    only validates teh BreakdownManager's functionality, and assumes that the
    bundle's hook method to update the item functions correctly.
    """

    item = FileItem(**file_item_data)
    item_sg_data = file_item_data.get("sg_data", None)
    if item_sg_data is None:
        expected_latest_data = {"version_number": 1}
    else:
        expected_latest_data = item_sg_data
        expected_latest_data["version_number"] = (
            item_sg_data.get("version_number", 0) + 1
        )

    # Set the item's latest published file
    item.latest_published_file = expected_latest_data

    if item.latest_published_file.get("path", {}).get("local_path", None):
        # Data is valid, expect the item to be updated to the latest
        expected_item_path = expected_latest_data["path"]["local_path"]
        expected_item_sg_data = expected_latest_data
    else:
        # Data is invalid, nothing should be updated
        expected_item_path = item.path
        expected_item_sg_data = item.sg_data

    manager = BreakdownManager(bundle)
    # Call the method that is to be tested.
    manager.update_to_latest_version(item)
    assert item.path == expected_item_path
    assert item.sg_data == expected_item_sg_data


def test_update_to_latest_version_no_latest(bundle, file_item_data):
    """
    Test the Breakdown Manager 'update_to_latest_version' method. This test case
    only validates teh BreakdownManager's functionality, and assumes that the
    bundle's hook method to update the item functions correctly.
    """

    item = FileItem(**file_item_data)
    item.latest_published_file = None
    # No update should occur, save the item state before the update is called.
    expected_item_path = item.path
    expected_item_sg_data = item.sg_data

    manager = BreakdownManager(bundle)
    # Call the method that is to be tested.
    manager.update_to_latest_version(item)

    assert item.path == expected_item_path
    assert item.sg_data == expected_item_sg_data


@pytest.mark.parametrize(
    "file_item_data",
    [(False, False), (True, False), (False, True), (True, True)],
    indirect=["file_item_data"],
)
@pytest.mark.parametrize(
    "sg_data",
    [
        None,
        {},
        {"version_number": 6, "id": 1, "name": "beep", "code": "boop"},
        {
            "version_number": 6,
            "id": 1,
            "name": "beep",
            "code": "boop",
            "path": {"missing_local_path": "no path"},
        },
        {
            "version_number": 6,
            "id": 1,
            "name": "beep",
            "code": "boop",
            "path": {"local_path": "/this/is/a/valid/data/object"},
        },
    ],
)
def test_update_to_specific_version(bundle, file_item_data, sg_data):
    """
    Test the Breakdown Manager 'update_to_latest_version' method. This test case
    only validates teh BreakdownManager's functionality, and assumes that the
    bundle's hook method to update the item functions correctly.
    """

    item = FileItem(**file_item_data)

    # Determine if the item should be updated, based on the validity of the sg_data. Save the original
    # item's data, if the item should not be updated to assert nothing has changed after calling update.
    if not sg_data or not sg_data.get("path", {}).get("local_path", None):
        # Data is invalid, nothing should be updated
        expected_item_path = item.path
        expected_item_sg_data = item.sg_data

    else:
        expected_item_path = sg_data["path"]["local_path"]
        expected_item_sg_data = sg_data

    manager = BreakdownManager(bundle)
    # Call the method that is to be tested
    manager.update_to_specific_version(item, sg_data)
    assert item.path == expected_item_path
    assert item.sg_data == expected_item_sg_data


class TestBreakdownManager(AppTestBase):
    """
    This test class purpose is to more completely test the BreakdownManager.
    It is a subclass of TankTestBase, which means an engine, app, mock databas,
    etc. are set up and available to use to further test the api functionality.
    """

    def setUp(self):
        """
        Set up before any tests are executed.
        """

        os.environ["TEST_ENVIRONMENT"] = "test"
        super(TestBreakdownManager, self).setUp()

        # Set the environment variable for the hook scene operations method 'scan_scene'
        os.environ["TK_TEST_PROJECT_ROOT_PATHS"] = self.project_root

        # Set up the mock entity data
        self.version = self.create_version(code="version_code")
        self.task = self.create_task(
            content="Test Breakdown2 Concept", entity=self.version
        )

        # These path caches should match the "path" value of the items returned by the
        # bundle's hook scene operation 'scan_scene", if it is intended to be found in
        # the BreakdownManager's 'scan_scene'.
        self.first_publish_path_cache = "foo/bar/hello"
        self.second_publish_path_cache = "foo/bar/world"
        self.third_publish_path_cache = "foo/bar/again"

        # Add a published file to the mock database
        self.first_publish = self.create_published_file(
            code="hello",
            name="hello",
            path_cache="%s/%s" % (self.project_name, self.first_publish_path_cache),
            path_cache_storage=self.primary_storage,
            path={
                "local_path": os.path.normpath(
                    os.path.join(self.project_root, "files", "images", "svenFace.jpg")
                )
            },
            created_at=datetime.datetime(2021, 1, 4, 12, 1),
            task=self.task,
            entity=self.version,
            version_number=1,
        )
        # Add another published file to the mock database
        self.second_publish = self.create_published_file(
            code="world",
            name="world",
            path_cache="%s/%s" % (self.project_name, self.second_publish_path_cache),
            path_cache_storage=self.primary_storage,
            path={
                "local_path": os.path.normpath(
                    os.path.join(self.project_root, "files", "images", ".svenThumb.png")
                )
            },
            created_at=datetime.datetime(2021, 1, 4, 12, 1),
            task=self.task,
            entity=self.version,
            version_number=2,
        )
        # Update the first pubilshed file added to the database.
        self.first_publish_latest = self.create_published_file(
            code="hello2",
            name="hello",
            path_cache="%s/%s" % (self.project_name, self.third_publish_path_cache),
            path_cache_storage=self.primary_storage,
            path={
                "local_path": os.path.normpath(
                    os.path.join(self.project_root, "files", "images", "svenFace.jpg")
                )
            },
            created_at=datetime.datetime(2021, 1, 4, 12, 1),
            task=self.task,
            entity=self.version,
            version_number=2,
        )

        # A mapping of published file path caches to the entity
        self.published_files = {
            os.path.join(
                self.project_root,
                self.first_publish_path_cache.replace("/", os.path.sep),
            ): self.first_publish,
            os.path.join(
                self.project_root,
                self.second_publish_path_cache.replace("/", os.path.sep),
            ): self.second_publish,
            os.path.join(
                self.project_root,
                self.third_publish_path_cache.replace("/", os.path.sep),
            ): self.first_publish_latest,
        }

        # Generate the list of expected published files and paths that should be found by the
        # BreakdownManager scan scene
        self.expected_published_files_found = []
        self.expected_published_file_paths = []
        hook_result = self.app.execute_hook_method(
            "hook_scene_operations", "scan_scene"
        )
        for item in hook_result:
            pf = self.published_files.get(item["path"], None)
            if not pf:
                continue

            if item["path"] in self.expected_published_file_paths:
                continue

            self.expected_published_file_paths.append(item["path"])
            self.expected_published_files_found.append(
                {"id": pf["id"], "project": pf["project"]}
            )

    def test_scan_scene(self):
        """
        Test scanning the current scene.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)
        assert len(scene_items) == len(self.expected_published_files_found)

        fields = self.constants.PUBLISHED_FILES_FIELDS + self.app.get_setting(
            "published_file_fields", []
        )

        found_paths = []
        found_published_files = []
        for item in scene_items:
            assert hasattr(item, "sg_data")
            assert isinstance(item.sg_data, dict)
            assert item.sg_data is not None

            sg_data_keys = item.sg_data.keys()
            for field in fields:
                assert field in sg_data_keys

            found_paths.append(item.path)
            found_published_files.append(
                {"id": item.sg_data["id"], "project": item.sg_data["project"]}
            )

        # Assert that all expected paths were found.
        assert set(found_paths) == set(self.expected_published_file_paths)
        # Assert that all the expected published files were found, and no unexpected files were found.
        assert [
            pf
            for pf in found_published_files
            if pf not in self.expected_published_files_found
        ] == []
        assert [
            pf
            for pf in self.expected_published_files_found
            if pf not in found_published_files
        ] == []

    def test_scan_scene_with_extra_fields(self):
        """
        Test scanning the current scene.
        """

        # If we move away from unittest.TestCase, we can leverage pytest's
        # parameterize functionality to achieve this.
        possible_extra_fields = [
            [],
            ["one_field"],
            ["one_field", "two fields", "some field"],
        ]
        for extra_fields in possible_extra_fields:
            scene_items = self.manager.scan_scene(extra_fields)
            assert isinstance(scene_items, list)

            fields = self.constants.PUBLISHED_FILES_FIELDS + self.app.get_setting(
                "published_file_fields", []
            )
            if extra_fields:
                fields += extra_fields

            found_paths = []
            found_published_files = []
            for item in scene_items:
                assert hasattr(item, "sg_data")
                assert isinstance(item.sg_data, dict)
                assert item.sg_data is not None

                sg_data_keys = item.sg_data.keys()
                for field in fields:
                    assert field in sg_data_keys

                found_paths.append(item.path)
                found_published_files.append(
                    {"id": item.sg_data["id"], "project": item.sg_data["project"]}
                )

            # Assert that all expected paths were found.
            assert set(found_paths) == set(self.expected_published_file_paths)
            # Assert that all the expected published files were found, and no unexpected files were found.
            assert [
                pf
                for pf in found_published_files
                if pf not in self.expected_published_files_found
            ] == []
            assert [
                pf
                for pf in self.expected_published_files_found
                if pf not in found_published_files
            ] == []

    def test_get_latest_published_file(self):
        """
        Test getting the latest available published file according to the current item context.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)

        try:
            item = next(
                i
                for i in scene_items
                if i.sg_data["path"]["local_path"]
                == self.first_publish["path"]["local_path"]
            )

        except StopIteration:
            # self.first_publish should be in the scan scene result.
            raise InvalidTestData("Expected test data to be found in result.")

        latest = self.manager.get_latest_published_file(item)
        assert item.latest_published_file == latest
        assert (
            latest.get("version_number", None)
            == self.first_publish_latest["version_number"]
        )

    def test_get_published_file_history(self):
        """
        Test getting the published history for the selected item.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)

        # Use any item from the scene
        try:
            item = scene_items[0]
        except IndexError:
            # Test data is invalid, expected that scan scene would return at least one item.
            raise InvalidTestData("Expected result to have at least one item.")

        latest_published_file_before_update = item.latest_published_file
        result = self.manager.get_published_file_history(item)

        expected_fields = self.constants.PUBLISHED_FILES_FIELDS + self.app.get_setting(
            "published_file_fields", []
        )

        expected_latest = {}
        for result_item in result:
            if (
                not expected_latest
                or result_item["version_number"] > expected_latest["version_number"]
            ):
                expected_latest = result_item

            history_item_fields = result_item.keys()
            for field in expected_fields:
                assert field in history_item_fields

        if not item.sg_data or not result:
            assert result == []
            assert item.latest_published_file == latest_published_file_before_update
        else:
            assert item.latest_published_file == expected_latest

    def test_get_published_file_history_with_extra_fields(self):
        """
        Test getting the published history for the selected item.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)

        # Use any item from the scene
        try:
            item = scene_items[0]
        except IndexError:
            # Test data is invalid, expected that scan scene would return at least one item.
            raise InvalidTestData("Expected result to have at least one item.")

        latest_published_file_before_update = item.latest_published_file
        possible_extra_fields = [
            [],
            ["one_field"],
            ["one_field", "two fields", "some field"],
        ]
        for extra_fields in possible_extra_fields:
            result = self.manager.get_published_file_history(item, extra_fields)
            expected_fields = (
                self.constants.PUBLISHED_FILES_FIELDS
                + self.app.get_setting("published_file_fields", [])
                + extra_fields
            )

            expected_latest = {}
            for result_item in result:
                if (
                    not expected_latest
                    or result_item["version_number"] > expected_latest["version_number"]
                ):
                    expected_latest = result_item

                history_item_fields = result_item.keys()
                for field in expected_fields:
                    assert field in history_item_fields

            if not item.sg_data or not result:
                assert result == []
                assert item.latest_published_file == latest_published_file_before_update
            else:
                assert item.latest_published_file == expected_latest

    def test_update_to_latest_version(self):
        """
        Test the Breakdown Manager 'update_to_latest_version' method.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)

        # Use any item from the scene
        try:
            item = scene_items[0]
        except IndexError:
            # Test data is invalid, expected that scan scene would return at least one item.
            raise InvalidTestData("Expected result to have at least one item.")

        if item.sg_data is None:
            expected_latest_data = {"version_number": 1}
        else:
            expected_latest_data = item.sg_data
            expected_latest_data["version_number"] = (
                item.sg_data.get("version_number", 0) + 1
            )

        # Set the item's latest published file
        item.latest_published_file = expected_latest_data

        if item.latest_published_file.get("path", {}).get("local_path", None):
            # Data is valid, expect the item to be updated to the latest
            expected_item_path = expected_latest_data["path"]["local_path"]
            expected_item_sg_data = expected_latest_data
        else:
            # Data is invalid, nothing should be updated
            expected_item_path = item.path
            expected_item_sg_data = item.sg_data

        manager = BreakdownManager(self.app)
        # Call the method that is to be tested.
        manager.update_to_latest_version(item)
        assert item.path == expected_item_path
        assert item.sg_data == expected_item_sg_data

    def test_update_to_specific_version(self):
        """
        Test the Breakdown Manager 'update_to_latest_version' method.
        """

        scene_items = self.manager.scan_scene()
        assert isinstance(scene_items, list)
        # Make sure there is data to be tested
        assert len(scene_items) > 0

        # Use any scene item that has a history
        item = None
        sg_data = None
        for scene_item in scene_items:
            history = self.manager.get_published_file_history(scene_item)

            if len(history) > 1:
                item = scene_item

                for history_item in history:
                    if history_item["id"] != item.sg_data["id"]:
                        # Use sg_data that is not our item's sg_data
                        sg_data = history_item
                        break

            if item is not None:
                break

        # This is not a failure may be due to the testing set up. This requires that
        # there is at least one published file with a history of at least two items (itself
        # and one other)
        assert item is not None

        # Determine if the item should be updated, based on the validity of the sg_data. Save the original
        # item's data, if the item should not be updated to assert nothing has changed after calling update.
        if not sg_data or not sg_data.get("path", {}).get("local_path", None):
            # Data is invalid, nothing should be updated
            expected_item_path = item.path
            expected_item_sg_data = item.sg_data

        else:
            expected_item_path = sg_data["path"]["local_path"]
            expected_item_sg_data = sg_data

        # Call the method that is to be tested
        self.manager.update_to_specific_version(item, sg_data)
        assert item.path == expected_item_path
        assert item.sg_data == expected_item_sg_data


class TestBreakdownManagerMultipleProjects(TestBreakdownManager):
    """
    Test the BreadownManager with multiple projects set up, in order
    to test that published files can be found from not only the current
    project.

    This test class will re-run all of TestBreakdownManager class tests, but
    with two projects set up to find publishes from.
    """

    def setUp(self):
        """
        Set up before any tests are executed.
        """

        super(TestBreakdownManagerMultipleProjects, self).setUp()

        # Create a second project for the test module
        _, project2_root = self.create_project({"name": "project 2"})

        # Add the new project path to the environment variable
        os.environ["TK_TEST_PROJECT_ROOT_PATHS"] += "," + project2_root

        project2_name = os.path.basename(project2_root)

        project2_publish1 = self.create_published_file(
            code="abc",
            name="some name",
            path_cache="%s/%s" % (project2_name, self.first_publish_path_cache),
            path_cache_storage=self.primary_storage,
            path={
                "local_path": os.path.normpath(
                    "%s/files/images/svenFace.jpg" % project2_root
                )
            },
            created_at=datetime.datetime(2021, 1, 4, 12, 1),
            version_number=4,
        )
        project2_publish2 = self.create_published_file(
            code="abc2",
            name="some name",
            path_cache="%s/%s" % (project2_name, self.second_publish_path_cache),
            path_cache_storage=self.primary_storage,
            path={
                "local_path": os.path.normpath(
                    "%s/files/images/svenFace.jpg" % project2_root
                )
            },
            created_at=datetime.datetime(2021, 1, 4, 12, 1),
            version_number=5,
        )

        # Add to the list of published files
        self.published_files[
            os.path.join(
                project2_root, self.first_publish_path_cache.replace("/", os.path.sep)
            )
        ] = project2_publish1
        self.published_files[
            os.path.join(
                project2_root, self.second_publish_path_cache.replace("/", os.path.sep)
            )
        ] = project2_publish2

        # Add to the expected results
        hook_result = self.app.execute_hook_method(
            "hook_scene_operations", "scan_scene"
        )
        for item in hook_result:
            pf = self.published_files.get(item["path"], None)
            if not pf:
                continue

            if item["path"] in self.expected_published_file_paths:
                continue

            self.expected_published_file_paths.append(item["path"])
            self.expected_published_files_found.append(
                {"id": pf["id"], "project": pf["project"]}
            )
