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
from sgtk.platform.qt import QtCore


class FilterItem(object):
    """
    Class object to encapsulate all the necessary data to filter items in a model.
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

        :param filter_type: The data type for the filter
        :type filter_type: One of the filter type enums defined for this class; e.g.:
            TYPE_BOOL
            TYPE_STR
            TYPE_NUMBER
            TYPE_LIST
            TYPE_GROUP
        :param filter_op:
        :type filter_op: One of the filter operation enums defined for this class; e.g.:
            OP_AND
            OP_OR
            OP_IS_TRUE
            OP_IS_FALSE
            OP_IN
            OP_NOT_IN
            OP_EQUAL
            OP_NOT_EQUAL
            OP_LESS_THAN
            OP_LESS_THAN_OR_EQUAL
            OP_GREATER_THAN
        :param filter_role: An item data role to extract the index data to filter based on (optional).
        :type filter_role: :class:`sgtk.platform.qt.QtCore.Qt.ItemDataRole`
        :param data_func: A function that can be called to extract the index data to filter based on (optional).
                          NOTE: if a filter_role is defined, this will have no effect.
        :param filter_value: The value the item's data will be filtered by (optional). This value may be set
                             later, if not known at time of init.
        :type filter_value: The data type for this filter
        :param filters: A list of FilterItem objects (optional). This is used for group filters; this list of
                        filter items are the group of filters to apply to the data.
        :type filters: list<FilterItem>
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
            self.TYPE_NUMBER: self.is_number_valid,
            self.TYPE_LIST: self.is_list_valid,
        }

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
        Return the index's data based on the filter item. The index data will be first
        attempted to be retrieved from the index's data method, using the filter role.
        If no role is defined, the data_func will be called to extract the data (if such
        a function is defined).

        A `filter_role` or `data_func` must be defined to reteieve the index data.

        :param index: The index to get the data from
        :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`

        :return: The index data
        """

        if self.filter_role:
            return index.data(self.filter_role)

        if self.data_func:
            return self.data_func(index)

        assert (
            False
        ), "FilterItem does not have a filter role or data function to retrieve index data to filter on"
        return None

    def accepts(self, index):
        """
        Return True if this filter item accepts the given index.

        :param index: The index that holds the data to filter on.
        :type index: :class:`sgtk.platform.qt.QtCore.QModelIndex`

        :return: True if the filter accepts the index, else False.
        """

        data = self.get_index_data(index)
        filter_func = self._filter_funcs_by_type.get(self.filter_type, None)

        if filter_func is None:
            return False  # Invalid filter type

        return filter_func(data)

    def is_bool_valid(self, value):
        """
        Filter the incoming boolean value.

        :param value: The value to filter.
        :type value: bool

        :return: True if the filter accepts the value, else False.
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
        Filter the incoming string value.

        :param value: The value to filter.
        :type value: str

        :return: True if the filter accepts the value, else False.
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
        Filter the incoming number value.

        :param value: The value to filter.
        :type value: int | float | ...

        :return: True if the filter accepts the value, else False.
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
        Filter the incoming list value.

        :param value: The value to filter.
        :type value: list

        :return: True if the filter accepts the value, else False.
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
