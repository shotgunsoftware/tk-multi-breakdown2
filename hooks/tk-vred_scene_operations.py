# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import os
import sgtk


HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """A hook to perform scene operations in VRED necessary for Breakdown 2 App."""

    def __init__(self, *args, **kwargs):
        """Class constructor."""

        super(BreakdownSceneOperations, self).__init__(*args, **kwargs)

        self._vredpy = self.parent.engine.vredpy

        # Keep track of the scene change callbacks that are registered, so that they can be
        # disconnected at a later time.
        self._on_references_changed_cb = None

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

        for r in self._vredpy.vrReferenceService.getSceneReferences():

            # we only want to keep the top references
            has_parent = self._vredpy.vrReferenceService.getParentReferences(r)
            if has_parent:
                continue

            if r.hasSmartReference():
                node_type = "smart_reference"
                path = r.getSmartPath()
            elif r.hasSourceReference():
                node_type = "source_reference"
                path = r.getSourcePath()
            else:
                node_type = "reference"
                path = None

            if path:
                refs.append(
                    {
                        "node_name": r.getName(),
                        "node_type": node_type,
                        "path": path,
                        "extra_data": {"node_id": r.getObjectId()},
                    }
                )

        return refs

    def update(self, item):
        """
        Update the reference(s) given the item data.

        A list of items or a single item may be passed to this method.

        :param item: The item data used to perform the reference update.
        :type item: dict | List[dict]

        :return: The items that were updated or True when `item` is a single item.
        :rtype: List[dict] | True
        """

        if isinstance(item, list):
            return self.update_items(item)
        return self.update_item(item)

    def update_items(self, items):
        """
        Update the references given the item data.

        :param item: The item data used to perform the reference updates.
        :type item: List[dict]

        :return: The items that were updated.
        :rtype: List[dict]
        """

        # Prepare the items to update
        updated_items = []
        refs_to_load = []
        smart_refs_to_import = []
        for item in items:
            # Get the current reference from the item data
            node_id = item.get("extra_data", {}).get("node_id")
            ref_node = self.get_reference_by_id(node_id)
            if not ref_node:
                self.logger.error(
                    "Couldn't get reference node named {}".format(item["node_name"])
                )
                continue
            # Update the current reference based on the item data
            node_type = item["node_type"]
            path = item["path"]
            if node_type == "source_reference":
                new_node_name = os.path.splitext(os.path.basename(path))[0]
                ref_node.setSourcePath(path)
                ref_node.setName(new_node_name)
                refs_to_load.append(ref_node)
                updated_items.append(item)
            elif node_type == "smart_reference":
                ref_node.setSmartPath(path)
                smart_refs_to_import.append(ref_node)
                updated_items.append(item)

        # Update the VRED references based on their reference type being source or smart
        if refs_to_load:
            self._vredpy.vrReferenceService.loadSourceReferences(refs_to_load)
        if smart_refs_to_import:
            self._vredpy.vrReferenceService.reimportSmartReferences(
                smart_refs_to_import
            )

        # Return the list of items that were updated
        return updated_items

    def update_item(self, item):
        """
        Update the single reference given item data.

        :param item: The item data used to perform the reference update.
        :type item: dict

        :return: True if the item was updated, else False.
        :rtype: True
        """

        node_id = item.get("extra_data", {}).get("node_id")
        ref_node = self.get_reference_by_id(node_id)
        if not ref_node:
            self.logger.error(
                "Couldn't get reference node named {}".format(item["node_name"])
            )
            return False

        node_type = item["node_type"]
        path = item["path"]
        if node_type == "source_reference":
            new_node_name = os.path.splitext(os.path.basename(path))[0]
            ref_node.setSourcePath(path)
            ref_node.loadSourceReference()
            ref_node.setName(new_node_name)
            return True

        if node_type == "smart_reference":
            ref_node.setSmartPath(path)
            self._vredpy.vrReferenceService.reimportSmartReferences([ref_node])
            return True

        # Return False to indicate the item was not updated
        return False

    def register_scene_change_callback(self, scene_change_callback):
        """
        Register the callback such that it is executed on a scene change event.

        This hook method is useful to reload the breakdown data when the data in the scene has
        changed.

        For Alias, the callback is registered with the AliasEngine event watcher to be
        triggered on a PostRetrieve event (e.g. when a file is opened).

        :param scene_change_callback: The callback to register and execute on scene chagnes.
        :type scene_change_callback: function
        """

        # Keep track of the callback so that it can be disconnected later
        self._on_references_changed_cb = (
            lambda nodes=None, cb=scene_change_callback: cb()
        )

        # Set up the signal/slot connection to potentially call the scene change callback
        # based on how the references have cahnged.
        # NOTE ideally the VRED API would have signals for specific reference change events,
        # until then, any reference change will trigger a full reload of the app.
        if hasattr(self._vredpy, "vrScenegraphService"):
            self._vredpy.vrScenegraphService.scenegraphChanged.connect(
                self._on_references_changed_cb
            )
        else:
            self._vredpy.vrReferenceService.referencesChanged.connect(
                self._on_references_changed_cb
            )

    def unregister_scene_change_callback(self):
        """Unregister the scene change callbacks by disconnecting any signals."""

        if self._on_references_changed_cb:
            if hasattr(self._vredpy, "vrScenegraphService"):
                try:
                    self._vredpy.vrScenegraphService.scenegraphChanged.disconnect(
                        self._on_references_changed_cb
                    )
                except RuntimeError:
                    # Signal was never connected
                    pass
                finally:
                    self._on_references_changed_cb = None
            else:
                try:
                    self._vredpy.vrReferenceService.referencesChanged.disconnect(
                        self._on_references_changed_cb
                    )
                except RuntimeError:
                    # Signal was never connected
                    pass
                    self._on_references_changed_cb = None

    def get_reference_by_id(self, ref_id):
        """
        Get a reference node from its name.

        :param ref_name: Name of the reference we want to get the associated node from
        :returns: The reference node associated to the reference name
        """
        ref_list = self._vredpy.vrReferenceService.getSceneReferences()
        for r in ref_list:
            if r.getObjectId() == ref_id:
                return r
        return None
