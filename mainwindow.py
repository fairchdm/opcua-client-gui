#! /usr/bin/env python3

import sys 
sys.path.insert(0, "..") #FIXME remove

from PySide import QtCore
from PySide import QtGui 


from uaclient import UaClient
from mainwindow_ui import Ui_MainWindow

from IPython import embed


class SubHandler(object):

    """
    Subscription Handler. To receive events from server for a subscription
    """
    def __init__(self, model):
        self._model = model

    def data_change(self, handle, node, val, attr):
        print("Python: New data change event", handle, node, val, attr)
        items = self._model.findItems(node.nodeid.to_string(), column=2)
        print("ITEMS are ", items)
        for item in items:
            idx = self._model.indexFromItem(item)
            i = idx.sibling(idx.row(), 3)
            it = self._model.itemFromIndex(i)
            it.setText(str(val))

    def event(self, handle, event):
        print("Python: New event", handle, event)




class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #fix stuff imposible to do in qtdesigner
        #remove dock titlebar for addressbar
        w = QtGui.QWidget()
        self.ui.addrDockWidget.setTitleBarWidget(w)
        #tabify some docks
        self.tabifyDockWidget(self.ui.evDockWidget, self.ui.subDockWidget)
        self.tabifyDockWidget(self.ui.subDockWidget, self.ui.refDockWidget)


        # init widgets
        self.ui.statusBar.hide()
        self.ui.addrLineEdit.setText("opc.tcp://localhost:4841/")

        self.attr_model = QtGui.QStandardItemModel()
        self.refs_model = QtGui.QStandardItemModel()
        self.sub_model = QtGui.QStandardItemModel()
        self.ui.attrView.setModel(self.attr_model)
        self.ui.refView.setModel(self.refs_model)
        self.ui.subView.setModel(self.sub_model)

        self.model = MyModel(self)
        self.model.clear()
        self.model.error.connect(self.show_error)
        self.ui.treeView.setModel(self.model)
        self.ui.treeView.setUniformRowHeights(True)
        self.ui.treeView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)

        self.uaclient = UaClient() 
        self.ui.connectButton.clicked.connect(self._connect)
        self.ui.disconnectButton.clicked.connect(self._disconnect)
        self.ui.treeView.activated.connect(self._show_attrs_and_refs)
        self.ui.treeView.clicked.connect(self._show_attrs_and_refs)
        self.ui.treeView.expanded.connect(self._fit)

        self.ui.actionSubscribe.triggered.connect(self._subscribe)
        self.ui.actionConnect.triggered.connect(self._connect)
        self.ui.actionDisconnect.triggered.connect(self._disconnect)
        
        # handle subscriptions
        self._subhandler = SubHandler(self.sub_model)

    def show_error(self, msg, level=1):
        print("showing error: ", msg, level)
        self.ui.statusBar.show()
        self.ui.statusBar.setStyleSheet("QStatusBar { background-color : red; color : black; }")
        #self.ui.statusBar.clear()
        self.ui.statusBar.showMessage(str(msg))
        QtCore.QTimer.singleShot(1500, self.ui.statusBar.hide)
        
    def _fit(self, idx):
        self.ui.treeView.resizeColumnToContents(0)

    def _subscribe(self):
        idx = self.ui.treeView.currentIndex()
        it = self.model.itemFromIndex(idx)
        if not id:
            print("No item currently selected")
        node = it.data()
        attrs = self.uaclient.get_node_attrs(node)
        self.sub_model.setHorizontalHeaderLabels(["DisplayName", "Browse Name", 'NodeId', "Value"])
        item = QtGui.QStandardItem(attrs[1])
        self.sub_model.appendRow([item,
                    QtGui.QStandardItem(attrs[2]),
                    QtGui.QStandardItem(attrs[3])
                    ])
        try:
            handle = self.uaclient.subscribe(node, self._subhandler)
        except Exception as ex:
            self.show_error(ex)
            idx = self.sub_model.indexFromItem(item)
            self.sub_model.takeRow(idx.row())

    def unsubscribe(self):
        idx = self.model.currentIndex()
        it = self.model.itemFromIndex(idx)
        if not id:
            print("No item currently selected")
        node = it.data()
        self.uaclient.unsubscribe(node)

    def _show_attrs_and_refs(self, idx):
        it = self.model.itemFromIndex(idx)
        if not it:
            return
        node = it.data()
        if not node:
            print("No node for item:", it, it.text()) 
            return
        self._show_attrs(node)
        self._show_refs(node)

    def _show_refs(self, node):
        self.refs_model.clear()
        self.refs_model.setHorizontalHeaderLabels(['ReferenceType', 'NodeId', "BrowseName", "TypeDefinition"])
        try:
            refs = self.uaclient.get_all_refs(node) 
        except Exception as ex:
            self.show_error(ex)
            raise
        for ref in refs:
            self.refs_model.appendRow([QtGui.QStandardItem(str(ref.ReferenceTypeId)),
                    QtGui.QStandardItem(str(ref.NodeId)),
                    QtGui.QStandardItem(str(ref.BrowseName)),
                    QtGui.QStandardItem(str(ref.TypeDefinition))])
        self.ui.refView.resizeColumnToContents(0)
        self.ui.refView.resizeColumnToContents(1)
        self.ui.refView.resizeColumnToContents(2)
        self.ui.refView.resizeColumnToContents(3)

    def _show_attrs(self, node):
        try:
            attrs = self.uaclient.get_all_attrs(node) 
        except Exception as ex:
            self.show_error(ex)
            raise
        self.attr_model.clear()
        self.attr_model.setHorizontalHeaderLabels(['Attribute', 'Value'])
        for k, v in attrs.items():
            self.attr_model.appendRow([QtGui.QStandardItem(k), QtGui.QStandardItem(str(v))])
        self.ui.attrView.resizeColumnToContents(0)
        self.ui.attrView.resizeColumnToContents(1)

    def _connect(self):
        uri = self.ui.addrLineEdit.text()
        try:
            self.uaclient.connect(uri)
        except Exception as ex:
            self.show_error(ex)
            raise

        self.model.client = self.uaclient
        self.model.clear()
        self.model.add_item(self.uaclient.get_root_attrs())
        self.ui.treeView.resizeColumnToContents(0)
        self.ui.treeView.resizeColumnToContents(1)
        self.ui.treeView.resizeColumnToContents(2)

    def _disconnect(self):
        try:
            self.uaclient.disconnect()
        except Exception as ex:
            self.show_error(ex)
            raise
        finally:
            self.model.clear()
            self.sub_model.clear()
            self.model.client = None

    def closeEvent(self, event):
        self._disconnect()
        event.accept()


