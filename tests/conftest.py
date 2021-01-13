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
import random
import string


@pytest.fixture
def publish_file_path_root():
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def file_item_data(request):
    """
    Create a FileItem object.
    """

    # Generate random data for FileItem. The exact data does not necessarily
    # depict data as expected in production, this is meant to just be used
    # to test the basics of the FileItem class methods.
    any_char = string.ascii_letters + string.digits + string.punctuation
    letters_and_digits = string.ascii_letters + string.digits

    node_name = "".join(random.choice(any_char) for i in range(10))
    node_type = random.choice(["reference", "file"])
    path = "/".join(
        "".join(random.choice(letters_and_digits) for i in range(8)) for j in range(5)
    )

    param = request.param if hasattr(request, "param") else (False, False)
    sg_data = param[0]
    extra_data = param[1]
    if isinstance(sg_data, bool):
        sg_data = (
            {
                "version_number": random.randint(1, 1000),
                "some_field": "".join(random.choice(any_char) for i in range(10)),
            }
            if sg_data
            else None
        )
    if isinstance(extra_data, bool):
        extra_data = (
            {
                "extra_field__key": random.randint(1, 1000),
                "field": "".join(random.choice(any_char) for i in range(10)),
            }
            if extra_data
            else None
        )

    return {
        "node_name": node_name,
        "node_type": node_type,
        "path": path,
        "sg_data": sg_data,
        "extra_data": extra_data,
    }
