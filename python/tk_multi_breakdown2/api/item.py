# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


class FileItem(object):
    """
    Encapsulate details about a single version of a file. Each instance represents a single "version" but will contain
    details about the latest available version of the file.
    """

    def __init__(self, node_name, node_type, path, sg_data=None, extra_data=None):
        """
        Class constructor.

        :param node_name:  Name of the file node
        :param node_type:  Type of the file node
        :param path:       Path on disk of this file
        :param sg_data:    Dictionary of Shotgun data representing this file in the database
        :param extra_data: Dictionary containing additional information about this file
        """

        self.node_name = node_name
        self.node_type = node_type
        self.path = path
        self.sg_data = sg_data
        self.extra_data = extra_data
        self.latest_published_file = None

    @property
    def highest_version_number(self):
        """
        :return: The highest version number available in the Shotgun database for this file
        """

        if self.latest_published_file:
            return self.latest_published_file.get("version_number")
        else:
            return None

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
