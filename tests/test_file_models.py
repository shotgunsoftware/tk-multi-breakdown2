# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import pytest
import os
import datetime

import sgtk
from tank_test.tank_test_base import setUpModule  # noqa

from app_test_base import AppTestBase

try:
    from sgtk.platform.qt import QtCore, QtGui
except:
    # components also use PySide, so make sure  we have this loaded up correctly
    # before starting auto-doc.
    from tank.util.qt_importer import QtImporter

    importer = QtImporter()
    sgtk.platform.qt.QtCore = importer.QtCore
    sgtk.platform.qt.QtGui = importer.QtGui
    from sgtk.platform.qt import QtCore, QtGui


class TestFileModels(AppTestBase):
    """
    Test the breakdown2 FileModel class.
    """

    def setUp(self):
        """Fixtures setup."""

        super(TestFileModels, self).setUp()

        self.FileModel = self.tk_multi_breakdown2.FileModel
        self.file_model = self.FileModel(None, self.bg_task_manager)
        self.addCleanup(self.file_model.destroy)

        self.FileProxyModel = self.tk_multi_breakdown2.FileProxyModel
        self.file_proxy_model = self.FileProxyModel(None)
        self.file_proxy_model.setSourceModel(self.file_proxy_model)

        self.FileHiistoryModel = self.tk_multi_breakdown2.FileHiistoryModel
        self.file_history_model = self.FileHiistoryModel(None, self.bg_task_manager)

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

    def test_status_icons(self):
        """Test the get_status_icon method."""

        # There should be no icon for the 'none' status
        icon = self.file_model.get_status_icon(self.file_model.STATUS_NONE)
        assert not icon

        icon = self.file_model.get_status_icon(self.file_model.STATUS_UP_TO_DATE)
        assert icon
        assert isinstance(icon, QtGui.QIcon)

        icon = self.file_model.get_status_icon(self.file_model.STATUS_OUT_OF_SYNC)
        assert icon
        assert isinstance(icon, QtGui.QIcon)

        icon = self.file_model.get_status_icon(self.file_model.STATUS_LOCKED)
        assert icon
        assert isinstance(icon, QtGui.QIcon)

    def test_process_files(self):
        """Test the process files method."""

        assert self.file_model.rowCount() == 0
        self.file_model.process_files()

        # Based on the data the hook returns and the published files created in the set up,
        # the model should have created one group (since all published files are in the
        # same project), and three file item children
        assert self.file_model.rowCount() == 1
        # NOTE the project group QStandardItem has a null child at index 0 on creation, this
        # seems like a Qt oddity? Will be somethign to keep an eye on...
        assert self.file_model.rowCount(self.file_model.index(0, 0)) == 3 + 1
