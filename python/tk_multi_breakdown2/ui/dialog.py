# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialog.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1150, 643)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.header_layout = QtGui.QHBoxLayout()
        self.header_layout.setObjectName("header_layout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.header_layout.addItem(spacerItem)
        self.file_view_btn = QtGui.QToolButton(Dialog)
        self.file_view_btn.setText("")
        self.file_view_btn.setCheckable(True)
        self.file_view_btn.setChecked(True)
        self.file_view_btn.setObjectName("file_view_btn")
        self.header_layout.addWidget(self.file_view_btn)
        self.list_view_btn = QtGui.QToolButton(Dialog)
        self.list_view_btn.setText("")
        self.list_view_btn.setCheckable(True)
        self.list_view_btn.setObjectName("list_view_btn")
        self.header_layout.addWidget(self.list_view_btn)
        self.details_button = QtGui.QPushButton(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.details_button.sizePolicy().hasHeightForWidth())
        self.details_button.setSizePolicy(sizePolicy)
        self.details_button.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.details_button.setObjectName("details_button")
        self.header_layout.addWidget(self.details_button)
        self.verticalLayout.addLayout(self.header_layout)
        self.details_splitter = QtGui.QSplitter(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.details_splitter.sizePolicy().hasHeightForWidth())
        self.details_splitter.setSizePolicy(sizePolicy)
        self.details_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.details_splitter.setObjectName("details_splitter")
        self.file_view = GroupedItemView(self.details_splitter)
        self.file_view.setObjectName("file_view")
        self.details_panel = QtGui.QGroupBox(self.details_splitter)
        self.details_panel.setMinimumSize(QtCore.QSize(300, 0))
        self.details_panel.setMaximumSize(QtCore.QSize(300, 16777215))
        self.details_panel.setTitle("")
        self.details_panel.setObjectName("details_panel")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.details_panel)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.file_details = ShotgunFolderWidget(self.details_panel)
        self.file_details.setMinimumSize(QtCore.QSize(250, 250))
        self.file_details.setObjectName("file_details")
        self.verticalLayout_2.addWidget(self.file_details)
        self.file_history_view = QtGui.QListView(self.details_panel)
        self.file_history_view.setObjectName("file_history_view")
        self.verticalLayout_2.addWidget(self.file_history_view)
        self.verticalLayout.addWidget(self.details_splitter)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.details_button.setText(QtGui.QApplication.translate("Dialog", "Show Details", None, QtGui.QApplication.UnicodeUTF8))

from ..framework_qtwidgets import ShotgunFolderWidget, GroupedItemView
