# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from .framework_qtwidgets import utils


def get_ui_published_file_fields(app):
    """
    Returns a list of ShotGrid fields we want to retrieve when querying ShotGrid. We're going through each widget
    configuration in order to be sure to have all the necessary data to fill the fields.

    :param app: The app we're running the command from
    :returns: A list of ShotGrid Published File fields
    """

    fields = []

    # in order to be able to return all the needed ShotGrid fields, we need to look for the way the UI is configured
    file_item_config = app.execute_hook_method("hook_ui_config", "file_item_details")

    fields += utils.resolve_sg_fields(file_item_config.get("top_left"))
    fields += utils.resolve_sg_fields(file_item_config.get("top_right"))
    fields += utils.resolve_sg_fields(file_item_config.get("body"))
    if file_item_config["thumbnail"]:
        fields.append("image")

    main_file_history_config = app.execute_hook_method(
        "hook_ui_config", "main_file_history_details"
    )

    fields += utils.resolve_sg_fields(main_file_history_config.get("header"))
    fields += utils.resolve_sg_fields(main_file_history_config.get("body"))
    if main_file_history_config["thumbnail"] and "image" not in fields:
        fields.append("image")

    file_history_config = app.execute_hook_method(
        "hook_ui_config", "file_history_details"
    )

    fields += utils.resolve_sg_fields(file_history_config.get("top_left"))
    fields += utils.resolve_sg_fields(file_history_config.get("top_right"))
    fields += utils.resolve_sg_fields(file_history_config.get("body"))
    if file_history_config["thumbnail"] and "image" not in fields:
        fields.append("image")

    return list(set(fields))
