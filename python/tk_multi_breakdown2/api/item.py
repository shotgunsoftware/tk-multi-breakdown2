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
    """

    def __init__(self, node_name, node_type, path, sg_data=None, extra_data=None):
        """
        """

        self.node_name = node_name
        self.node_type = node_type
        self.path = path
        self.sg_data = sg_data
        self.extra_data = extra_data
        self._highest_version = None
        self.file_history = None

    @property
    def highest_version(self):
        """
        """
        if self._highest_version:
            return self._highest_version
        elif self.file_history:
            self._highest_version = self.file_history[0].get("version_number")
        else:
            return None

    @highest_version.setter
    def highest_version(self, version):
        """
        :param version:
        :return:
        """
        self._highest_version = version

    def to_dict(self):
        """
        :return:
        """
        return {
            "node_name": self.node_name,
            "node_type": self.node_type,
            "path": self.path,
            "extra_data": self.extra_data,
        }
