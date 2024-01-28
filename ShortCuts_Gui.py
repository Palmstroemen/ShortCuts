# ShortCuts overlay for FreeCAD
# Copyright (C) 2016, 2017, 2018 triplus @ FreeCAD
#
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

"""Shortcuts manager for FreeCAD"""


import os
from PySide import QtWidgets, QtGui, QtCore
import FreeCADGui as Gui
import FreeCAD as App


scheme = {}
actions = {}
defaults = {}
localUser = {}
globalUser = {}
mw = Gui.getMainWindow()
verify = QtGui.QAction(mw)
p = App.ParamGet("User parameter:BaseApp/ShortCutsDev")
path = os.path.dirname(__file__) + "/Resources/icons/"
__showAll__ = False


def wbIcon(i):
    """Create workbench icon."""
    if str(i.find("XPM")) != "-1":
        try:
            icon = []
            for a in ((((i
                         .split('{', 1)[1])
                        .rsplit('}', 1)[0])
                       .strip())
                      .split("\n")):
                icon.append((a
                             .split('"', 1)[1])
                            .rsplit('"', 1)[0])
            icon = QtGui.QIcon(QtGui.QPixmap(icon))
        except:
            icon = QtGui.QIcon(":/icons/freecad")
    else:
        icon = QtGui.QIcon(QtGui.QPixmap(i))
    if icon.isNull():
        icon = QtGui.QIcon(":/icons/freecad")
    return icon


def itemIcon(command):
    """Shortcut item icon indicator."""
    if command in localUser and command in defaults and defaults[command]:
        icon = QtGui.QIcon(path + os.sep + "ShortCuts_LocalGlobal.svg")
    elif command in localUser and command in globalUser:
        icon = QtGui.QIcon(path + os.sep + "ShortCuts_LocalGlobal.svg")
    elif command in localUser:
        icon = QtGui.QIcon(path + os.sep + "ShortCuts_Local.svg")
    else:
        icon = QtGui.QIcon(path + os.sep + "ShortCuts_Global.svg")
    return icon


def updateActions():
    """Create and update a dictionary of unique actions."""
    actions.clear()
    duplicates = []
    for i in mw.findChildren(QtGui.QAction):
        name = i.objectName()
        if name and i.text() and "," not in name:
            if name in actions:
                if name not in duplicates:
                    duplicates.append(name)
            else:
                actions[name] = i
    for d in duplicates:
        del actions[d]


def hasGroup(source=None, workbench=None):
    """Reduce creation of empty database groups."""
    if not all([source, workbench]):
        return False
    if not p.HasGroup(source):
        return False
    if not p.GetGroup(source).HasGroup(workbench):
        return False
    return True


def splitIndex(source=None, workbench=None):
    """Create and return an index list."""
    index = []
    if not all([source, workbench]):
        return index
    if not hasGroup(source, workbench):
        return index
    index = p.GetGroup(source).GetGroup(workbench).GetString("index")
    if index:
        index = index.split(",")
    return index


def resetShortcuts():
    """Reset shortcuts to defaults."""
    for s in scheme:
        if s in defaults and s in actions:
            actions[s].setShortcut(QtGui.QKeySequence(defaults[s]))
        elif s in actions:
            actions[s].setShortcut(QtGui.QKeySequence(""))
        else:
            pass


def applyShortcuts():
    """Save defaults and apply shortcuts from scheme."""
    for a in actions:
        if a not in defaults:
            defaults[a] = actions[a].shortcut().toString()
    for s in scheme:
        if s in actions:
            actions[s].setShortcut(QtGui.QKeySequence(scheme[s]))


def printShortcuts():
    """Print active shortcuts to the report view"""
    for a in mw.findChildren(QtGui.QAction):
        if a.shortcut().toString():
            if a.text():
                text = a.text()
            else:
                text = "N/A"
            App.Console.PrintMessage(text.replace("&", "") +
                                     "\t" +
                                     a.shortcut().toString() +
                                     "\n")


