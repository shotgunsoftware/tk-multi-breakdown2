.. _breakdown-hooks:

Breakdown Hooks
===============

hook_scene_operations:
----------------------

An engine specific hook that handles detecting references in the scene.

hook_get_published_files:
-------------------------

A hook to define how Published Files are queried; e.g. specifiy filters, fields, order, etc. when retrieving Published Files, which are displayed in the file view.

hook_ui_config:
---------------

A simple hook to customize the display of the view and details widget. When the application displays the items in the main file view, the right-hand panel details widget and history view, it will call this hook to determine which data to display for that particular widget and how it should be formatted.

**Methods:**

file_item_details
    - Set the data shown in the file list items, and define how that data is formatted

main_file_history_details
    - Set the data shown in right-hand side panel widget, and define how that data is formatted

file_history_details
    - Set the data shown in the right-hand side panel, file history list items, and define how that data is formattted


Basic Examples:
^^^^^^^^^^^^^^^

Each of the hook methods will return the formatted data in the form of a templated string, for example::

    <b>By:</b> {created_by}{[<br><b>Description:</b> ]description}

What this templated string does:

    1. Uses HTML tags to make the text, *"By:"*, bolded
    2. Uses ShotGrid token resolution to display and format the entity's description field

.. _sg_token_res:

ShotGrid Token Resolution and Formatting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


The ShotGrid token resolution will convert the values defined like, ``{token}``, into formatted strings using ShotGrid data. These token values can be defined using the following format::

    {[preroll]shotgun.field.name|sg_field_name_fallback::directive[postroll]}

**Formatting Options:**

    Simple format: {field}
      - Example, ``{code}`` will be substituted with the entity's code value

    Deep links: {field1.field1_type.field_of_field1}
      - Example, ``{sg_sequence.Sequence.code}`` will be substituted with the entity's Sequence code value

    Fallback options: {field | field2}
      - Example, ``{artist|created_by}`` will be substituted with the entity's artist, if it does not exist, then it will substitute with the created by user

    Directives: {...::directive1::directive2}
      - Directives can be chained to apply multiple directives
      - Example, ``{sg_sequence::showtype}`` - This will generate a link saying 'Sequence ABC123' instead of the default, 'ABC123'
      - Example, ``{sg_sequence::nolink}`` - No url link will be created or shown

    Pre/Post Rolls: {[pre_roll]...[post_roll]}
      - If a value is null, pre- and post-strings are omitted from the final result.
      - Pre roll example, ``{[Name: ]code}`` - If code is set, 'Name: xxx' will be printed out, otherwise nothing.
      - Pre and Post roll example, ``{[Name: ]code[<br>]}`` - Same as above but with a post line break

hook_ui_config_advanced:
------------------------

This is an advanced hook to customize the UI. For a simplified approach, see the hook_ui_config.

When using this hook, it is beneficial to have an understanding of Object Oriented Programming (e.g. class inheritance) and how Qt Models work (e.g. including the use of proxy models). You may also need to reference the Breakdown2 classes, such as the FileModel, FileProxyModel and FileHistoryModel, as well as the tk-framework-qtwidgets utils module and ViewItemDelegate class.

The default hook implementation will call the hook_ui_config under the hood, to retrieve the data and formatting that should be displayed. Then, any further processing of the data can be applied in this hook. The template strings returned from the hook_ui_config, are stored as class attributes in this hook, so that each hook method to access.

Class Attributes:
^^^^^^^^^^^^^^^^^

_title_template_string
    - This is the `"top-left"` value of the dictionary returned by the hook_ui_config method `file_item_details`

_subtitle_template_string
    - This is the `"top-right"` value of the dictionary returned by the hook_ui_config method `file_item_details`

_details_template_string
    - This is the `"body"` value of the dictionary returned by the hook_ui_config method `file_item_details`

_short_text_template_string
    - This is the `"thumbnail-body"` value of the dictionary returned by the hook_ui_config method `file_item_details`

_show_thumbnail
    - This is the `"thumbnail"` value of the dictionary returned by the hook_ui_config method `file_item_details`

