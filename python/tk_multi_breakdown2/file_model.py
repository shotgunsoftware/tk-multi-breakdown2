# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtGui, QtCore

shotgun_data = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_data"
)
ShotgunDataRetriever = shotgun_data.ShotgunDataRetriever


class FileModel(QtGui.QStandardItemModel):
    """
    """

    # additional data roles defined for the model:
    FILE_ITEM_ROLE = QtCore.Qt.UserRole + 32

    class GroupModelItem(QtGui.QStandardItem):
        """
        """

        def __init__(self, text):
            """
            :param text:
            """
            QtGui.QStandardItem.__init__(self, text)

    class FileModelItem(QtGui.QStandardItem):
        """
        """

        def __init__(self, text):
            """
            """

            QtGui.QStandardItem.__init__(self, text)

    def __init__(self, bg_task_manager, parent):
        """
        :param parent:
        """

        QtGui.QStandardItemModel.__init__(self, parent)

        self._app = sgtk.platform.current_bundle()
        self._group_items = {}
        self._pending_thumbnail_requests = {}
        self._pending_version_requests = {}

        self._manager = self._app.create_breakdown_manager()

        self._bg_task_manager = bg_task_manager
        self._bg_task_manager.task_completed.connect(self._on_background_task_completed)
        self._bg_task_manager.task_failed.connect(self._on_background_task_failed)
        # self._bg_task_manager.task_group_finished.connect(self._on_background_search_finished)

        # sg data retriever is used to download thumbnails in the background
        self._sg_data_retriever = ShotgunDataRetriever(bg_task_manager=bg_task_manager)
        self._sg_data_retriever.work_completed.connect(self._on_data_retriever_work_completed)
        self._sg_data_retriever.work_failure.connect(self._on_data_retriever_work_failed)

    def destroy(self):
        """
        Called to clean-up and shutdown any internal objects when the model has been finished
        with.  Failure to call this may result in instability or unexpected behaviour!
        """
        # clear the model:
        self.clear()

        # stop the data retriever:
        if self._sg_data_retriever:
            self._sg_data_retriever.stop()
            self._sg_data_retriever.deleteLater()
            self._sg_data_retriever = None

        # shut down the task manager
        if self._bg_task_manager:
            self._bg_task_manager.task_completed.disconnect(self._on_background_task_completed)
            self._bg_task_manager.task_failed.disconnect(self._on_background_task_failed)
            # self._bg_task_manager.task_group_finished.disconnect(self._on_background_search_finished)

    def process_files(self):
        """
        :return:
        """

        file_items = self._manager.scan_scene()

        for file_item in file_items:

            if not file_item.sg_data:
                continue

            # group scene object by project
            project = file_item.sg_data["project"]
            if project["id"] not in self._group_items.keys():
                group_item = FileModel.GroupModelItem(project["name"])
                self.invisibleRootItem().appendRow(group_item)
                self._group_items[project["id"]] = group_item
            else:
                group_item = self._group_items[project["id"]]

            file_model_item = FileModel.FileModelItem("")
            file_model_item.setData(file_item, FileModel.FILE_ITEM_ROLE)
            group_item.appendRow(file_model_item)

            task_id = self._bg_task_manager.add_task(
                self._manager.get_file_history,
                task_kwargs={"item": file_item},
            )
            self._pending_version_requests[task_id] = file_model_item

            # finally, download the thumbnail
            if file_item.sg_data.get("image"):
                request_id = self._sg_data_retriever.request_thumbnail(
                    file_item.sg_data["image"],
                    file_item.sg_data["type"],
                    file_item.sg_data["id"],
                    "image",
                )
                self._pending_thumbnail_requests[request_id] = file_model_item

    def _on_data_retriever_work_completed(self, uid, request_type, data):
        """
        Slot triggered when the data-retriever has finished doing some work.  The data retriever is currently
        just used to download thumbnails for published files so this will be triggered when a new thumbnail
        has been downloaded and loaded from disk.

        :param uid:             The unique id representing a task being executed by the data retriever
        :param request_type:    A string representing the type of request that has been completed
        :param data:            The result from completing the work
        """
        if uid not in self._pending_thumbnail_requests:
            return
        file_model_item = self._pending_thumbnail_requests[uid]
        del self._pending_thumbnail_requests[uid]

        thumb_path = data.get("thumb_path")
        if thumb_path:
            file_model_item.setIcon(QtGui.QPixmap(thumb_path))
            file_model_item.emitDataChanged()

    def _on_data_retriever_work_failed(self, uid, error_msg):
        """
        Slot triggered when the data retriever fails to do some work!

        :param uid:         The unique id representing the task that the data retriever failed on
        :param error_msg:   The error message for the failed task
        """
        if uid in self._pending_thumbnail_requests:
            del self._pending_thumbnail_requests[uid]
        self._app.log_debug(
            "File Model: Failed to find thumbnail for id %s: %s" % (uid, error_msg)
        )

    def _on_background_task_completed(self, uid, group_id, result):
        """
        """
        if uid not in self._pending_version_requests:
            return
        file_model_item = self._pending_version_requests[uid]
        del self._pending_version_requests[uid]

        file_model_item.emitDataChanged()

    def _on_background_task_failed(self, uid, group_id, msg, stack_trace):
        """
        """
        if uid in self._pending_version_requests:
            del self._pending_version_requests[uid]
        self._app.log_debug(
            "File Model: Failed to find highest version number for id %s: %s" % (uid, msg)
        )