def updateDict(source, wb, userLG):
    """Update dictionary."""
    if not hasGroup(source, wb):
        return False
    index = splitIndex(source, wb)
    base = p.GetGroup(source).GetGroup(wb)
    for i in index:
        g = base.GetGroup(i)
        command = g.GetString("command")
        # Py2/Py3
        try:
            shortcut = g.GetString("shortcut").decode("UTF-8")
        except AttributeError:
            shortcut = g.GetString("shortcut")
        if command and shortcut:
            userLG[command] = shortcut
            if command not in scheme:
                scheme[command] = shortcut
    return True


def update(workbench):
    """Update shortcuts and apply them."""
    updateActions()
    resetShortcuts()

    scheme.clear()
    localUser.clear()
    updateDict("User", workbench, localUser)
    globalUser.clear()
    if workbench != "GlobalShortcuts":
        updateDict("User", "GlobalShortcuts", globalUser)

    applyShortcuts()


def onWorkbench():
    """Update shortcuts on workbench activated."""
    workbench = Gui.activeWorkbench().__class__.__name__
    update(workbench)


def wbSelectorWidget():
    """Workbench selector combo box."""
    wbSelector = QtGui.QListWidget()
    wbSelector.setMinimumWidth(220)

    listWB = Gui.listWorkbenches()
    listWBSorted = sorted(listWB)
    listWBSorted.reverse()

    icon = QtGui.QIcon(":/icons/freecad")
    item = QtGui.QListWidgetItem(icon, "Global shortcuts", wbSelector)
    item.setData(QtCore.Qt.UserRole, "GlobalShortcuts")
    wbSelector.addItem(item)
    for i in listWBSorted:
        try:
            icon = wbIcon(Gui.listWorkbenches()[i].Icon)
        except AttributeError:
            icon = QtGui.QIcon(":/icons/freecad")
        item = QtGui.QListWidgetItem(icon, listWB[i].MenuText, wbSelector)
        item.setData(QtCore.Qt.UserRole, listWB[i].__class__.__name__)
        wbSelector.addItem(item)

    wbSelector.setCurrentRow(0)

    activeWB = Gui.activeWorkbench().__class__.__name__
    for count in range(wbSelector.count()):
        item = wbSelector.item(count)
        if item is not None:
            item_data = item.data(QtCore.Qt.UserRole)
            if item_data == activeWB:
                wbSelector.setCurrentRow(count)
    return wbSelector


def searchLine(table):
    """Search line for preferences."""
    search = QtGui.QLineEdit()

    def onSearch(text):
        """Show or hide commands on search."""
        for n in range(table.rowCount()):
            t = table.item(n, 0).text()
            if t and text and text.lower() in t.lower():
                table.setRowHidden(n, False)
            elif text:
                table.setRowHidden(n, True)
            else:
                table.setRowHidden(n, False)

    search.textEdited.connect(onSearch)
    return search



def tableWidget():
    """Table for commands and shortcuts."""
    table = QtGui.QTableWidget(0, 2)
    table.verticalHeader().setVisible(False)
    table.setHorizontalHeaderLabels(["Shortcut", "Command"])
    table.setFixedWidth(300)
    table.setColumnWidth(0, 100)
    
    # Qt4/Qt5
    try:
        table.horizontalHeader().setSectionResizeMode(0, QtGui.QHeaderView.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QtGui.QHeaderView.Stretch)
    except AttributeError:
        table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Fixed)
        table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
    table.setColumnWidth(0, 100)  # Set the desired width for the first column
    return table

