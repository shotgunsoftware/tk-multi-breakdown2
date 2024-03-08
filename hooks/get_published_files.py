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

    def get_published_files_for_items(self, items, data_retriever=None, extra_fields=None, published_file_filters=None):
        """
        Make an API request to get all published files for the given file items.

        :param items: a list of :class`FileItem` we want to get published files for.
        :type items: List[FileItem]
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever
        :param filters: Additional filters to apply to the published file query.
        :type filters: List[List[str]]

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        # Get the filters to query published files for the given items.
        filters = self.get_published_file_filters_for_items(items)
        if published_file_filters:
            filters.extend(published_file_filters)

        # Get the query fields. This assumes all file items in the list have the same fields.
        fields = list(items[0].sg_data.keys()) + ["version_number", "path"]
        fields += extra_fields

        # Order the results by version number in descending order, such that the latest version
        # is the first result.
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
        Query ShotGrid to get the latest published file for the given item.

        :param item: :class`FileItem` object we want to get the latest published file for
        :type item: :class`FileItem`
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        published_file_filters = kwargs.get("published_file_filters", [])
        extra_fields = kwargs.get("extra_fields", [])

        # Get the filters to query published files for the given items.
        filters = self.get_published_file_filters_for_items([item])
        if published_file_filters:
            filters.extend(published_file_filters)

        # Get the query fields. This assumes all file items in the list have the same fields.
        fields = list(item.sg_data.keys()) + ["version_number", "path"]
        fields += extra_fields

        # Order the results by version number in descending order, such that the latest version
        # is the first result.
        order = [{"field_name": "version_number", "direction": "desc"}]

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

    def get_published_file_filters_for_items(self, items):
        """
        Get published file filters based on the given items.

        The filters returned can be used to query for published files that belong to the given
        items.

        :param items: a list of :class`FileItem` we want to get published files for.
        :type items: List[FileItem]

        :return: The published file filters.
        :rtype: List
        """

        if not items:
            return []
        
        # Build the filters to get all published files for at once for all the file items.
        entities = []
        names = []
        tasks = []
        none_entity = False
        none_task = False
        pf_types = []

        filters_by_project = {}

        for file_item in items:
            project_id = file_item.sg_data["project"]["id"]
            filters_by_project.setdefault(project_id, {})

            # Required published file fields are name and published file type. There will be
            # an api error if these are not set.
            filters_by_project[project_id].setdefault("names", []).append(file_item.sg_data["name"])

            filters_by_project[project_id].setdefault("published_file_types", []).append(file_item.sg_data["published_file_type"])

            # Optional fields are linked entity and task.
            entity = file_item.sg_data["entity"]
            if entity:
                filters_by_project[project_id].setdefault("entities", []).append(entity)
            else:
                filters_by_project[project_id]["none_entity"] = True

            task = file_item.sg_data["task"]
            if task:
                filters_by_project[project_id].setdefault("tasks", []).append(task)
            else:
                filters_by_project[project_id]["none_task"] = True

        filters = []
        for project_id, project_filters in filters_by_project.items():
            names = project_filters.get("names", [])
            pf_types = project_filters.get("published_file_types", [])
            
            # Build the entity filters
            entities = project_filters.get("entities", [])
            none_entity = project_filters.get("none_entity", False)
            entity_filters = []
            if entities:
                entity_filters.append(["entity", "in", entities])
            if none_entity:
                entity_filters.append(["entity", "is", None])

            # Build the task filters
            tasks = project_filters.get("tasks", [])
            none_task = project_filters.get("none_task", False)
            task_filters = []
            if tasks:
                task_filters.append(["task", "in", tasks])
            if none_task:
                task_filters.append(["task", "is", None])

            # Published files will be found by their entity, name, task and published file type.
            filters.append({
                "filter_operator": "all",
                "filters": [
                    ["project.Project.id", "is", project_id],
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
                ],
            })

        return [
            {
                "filter_operator": "any",
                "filters": filters,
            },
        ]
