Breakdown2 API Reference
########################

Overview
********

tk-multi-breakdown2 (Breakdown2) is a customizable Toolkit App that allows studios to manage the behaviour when referencing PublishedFiles within a DCC Engine. It is meant to be a replacement for the original tk-multi-breakdown Application.

Improvements beyond the original Breakdown App
==============================================

.. important::
    We now use ShotGrid instead of the filesystem to determine the versions of PublishedFiles available.

* Ability to manage references in multiple ShotGrid Projects
* Ability to override to a version of a PublishedFile that is not the latest
* Get version history file information
* Multiple configurable and scalable viewing styles available

Default configuration behaviour
===============================

Please see the :ref:`engine-specific-notes` section to see the default hooks provided.

Customizations
==============

Please read the :ref:`breakdown-hooks` section of this documentation.

.. toctree::
    :maxdepth: 2

    api
    hooks
    engine-specific-notes
