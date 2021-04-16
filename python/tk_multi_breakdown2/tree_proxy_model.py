# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtCore, QtGui

from .framework_qtwidgets import HierarchicalFilteringProxyModel


class TreeProxyModel(HierarchicalFilteringProxyModel):
    """
    A proxy model for source models with a tree data structure.

    TODO: Move this to tk-frameowrk-qtwidgets once the model is more fleshed out.
    """

    def __init__(self, parent, filter_items=None):
        """
        TreeProxyModel constructor
        """

        HierarchicalFilteringProxyModel.__init__(self, parent)

        self._filter_items = filter_items

    @property
    def filter_items(self):
        """
        Get or set the filter items used to filter the model data.
        """
        return self._filter_items

    @filter_items.setter
    def filter_items(self, items):
        self._filter_items = items
        self.invalidateFilter()

    def _is_row_accepted(self, src_row, src_parent_idx, parent_accepted):
        """
        Override the base method.

        Go through the list of filters and check whether or not the src_row
        is accepted based on the filters.
        """

        src_idx = self.sourceModel().index(src_row, 0, src_parent_idx)
        if not src_idx.isValid():
            return False

        if not src_parent_idx.isValid():
            return True  # Accept all group headers for now

        if not self.filter_items:
            return True  # No filters set, accept everything

        return self._do_filter(src_idx, self.filter_items, FilterItem.OP_AND)

    def _do_filter(self, src_idx, filter_items, op):
        """
        Recursively filter the data for the given src_idx.
        """

        if not FilterItem.is_group_op:
            raise ValueError("Invalid filter group operation {}".format(op))

        for filter_item in filter_items:
            if filter_item.is_group():
                self._do_filter(src_idx, filter_item.filters, filter_item.filter_op)

            else:
                accepted = filter_item.accepts(src_idx)

                if op == FilterItem.OP_AND and not accepted:
                    return False

                if op == FilterItem.OP_OR and accepted:
                    return True

        if op == FilterItem.OP_AND:
            # Accept if the operation is AND since it would have been rejected immediately if
            # any filter item did not accept it.
            return True

        # Do not accept if the operation is OR (or invalid) since the value would have
        # been accepted immediately if any filters accepted it.
        return False


class FilterItem(object):
    """
    A class object to store all necesasry information for a filter used by the TreeProxyModel.
    """

    # The filter operations
    OP_AND = "and"
    OP_OR = "or"
    OP_IS_TRUE = "true"
    OP_IS_FALSE = "false"
    OP_IN = "in"
    OP_NOT_IN = "!in"
    OP_EQUAL = "="
    OP_NOT_EQUAL = "!="
    OP_LESS_THAN = "<"
    OP_LESS_THAN_OR_EQUAL = "<="
    OP_GREATER_THAN = ">"
    OP_GREATER_THAN_OR_EQUAL = ">="

    # The filter types
    TYPE_BOOL = "bool"
    TYPE_STR = "str"
    # TYPE_REGEX_STR = "regex"
    TYPE_NUMBER = "number"
    TYPE_LIST = "list"
    # The group type is a special type that contains a list of filters itself and its operation
    # is either AND or OR the list of filters
    TYPE_GROUP = "group"

    def __init__(
        self,
        filter_type,
        filter_op,
        filter_role=None,
        data_func=None,
        filter_value=None,
        filters=None,
    ):
        """
        Constructor
        """

        self.filter_type = filter_type
        self.filter_role = filter_role
        self.filter_value = filter_value
        self.filter_op = filter_op
        self.filters = filters
        self.data_func = data_func

        self._filter_funcs_by_type = {
            self.TYPE_BOOL: self.is_bool_valid,
            self.TYPE_STR: self.is_str_valid,
            # self.TYPE_REGEX_STR: self.is_regex_str_valid,
            self.TYPE_NUMBER: self.is_number_valid,
            self.TYPE_LIST: self.is_list_valid,
        }

    def is_bool_valid(self, value):
        """
        Filter str tupe.
        """

        if self.filter_op == self.OP_IS_TRUE:
            return value

        if self.filter_op == self.OP_IS_FALSE:
            return not value

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        assert False, "Unsupported operation for filter type 'bool'"
        return False

    def is_str_valid(self, value):
        """
        Filter str tupe.
        """

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        if self.filter_op == self.OP_IN:
            regex = QtCore.QRegularExpression(
                self.filter_value, QtCore.QRegularExpression.CaseInsensitiveOption
            )

            match = regex.match(value)
            return match.hasMatch()

        assert False, "Unsupported operation for filter type 'str'"
        return False

    def is_number_valid(self, value):
        """
        Filter str tupe.
        """

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        if self.filter_op == self.OP_GREATER_THAN:
            return value > self.filter_value

        if self.filter_op == self.OP_GREATER_THAN_OR_EQUAL:
            return value >= self.filter_value

        if self.filter_op == self.OP_LESS_THAN:
            return value < self.filter_value

        if self.filter_op == self.OP_LESS_THAN_OR_EQUAL:
            return value <= self.filter_value

        assert False, "Unsupported operation for filter type 'number'"
        return False

    def is_list_valid(self, value):
        """
        Filter str tupe.
        """

        if self.filter_op == self.OP_IN:
            for filter_val in self.filter_value:
                if value == filter_val:
                    return True
            return False

        if self.filter_op == self.OP_EQUAL:
            return value == self.filter_value

        assert False, "Unsupported operation for filter type 'list'"
        return False

    @classmethod
    def is_group_op(cls, op):
        """
        Return True if the filter item operation is valid.
        """

        return op in (cls.OP_AND, cls.OP_OR)

    def is_group(self):
        """
        Return True if this filter item is a group
        """

        return self.filter_type == self.TYPE_GROUP

    def get_index_data(self, index):
        """
        Return the data for this filter item and index.
        """

        if self.filter_role:
            return index.data(self.filter_role)

        if self.data_func:
            return self.data_func(index)

        return None

    def accepts(self, index):
        """
        Return True if this filter item accepts the given index.
        """

        data = self.get_index_data(index)
        filter_func = self._filter_funcs_by_type.get(self.filter_type, None)

        if filter_func is None:
            return False  # Invalid filter type

        return filter_func(data)
