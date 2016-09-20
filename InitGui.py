# ShortCuts overlay for FreeCAD
# Copyright (C) 2016  triplus @ FreeCAD
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


from PySide import QtGui
import FreeCADGui as Gui

mw = Gui.getMainWindow()


def shortCuts():
    """
    ShortCuts overlay for FreeCAD.
    """
    import platform
    from PySide import QtGui
    from PySide import QtCore
    import FreeCADGui as Gui
    import FreeCAD as App

    macOS = False

    if platform.system() == "Darwin":
        macOS = True
    else:
        pass

    mw = Gui.getMainWindow()
    mdi = mw.findChild(QtGui.QMdiArea)
    paramGet = App.ParamGet("User parameter:BaseApp/ShortCuts/User")

    iconSvgNone = """<svg
        xmlns="http://www.w3.org/2000/svg" height="64" width="64">
         <rect height="64" width="64" fill="none" />
        </svg>"""

    iconSvgLocal = """<svg
        xmlns="http://www.w3.org/2000/svg" height="64" width="64">
         <circle cx="32" cy="32" r="20"
          stroke="black" stroke-width="2" fill="#008000" />
        </svg>"""

    iconSvgGlobal = """<svg
        xmlns="http://www.w3.org/2000/svg" height="64" width="64">
         <circle cx="32" cy="32" r="20"
          stroke="black" stroke-width="2" fill="#edd400" />
        </svg>"""

    iconSvgLG = """<svg
        xmlns="http://www.w3.org/2000/svg" height="64" width="64">
         <circle cx="44" cy="44" r="18"
          stroke="black" stroke-width="2" fill="#edd400" />
         <circle cx="20" cy="20" r="18"
          stroke="black" stroke-width="2" fill="#008000" />
        </svg>"""

    iconSvgPref = """<svg
        xmlns="http://www.w3.org/2000/svg" height="64" width="64">
         <rect height="7" width="44" y="11" x="10" fill="#888a85" />
         <rect height="7" width="44" y="28.5" x="10" fill="#888a85" />
         <rect height="7" width="44" y="46" x="10" fill="#888a85" />
        </svg>"""

    iconPixNone = QtGui.QPixmap()
    iconPixNone.loadFromData(iconSvgNone)

    iconPixLocal = QtGui.QPixmap()
    iconPixLocal.loadFromData(iconSvgLocal)

    iconPixGlobal = QtGui.QPixmap()
    iconPixGlobal.loadFromData(iconSvgGlobal)

    iconPixLG = QtGui.QPixmap()
    iconPixLG.loadFromData(iconSvgLG)

    iconPixPref = QtGui.QPixmap()
    iconPixPref.loadFromData(iconSvgPref)

    iconFreeCAD = QtGui.QIcon.fromTheme("freecad")

    if iconFreeCAD.isNull():
        iconFreeCAD = QtGui.QIcon(iconPixNone)
    else:
        pass

    styleEdit = """
        QLineEdit {
            border: 1px outset silver;
        }"""

    styleButtonPref = """
        QToolButton {
            border: 1px solid #1e1e1e;
            background-color: #3c3c3c;
        }"""

    styleContainer = """
        QMenu {
            background: transparent
        }"""

    def xpmParse(i):
        """
        Parse and prepare workbench icon in XPM format.
        """
        icon = []

        for a in ((((i
                     .split('{', 1)[1])
                    .rsplit('}', 1)[0])
                   .strip())
                  .split("\n")):
            icon.append((a
                         .split('"', 1)[1])
                        .rsplit('"', 1)[0])

        return icon

    def wbIcon(i):
        """
        Create and return workbench icon.
        """
        if str(i.find("XPM")) != "-1":
            icon = QtGui.QIcon(QtGui.QPixmap(xpmParse(i)))
        else:
            icon = QtGui.QIcon(QtGui.QPixmap(i))

        if icon.isNull():
            icon = iconFreeCAD
        else:
            pass

        return icon

    def actionList():
        """
        Create a dictionary of unique actions.
        """
        actions = {}
        duplicates = []

        for i in mw.findChildren(QtGui.QAction):
            if i.objectName() and i.text():
                if i.objectName() in actions:
                    if i.objectName() not in duplicates:
                        duplicates.append(i.objectName())
                    else:
                        pass
                else:
                    actions[i.objectName()] = i
            else:
                pass

        for d in duplicates:
            del actions[d]

        return actions

    class ShortCutsEdit(QtGui.QLineEdit):
        """
        ShortCuts main line edit.
        """
        def __init__(self, parent=None):
            super(ShortCutsEdit, self).__init__(parent)

        def focusOutEvent(self, e):
            """
            Hide line edit when focus is lost.
            """
            setVisibility()

        def keyPressEvent(self, e):
            """
            Hide line edit on ESC key.
            Show all available completions on down key.
            """
            if e.key() == QtCore.Qt.Key_Escape:
                setVisibility()
            elif e.key() == QtCore.Qt.Key_Down:
                edit.clear()
                completer.setCompletionPrefix("")
                completer.complete()
            else:
                QtGui.QLineEdit.keyPressEvent(self, e)

    def globalShortcuts():
        """
        Create a dictionary of available global shortcuts.
        """
        currentGlobal.clear()
        index = paramGet.GetGroup("Global shortcuts").GetString("IndexList")
        index = index.split(",")

        for i in index:
            command = (paramGet
                       .GetGroup("Global shortcuts")
                       .GetGroup(i)
                       .GetString("command")
                       .decode("UTF-8"))

            shortcut = (paramGet
                        .GetGroup("Global shortcuts")
                        .GetGroup(i)
                        .GetString("shortcut")
                        .decode("UTF-8"))

            if command and shortcut:
                currentGlobal[command] = shortcut
            else:
                index.remove(i)
                paramGet.GetGroup("Global shortcuts").RemGroup(i)

        string = ",".join(index)
        paramGet.GetGroup("Global shortcuts").SetString("IndexList", string)

    def localShortcuts():
        """
        Create a dictionary of available local shortcuts.
        """
        currentLocal.clear()

        if Gui.activeWorkbench().MenuText:
            activeWB = Gui.activeWorkbench().MenuText
        else:
            activeWB = None

        if activeWB:
            index = paramGet.GetGroup(activeWB).GetString("IndexList")
            index = index.split(",")

            for i in index:
                command = (paramGet
                           .GetGroup(activeWB)
                           .GetGroup(i)
                           .GetString("command")
                           .decode("UTF-8"))

                shortcut = (paramGet
                            .GetGroup(activeWB)
                            .GetGroup(i)
                            .GetString("shortcut")
                            .decode("UTF-8"))

                if command and shortcut:
                    currentLocal[command] = shortcut
                else:
                    index.remove(i)
                    paramGet.GetGroup(activeWB).RemGroup(i)

            string = ",".join(index)
            paramGet.GetGroup(activeWB).SetString("IndexList", string)
        else:
            pass

    def itemList(activeWB=None):
        """
        Create and return an alphabetically sorted list
        of table widget items.
        """
        items = []
        names = []
        applyShortcuts()
        actions = actionList()

        for i in actions:
            text = actions[i].text()
            text = text.replace("&", "")
            names.append([text, actions[i].objectName()])

        names = sorted(names)

        sort = []

        for i in names:
            sort.append(i[1])

        for i in sort:
            if i in actions:
                command = QtGui.QTableWidgetItem()
                text = actions[i].text()
                text = text.replace("&", "")
                command.setText(text)
                command.setToolTip(actions[i].toolTip())
                command.setFlags(QtCore.Qt.ItemIsEnabled)

                if actions[i].icon():
                    command.setIcon(actions[i].icon())
                else:
                    command.setIcon(QtGui.QIcon(iconPixNone))

                shortcut = QtGui.QTableWidgetItem()

                if (i in currentLocal and
                        i in currentGlobal and
                        activeWB != "Global shortcuts"):
                    shortcut.setText(currentLocal[i])
                    shortcut.setIcon(QtGui.QIcon(iconPixLG))
                    shortcut.setToolTip(activeWB +
                                        ": " +
                                        currentLocal[i] +
                                        "    Global: " +
                                        currentGlobal[i])
                elif i in currentLocal and activeWB != "Global shortcuts":
                    shortcut.setText(currentLocal[i])
                    shortcut.setIcon(QtGui.QIcon(iconPixLocal))
                    shortcut.setToolTip(activeWB + ": " + currentLocal[i])
                elif i in currentGlobal:
                    shortcut.setText(currentGlobal[i])
                    shortcut.setIcon(QtGui.QIcon(iconPixGlobal))
                    shortcut.setToolTip("Global: " + currentGlobal[i])
                else:
                    pass

                shortcut.setData(QtCore.Qt.UserRole, actions[i].objectName())

                items.append([command, shortcut])
            else:
                pass

        return items

    def groupNum(activeWB, command):
        """
        Search for existing command group index number.
        Define new command group index number if one does not exist yet.
        """
        indexNumber = None
        index = paramGet.GetGroup(activeWB).GetString("IndexList")
        index = index.split(",")

        for i in index:
            if (paramGet
                    .GetGroup(activeWB)
                    .GetGroup(i)
                    .GetString("command")
                    .decode("UTF-8") == command):
                indexNumber = i
            else:
                pass

        if not indexNumber:
            x = 1
            maxNum = 999

            while str(x) in index and x < maxNum:
                x += 1
            else:
                indexNumber = str(x)

            if indexNumber and int(indexNumber) != maxNum:
                index.append(indexNumber)
                (paramGet
                 .GetGroup(activeWB)
                 .SetString("IndexList", ",".join(index)))
            else:
                indexNumber = None
        else:
            pass

        return indexNumber

    def deleteGroup(activeWB, command):
        """
        Delete the command data and corresponding group from the database.
        """
        index = paramGet.GetGroup(activeWB).GetString("IndexList")
        index = index.split(",")

        for i in index:
            if (paramGet
                    .GetGroup(activeWB)
                    .GetGroup(i)
                    .GetString("command")
                    .decode("UTF-8") == command):
                index.remove(i)
                paramGet.GetGroup(activeWB).RemGroup(i)
                (paramGet
                 .GetGroup(activeWB)
                 .SetString("IndexList", ",".join(index)))
            else:
                pass

    model = QtGui.QStandardItemModel()
    model.setColumnCount(1)

    def modelData():
        """
        Model data for completer.
        """
        applyShortcuts()

        actions = actionList()

        if Gui.activeWorkbench().MenuText:
            activeWB = Gui.activeWorkbench().MenuText
        else:
            activeWB = None

        row = 0
        model.clear()

        if activeWB:
            for command in currentLocal:
                if command in actions:
                    item = QtGui.QStandardItem()

                    shortcut = currentLocal[command]

                    text = (shortcut +
                            "  " +
                            (actions[command].text()).replace("&", ""))

                    item.setText(text)

                    if actions[command].icon():
                        item.setIcon(actions[command].icon())
                    else:
                        item.setIcon(QtGui.QIcon(iconPixNone))

                    item.setToolTip(actions[command].toolTip())
                    item.setEnabled(actions[command].isEnabled())
                    item.setData(actions[command].objectName(),
                                 QtCore.Qt.UserRole)

                    model.setItem(row, 0, item)
                    row += 1

            for command in currentGlobal:
                if command in actions:
                    item = QtGui.QStandardItem()

                    shortcut = currentGlobal[command]

                    text = (shortcut +
                            "  " +
                            (actions[command].text()).replace("&", ""))

                    item.setText(text)

                    if actions[command].icon():
                        item.setIcon(actions[command].icon())
                    else:
                        item.setIcon(QtGui.QIcon(iconPixNone))

                    item.setToolTip(actions[command].toolTip())
                    item.setEnabled(actions[command].isEnabled())
                    item.setData(actions[command].objectName(),
                                 QtCore.Qt.UserRole)

                    model.setItem(row, 0, item)
                    row += 1

    completer = QtGui.QCompleter()
    completer.setModel(model)
    completer.setMaxVisibleItems(16)
    completer.popup().setMinimumWidth(220)
    completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

    def onHighlighted():
        """
        Hide preferences button.
        Increase line edit size.
        """
        buttonPref.hide()
        edit.setMinimumWidth(220)

    completer.highlighted.connect(onHighlighted)

    def onCompleter(modelIndex):
        """
        Run selected command on completion.
        Set visibility.
        """
        actions = actionList()

        index = completer.completionModel().mapToSource(modelIndex)
        item = model.itemFromIndex(index)
        data = item.data(QtCore.Qt.UserRole)

        if data in actions:
            actions[data].trigger()
        else:
            pass

        setVisibility(mode=1)

    completer.activated[QtCore.QModelIndex].connect(onCompleter)

    edit = ShortCutsEdit()
    edit.hide()
    edit.setCompleter(completer)
    edit.setStyleSheet(styleEdit)
    edit.setGeometry(10, 10, 40, 24)
    edit.setAlignment(QtCore.Qt.AlignHCenter)
    edit.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def onTextEdited(text):
        """
        Restore default line edit size.
        """
        if text:
            pass
        else:
            edit.setMinimumWidth(40)
            edit.setGeometry(10, 10, 40, 24)
            buttonPref.show()

    edit.textEdited.connect(onTextEdited)

    def onReturnPressed():
        """
        Clear or hide line edit after enter key is pressed.
        """
        if edit.text():
            edit.clear()
        else:
            setVisibility()

    edit.returnPressed.connect(onReturnPressed)

    buttonPref = QtGui.QToolButton()
    buttonPref.hide()
    buttonPref.setGeometry(60, 10, 24, 24)
    buttonPref.setStyleSheet(styleButtonPref)

    actionPref = QtGui.QAction(buttonPref)
    actionPref.setIcon(QtGui.QIcon(iconPixPref))

    buttonPref.setDefaultAction(actionPref)

    def onPreferences():
        """
        Delete existing preferences dialog if it exists.
        Open new preferences dialog.
        """
        for i in mw.findChildren(QtGui.QDialog):
            if i.objectName() == "ShortCuts":
                i.deleteLater()
            else:
                pass

        dialog = prefDialog()
        dialog.show()

    buttonPref.triggered.connect(onPreferences)

    currentLocal = {}
    currentGlobal = {}

    if macOS:
        menu = QtGui.QMenu(mw)
        menu.setParent(mw)
        menu.setMinimumWidth(236)
        menu.setMinimumHeight(36)
        menu.setGeometry(0, 0, 236, 36)
        menu.setStyleSheet(styleContainer)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint)

        edit.setParent(menu)
        buttonPref.setParent(menu)
    else:
        edit.setParent(mdi)
        buttonPref.setParent(mdi)

    def setVisibility(mode=0):
        """
        Restore default line edit size.
        Show or hide ShortCuts.
        """
        mdi = mw.findChild(QtGui.QMdiArea)

        edit.setMinimumWidth(40)
        edit.setGeometry(10, 10, 40, 24)

        if macOS:
            if menu.isVisible() or mode == 1:
                edit.clear()
                menu.hide()
                completer.popup().hide()
                mdi.setFocus()
            else:
                modelData()
                edit.clear()
                menu.popup(QtCore.QPoint(mw.geometry().x() + mdi.pos().x(),
                                         mw.geometry().y() + mdi.pos().y()))
                edit.setVisible(True)
                buttonPref.setVisible(True)
                edit.setFocus()
        else:
            if edit.isVisible() or mode == 1:
                edit.clear()
                edit.hide()
                completer.popup().hide()
                buttonPref.hide()
                mdi.setFocus()
            else:
                modelData()
                edit.show()
                edit.clear()
                buttonPref.show()
                edit.setFocus()

    invokeKey = QtGui.QAction(mw)
    invokeKey.setObjectName("Std_ShortCuts")
    invokeKey.setShortcut(QtGui.QKeySequence("W"))
    invokeKey.triggered.connect(setVisibility)

    additionalKey = QtGui.QAction(mw)
    additionalKey.triggered.connect(setVisibility)

    mw.addAction(invokeKey)
    mw.addAction(additionalKey)

    def setInvokeKey():
        """
        Set invoke and additional invoke key shortcut combination.
        """
        modifiers = ["CTRL+",
                     "SHIFT+",
                     "ALT+",
                     "META+"]

        enable = paramGet.GetBool("InvokeKey")
        key = paramGet.GetString("InvokeKey").decode("UTF-8")
        modifier = paramGet.GetString("ModifierKey").decode("UTF-8")

        if modifier in modifiers:
            pass
        else:
            modifier = None

        if enable and modifier and key:
            text = modifier + key
        elif enable and key:
            text = key
        else:
            text = False

        if text:
            additionalKey.setShortcut(QtGui.QKeySequence(text))
        else:
            additionalKey.setShortcut(None)

        for i in mw.findChildren(QtGui.QAction):
            if i.shortcut().toString() == "W":
                i.setShortcut(None)
            else:
                pass

        invokeKey.setShortcut(QtGui.QKeySequence("W"))

    mw.workbenchActivated.connect(setInvokeKey)

    def applyShortcuts():
        """
        Apply global and local shortcuts.
        """
        globalShortcuts()
        localShortcuts()

    mw.workbenchActivated.connect(applyShortcuts)

    def prefDialog():
        """
        Preferences dialog.
        """
        class InvokeEdit(QtGui.QLineEdit):
            """
            Invoke key line edit.
            """
            def __init__(self, parent=None):
                super(InvokeEdit, self).__init__(parent)

            def keyPressEvent(self, e):
                """
                Set focus (button Done) on Return key pressed.
                """
                if e.key() == QtCore.Qt.Key_Return:
                    buttonDone.setFocus()
                else:
                    QtGui.QLineEdit.keyPressEvent(self, e)

        def comboBox():
            """
            Workbench selector combo box.
            """
            cBox = QtGui.QComboBox()
            cBox.setMinimumWidth(220)

            listWB = Gui.listWorkbenches()
            listWBSorted = sorted(listWB)
            listWBSorted.reverse()

            for i in listWBSorted:
                if i in listWB:
                    try:
                        icon = wbIcon(Gui.listWorkbenches()[i].Icon)
                    except AttributeError:
                        icon = iconFreeCAD

                    cBox.insertItem(0, icon, listWB[i].MenuText)

            cBox.insertSeparator(0)
            icon = iconFreeCAD
            cBox.insertItem(0, icon, "Global shortcuts")
            cBox.setCurrentIndex(0)

            activeWB = Gui.activeWorkbench().MenuText

            for count in range(cBox.count()):

                if cBox.itemText(count) == activeWB:
                    cBox.setCurrentIndex(count)
                else:
                    pass

            def onCurrentIndexChanged():
                """
                Activate workbench on selection.
                """
                listWB = Gui.listWorkbenches()

                for i in listWB:
                    if listWB[i].MenuText == cBox.currentText():
                        Gui.activateWorkbench(i)
                    else:
                        pass

                updateStats()
                updateTable()

            cBox.currentIndexChanged.connect(onCurrentIndexChanged)

            return cBox

        def tableWidget():
            """
            Table of commands and shortcuts.
            """
            table = QtGui.QTableWidget(0, 2)
            table.verticalHeader().setVisible(False)
            table.setHorizontalHeaderLabels(["Command", "Shortcut"])
            table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)

            def onItemChanged(item):
                """
                Save shortcut.
                Delete command from database if no shortcut is provided.
                """
                activeWB = cBox.currentText()

                if item.text() and activeWB and item.data(32):

                    indexNumber = groupNum(activeWB,
                                           item.data(32).encode("UTF-8"))

                    if indexNumber:
                        (paramGet
                         .GetGroup(activeWB)
                         .GetGroup(indexNumber)
                         .SetString("command", item.data(32).encode("UTF-8")))
                        (paramGet
                         .GetGroup(activeWB)
                         .GetGroup(indexNumber)
                         .SetString("shortcut",
                                    item.text().upper().encode("UTF-8")))
                    else:
                        print "ShortCuts: " + activeWB + " database is full."
                elif activeWB and item.data(32):
                    deleteGroup(activeWB, item.data(32).encode("UTF-8"))
                else:
                    pass

                applyShortcuts()
                updateTable()
                updateStats()

            table.itemChanged.connect(onItemChanged)

            return table

        def updateTable():
            """
            Update table items.
            """
            items = itemList(cBox.currentText())

            table.blockSignals(True)
            table.setRowCount(len(items))

            row = 0

            for i in items:
                table.setItem(row, 0, i[0])
                table.setItem(row, 1, i[1])
                row += 1

            table.blockSignals(False)

        def updateStats():
            """
            Update statistic information for current number of shortcuts.
            """
            activeWB = cBox.currentText()

            if activeWB == "<none>":
                activeWB = "None"
            else:
                pass

            if activeWB == "Global shortcuts":
                stats.setText("<br>" +
                              "Global: " +
                              "<b>" + str(len(currentGlobal)) + "</b>")
            else:
                stats.setText(activeWB +
                              ": " +
                              "<b>" + str(len(currentLocal)) + "</b>" +
                              "<br>" +
                              "Global: " +
                              "<b>" + str(len(currentGlobal)) + "</b>")

        def setKey():
            """
            Save additional invoke key in the database.
            Set additional action shortcut.
            """
            text = editAdditional.text().upper()

            if text:
                text = text[-1:]
                paramGet.SetString("InvokeKey", text.encode("UTF-8"))
                key = paramGet.GetString("InvokeKey").decode("UTF-8")

                editAdditional.blockSignals(True)
                editAdditional.setText(key)
                editAdditional.blockSignals(False)
                setInvokeKey()
            else:
                additionalKey.setShortcut(None)

        def onModMenu(i):
            """
            Save modifier key in the database.
            Set additional action shortcut.
            """
            buttonMod.setText(i.text())

            if i.text() == "Disable":
                editAdditional.setEnabled(False)
                paramGet.SetBool("InvokeKey", 0)
                paramGet.RemString("ModifierKey")
            elif i.text() == "None":
                editAdditional.setEnabled(True)
                paramGet.SetBool("InvokeKey", 1)
                paramGet.RemString("ModifierKey")
            else:
                editAdditional.setEnabled(True)
                paramGet.SetBool("InvokeKey", 1)
                paramGet.SetString("ModifierKey",
                                   i.text().encode("UTF-8"))

            setInvokeKey()

        dialog = QtGui.QDialog(mw)
        dialog.resize(800, 450)
        dialog.setWindowTitle("ShortCuts")
        dialog.setObjectName("ShortCuts")

        cBox = comboBox()
        cBox.setParent(dialog)

        table = tableWidget()
        table.setParent(dialog)

        stats = QtGui.QLabel()
        stats.setAlignment(QtCore.Qt.AlignRight)

        home = QtGui.QWidget(dialog)
        layoutHome = QtGui.QVBoxLayout()
        home.setLayout(layoutHome)

        settings = QtGui.QWidget(dialog)
        layoutSettings = QtGui.QVBoxLayout()
        settings.setLayout(layoutSettings)

        stack = QtGui.QStackedWidget(dialog)
        stack.insertWidget(0, home)
        stack.insertWidget(1, settings)

        buttonClose = QtGui.QPushButton("Close", home)
        buttonSettings = QtGui.QPushButton("Settings", home)
        buttonDone = QtGui.QPushButton("Done", settings)

        labelDefault = QtGui.QLabel("Default:")

        editDefault = QtGui.QLineEdit()
        editDefault.setEnabled(False)
        editDefault.setMaximumWidth(70)
        editDefault.setAlignment(QtCore.Qt.AlignHCenter)

        labelAdditional = QtGui.QLabel("Additional:")

        editAdditional = InvokeEdit()
        editAdditional.setMaximumWidth(70)
        editAdditional.setAlignment(QtCore.Qt.AlignHCenter)
        editAdditional.textChanged.connect(setKey)

        buttonMod = QtGui.QPushButton()
        menuMod = QtGui.QMenu(buttonMod)
        buttonMod.setMenu(menuMod)

        actionDisable = QtGui.QAction("Disable", menuMod)
        actionNone = QtGui.QAction("None", menuMod)
        actionCtrl = QtGui.QAction("CTRL+", menuMod)
        actionShift = QtGui.QAction("SHIFT+", menuMod)
        actionAlt = QtGui.QAction("ALT+", menuMod)
        actionMeta = QtGui.QAction("META+", menuMod)

        menuMod.addAction(actionDisable)
        menuMod.addSeparator()
        menuMod.addAction(actionNone)
        menuMod.addAction(actionCtrl)
        menuMod.addAction(actionShift)
        menuMod.addAction(actionAlt)
        menuMod.addAction(actionMeta)
        menuMod.triggered.connect(onModMenu)

        layout = QtGui.QVBoxLayout()
        dialog.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(stack)

        layoutScope = QtGui.QHBoxLayout()
        layoutScope.addWidget(cBox)
        layoutScope.addStretch(1)
        layoutScope.addWidget(stats)

        layoutBottom = QtGui.QHBoxLayout()
        layoutBottom.addWidget(buttonSettings)
        layoutBottom.addStretch(1)
        layoutBottom.addWidget(buttonClose)

        layoutHome.insertLayout(0, layoutScope)
        layoutHome.addWidget(table)
        layoutHome.insertLayout(2, layoutBottom)

        layoutSettingsBottom = QtGui.QHBoxLayout()
        layoutSettingsBottom.addWidget(buttonDone)
        layoutSettingsBottom.addStretch(1)

        layoutDefault = QtGui.QHBoxLayout()
        layoutDefault.insertWidget(0, labelDefault)
        layoutDefault.addStretch(1)
        layoutDefault.insertWidget(2, editDefault)

        layoutAdditional = QtGui.QHBoxLayout()
        layoutAdditional.insertWidget(0, labelAdditional)
        layoutAdditional.addStretch(1)
        layoutAdditional.insertWidget(2, buttonMod)
        layoutAdditional.insertWidget(3, editAdditional)

        groupInvoke = QtGui.QGroupBox("Invoke key")

        layoutGroupInvoke = QtGui.QVBoxLayout()
        groupInvoke.setLayout(layoutGroupInvoke)

        layoutGroupInvoke.insertLayout(0, layoutDefault)
        layoutGroupInvoke.insertLayout(1, layoutAdditional)

        stretch = QtGui.QHBoxLayout()
        stretch.addStretch(1)

        layoutSettingsLeft = QtGui.QVBoxLayout()
        layoutSettingsLeft.addWidget(groupInvoke)

        layoutSettingsRight = QtGui.QVBoxLayout()
        layoutSettingsRight.insertLayout(0, stretch)

        layoutSettingsCombine = QtGui.QHBoxLayout()
        layoutSettingsCombine.insertLayout(0, layoutSettingsLeft)
        layoutSettingsCombine.insertLayout(1, layoutSettingsRight)

        layoutSettings.insertLayout(0, layoutSettingsCombine)
        layoutSettings.addStretch(1)
        layoutSettings.insertLayout(2, layoutSettingsBottom)

        def onAccepted():
            """
            Close dialog on button close.
            """
            dialog.done(1)

        buttonClose.clicked.connect(onAccepted)

        def onFinished():
            """
            Delete dialog on close.
            """
            dialog.deleteLater()

        dialog.finished.connect(onFinished)

        def onSettings():
            """
            Change to settings on button settings.
            """
            stack.setCurrentIndex(1)

        buttonSettings.clicked.connect(onSettings)

        def onDone():
            """
            Change to home on button done.
            """
            stack.setCurrentIndex(0)
            buttonClose.setFocus()

        buttonDone.clicked.connect(onDone)

        def prefDefaults():
            """
            Set preferences default values.
            """
            editDefault.setText(invokeKey.shortcut().toString())

            enable = paramGet.GetBool("InvokeKey")
            key = paramGet.GetString("InvokeKey").decode("UTF-8")
            modifier = paramGet.GetString("ModifierKey").decode("UTF-8")

            if enable and modifier:
                for i in menuMod.actions():
                    if i.text() == modifier:
                        i.trigger()
                    else:
                        pass
            elif enable:
                actionNone.trigger()
            else:
                actionDisable.trigger()

            editAdditional.setText(key)

            updateTable()
            updateStats()

        prefDefaults()

        return dialog


# Single instance
if mw.findChild(QtGui.QAction, "Std_ShortCuts"):
    pass
else:
    shortCuts()