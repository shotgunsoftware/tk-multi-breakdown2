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

HookBaseClass = sgtk.get_hook_baseclass()


class GetPublishedFiles(HookBaseClass):
    """Hook to specify the query to retrieve Published Files for the app."""

    def get_published_files_for_items(self, items, data_retriever=None):
        """
        Make an API request to get all published files for the given file items.

        :param items: a list of :class`FileItem` we want to get published files for.
        :type items: List[FileItem]
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        if not items:
            return {}

        # Build the filters to get all published files for at once for all the file items.
        entities = []
        names = []
        tasks = []
        none_entity = False
        none_task = False
        pf_types = []
        for file_item in items:
            # Required published file fields are name and published file type. There will be
            # an api error if these are not set.
            names.append(file_item.sg_data["name"])
            pf_types.append(file_item.sg_data["published_file_type"])

            # Optional fields are linked entity and task.
            entity = file_item.sg_data["entity"]
            if entity:
                entities.append(entity)
            else:
                none_entity = True

            task = file_item.sg_data["task"]
            if task:
                tasks.append(task)
            else:
                none_task = True

        # Build the entity filters
        entity_filters = []
        if entities:
            entity_filters.append(["entity", "in", entities])
        if none_entity:
            entity_filters.append(["entity", "is", None])

        # Build the task filters
        task_filters = []
        if tasks:
            task_filters.append(["task", "in", tasks])
        if none_task:
            task_filters.append(["task", "is", None])

        # Published files will be found by their entity, name, task and published file type.
        filters = [
            ["name", "in", names],
            ["published_file_type", "in", pf_types],
            {
                "filter_operator": "any",
                "filters": entity_filters,
            },
            {
                "filter_operator": "any",
                "filters": task_filters,
            },
        ]

        # Get the query fields. This assumes all file items in the list have the same fields.
        fields = list(items[0].sg_data.keys()) + ["version_number", "path"]
        order = [{"field_name": "version_number", "direction": "desc"}]

        if data_retriever:
            # Execute async and return the background task id.
            return data_retriever.execute_find(
                "PublishedFile",
                filters=filters,
                fields=fields,
                order=order,
            )

        # No data retriever, execute synchronously and return the published file data result.
        return self.sgtk.shotgun.find(
            "PublishedFile",
            filters=filters,
            fields=fields,
            order=order,
        )

    def get_latest_published_file(self, item, data_retriever=None, **kwargs):
        """
        Query Flow Production Tracking to get the latest published file for the given item.

        :param item: :class`FileItem` object we want to get the latest published file for
        :type item: :class`FileItem`
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        filters = [
            ["entity", "is", item.sg_data["entity"]],
            ["name", "is", item.sg_data["name"]],
            ["task", "is", item.sg_data["task"]],
            ["published_file_type", "is", item.sg_data["published_file_type"]],
        ]
        fields = list(item.sg_data.keys()) + ["version_number", "path"]
        order = [{"field_name": "version_number", "direction": "desc"}]

        # todo: check if this work with url published files
        # todo: need to check for path comparison?
        if data_retriever:
            result = data_retriever.execute_find_one(
                "PublishedFile",
                filters=filters,
                fields=fields,
                order=order,
            )
        else:
            result = self.sgtk.shotgun.find_one(
                "PublishedFile",
                filters=filters,
                fields=fields,
                order=order,
            )

        return result
