# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import sgtk
from tank.errors import TankHookMethodDoesNotExistError

from .item import FileItem
from .. import constants


class BreakdownManager(object):
    """This class is used for managing and executing file updates."""

    def __init__(self, bundle):
        """Initialize the manager."""

        self._bundle = bundle

    @sgtk.LogManager.log_timing
    def get_scene_objects(self, execute_in_main_thread=True):
        """
        Get the current scene objects by executing the scan_scene hook method.

        A list of dictionaries representing the scene references will be returned.
        The return dict value has the following key-values:

            node (str)
                The name of the node which holds the reference.
            type (str)
                The node type.
            path (str)
                The reference file path.
            extra_data (dict)
                Extra data for the reference (optional).

        :param execute_in_main_thread: True will ensure the hook method is executed in the
            main thread, else False will execute in the current thread. Default is True, since
            the scan_scene function will need to execute DCC functionality that likely needs
            to execute in the main thread (e.g. GUI events).
        :type execute_in_main_thread: bool

        :return: A list of scene references.
        :rtype: List[dict]
        """

        if execute_in_main_thread:
            # Ensure that the scan scene operation is executed in the main UI thread. Many
            # apps are sensitive to these types of operations happening in other threads.
            return self._bundle.engine.execute_in_main_thread(
                self._bundle.execute_hook_method, "hook_scene_operations", "scan_scene"
            )

        # Execute in the current thread
        return self._bundle.execute_hook_method("hook_scene_operations", "scan_scene")

    @sgtk.LogManager.log_timing
    def scan_scene(self, extra_fields=None, execute_in_main_thread=True):
        """
        Scan the current scene to return a list of scene references.

        A list of FileItem objects representing the scene references will be returned.

        :param execute_in_main_thread: True will ensure the hook method is executed in the
            main thread, else False will execute in the current thread. Default is True, since
            the scan_scene function will need to execute DCC functionality that likely needs
            to execute in the main thread (e.g. GUI events).
        :type execute_in_main_thread: bool

        :return: A list of scene references.
        :rtype: List[FileItem]
        """

        scene_objects = self.get_scene_objects(
            execute_in_main_thread=execute_in_main_thread
        )
        file_paths = [o["path"] for o in scene_objects]
        published_files = self.get_published_files_from_file_paths(
            file_paths, extra_fields=extra_fields
        )
        return self.get_file_items(scene_objects, published_files)

    @sgtk.LogManager.log_timing
    def get_published_files_from_file_paths(
        self, file_paths, extra_fields=None, bg_task_manager=None
    ):
        """
        Query the Flow Production Tracking API to get the published files for the given file paths.

        :param file_paths: A list of file paths to get the published files from.
        :type file_paths: List[str]
        :param extra_fields: A list of Flow Production Tracking fields to append to the Flow Production Tracking query
                             when retreiving the published files.
        :type extra_fields: List[str]
        :param bg_task_manager: (optional) A background task manager to execute the request
            async. If not provided, the request will be executed synchronously.
        :type: BackgroundTaskManager

        :return: The task id for the request is returned if executed async, else the published
            files data is returned if executed synchronosly.
        :rtype: int | dict
        """

        if not file_paths:
            return None if bg_task_manager else {}

        # Get the published file fields to pass to the query
        fields = self.get_published_file_fields()
        if extra_fields is not None:
            fields += extra_fields

        # Get the published file filters defined in the config to pass to the query
        filters = self.get_published_file_filters()

        # Option to run this in a background task since this can take some time to execute.
        if bg_task_manager:
            # Execute the request async and return the task id for the operation.
            return bg_task_manager.add_task(
                sgtk.util.find_publish,
                task_args=[self._bundle.sgtk, file_paths],
                task_kwargs={
                    "filters": filters,
                    "fields": fields,
                    "only_current_project": False,
                },
            )

        # No background task manager provided, execute the request synchronously and return
        # the published files data immediately.
        return sgtk.util.find_publish(
            self._bundle.sgtk,
            file_paths,
            filters=filters,
            fields=fields,
            only_current_project=False,
        )

    def get_file_items(self, scene_objects, published_files):
        """
        Get the file item objects for the given scene objects.

        Scene objects that do not have a corresponding Flow Production Tracking Published File
        will be omitted from the result (a FileItem will not be created for it).

        The `scene_objects` dict param expects the key-values:

            node (str)
                The name of the node which holds the reference.
            type (str)
                The node type.
            path (str)
                The reference file path.
            extra_data (dict)
                Extra data for the reference (optional).

        :param scene_objects: Objects from the DCC. This value can be the result returned by
            the `scan_scene` method.
        :type scene_objects: dict
        :param published_files: The list of published files corresponding to the
            `scene_objects`. Any scene objects that do not have a matching published will be
            omitted from the result (there will not be a FileItem object created for it). This
            can be the result returned by the `sgtk.util.find_publish` method.
        :type publishehd_files: List[dict]

        :return: A list of FileItem objects representing the scene objects.
        :rtype: List[FileItem]
        """

        file_items = []

        for obj in scene_objects:
            if obj["path"] in published_files:
                file_items.append(
                    FileItem(
                        obj["node_name"],
                        obj["node_type"],
                        obj["path"],
                        sg_data=published_files[obj["path"]],
                        extra_data=obj.get("extra_data"),
                        locked=obj.get("locked", False),
                        loaded=obj.get("loaded", True),
                    )
                )

        return file_items

    def get_published_file_fields(self):
        """
        Get the fields to pass to the query to retrieve the published files when scanning the
        scene.

        :return: The published file fields.
        :rtype: list<str>
        """

        return constants.PUBLISHED_FILES_FIELDS + self._bundle.get_setting(
            "published_file_fields", []
        )

    def get_published_file_filters(self):
        """
        Get additional filters to pass to the query to retrieve the published files when
        scanning the scene.

        :return: The published file filters.
        :rtype: List[List[dict]]
        """

        return self._bundle.get_setting("published_file_filters", [])

    def get_history_published_file_filters(self):
        """
        Get additional filters to pass to the query to retrieve the history published files
        for a given file item.

        :param item: The file item to get the history published file filters for.
        :type item: FileItem

        :return: The history published file filters.
        :rtype: List[List[dict]]
        """

        return self._bundle.get_setting("history_published_file_filters", [])

    def get_latest_published_file(self, item, data_retriever=None, extra_fields=None):
        """
        Get the latest available published file according to the current item context.

        :param item: :class`FileItem` object we want to get the latest published file
        :type item: FileItem
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: The latest published file as a Flow Production Tracking entity dictionary if the request was
            synchronous, else the request background task id if the request was async.
        """

        if not item or not item.sg_data:
            return None if data_retriever else {}

        fields = self.get_published_file_fields()
        if extra_fields:
            fields += extra_fields

        filters = self.get_history_published_file_filters()

        result = self._bundle.execute_hook_method(
            "hook_get_published_files",
            "get_latest_published_file",
            item=item,
            data_retriever=data_retriever,
            extra_fields=fields,
            published_file_filters=filters,
        )

        # Only set the latest published file data if the result was immediately returned.
        if data_retriever is None:
            item.latest_published_file = result

        return result

    def get_published_files_for_items(
        self, items, data_retriever=None, extra_fields=None
    ):
        """
        Get all published files (history) for the given items.

        :param items: the list of :class`FileItem` we want to get published files for.
        :type items: List[FileItem]
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        if not items:
            return None if data_retriever else {}

        fields = self.get_published_file_fields()
        if extra_fields:
            fields += extra_fields

        filters = self.get_history_published_file_filters()

        return self._bundle.execute_hook_method(
            "hook_get_published_files",
            "get_published_files_for_items",
            items=items,
            data_retriever=data_retriever,
            extra_fields=fields,
            published_file_filters=filters,
        )

    def get_published_file_history(self, item, extra_fields=None, data_retriever=None):
        """
        Get the published history for the selected item. It will gather all the published files with the same context
        than the current item (project, name, task, ...)

        :param item: :class`FileItem` object we want to get the published file history
        :type item: FileItem
        :param extra_fields: A list of Flow Production Tracking fields to append to the Flow Production Tracking query fields.
        :type extra_fields: List[str]
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file history.
        :rtype: str | dict
        """

        if not item or not item.sg_data:
            return []

        result = self.get_published_files_for_items(
            [item], data_retriever=data_retriever, extra_fields=extra_fields
        )
        if result and isinstance(result, list):
            item.latest_published_file = result[0]
        return result

    def update_to_latest_version(self, items):
        """
        Update the item to its latest version.

        :param items: The item or items to update.
        :type items: FileItem | List[FileItem]

        :return: The list of file item objects that were updated to the latest version.
        :rtype: List[FileItem]
        """

        if not isinstance(items, list):
            items = [items]

        # First try to execute the hook method to update items in batch for performance.
        try:
            return self.update_items_to_latest_version(items)
        except TankHookMethodDoesNotExistError:
            # Fallback to updating items one by one.
            updated_items = []
            for item in items:
                do_update = self.update_to_specific_version(
                    item, item.latest_published_file
                )
                if do_update:
                    updated_items.append(item)
            return updated_items

    def update_items_to_latest_version(self, items):
        """
        Update the list of items to their respective latest version.

        :param items: The item or items to update.
        :type items: FileItem | List[FileItem]

        :return: The list of file item objectggs that were updated to the latest version.
        :rtype: List[FileItem]
        """

        hook_path = self._bundle.get_setting("hook_scene_operations")
        scene_operation_hook = self._bundle.create_hook_instance(hook_path)
        if not hasattr(scene_operation_hook, "update_items"):
            raise TankHookMethodDoesNotExistError

        # Prepare the items to update
        items_by_dict = {}
        for item in items:
            sg_data = item.latest_published_file
            if not sg_data or not sg_data.get("path", {}).get("local_path", None):
                continue
            item_dict = item.to_dict()
            item_dict["path"] = sg_data["path"]["local_path"]
            if item_dict["extra_data"] is None:
                item_dict["extra_data"] = {"old_path": item.path}
            else:
                item_dict["extra_data"]["old_path"] = item.path
            items_by_dict[item] = item_dict

        # No items to update, return empty list to indicate no further action.
        if not items_by_dict:
            return []

        # Execute the hook to perform the update operation.
        items_to_update = self._bundle.execute_hook_method(
            "hook_scene_operations",
            "update_items",
            items=items_by_dict.values(),
        )

        # Update the FileItem objects model data directly, if specified.
        if items_to_update is None:
            # Default to updating all items
            items_to_update = items

        # The returned items are the FileItem dict representations. We will need to map these
        # back to their FileItem object.
        updated_items = []
        if items_to_update:
            # Only update the file item if specified. Updating the item will affect the data
            # model directly
            for item, item_dict in items_by_dict.items():
                if item not in items_to_update:
                    continue
                item.sg_data = item.latest_published_file
                item.path = item_dict["path"]
                item.extra_data = item_dict["extra_data"]
                updated_items.append(item)

        return updated_items

    def update_to_specific_version(self, item, sg_data):
        """
        Update the item to a specific version.

        :param item: Item to update
        :type item: FileItem
        :param sg_data: Dictionary of Flow Production Tracking data representing the published file we want to update the item to
        :type sg_data: dict

        :return: True if the item requires the data model to update, else False will not
            trigger a model update.
        :rtype: bool
        """

        if not sg_data or not sg_data.get("path", {}).get("local_path", None):
            return False

        item_dict = item.to_dict()
        item_dict["path"] = sg_data["path"]["local_path"]
        if item_dict["extra_data"] is None:
            item_dict["extra_data"] = {"old_path": item.path}
        else:
            item_dict["extra_data"]["old_path"] = item.path

        do_update = self._bundle.execute_hook_method(
            "hook_scene_operations",
            "update",
            item=item_dict,
        )
        if do_update is None:
            # Default to True if the hook return value was not explictly set
            do_update = True

        if do_update:
            # Only update the file item if specified. Updating the item will affect the data
            # model directly
            item.sg_data = sg_data
            item.path = item_dict["path"]
            item.extra_data = item_dict["extra_data"]

        return do_update
