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

        # FIXME update this icon, just using whatever we have available at the moment.
        self._unloaded_ref_icon = QtGui.QIcon(":/tk-multi-breakdown2/red_bullet.png")

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

        self._short_text_template_string = "<br/>".join(
            [
                # "<span style='font-size: 13px; font-weight: bold;'>{name}</span>",
                "<span style='color: rgba(200, 200, 200, 40%);'>{published_file_type.PublishedFileType.code}</span>",
                # "<span style='color: rgba(200, 200, 200, 40%);'>{sg_status_list::text::icon}</span>",
            ]
        )

    @staticmethod
    def get_file_item(index):
        """
        Convenience method to get the file item data from the index.
        """

        if not index.isValid():
            return None

        try:
            role = index.model().FILE_ITEM_ROLE
            return index.data(role)
        except AttributeError:
            # Let this error go, and try to get the file item from the source model.
            pass

        try:
            role = index.model().sourceModel().FILE_ITEM_ROLE
            return index.data(role)

        except AttributeError:
            raise sgtk.TankError(
                "Model '{model_class}' does not have specified role 'FILE_ITEM_ROLE".format(
                    model_class=index.model().__class__.__name__
                )
            )

    def get_item_title(self, index):
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

        file_item = self.get_file_item(index)
        if file_item:
            if self._title_template_string:
                # Search and replace any non-shotgun data fields
                template_string = _resolve_file_item_tokens(
                    file_item, self._title_template_string
                )
                return (template_string, file_item.sg_data)

            return index.data(QtCore.Qt.DisplayRole)

        return "<span style='font-size: 14px; font-weight: bold;'>{}</span>".format(
            index.data(QtCore.Qt.DisplayRole)
        )

    def get_item_subtitle(self, index):
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

        subtitle = None
        file_item = self.get_file_item(index)

        if file_item:
            if self._subtitle_template_string:
                # Search and replace any non-shotgun data fields
                template_string = _resolve_file_item_tokens(
                    file_item, self._subtitle_template_string
                )
                subtitle = (template_string, file_item.sg_data)

        else:
            # Group header item
            try:
                # This will raise an Attribute error if this is not a proxy model
                source_model = index.model().sourceModel()
                # The index passed is from the proxy model
                proxy_model = index.model()
                proxy_index = index
                source_index = proxy_model.mapToSource(index)
                proxy_rows = proxy_model.rowCount(proxy_index)
                source_rows = source_model.rowCount(source_index)
            except AttributeError:
                # This is the source index, no proxy model.
                source_model = index.model()
                source_index = index
                source_rows = source_model.rowCount(source_index)
                proxy_model = None
                proxy_rows = 0
                proxy_index = None

            if not source_rows:
                subtitle = "NO FILES FOUND"

            else:
                loaded = 0
                source_out_of_sync = 0
                for row in range(source_rows):
                    child_index = source_model.index(row, 0, source_index)

                    status = child_index.data(source_model.STATUS_ROLE)
                    if status == source_model.STATUS_OUT_OF_SYNC:
                        source_out_of_sync += 1

                    is_loading = child_index.data(source_model.VIEW_ITEM_LOADING_ROLE)
                    if not is_loading:
                        loaded += 1

                out_of_sync_str = None
                if loaded < source_rows:
                    # Show how many files are still loading.
                    total_files_str = "LOADING {loaded} of {total} FILES".format(
                        loaded=loaded,
                        total=source_rows,
                    )
                else:
                    # Check if there are any filters applied, and indicate how many are shown of the total.
                    proxy_out_of_sync = 0
                    for row in range(proxy_rows):
                        child_index = proxy_model.index(row, 0, proxy_index)
                        # The status role and enum are defined on the source model
                        status = child_index.data(source_model.STATUS_ROLE)
                        if status == source_model.STATUS_OUT_OF_SYNC:
                            proxy_out_of_sync += 1

                    if proxy_rows != source_rows:
                        total_files_str = (
                            "SHOWING {proxy_count} OF {total_count} FILES".format(
                                proxy_count=proxy_rows, total_count=source_rows
                            )
                        )
                    else:
                        # There are no filters applied
                        total_files_str = "{total} FILES".format(total=source_rows)

                    if source_out_of_sync > 0:
                        if proxy_out_of_sync != source_out_of_sync:
                            out_of_sync_str = "{proxy_out_of_sync} OF {total_out_of_sync} OUT OF DATE".format(
                                proxy_out_of_sync=proxy_out_of_sync,
                                total_out_of_sync=source_out_of_sync,
                            )
                        else:
                            out_of_sync_str = "{out_of_sync} OUT OF DATE".format(
                                out_of_sync=source_out_of_sync
                            )

                text_items = [
                    "<span style='color: rgba(200, 200, 200, 40%);'>{}</span>".format(
                        total_files_str
                    ),
                ]
                if out_of_sync_str:
                    text_items.append(out_of_sync_str)

                join_char = "<span style='color: rgba(200, 200, 200, 40%);'> | </span>"
                subtitle = join_char.join(text_items)

        return subtitle

    def get_item_details(self, index):
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

        file_item = self.get_file_item(index)
        if file_item:
            if self._details_template_string:
                # Search and replace any non-shotgun data fields
                template_string = _resolve_file_item_tokens(
                    file_item, self._details_template_string
                )
                return (template_string, file_item.sg_data)

            return file_item.sg_data

        return None

    def get_item_short_text(self, index):
        """
        Returns the short text data to display for this model index item.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: The short text for this item.
        :rtype: str | tuple<str,str>
        """

        file_item = self.get_file_item(index)
        if file_item and self._short_text_template_string:
            # Search and replace any non-shotgun data fields
            template_string = _resolve_file_item_tokens(
                file_item, self._short_text_template_string
            )
            return (template_string, file_item.sg_data)

        return None

    def get_item_thumbnail(self, index):
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

        thumbnail = index.data(QtCore.Qt.DecorationRole)
        if isinstance(thumbnail, QtGui.QIcon):
            thumbnail = thumbnail.pixmap(512)

        return thumbnail

    def get_item_icons(self, index):
        """
        Returns the data to display for this model index item's icons. Default implementation
        does not show any icon badges over the thumbnail.

        :param item: The model item.
        :type item: :class:`FileModelItem` | :class:`GroupModelItem`
        :param file_item: The FileItem associated with the item. This will be None
                          for :class:`GroupModelItem` items.
        :type file_item: :class:`FileItem`

        :return: Dictionary containing the item's icon data.
        :rtype: dict
        """

        icons = {}

        file_item = self.get_file_item(index)
        if file_item:
            role = index.model().REFERENCE_LOADED
            is_local = index.data(role)
            if not is_local:
                icons["bottom-right"] = {
                    "pixmap": self._unloaded_ref_icon,
                    "inset": True,
                }

        return icons

    def get_item_separator(self, index):
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

        file_item = self.get_file_item(index)

        # Only group headers have a separator.
        return file_item is None

    def get_item_width(self, index):
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

        file_item = self.get_file_item(index)

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

    def get_history_item_icons(self, item, sg_data):
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
                "top-left":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
                "top-right":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
                "bottom-left":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
                "bottom-right":
                    :class:`sgtk.platform.qt.QtGui.QPixmap`,
            }
        """

        icons = {}

        badge_icon = item.data(item.model().BADGE_ROLE)
        if badge_icon:
            icons["top-right"] = {
                "pixmap": badge_icon,
                "inset": False,
            }

        return icons

    def get_history_item_separator(self, item, sg_data):
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

        # NOTE uncomment to draw separtor above current version, when it is not the latest
        # TODO delegate to handle decorations when drawing the separator
        # status = item.data(item.model().STATUS_ROLE)
        # show_separator = status is not None and status != item.model().STATUS_UP_TO_DATE

        # if show_separator:
        #     return {
        #         "position": "top",
        #         "decorations": {
        #             "left": "New"
        #         }
        #     }

        return False


def _resolve_tokens(token, value, text):
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


def _resolve_file_item_tokens(file_item, template_string):
    """
    Convenience method to resolve any File item (non-shotgun) specific fields.
    """

    for token in ["NODE_NAME", "PATH"]:
        template_string = _resolve_tokens(
            token,
            getattr(file_item, token.lower()),
            template_string,
        )

    return template_string
