# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Y:\SGTK\devs\tk-multi-breakdown2\resources\file_group_widget.ui'
#
# Created: Thu Sep 03 15:56:17 2020
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_FileGroupWidget(object):
    def setupUi(self, FileGroupWidget):
        FileGroupWidget.setObjectName("FileGroupWidget")
        FileGroupWidget.resize(411, 50)
        FileGroupWidget.setMinimumSize(QtCore.QSize(0, 50))
        FileGroupWidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.verticalLayout = QtGui.QVBoxLayout(FileGroupWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.header_layout = QtGui.QHBoxLayout()
        self.header_layout.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.header_layout.setObjectName("header_layout")
        self.expand_check_box = QtGui.QCheckBox(FileGroupWidget)
        self.expand_check_box.setMinimumSize(QtCore.QSize(0, 20))
        self.expand_check_box.setText("")
        self.expand_check_box.setObjectName("expand_check_box")
        self.header_layout.addWidget(self.expand_check_box)
        self.header = QtGui.QLabel(FileGroupWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.header.sizePolicy().hasHeightForWidth())
        self.header.setSizePolicy(sizePolicy)
        self.header.setObjectName("header")
        self.header_layout.addWidget(self.header)
        spacerItem = QtGui.QSpacerItem(0, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.header_layout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.header_layout)
        self.line = QtGui.QFrame(FileGroupWidget)
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout.addWidget(self.line)

        self.retranslateUi(FileGroupWidget)
        QtCore.QMetaObject.connectSlotsByName(FileGroupWidget)

    def retranslateUi(self, FileGroupWidget):
        FileGroupWidget.setWindowTitle(QtGui.QApplication.translate("FileGroupWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.header.setText(QtGui.QApplication.translate("FileGroupWidget", "Header", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