class MyModel(QtGui.QStandardItemModel):

    error = QtCore.Signal(str)

    def __init__(self, parent):
        super(MyModel, self).__init__(parent)
        self.client = None
        self._fetched = [] 

    def clear(self):
        QtGui.QStandardItemModel.clear(self)
        self._fetched = []
        self.setHorizontalHeaderLabels(['Name', "Browse Name", 'NodeId'])

    def add_item(self, attrs, parent=None):
        data = [QtGui.QStandardItem(str(attr)) for attr in attrs[1:]]
        data[0].setData(attrs[0])
        if parent:
            return parent.appendRow(data)
        else:
            return self.appendRow(data)

    def canFetchMore(self, idx):
        item = self.itemFromIndex(idx)
        if not item:
            return True
        node = item.data()
        if node not in self._fetched:
            self._fetched.append(node)
            return True
        return False

    def hasChildren(self, idx):
        item = self.itemFromIndex(idx)
        if not item:
            return True
        node = item.data()
        if node in self._fetched:
            return QtGui.QStandardItemModel.hasChildren(self, idx)
        return True

    def fetchMore(self, idx):
        parent = self.itemFromIndex(idx)
        if parent:
            self._fetchMore(parent)

    def _fetchMore(self, parent):
        try:
            for attrs in self.client.get_children(parent.data()):
                self.add_item(attrs, parent)
        except Exception as ex:
            self.error.emit(ex)
            raise



if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

