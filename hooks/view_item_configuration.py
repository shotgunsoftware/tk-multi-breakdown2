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
from sgtk.platform.qt import QtCore, QtGui
from tank.util import sgre as re

HookClass = sgtk.get_hook_baseclass()


class ViewItemConfiguration(HookClass):
    """
    Hook to customize how a view item's data is displayed.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor

        Get the File and File History item configurations from the ui_configuration hook.
        The File and File History item configurations define how to format and display
        the items.

        :param args: The positional arguments to pass to the base constructor.
        :param kwags: The keyword arguments to tpass to the base constructor.
        """

        super(ViewItemConfiguration, self).__init__(*args, **kwargs)

        file_item_config = self.parent.execute_hook_method(
            "hook_ui_configurations", "file_item_details"
        )
        self._title_template_string = file_item_config.get("top_left", "")
        self._subtitle_template_string = file_item_config.get("top_right", "")
        self._details_template_string = file_item_config.get("body", "")
        self._show_thumbnail = file_item_config.get("thumbnail", False)

        file_details_history_config = self.parent.execute_hook_method(
            "hook_ui_configurations", "file_history_details"
        )
        self._history_title_template_string = file_details_history_config.get(
            "top_left", ""
        )
        self._history_subtitle_template_string = file_details_history_config.get(
            "top_right", ""
        )
        self._history_details_template_string = file_details_history_config.get(
            "body", ""
        )
        self._history_show_thumbnail = file_details_history_config.get(
            "thumbnail", False
        )

    def get_item_title(self, item, file_item=None):
        """
        Returns the data to display for this model index item's title.

        If a title template string is defined, return a tuple where the first item is the
        template string and the second item is the Shotgun data to format the template
        string with. This tuple return value may be consumed by the :class:`ViewItemDelegate`
        that will search and replace the tempalte string with the specified values from
        the Shotgun data provided.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: The title for this item.
        :rtype: str | tuple<str,str>
        """

        if file_item:
            if self._title_template_string:
                return (self._title_template_string, file_item.sg_data)

            return item.data(QtCore.Qt.DisplayRole)

        return "<span style='font: 14px;'>{}</span>".format(
            item.data(QtCore.Qt.DisplayRole)
        )

    def get_item_subtitle(self, item, file_item=None):
        """
        Returns the data to display for this model index item's subtitle.

        If a subtitle template string is defined, return a tuple where the first item is the
        template string and the second item is the Shotgun data to format the template
        string with. This tuple return value may be consumed by the :class:`ViewItemDelegate`
        that will search and replace the tempalte string with the specified values from
        the Shotgun data provided.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: The subtitle for this item.
        :rtype: str | tuple<str,str>
        """

        if file_item and self._subtitle_template_string:
            return (self._subtitle_template_string, file_item.sg_data)

        return None

    def get_item_details(self, item, file_item=None):
        """
        Returns the data to display for this model index item's detailed text.

        If a details template string is defined, return a tuple where the first item is the
        template string and the second item is the Shotgun data to format the template
        string with. This tuple return value may be consumed by the :class:`ViewItemDelegate`
        that will search and replace the tempalte string with the specified values from
        the Shotgun data provided.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: The details for this item.
        :rtype: str | tuple<str,str>
        """

        if file_item:
            if self._details_template_string:
                # Search and replace any non-shotgun data fields
                for token in ["NODE_NAME", "PATH"]:
                    self._details_template_string = resolve_tokens(
                        token,
                        getattr(file_item, token.lower()),
                        self._details_template_string,
                    )

                return (self._details_template_string, file_item.sg_data)

            return file_item.sg_data

        return None

    def get_item_thumbnail(self, item, file_item=None):
        """
        Returns the data to display for this model index item's thumbnail.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: The item thumbnail.
        :rtype: :class:`sgtk.platform.qt.QtGui.QPixmap`
        """

        if not self._show_thumbnail:
            return None

        thumbnail = item.data(QtCore.Qt.DecorationRole)
        if isinstance(thumbnail, QtGui.QIcon):
            thumbnail = thumbnail.pixmap(512)

        return thumbnail

    def get_item_icons(self, item, file_item=None):
        """
        Returns the data to display for this model index item's icons.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: Dictionary containing the item's icon data.
        :rtype: dict, format e.g.:
            {
                "float-top-left":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
                "float-top-right":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
                "float-bottom-left":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
                "float-bottom-right":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
            }
        """

        icons = {}

        if not file_item:
            return icons

        if file_item.highest_version_number:
            if file_item.sg_data["version_number"] >= file_item.highest_version_number:
                icons["float-top-left"] = QtGui.QPixmap(
                    ":/tk-multi-breakdown2/green_bullet.png"
                )
            else:
                icons["float-top-left"] = QtGui.QPixmap(
                    ":/tk-multi-breakdown2/red_bullet.png"
                )

        return icons

    def get_item_loading(self, item, file_item=None):
        """
        Returns True to indicate the item is in a loading state, else False.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: True to indicate the item is loading, else False.
        :rtype: bool
        """

        if file_item:
            return not file_item.highest_version_number

        return False

    def get_item_separator(self, item, file_item=None):
        """
        Returns True to indicate the item has a separator, else False. This may be
        used to indicate to the delegate to draw a line separator for the item or not.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: True to indicate the item has a separator, else False.
        :rtype: bool
        """

        # Only group headers have a separator.
        return file_item is None

    def get_item_width(self, item, file_item=None):
        """
        Returns the width for this item. This may be used by the delegate to help
        draw the item as desired. NOTE: if the ViewItemDelegate has a fixed width
        set up, this method will not affect the row width.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: The item rect display width
        :rtype: int
        """

        # Set the width to 375 for File items and set to -1 for Group File items (headers)
        # to expand to the full available width.
        return 375 if file_item else -1

    def get_history_item_title(self, item, sg_data):
        """
        Returns the data to display for this model index item's title. Specifically, a
        tuple will be returned, where item (1) is a template string and item (2) is the
        Shotgun data to format the template string with. This tuple return value may be
        consumed by the :class:`ViewItemDelegate` that will search and replace the tempalte
        string with the specified values from the Shotgun data provided.

        :param item: The model item representing file history item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param sg_data: The Shotgun data associated with this item.
        :type sg_data: dict

        :return: The title data to display.
        :rtype: tuple<str,str>
        """

        if self._history_title_template_string:
            return (self._history_title_template_string, sg_data)

        return None

    def get_history_item_subtitle(self, item, sg_data):
        """
        Returns the data to display for this model index item's subtitle. Specifically, a
        tuple will be returned, where item (1) is a template string and item (2) is the
        Shotgun data to format the template string with. This tuple return value may be
        consumed by the :class:`ViewItemDelegate` that will search and replace the tempalte
        string with the specified values from the Shotgun data provided.

        :param item: The model item representing file history item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param sg_data: The Shotgun data associated with this item.
        :type sg_data: dict

        :return: The subtitle data to display.
        :rtype: tuple<str,str>
        """

        if self._history_subtitle_template_string:
            return (self._history_subtitle_template_string, sg_data)

        return None

    def get_history_item_details(self, item, sg_data):
        """
        Returns the data to display for this model index item's details. Specifically, a
        tuple will be returned, where item (1) is a template string and item (2) is the
        Shotgun data to format the template string with. This tuple return value may be
        consumed by the :class:`ViewItemDelegate` that will search and replace the tempalte
        string with the specified values from the Shotgun data provided.

        :param item: The model item representing file history item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param sg_data: The Shotgun data associated with this item.
        :type sg_data: dict

        :return: The details data to display.
        :rtype: tuple<str,str>
        """

        if self._history_details_template_string:
            return (self._history_details_template_string, sg_data)

        return None

    def get_history_item_thumbnail(self, item, sg_data):
        """
        Returns the data to display for this model index item's thumbnail.

        :param item: The model item representing file history item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param sg_data: The Shotgun data associated with this item.
        :type sg_data: dict

        :return: The item thumbnail.
        :rtype: :class:`sgtk.platform.qt.QtGui.QPixmap`
        """

        thumbnail = None

        if self._history_show_thumbnail:
            thumbnail = item.data(QtCore.Qt.DecorationRole)
            if thumbnail:
                thumbnail = thumbnail.pixmap(512)
            else:
                # Return empty pixamp to indicate that a thumbnail should be drawn but the item
                # does not specifically have one.
                thumbnail = QtGui.QPixmap()

        return thumbnail


def resolve_tokens(token, value, text):
    """
    Helper method to search and replace tokens in the given string.

    :param token: The token string to search for.
    :type token: str
    :param value: The value to replace the token string with.
    :type value: str
    :param text: The string to search and replace tokens in.
    :type text: str
    :return: The text string with all tokens replaced.
    :rtype: str
    """

    pattern = "{{<{pattern}>}}".format(pattern=token)
    value = value.replace("\\", "\\\\")
    return re.sub(pattern, r"{}".format(value), text)
