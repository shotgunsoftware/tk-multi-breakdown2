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
import sys

from unittest.mock import patch, MagicMock

# Manually add the app modules to the path in order to import them here.
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
app_dir = os.path.abspath(os.path.join(base_dir, "tk_multi_breakdown2"))
api_dir = os.path.abspath(os.path.join(app_dir, "api"))
sys.path.extend([base_dir, app_dir, api_dir])
from tk_multi_breakdown2 import constants
from tk_multi_breakdown2.api import BreakdownManager
from tk_multi_breakdown2.api.item import FileItem

import sys

sys.path.append("/Users/oues/python_libs")
import ptvsd

ptvsd.enable_attach()
ptvsd.wait_for_attach()

"""
The purpose of this test module is to validate the BreakdownManager class functionality.
It is a light-weight module that does not use any other Toolkit functionality (e.g. sgtk,
Application, Engine, etc.), and strictly focuses on testing the BreakdownManager class.
These tests are not a subclass of TankTestBase (unittest.TestCase) so that we can
leverage pytest's functionality, like parametrize and fixtures.

A set of fixtures are defined for the tests in this module. The fixtures provide
mock data for the BreakdownManager, so that the BreakdownManager methods can
execute without requiring additional Toolkit instances created.
"""


@pytest.fixture
def find_publish_return_value_fixture(publish_file_path_root):
    """
    This is the return value for 'sgtk.util.find_publish' method call in
    BreakdownManager scan_scene method.
    """

    return {
        os.path.expandvars("%s/foo/bar/hello" % publish_file_path_root): {
            "id": 6,
            "type": "PublishedFile",
        },
        os.path.expandvars("%s/foo/bar/world" % publish_file_path_root): {
            "id": 2,
            "type": "PublishedFile",
        },
    }


@pytest.fixture
def scene_items_fixture(publish_file_path_root):
    """
    The return value for the BreakdownManager's class variable '_bundle' method
    call 'execute_hook_method("hook_scene_operation", "scan_scene")'.
    """

    return [
        {
            "node_name": "A reference node",
            "node_type": "reference",
            "path": "%s/foo/bar/hello" % publish_file_path_root,
        },
        {
            "node_name": "A file node",
            "node_type": "file",
            "path": "%s/foo/bar/world" % publish_file_path_root,
        },
        {
            "node_name": "An updated reference node",
            "node_type": "reference",
            "path": "%s/foo/bar/hello" % publish_file_path_root,
        },
    ]


@pytest.fixture
def bundle_settings_fixture():
    """
    The settings for the BreakdownManager class variable '_bundle'.
    """

    return {"published_file_fields": ["test_field1", "test_field2", "test_field3"]}


@pytest.fixture
def bundle_hook_methods_fixture(scene_items_fixture, publish_file_path_root):
    """
    The mapping of hooks and return value for the BreakdownManager's class variable '_bundle'.
    """

    return {
        "hook_scene_operations": {"scan_scene": scene_items_fixture, "update": None},
        "hook_get_published_files": {
            "get_latest_published_file": {
                "node_name": "A reference node",
                "node_type": "reference",
                "path": "%s/foo/bar/hello" % publish_file_path_root,
            },
        },
    }


@pytest.fixture
def bundle_fixture(bundle_settings_fixture, bundle_hook_methods_fixture):
    """
    A BreakdownManager object. Mock the BreakdownManager's class variable '_bundle'. Note that
    the mocked _bundle object does not provide the full functionality of the actual object is represents;
    if additional functionality of the _bundle is used in the future, that functionality may need to be
    mocked here.
    """

    def mock_app_get_setting(name, default_value=None):
        """
        Mock the Application method 'get_settings'
        """
        return bundle_settings_fixture.get(name, default_value)

    def mock_app_execute_hook_method(hook_name, hook_method, **kwargs):
        """
        Mock the Application method 'execute_hook_method'.
        """
        return bundle_hook_methods_fixture.get(hook_name, {}).get(hook_method, None)

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
        Mock the Application method 'find' of it's property shotgun.
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

    # Set up the mock Application to pass to the Breakdown Manager
    app = MagicMock()
    app.get_setting = mock_app_get_setting
    app.execute_hook_method = mock_app_execute_hook_method
    app.sgtk = MagicMock()
    app.shotgun = MagicMock()
    app.shotgun.find = mock_app_shotgun_find

    # Finally, return the mock object
    return app


