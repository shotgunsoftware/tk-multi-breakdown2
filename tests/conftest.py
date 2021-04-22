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
import random
import string
import pytest


@pytest.fixture(scope="session")
def storage_root_path():
    """
    The storage root path for test modules that do not create an actual stoage
    root object. This path could be anything, this is just to ensure that the
    same path is used for testing.
    """

    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="session")
def file_item_required_fields():
    """
    Return the list of FileItem attributes that are initialized on create.
    """

    return ["node_name", "node_type", "path"]


@pytest.fixture(scope="session")
def file_item_optional_fields():
    """
    Return the list of FileItem attribuets that may or may not be initialized on create.
    """

    return ["sg_data", "extra_data"]


@pytest.fixture
def file_item_data(request):
    """
    Return a FileItem data that can be used to create a new FileItem object. The
    data is mostly randomly generated, since the this fixture is mainly used for
    convenience to strictly test the API functionality (does not need to validate
    the actual data).

    The request param may include 'sg_data' to provide more realistic data for
    testing:

    :param request: pytest fixture that provides information for the test function
    that requested this fixture. The request will have a 'param' attribute that
    contains a list of parmas passed by the test function. In this case, param may
    have up to two items, (1) sg_data and (2) extra_data.
    """

    # Random character sets to generate random data from
    any_char = string.ascii_letters + string.digits + string.punctuation
    letters_and_digits = string.ascii_letters + string.digits

    node_name = "".join(random.choice(any_char) for i in range(10))
    node_type = random.choice(["reference", "file"])
    path = "/".join(
        "".join(random.choice(letters_and_digits) for i in range(8)) for j in range(5)
    )

    # Use the sg_data and extra_data params, if passed in, else generate random data.
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
