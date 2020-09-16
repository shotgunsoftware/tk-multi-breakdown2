# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import maya.cmds as cmds
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """
    """

    def scan_scene(self):
        """
        """

        refs = []

        # first let's look at maya references
        for ref in cmds.file(q=1, reference=1):
            node_name = cmds.referenceQuery(ref, referenceNode=1)

            # get the path and make it platform dependent
            # (maya uses C:/style/paths)
            maya_path = ref.replace("/", os.path.sep)
            refs.append({"node_name": node_name, "node_type": "reference", "path": maya_path})

        # now look at file texture nodes
        for file_node in cmds.ls(l=True, type="file"):
            # ensure this is actually part of this scene and not referenced
            if cmds.referenceQuery(file_node, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in the breakdown
                continue

            # get path and make it platform dependent (maya uses C:/style/paths)
            path = cmds.getAttr("%s.fileTextureName" % file_node).replace(
                "/", os.path.sep
            )

            refs.append({"node_name": file_node, "node_type": "file", "path": path})

        return refs

    def update(self, item):
        """
        :param item:
        :return:
        """

        node_name = item["node_name"]
        node_type = item["node_type"]
        path = item["path"]

        if node_type == "reference":
            # maya reference
            self.logger.debug(
                "Maya Reference %s: Updating to version %s" % (node_name, path)
            )
            cmds.file(path, loadReference=node_name)

        elif node_type == "file":
            # file texture node
            self.logger.debug(
                "File Texture %s: Updating to version %s" % (node_name, path)
            )
            file_name = cmds.getAttr("%s.fileTextureName" % node_name)
            cmds.setAttr("%s.fileTextureName" % node_name, path, type="string")