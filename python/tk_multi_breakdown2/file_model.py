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
    The FileModel maintains a model of all the files found when parsing the current scene. Details of each file are
    contained in a FileItem instance and presented as a single model item.

    File items are grouped into groups defined by the app configuration.
    """

    # additional data roles defined for the model:
    FILE_ITEM_ROLE = QtCore.Qt.UserRole + 32

    files_processed = QtCore.Signal()

    class GroupModelItem(QtGui.QStandardItem):
        """
        Model item that represents a group in the model.
        """

        def __init__(self, text):
            """
            :param text: String used for the label/display role for this item
            """
            QtGui.QStandardItem.__init__(self, text)

    class FileModelItem(QtGui.QStandardItem):
        """
        Model item that represents a single FileItem in the model.
        """

        def __init__(self, text):
            """
            :param text: String used for the label/display role for this item
            """

            QtGui.QStandardItem.__init__(self, text)

    def __init__(self, bg_task_manager, parent):
        """
        :param bg_task_manager: A BackgroundTaskManager instance that will be used for all background/threaded
                                work that needs undertaking
        :param parent:          The parent QObject for this instance
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

        # sg data retriever is used to download thumbnails in the background
        self._sg_data_retriever = ShotgunDataRetriever(bg_task_manager=bg_task_manager)
        self._sg_data_retriever.work_completed.connect(self._on_data_retriever_work_completed)
        self._sg_data_retriever.work_failure.connect(self._on_data_retriever_work_failed)

    def destroy(self):
        """
        Called to clean-up and shutdown any internal objects when the model has been finished
        with. Failure to call this may result in instability or unexpected behaviour!
        """

        # clear the model
        self.clear()

        # stop the data retriever
        if self._sg_data_retriever:
            self._sg_data_retriever.stop()
            self._sg_data_retriever.deleteLater()
            self._sg_data_retriever = None

        # shut down the task manager
        if self._bg_task_manager:
            self._bg_task_manager.task_completed.disconnect(self._on_background_task_completed)
            self._bg_task_manager.task_failed.disconnect(self._on_background_task_failed)

    def process_files(self):
        """
        Scan the current scene to get all the items we could perform actions on and for each item, build a model item
        and a data structure to represent them.
        """

        # scan the current scene
        file_items = self._manager.scan_scene()

        for file_item in file_items:

            # if the item doesn't have any associated shotgun data, it means that the file is not a Published File so
            # skip it
            if not file_item.sg_data:
                continue

            # group scene object by project
            # todo: use an app setting to be able to group scene object by another Shotgun field
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

            # for each item, we need to determine the latest version in order to know if the file is up-to-date or not
            task_id = self._bg_task_manager.add_task(
                self._manager.get_latest_published_file,
                task_kwargs={"item": file_item},
            )
            self._pending_version_requests[task_id] = file_model_item

            # finally, download the file thumbnail
            if file_item.sg_data.get("image"):
                request_id = self._sg_data_retriever.request_thumbnail(
                    file_item.sg_data["image"],
                    file_item.sg_data["type"],
                    file_item.sg_data["id"],
                    "image",
                )
                self._pending_thumbnail_requests[request_id] = file_model_item

        self.files_processed.emit()

    def _on_data_retriever_work_completed(self, uid, request_type, data):
        """
        Slot triggered when the data-retriever has finished doing some work. The data retriever is currently
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
        Slot triggered when the background manager has finished doing some task. The only task we're asking the manager
        to do is to find the latest published file associated to the current item.

        :param uid:      Unique id associated with the task
        :param group_id: The group the task is associated with
        :param result:   The data returned by the task
        """
        if uid not in self._pending_version_requests:
            return
        file_model_item = self._pending_version_requests[uid]
        del self._pending_version_requests[uid]

        file_model_item.emitDataChanged()

    def _on_background_task_failed(self, uid, group_id, msg, stack_trace):
        """
        Slot triggered when the background manager fails to do some task.

        :param uid:         Unique id associated with the task
        :param group_id:    The group the task is associated with
        :param msg:         Short error message
        :param stack_trace: Full error traceback
        """
        if uid in self._pending_version_requests:
            del self._pending_version_requests[uid]
        self._app.log_debug(
            "File Model: Failed to find the latest published file for id %s: %s" % (uid, msg)
        )