def updateTable(wbSelector, table):
    """Update table widget items."""
    #workbench = wbSelector.itemData(wbSelector.currentIndex())
    wb = wbSelector.selectedItems()
    wb = wb[0]
    workbench = wb.data(QtCore.Qt.UserRole)

    update(workbench)

    # build shortcuts list
    actionList = []
    row = 0
    for i in actions:
        text = actions[i].text()
        text = text.replace("&", "")
        shortcut = actions[i].shortcut().toString()
        if shortcut:
            row += 1
        actionList.append([text, actions[i].objectName(), shortcut])
    App.tableNames = actionList

    if __showAll__: # sort by action
        actionList = sorted(actionList)
        row   = len(actions)
    else: # sort by shortcut (the third element of triple in action list)
        actionList = sorted(actionList,key=lambda x: x[2])
    sort = []
    for i in actionList:
        sort.append(i[1])

    table.blockSignals(True)
    table.clearContents()
    table.setRowCount(row)

    # build the table
    row = 0
    iconNr = 0
    for i in sort:
        showLine = True
        shortcut = QtGui.QTableWidgetItem()
        text = actions[i].shortcut().toString()
        if text:
            shortcut.setText(text)
            shortcut.setIcon(QtGui.QIcon(itemIcon(i)))
        elif not __showAll__:
            showLine = False

        if showLine:
            shortcut.setData(32, i)

            command = QtGui.QTableWidgetItem()
            text = actions[i].text()
            text = text.replace("&", "")
            command.setText(text)
            command.setToolTip(actions[i].toolTip())
            command.setFlags(QtCore.Qt.ItemIsEnabled)
            if actions[i].icon():
                command.setIcon(actions[i].icon())
            else:
                command.setIcon(QtGui.QIcon(":/icons/freecad"))

            table.setItem(row, 0, shortcut)
            table.setItem(row, 1, command)
            row += 1
    table.blockSignals(False)


def database(source=None, workbench=None, commands=None):
    """Manage shortcuts database access."""
    current = {}
    index = splitIndex(source, workbench)
    if index:
        base = p.GetGroup(source).GetGroup(workbench)
        for i in index:
            command = base.GetGroup(i).GetString("command")
            # Py2/Py3
            try:
                shortcut = (base
                            .GetGroup(i)
                            .GetString("shortcut")
                            .decode("UTF-8"))
            except AttributeError:
                shortcut = base.GetGroup(i).GetString("shortcut")
            if command and shortcut:
                current[command] = shortcut
        p.GetGroup(source).RemGroup(workbench)
    if commands:
        for cmd in commands:
            if commands[cmd]:
                current[cmd] = commands[cmd]
            elif cmd in current:
                del current[cmd]
            else:
                pass
    n = 1
    index = []
    base = p.GetGroup(source).GetGroup(workbench)
    for i in current:
        index.append(str(n))
        g = base.GetGroup(str(n))
        g.SetString("command", i)
        # Py2/Py3
        try:
            g.SetString("shortcut", current[i].encode("UTF-8"))
        except TypeError:
            g.SetString("shortcut", current[i])
        n += 1
    base.SetString("index", ",".join(index))
    if not splitIndex(source, workbench):
        p.GetGroup(source).RemGroup(workbench)

import Keyboard_Layout as kb

