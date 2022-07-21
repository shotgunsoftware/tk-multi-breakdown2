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
from sgtk.platform.qt import QtGui, QtCore

from .file_model import FileModel
from .framework_qtwidgets import FilterItemTreeProxyModel


class FileProxyModel(FilterItemTreeProxyModel):
    """
    A proxy model for the FileModel. Subclasses the FilterItemTreeProxyModel that implements
    generic filtering.
    """

    UI_CONFIG_ADV_HOOK_PATH = "hook_ui_config_advanced"

    def __init__(self, *args, **kwargs):
        """
        FileProxyModel constructor.
        """

        self._app = sgtk.platform.current_bundle()

        ui_config_adv_hook_path = self._app.get_setting(self.UI_CONFIG_ADV_HOOK_PATH)
        self._ui_config_adv_hook = self._app.create_hook_instance(
            ui_config_adv_hook_path
        )

        self._search_text_filter_item = None

        super(FileProxyModel, self).__init__(*args, **kwargs)

    @property
    def search_text_filter_item(self):
        """
        Get or set the search text filter item.
        """
        return self._search_text_filter_item

    @search_text_filter_item.setter
    def search_text_filter_item(self, filter_item):
        self._search_text_filter_item = filter_item
        self.layoutAboutToBeChanged.emit()
        self.invalidateFilter()
        self.layoutChanged.emit()

    def data(self, index, role):
        """
        Override the base method.

        Return the data for the item for the specified role.

        :param role: The :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole` role.
        :return: The data for the specified roel.
        """

        if not index.isValid():
            return

        # Call any UI config hook methods from here (instead of the source model), which
        # require access to proxy model data. By calling the hook methods here, the proxy
        # model index is passed to the hook method, which provides access to both the
        # proxy and source model data.
        if role == FileModel.VIEW_ITEM_SUBTITLE_ROLE:
            # The subtitle requires the proxy model data to display how many files items
            # are currently filtered
            return self._ui_config_adv_hook.get_item_subtitle(index)

        source_index = self.mapToSource(index)
        return self.sourceModel().data(source_index, role)

    def _is_row_accepted(self, src_row, src_parent_idx, parent_accepted):
        """
        Override the base method.

        Go through the list of filters and check whether or not the src_row
        is accepted based on the filters.
        """

        base_model_accepts = super(FileProxyModel, self)._is_row_accepted(
            src_row, src_parent_idx, parent_accepted
        )
        if not base_model_accepts:
            return False

        src_idx = self.sourceModel().index(src_row, 0, src_parent_idx)
        if not src_idx.isValid():
            return False

        # Do not accept any of the file groupings. File groups are only accepted if it has a
        # child index that is accepted. NOTE this is a bit of a work around to how filter
        # values of "None" is handled - the group indexes will return None when checking for
        # acceptance, but if the filter value is None, then the group will be accepted even
        # if it has no children, which then causes the view to show empty groupings. TODO
        # modify the filtering functionality to handle filter values of "None" better.
        is_grouping = src_idx.data(self.sourceModel().FILE_ITEM_ROLE) is None
        if is_grouping:
            return False

        if not self.search_text_filter_item:
            return True  # No filters set, accept everything

        return self.search_text_filter_item.accepts(src_idx)