@pytest.mark.parametrize(
    "extra_fields",
    [None, [], ["one_field"], ["one_field", "two_field", "three_field"],],
)
def test_scan_scene(
    bundle_fixture, find_publish_return_value_fixture, scene_items_fixture, extra_fields
):
    """
    Test the BreakdownManager 'scan_scene' method. This test case focuses on testing that
    the return value is a list with the expected number of items, and each item is valid; e.g. each
    item has the expected attributes and specifically the 'sg_data' attribute has the expected
    dictionary keys. This test case is not intended for validating the actual items returned.
    """

    manager = BreakdownManager(bundle_fixture)
    app = manager._bundle
    extra_fields = extra_fields or []
    fields = (
        constants.PUBLISHED_FILES_FIELDS
        + app.get_setting("published_file_fields", [])
        + extra_fields
    )
    # Insert expected keys in return value. The value does not matter.
    for key in find_publish_return_value_fixture.keys():
        for field in fields:
            find_publish_return_value_fixture[key][field] = "dummy value"

    # Patch the method call 'sgtk.util.find_publish' in the BreakdownManager scan_scene.
    with patch(
        "sgtk.util.find_publish", return_value=find_publish_return_value_fixture
    ):
        # Call the method that is to be tested.
        scene_items = manager.scan_scene(extra_fields=extra_fields)
        if extra_fields is None:
            # Assert that passing no param for extra_fields is the same as passing None
            scene_items2 = manager.scan_scene()
            assert scene_items == scene_items2

    # Assert the return type and have the expected number of scene items
    assert isinstance(scene_items, list)
    assert len(scene_items) == len(scene_items_fixture)

    required_scene_item_props = [
        {"name": "node_name", "type": str},
        {"name": "node_type", "type": str},
        {"name": "path", "type": str},
        {"name": "sg_data", "type": dict},
    ]
    for item in scene_items:
        # Assert that we have all the required properties in the scene items's data
        for prop in required_scene_item_props:
            assert hasattr(item, prop["name"])
            assert isinstance(getattr(item, prop["name"]), prop["type"])
            assert getattr(item, prop["name"], None) is not None

        # Assert that the scene item 'sg_data' dict has the expected keys
        sg_data_keys = item.sg_data.keys()
        for field in fields:
            assert field in sg_data_keys


@pytest.mark.parametrize(
    "file_item_data",
    [(False, False), (True, False), (False, True), (True, True)],
    indirect=["file_item_data"],
)
def test_get_latest_published_file(bundle_fixture, file_item_data):
    """
    Test the BreakdownManager 'get_latest_publshed_file' method. This test case only
    validates the BreakdownManager's functionality, and assumes the latest published
    file returned by the bundle's hook method is correct.
    """

    manager = BreakdownManager(bundle_fixture)
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
def test_get_published_file_history(bundle_fixture, file_item_data):
    """
    Test the BreakdownManager 'get_published_file_history' method. This test case
    only validates the BreakdownManager's functionality, and assume that the
    publish file history returned by the bundle's hook is correct.
    """

    manager = BreakdownManager(bundle_fixture)
    item = FileItem(**file_item_data)
    latest_published_file_before_update = item.latest_published_file
    extra_fields = ["another_field", "and another"]

    # Call the method that is to be tested.
    result = manager.get_published_file_history(item, extra_fields)

    # Get the list of fields that are expected to be in each item of the result
    app = manager._bundle
    fields = (
        constants.PUBLISHED_FILES_FIELDS
        + app.get_setting("published_file_fields", [])
        + extra_fields
    )

    latest = {"version_number": -1}
    for result_item in result:
        if result_item["version_number"] > latest["version_number"]:
            latest = result_item

        # Assert that each item returned has the expected keys
        item_keys = result_item.keys()
        for field in fields:
            assert field in item_keys

    if not item.sg_data:
        # Assert the result is an empty list and that the latest published file
        # is unchanged, if the item is invalid (e.g. has no 'sg_data')
        assert result == []
        assert item.latest_published_file == latest_published_file_before_update

    else:
        if result:
            assert item.latest_published_file == latest
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
def test_update_to_latest_version(bundle_fixture, file_item_data):
    """
    Test the Breakdown Manager 'update_to_latest_version' method. This test case
    only validates teh BreakdownManager's functionality, and assumes that the
    bundle's hook method to update the item functions correctly.
    """

    item = FileItem(**file_item_data)
    item_sg_data = file_item_data.get("sg_data", None)
    if item_sg_data is None:
        latest_data = {"version_number": 1}
    else:
        latest_data = item_sg_data
        latest_data["version_number"] = item_sg_data.get("version_number", 0) + 1

    # Set the item's latest published file
    item.latest_published_file = latest_data

    if latest_data.get("path", {}).get("local_path", None):
        # Data is valid, expect the item to be updated to the latest
        should_update = True
    else:
        # Data is invalid, nothing should be updated
        should_update = False
        expected_item_path = item.path
        expected_item_sg_data = item.sg_data

    manager = BreakdownManager(bundle_fixture)
    # Call the method that is to be tested.
    manager.update_to_latest_version(item)

    if should_update:
        assert item.path == latest_data["path"]["local_path"]
        assert item.sg_data == latest_data

    else:
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
def test_update_to_specific_version(bundle_fixture, file_item_data, sg_data):
    """
    Test the Breakdown Manager 'update_to_latest_version' method. This test case
    only validates teh BreakdownManager's functionality, and assumes that the
    bundle's hook method to update the item functions correctly.
    """
    # Scan the scene to get an item to update.
    item = FileItem(**file_item_data)

    # Determine if the item should be updated, based on the validity of the sg_data. Save the original
    # item's data, if the item should not be updated to assert nothing has changed after calling update.
    if not sg_data or not sg_data.get("path", {}).get("local_path", None):
        # Data is invalid, nothing should be updated
        should_update = False
        item_path = item.path
        item_sg_data = item.sg_data

    else:
        should_update = True

    manager = BreakdownManager(bundle_fixture)
    # Call the method that is to be tested
    manager.update_to_specific_version(item, sg_data)

    if should_update:
        assert item.path == sg_data["path"]["local_path"]
        assert item.sg_data == sg_data

    else:
        assert item.path == item_path
        assert item.sg_data == item_sg_data