def preferences():
    """ShortCuts preferences dialog."""
    def onAccepted():
        """Close dialog on button close."""
        dia.done(1)

    def onFinished():
        """Delete dialog on close."""
        dia.deleteLater()
        onWorkbench()

    # Dialog
    dia = QtGui.QDialog(mw)
    dia.setModal(True)
    dia.resize(1100, 600)
    dia.setWindowTitle("Shortcuts")
    dia.finished.connect(onFinished)
    layout = QtGui.QVBoxLayout()
    dia.setLayout(layout)

    # Button close
    btnClose = QtGui.QPushButton("Close")
    btnClose.setToolTip("Close the preferences dialog")
    btnClose.clicked.connect(onAccepted)

    # Button print
    btnPrint = QtGui.QPushButton("Print")
    btnPrint.setToolTip("Print active shortcuts to the report view")
    btnPrint.clicked.connect(printShortcuts)

    loBtn = QtGui.QHBoxLayout()
    loBtn.addWidget(btnPrint)
    loBtn.addStretch()
    loBtn.addWidget(btnClose)

    # wbSelector
    wbSelector = wbSelectorWidget()
    wbSelector.setWindowTitle("select workbench")
    wbSelector.setFixedWidth(200)

    # Table widget
    table = tableWidget()

    # Search
    search = searchLine(table)

    # Functions and connections
    def onItemChanged(item):
        """Save shortcut."""
        workbench = wbSelector.itemData(wbSelector.currentIndex())
        command = item.data(32)
        shortcut = item.text()
        verify.setShortcut(QtGui.QKeySequence(shortcut))
        shortcut = verify.shortcut().toString()
        verify.setShortcut(QtGui.QKeySequence(""))
        database("User", workbench, commands={command: shortcut})
        update(workbench)
        table.blockSignals(True)
        if shortcut:
            item.setText(shortcut)
            item.setIcon(itemIcon(command))
        elif command in scheme and scheme[command]:
            item.setText(scheme[command])
            item.setIcon(itemIcon(command))
        elif command in defaults and defaults[command]:
            item.setText(defaults[command])
            item.setIcon(itemIcon(command))
        else:
            item.setText("")
            item.setIcon(QtGui.QIcon())
        table.blockSignals(False)

    table.itemChanged.connect(onItemChanged)

    def onCurrentWBchanged():
        """Activate workbench on selection."""
        selected_items = wbSelector.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            wb = selected_item.data(QtCore.Qt.UserRole)
            try:
                Gui.activateWorkbench(wb)
            except:
                a = 2 # dummy reaction.
        updateTable(wbSelector, table)

    def on_header_click(logical_index):
        header = table.horizontalHeaderItem(logical_index).text()
        print("Clicked on", header)
        global __showAll__
        if header == "Shortcut":
            __showAll__ = False
        else:
            __showAll__ = True
        updateTable(wbSelector, table)

    table.horizontalHeader().sectionClicked.connect(on_header_click)
    wbSelector.itemSelectionChanged.connect(onCurrentWBchanged)

    updateTable(wbSelector, table)

    # Layout
    loRight = QtGui.QVBoxLayout()
    loRight.addWidget(search)
    loRight.addWidget(table)
    loRight.insertLayout(2, loBtn)

    loMid = QtGui.QVBoxLayout()
    keyboard = kb.KeyboardLayout()
    loMid.addWidget(keyboard)
    loMid.addStretch()

    loTop = QtGui.QHBoxLayout()
    loTop.addWidget(wbSelector)
    loTop.insertLayout(1,loMid)
    loTop.insertLayout(2,loRight)

    layout.insertLayout(0, loTop)

    btnClose.setDefault(True)
    btnClose.setFocus()

    return dia


def onPreferences():
    """Open the preferences dialog."""
    dia = preferences()
    dia.show()


def accessoriesMenu():
    """Add ShortCuts preferences to accessories menu."""
    pref = QtGui.QAction(mw)
    pref.setText("ShortcutsDeveloper")
    pref.setObjectName("ShortCutsDeveloper")
    pref.triggered.connect(onPreferences)
    try:
        import AccessoriesMenu
        AccessoriesMenu.addItem("ShortCutsDeveloper")
    except ImportError:
        a = mw.findChild(QtGui.QAction, "AccessoriesMenu")
        if a:
            a.menu().addAction(pref)
        else:
            mb = mw.menuBar()
            action = QtGui.QAction(mw)
            action.setObjectName("AccessoriesMenu")
            action.setIconText("Accessories")
            m = QtGui.QMenu()
            action.setMenu(m)
            m.addAction(pref)

            def addMenu():
                """Add accessories menu to the menu bar."""
                mb.addAction(action)
                action.setVisible(True)

            addMenu()
            mw.workbenchActivated.connect(addMenu)


def onStart():
    """Start shortcuts."""
    start = False
    try:
        mw.workbenchActivated
        start = True
    except AttributeError:
        pass

    if start:
        timer.stop()
        timer.deleteLater()
        onWorkbench()
        accessoriesMenu()
        mw.workbenchActivated.connect(onWorkbench)


def onPreStart():
    """Improve start reliability and maintain FreeCAD 0.16 support."""
    if App.Version()[1] < "17":
        onStart()
    else:
        if mw.property("eventLoop"):
            onStart()


timer = QtCore.QTimer()
timer.timeout.connect(onPreStart)
timer.start(500)
