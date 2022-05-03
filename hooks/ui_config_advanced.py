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


class UIConfigAdvanced(HookClass):
    """
    TODO decide whether or not to include this hook, or move it into the application code.

    This is an advanced hook to customize the UI. For a simple hook to customize the data
    and formatting that is shown in the file and file history history views, see the
    UIConfig hook class (ui_config.py).

    This advanced hook allows the most flexibility in customzing the UI. While the simplified
    hook defines what data is shown and how it is formatted, these advanced hook provide a
    way to apply additional logic to alter how the views are displayed. For example, the
    get_item_separator method checks whether or not the item is a group header or a regular
    file item when deciding to draw a line separator for the item. A more complex example
    can be found in get_item_subtitle, where the source and prooxy file models are parsed to
    be able to display the total number of files, as well as how many are currently filtered.
    These methods will call the simplified hook to get what data to display, and then apply
    any further logic/processing before dispalying it.

    The methods in this hook are called from the FileModel and FileHistoryModel classes to
    retrieve the data to pass to the view item delegate, which controls how each view item
    is rendered. The FileModel stores the data displayed in the main file view. The
    FileHistoryModel stores the data displayed in the file details panel; e.g. when a file
    is selected, the file details that are shown for that selected item.

    Hook methods that alter the main file view:
        get_item_title:
            - The return value will decide the text displayed in the item's top left text area.

        get_item_subtitle:
            - The return value will decide the text displayed in the item's top right text area.

        get_item_details:
            - The return value will decide the item's main text body.

        get_item_short_text:
            - The return value will decide the text displayed for the item's condensed text. This
              value is used for the Thumbnail view.

        get_item_thumbnail:
            - The return value will decide the image displayed for the item.

        get_item_icons:
            - The return value will decide if any icons are displayed over the thumbnail; e.g:
              status icons.

        get_item_separator:
            - The return value will decide if a separator line wil lbe drawn for the item.

    Hook methods that alter the file details view (these will do the same as described for
    the main file view, except in the details list view):
        get_history_item_title
        get_history_item_subtitle
        get_history_item_details
        get_history_item_thumbnail
        get_history_item_icons
        get_history_item_separator
    """

    def __init__(self, *args, **kwargs):
        """
        UIConfigAdvanced constructor.

        Get the File and File History item configurations from the simplified ui_configuration
        hook. The File and File History item configurations define what data to display. The
        methods in this hook will call the simplified hook to get the data to display, and
        apply any further logic to how and/or when that data is displayed.

        :param args: The positional arguments to pass to the base constructor.
        :param kwags: The keyword arguments to tpass to the base constructor.
        """

        super(UIConfigAdvanced, self).__init__(*args, **kwargs)

        # The file UI configuration that defines what data to display for a file item
        file_item_config = self.parent.execute_hook_method(
            "hook_ui_config", "file_item_details"
        )
        self._title_template_string = file_item_config.get("top_left", "")
        self._subtitle_template_string = file_item_config.get("top_right", "")
        self._details_template_string = file_item_config.get("body", "")
        self._short_text_template_string = file_item_config.get("thumbnail_body", "")
        self._show_thumbnail = file_item_config.get("thumbnail", False)

        # The file history UI configuration that defines what data to display for a history item
        file_details_history_config = self.parent.execute_hook_method(
            "hook_ui_config", "file_history_details"
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

    @staticmethod
    def get_file_item(index):
        """
        Convenience method to get the file item data from the index.

        :param index: A model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

        :return: The file item data for the given index.
        :rtype: FileItem
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
        template string and the second item is the ShotGrid data to format the template
        string with. This tuple return value may be consumed by the :class:`ViewItemDelegate`
        that will search and replace the tempalte string with the specified values from
        the ShotGrid data provided.

        See the UIConfiguration class (ui_configuartion.py) for more details on how to
        construct a template string that can be processed and replaced with ShotGrid data.

        :param index: The model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

        :return: The title for this item.
        :rtype: str | tuple<str,str>
        """

        file_item = self.get_file_item(index)
        if file_item:
            if self._title_template_string:
                # Search and replace any non-ShotGrid data fields
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
        template string and the second item is the ShotGrid data to format the template
        string with. This tuple return value may be consumed by the :class:`ViewItemDelegate`
        that will search and replace the tempalte string with the specified values from
        the ShotGrid data provided.

        See the UIConfiguration class (ui_configuartion.py) for more details on how to
        construct a template string that can be processed and replaced with ShotGrid data.

        :param index: The model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

        :return: The subtitle for this item.
        :rtype: str | tuple<str,str>
        """

        subtitle = None
        file_item = self.get_file_item(index)

        if file_item:
            if self._subtitle_template_string:
                # Search and replace any non-ShotGrid data fields
                template_string = _resolve_file_item_tokens(
                    file_item, self._subtitle_template_string
                )
                subtitle = (template_string, file_item.sg_data)

        else:
            # Group header item
            #
            # Attempt to get the source and proxy model and indexes
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
                # We only have access to the source model and index
                source_model = index.model()
                source_index = index
                source_rows = source_model.rowCount(source_index)
                proxy_model = None
                proxy_rows = 0
                proxy_index = None

            # Build a status string based on the source and proxy model data
            if not source_rows:
                # The model has no data
                subtitle = "NO FILES FOUND"
            else:
                # Iterate through the source model items, counting how many items are being loaded
                # and how many have a status of out of sync
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
                    # The source model is loading items, set the group status to indicate the loading state.
                    total_files_str = "LOADING {loaded}/{total} FILES".format(
                        loaded=loaded,
                        total=source_rows,
                    )
                else:
                    # The source model is done loading, check if there are any filters applied and indicate
                    # if there are any items filtered or not.
                    proxy_out_of_sync = 0
                    for row in range(proxy_rows):
                        child_index = proxy_model.index(row, 0, proxy_index)
                        # The status role and enum are defined on the source model
                        status = child_index.data(source_model.STATUS_ROLE)
                        if status == source_model.STATUS_OUT_OF_SYNC:
                            proxy_out_of_sync += 1

                    if proxy_rows != source_rows:
                        # Filters are applied, display total and filtered items.
                        total_files_str = (
                            "SHOWING {proxy_count}/{total_count} FILES".format(
                                proxy_count=proxy_rows, total_count=source_rows
                            )
                        )
                    else:
                        # There are no filters applied
                        total_files_str = "{total} FILES".format(total=source_rows)

                    if source_out_of_sync > 0:
                        # Display how many files are out of sync

                        if proxy_out_of_sync != source_out_of_sync:
                            # Filters applied and have altered the total out of sync files currently shown.
                            out_of_sync_str = "{proxy_out_of_sync}/{total_out_of_sync} OUT OF DATE".format(
                                proxy_out_of_sync=proxy_out_of_sync,
                                total_out_of_sync=source_out_of_sync,
                            )
                        else:
                            out_of_sync_str = "{out_of_sync} OUT OF DATE".format(
                                out_of_sync=source_out_of_sync
                            )

                # Finally build the group status string to show in the item's subtitle
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
        template string and the second item is the ShotGrid data to format the template
        string with. This tuple return value may be consumed by the :class:`ViewItemDelegate`
        that will search and replace the tempalte string with the specified values from
        the ShotGrid data provided.

        See the UIConfiguration class (ui_configuartion.py) for more details on how to
        construct a template string that can be processed and replaced with ShotGrid data.

        :param index: The model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

        :return: The details for this item.
        :rtype: str | tuple<str,str>
        """

        file_item = self.get_file_item(index)
        if file_item:
            if self._details_template_string:
                # Search and replace any non-ShotGrid data fields
                template_string = _resolve_file_item_tokens(
                    file_item, self._details_template_string
                )
                return (template_string, file_item.sg_data)

            return file_item.sg_data

        return None

    def get_item_short_text(self, index):
        """
        Returns the short text data to display for this model index item.

        :param index: The model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

        :return: The short text for this item.
        :rtype: str | tuple<str,str>
        """

        file_item = self.get_file_item(index)
        if file_item and self._short_text_template_string:
            # Search and replace any non-ShotGrid data fields
            template_string = _resolve_file_item_tokens(
                file_item, self._short_text_template_string
            )
            return (template_string, file_item.sg_data)

        return None

    def get_item_thumbnail(self, index):
        """
        Returns the data to display for this model index item's thumbnail.

        :param index: The model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

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

        :param index: The model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

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
                    # FIXME this is just a placeholder icon, this should be updated when showing
                    # icons for unloaded references is enabled.
                    "pixmap": QtGui.QIcon(
                        ":/tk-multi-breakdown2/icons/icons/red_bullet.png"
                    ),
                    "inset": True,
                }

        return icons

    def get_item_separator(self, index):
        """
        Returns True to indicate the item has a separator, else False. This may be
        used to indicate to the delegate to draw a line separator for the item or not.

        :param index: The model item index
        :type index: :class:`sgkt.platofrm.qt.QtCore.QModelIndex`

        :return: True to indicate the item has a separator, else False.
        :rtype: bool
        """

        file_item = self.get_file_item(index)

        # Only group headers have a separator.
        return file_item is None

    def get_history_item_title(self, item, sg_data):
        """
        Returns the data to display for this model index item's title. Specifically, a
        tuple will be returned, where item (1) is a template string and item (2) is the
        ShotGrid data to format the template string with. This tuple return value may be
        consumed by the :class:`ViewItemDelegate` that will search and replace the tempalte
        string with the specified values from the ShotGrid data provided.

        :param item: The model item representing file history item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param sg_data: The ShotGrid data associated with this item.
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
        ShotGrid data to format the template string with. This tuple return value may be
        consumed by the :class:`ViewItemDelegate` that will search and replace the tempalte
        string with the specified values from the ShotGrid data provided.

        :param item: The model item representing file history item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param sg_data: The ShotGrid data associated with this item.
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
        ShotGrid data to format the template string with. This tuple return value may be
        consumed by the :class:`ViewItemDelegate` that will search and replace the tempalte
        string with the specified values from the ShotGrid data provided.

        :param item: The model item representing file history item.
        :type item: :class:`sgtk.platform.qt.QtGui.QStandardItem`
        :param sg_data: The ShotGrid data associated with this item.
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
        :param sg_data: The ShotGrid data associated with this item.
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
    Convenience method to resolve any File item (non-ShotGrid) specific fields.
    """

    for token in ["NODE_NAME", "PATH"]:
        template_string = _resolve_tokens(
            token,
            getattr(file_item, token.lower()),
            template_string,
        )

    return template_string
