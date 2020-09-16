# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Y:\SGTK\devs\tk-multi-breakdown2\resources\file_widget.ui'
#
# Created: Fri Sep 11 15:55:17 2020
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_FileWidget(object):
    def setupUi(self, FileWidget):
        FileWidget.setObjectName("FileWidget")
        FileWidget.resize(470, 135)
        self.horizontalLayout = QtGui.QHBoxLayout(FileWidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = QtGui.QFrame(FileWidget)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.frame)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.icon = QtGui.QLabel(self.frame)
        self.icon.setMinimumSize(QtCore.QSize(16, 16))
        self.icon.setMaximumSize(QtCore.QSize(16, 16))
        self.icon.setText("")
        self.icon.setPixmap(QtGui.QPixmap(":/tk-multi-breakdown2/green_bullet.png"))
        self.icon.setScaledContents(True)
        self.icon.setObjectName("icon")
        self.horizontalLayout_2.addWidget(self.icon)
        self.shotgun_widget = ShotgunListWidget(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.shotgun_widget.sizePolicy().hasHeightForWidth())
        self.shotgun_widget.setSizePolicy(sizePolicy)
        self.shotgun_widget.setObjectName("shotgun_widget")
        self.horizontalLayout_2.addWidget(self.shotgun_widget)
        self.horizontalLayout.addWidget(self.frame)

        self.retranslateUi(FileWidget)
        QtCore.QMetaObject.connectSlotsByName(FileWidget)

    def retranslateUi(self, FileWidget):
        FileWidget.setWindowTitle(QtGui.QApplication.translate("FileWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))

from ..framework_qtwidgets import ShotgunListWidget
from . import resources_rc
