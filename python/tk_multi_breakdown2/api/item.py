# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.


class FileItem(object):
    """
    Encapsulate details about a single version of a file. Each instance represents a single "version"
    but will contain details about the latest available version of the file.
    """

    def __init__(self, node_name, node_type, path, sg_data=None, extra_data=None):
        """
        Class constructor.

        :param node_name:  Name of the file node
        :param node_type:  Type of the file node
        :param path:       Path on disk of this file
        :param sg_data:    Dictionary of ShotGrid data representing this file in the database
        :param extra_data: Dictionary containing additional information about this file
        """

        self._node_name = node_name
        self._node_type = node_type
        self._path = path
        self._sg_data = sg_data
        self._extra_data = extra_data
        self._latest_published_file = None
        self._locked = False

    def __eq__(self, other):
        """
        Override the equality operator to allow comparing FileItem objects.

        :param other: The other FileItem to compare this one with.
        :type other: FileItem
        """

        return (
            self.node_name == other.node_name
            and self.node_type == other.node_type
            and self.path == other.path
            and self.sg_data.get("id") == other.sg_data.get("id")
        )

    ########################################## ####################################################
    ########################################## ####################################################
    @property
    def highest_version_number(self):
        """
        :return: The highest version number available in the ShotGrid database for this file
        """

        if self._latest_published_file:
            return self._latest_published_file.get("version_number")

        return None

    @property
    def node_name(self):
        """
        Get the name of the file node.
        """

        return self._node_name

    @node_name.setter
    def node_name(self, value):
        self._node_name = value

    @property
    def node_type(self):
        """
        Get the type of the file node.
        """

        return self._node_type

    @node_type.setter
    def node_type(self, value):
        self._node_type = value

    @property
    def path(self):
        """
        Get the path on disk for this file item.
        """

        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def locked(self):
        """
        Get whether or not this file item is locked.
        """

        return self._locked

    @locked.setter
    def locked(self, value):
        self._locked = value

    @property
    def latest_published_file(self):
        """
        Get the latest published file for this file item.
        """

        return self._latest_published_file

    @latest_published_file.setter
    def latest_published_file(self, value):
        self._latest_published_file = value

    @property
    def extra_data(self):
        """
        Get or set the extra data associated with this item.
        """

        return self._extra_data

    @extra_data.setter
    def extra_data(self, value):

        self._extra_data = value

    @property
    def sg_data(self):
        """
        Get or set the ShotGrid data associated with this item.
        """

        return self._sg_data

    @sg_data.setter
    def sg_data(self, value):

        self._sg_data = value

    def to_dict(self):
        """
        Return the FileItem as a dictionary. Only include the properties needed by the
        scene operation hook update method.i

        :return: The item properties as a dictionary
        """

        return {
            "node_name": self.node_name,
            "node_type": self.node_type,
            "path": self.path,
            "extra_data": self.extra_data,
        }
