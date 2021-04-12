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
    """"""

    def __init__(self, parent, filter_items=None):
        """
        Constructor
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
        """"""

        src_idx = self.sourceModel().index(src_row, 0, src_parent_idx)
        if not src_idx.isValid():
            return False

        if not src_parent_idx.isValid():
            return True  # Accept all group headers for now

        if not self.filter_items:
            return True  # No filters, accept everything

        accepted = self._do_filter(src_idx, self.filter_items, FilterItem.OP_AND)
        if accepted:
            return True

        return False

    def _do_filter(self, src_idx, filter_items, op):
        """
        Recursively filter
        """

        if not FilterItem.is_group_op:
            raise ValueError("Invalid filter group operation {}".format(op))

        for filter_item in filter_items:
            if filter_item.is_group():
                self._do_filter(src_idx, filter_item.filters, filter_item.op)

            else:
                # TODO move to filter item class
                if filter_item.filter_role:
                    data = src_idx.data(filter_item.filter_role)
                elif filter_item.data_func:
                    data = filter_item.data_func(src_idx)
                else:
                    data = None

                accepted = filter_item.accepts(data)

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
    A filter item to pass to the TreeProxyModel.
    """

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

    TYPE_GROUP = "group"
    TYPE_BOOL = "bool"
    TYPE_STR = "str"
    TYPE_REGEX_STR = "regex"
    TYPE_INT = "int"
    TYPE_LIST = "list"

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
            self.TYPE_REGEX_STR: self.is_regex_str_valid,
            self.TYPE_INT: self.is_int_valid,
            self.TYPE_LIST: self.is_list_valid,
        }

    def is_bool_valid(self, bool_value):
        """
        Filter str tupe.
        """

        # TODO
        return True

    def is_str_valid(self, str_value):
        """
        Filter str tupe.
        """

        # TODO
        return True

    def is_regex_str_valid(self, regex_value):
        """
        Filter regex str tupe.
        """

        # TODO enforce correct filter value type
        match = self.filter_value.match(regex_value)
        return match.hasMatch()

    def is_int_valid(self, str_value):
        """
        Filter str tupe.
        """

        # TODO
        return True

    def is_list_valid(self, str_value):
        """
        Filter str tupe.
        """

        # TODO
        return True

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

    def accepts(self, value):
        """
        Return True if this filter item accepts the given value.
        """

        filter_func = self._filter_funcs_by_type.get(self.filter_type, None)

        if filter_func is None:
            return False  # Invalid filter type

        return filter_func(value)
