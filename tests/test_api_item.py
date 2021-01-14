# Copyright (c) 2020 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import os
import pytest
import sys

# Manually add the app modules to the path in order to import them here.
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
app_dir = os.path.abspath(os.path.join(base_dir, "tk_multi_breakdown2"))
api_dir = os.path.abspath(os.path.join(app_dir, "api"))
sys.path.extend([base_dir, app_dir, api_dir])
from tk_multi_breakdown2.api.item import FileItem


class TestApiItem:
    """
    Test the FileItem class methods.
    """

    @pytest.mark.parametrize(
        "file_item_data",
        [(False, False), (True, False), (False, True), (True, True)],
        indirect=["file_item_data"],
    )
    def test_file_item_constructor(
        self, file_item_required_fields, file_item_optional_fields, file_item_data
    ):
        """
        Test the FileItem constructor.
        """

        kwargs = {}
        for field in file_item_required_fields:
            kwargs[field] = file_item_data[field]
        for field in file_item_optional_fields:
            if file_item_data[field] is not None:
                kwargs[field] = file_item_data[field]

        file_item = FileItem(**kwargs)
        assert file_item.node_name == file_item_data["node_name"]
        assert file_item.node_type == file_item_data["node_type"]
        assert file_item.path == file_item_data["path"]
        assert file_item.sg_data == file_item_data["sg_data"]
        assert file_item.extra_data == file_item_data["extra_data"]
        assert file_item.latest_published_file is None

    @pytest.mark.parametrize(
        "latest_published_file",
        [
            None,
            {"id": 1, "no_version_number": 3},
            {"id": 2, "type": "PublishedFile", "version_number": 5},
        ],
    )
    def test_highest_version_number(self, file_item_data, latest_published_file):
        """
        Test the highest_version_number property value.
        """

        file_item = FileItem(**file_item_data)

        if latest_published_file is not None:
            file_item.latest_published_file = latest_published_file

        if not isinstance(latest_published_file, dict):
            assert file_item.highest_version_number is None
        else:
            assert file_item.highest_version_number == latest_published_file.get(
                "version_number", None
            )

    @pytest.mark.parametrize(
        "file_item_data",
        [(False, False), (True, False), (False, True), (True, True)],
        indirect=["file_item_data"],
    )
    def test_to_dict(self, file_item_data):
        """
        Test the to_dict method.
        """

        expected_fields = ["node_name", "node_type", "path", "extra_data"]
        excluded_fields = ["sg_data", "latest_published_file"]

        file_item = FileItem(**file_item_data)
        file_item_dict = file_item.to_dict()

        for field in expected_fields:
            assert file_item_dict[field] == getattr(file_item, field)

        file_item_dict_keys = file_item_dict.keys()
        for field in excluded_fields:
            assert field not in file_item_dict_keys
