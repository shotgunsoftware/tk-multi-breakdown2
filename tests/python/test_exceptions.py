# Copyright (c) 2020 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.


class Breakdown2TestException(Exception):
    """
    Base class for custom exceptions used during testing.

    NOTE: this is not a test class; the file name must be prefixed with 'test'
    in order for pytest to find this module when importing in other test modules.
    """


class InvalidTestData(Breakdown2TestException):
    """
    Raised when there a test fails due to test data not being set up as expected.
    The test function was not able to be executed because of this.
    """
