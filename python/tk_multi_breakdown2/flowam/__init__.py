# Copyright (c) 2026 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""FlowAM integration for the Scene Breakdown app.

This package provides drop-in replacements for the standard Shotgun-based
Scene Breakdown models and actions, backed by Flow Asset Management (FlowAM).
"""

from .reference import (
    get_dependencies,
    get_published_file_type,
    get_scene_objects_and_publishes,
    update_dependency,
)
