# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Y:\SGTK\devs\tk-multi-breakdown2\resources\dialog.ui'
#
# Created: Tue Sep 29 12:07:10 2020
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(400, 300)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.file_view = GroupedListView(Dialog)
        self.file_view.setObjectName("file_view")
        self.verticalLayout.addWidget(self.file_view)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Form", None, QtGui.QApplication.UnicodeUTF8))

from ..framework_qtwidgets import GroupedListView