_history_title_template_string
    - This is the `"top-left"` value of the dictionary returned by the hook_ui_config method `file_history_details`

_history_subtitle_template_string
    - This is the `"top-right"` value of the dictionary returned by the hook_ui_config method `file_history_details`

_history_details_template_string
    - This is the `"body"` value of the dictionary returned by the hook_ui_config method `file_history_details`

_history_show_thumbnail
    - This is the `"thumbnail"` value of the dictionary returned by the hook_ui_config method `file_history_details`


The methods in this hook are called from the FileModel and FileHistoryModel classes to retrieve the data to pass to their respective view's delegate, which controls how each view item is rendered. The FileModel stores the data displayed in the main file view. The FileHistoryModel stores the data displayed in the file details panel; e.g. when a file is selected, the file details that are shown for that selected item.

Class Methods:
^^^^^^^^^^^^^^

get_item_title
    - The return value will decide the text displayed in the item's top left text area.

get_item_subtitle
    - The return value will decide the text displayed in the item's top right text area.

get_item_details
    - The return value will decide the item's main text body.

get_item_short_text
    - The return value will decide the text displayed for the item's condensed text. This value is used for the Thumbnail view.

get_item_thumbnail
    - The return value will decide the image displayed for the item.

get_item_icons
    - The return value will decide if any icons are displayed over the thumbnail; e.g: status icons.

get_item_separator
    - The return value will decide if a separator line wil lbe drawn for the item.

get_history_item_title
    - Similar to the `get_item_title` method, but this acts on the file history view.
    - The return value will decide the text displayed in the history item's top left text area.

get_history_item_subtitle
    - Similar to the `get_item_subtitle` method, but this acts on the file history view.
    - The return value will decide the text displayed in the history item's top right text area.

get_history_item_details
    - Similar to the `get_item_details` method, but this acts on the file history view.
    - The return value will decide the history item's main text body.

get_history_item_thumbnail
    - Similar to the `get_item_thumbnail` method, but this acts on the file history view.
    - The return value will decide the image displayed for the item.

get_history_item_icons
    - Similar to the `get_item_icons` method, but this acts on the file history view.
    - The return value will decide if any icons are displayed over the thumbnail; e.g: status icons.

get_history_item_separator
    - Similar to the `get_item_separator` method, but this acts on the file history view.
    - The return value will decide if a separator line wil lbe drawn for the item.

Static Methods
^^^^^^^^^^^^^^

get_file_item(index)
    - This is a helper method to extract the ``FileItem`` data from the given index. The `FileItem` object will hold the ShotGrid data associated with this index, that can be displayed in the view.

Basic Examples
^^^^^^^^^^^^^^

This example demonstrates how to get the index data from a model role, to display for the file item's title field. The ``DisplayRole`` data will be retrieved for each index and shown in the top-left of the file item text.

.. code-block:: python

  def get_item_title(self, index):
      return index.data(Qt.DisplayRole)

We can extend this example to use the hook's static method ``get_file_item``, to get the ShotGrid data for this index to display certain ShotGrid data:

.. code-block:: python

  def get_item_title(self, index):
      file_item = self.get_file_item(index)
      if file_item:
          return file_item.sg_data.get("created_by")

      return index.data(Qt.DisplayRole)

If the ``FileItem`` object is retrieved for this index, display the user who created this ShotGrid entity that the item is associated with. Notice that if a FileItem object was not found, we default to display the indexes DisplayRole data.

We can take this example one step further by using the hook attribute ``_title_template_string``:

.. code-block:: python

  def get_item_title(self, index):
      file_item = self.get_file_item(index)
      if file_item:
          if self._title_template_string:
              return (self._title_template_string, file_item.sg_data)

          return file_item.sg_data.get("created_by")

      return index.data(Qt.DisplayRole)

Here, we are returning a tuple containing the template string defined in the simple hook_ui_config and the FileItem object's ShotGrid data dictionary. The returned tuple will then be passed to the ``ViewItemDelegate`` class, which will process the template string with the provided ShotGrid data and replace any ``{token}`` values in the template string with the ShotGrid data. See :ref:`sg_token_res` for more details.
