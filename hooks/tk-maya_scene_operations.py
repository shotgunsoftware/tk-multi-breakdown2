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
    Breakdown operations for Maya.

    This implementation handles detection of maya references and file texture nodes.
    """

    def scan_scene(self):
        """
        The scan scene method is executed once at startup and its purpose is
        to analyze the current scene and return a list of references that are
        to be potentially operated on.

        The return data structure is a list of dictionaries. Each scene reference
        that is returned should be represented by a dictionary with three keys:

        - "node_name": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "node_type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.
        - "extra_data": Optional key to pass some extra data to the update method
          in case we'd like to access them when updating the nodes.

        Toolkit will scan the list of items, see if any of the objects matches
        a published file and try to determine if there is a more recent version
        available. Any such versions are then displayed in the UI as out of date.
        """

        refs = []

        # first let's look at maya references
        for ref in cmds.file(q=True, reference=True):
            node_name = cmds.referenceQuery(ref, referenceNode=True)

            # get the path and make it platform dependent
            # (maya uses C:/style/paths)
            maya_path = cmds.referenceQuery(
                ref, filename=True, withoutCopyNumber=True
            ).replace("/", os.path.sep)
            refs.append(
                {"node_name": node_name, "node_type": "reference", "path": maya_path}
            )

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
        Perform replacements given a number of scene items passed from the app.

        Once a selection has been performed in the main UI and the user clicks
        the update button, this method is called.

        :param item: Dictionary on the same form as was generated by the scan_scene hook above.
                     The path key now holds the path that the node should be updated *to* rather than the current path.
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
