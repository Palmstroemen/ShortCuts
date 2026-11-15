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
__listFilter__ = "shortcuts"  # right-list filter: all / shortcuts / empty


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
    itemAll = QtGui.QListWidgetItem(icon, "All workbenches", wbSelector)
    itemAll.setData(QtCore.Qt.UserRole, "AllWorkbenches")
    wbSelector.addItem(itemAll)
    item = QtGui.QListWidgetItem(icon, "Global shortcuts", wbSelector)
    item.setData(QtCore.Qt.UserRole, "GlobalShortcuts")
    wbSelector.addItem(item)
    for i in listWBSorted:
        if i == "NoneWorkbench" or listWB[i].MenuText == "<none>":
            continue
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
        """Show or hide commands on search (matches the name and the shortcut)."""
        t = text.lower()
        for n in range(table.count()):
            it = table.item(n)
            hay = (it.text() + " " + (it.data(SC_ROLE) or "")).lower()
            it.setHidden(bool(text) and t not in hay)

    search.textEdited.connect(onSearch)
    return search


# Same format the keyboard's drop target listens for (Keyboard_Layout).
MIME_COMMAND = "application/x-shortcuts-command"


class _CommandDragger(QtCore.QObject):
    """Starts a drag carrying a command name when a table row is dragged out.

    Left-press records the row's command; once the pointer moves past the drag
    threshold a QDrag with that command is started, to be dropped on a key.
    """

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self._name = None
        self._press = None

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QtCore.QEvent.MouseButtonPress \
                and event.button() == QtCore.Qt.LeftButton:
            try:
                pt = event.position().toPoint()
            except AttributeError:
                pt = event.pos()
            item = self.table.itemAt(pt)
            self._name = item.data(QtCore.Qt.UserRole) if item else None
            self._press = pt
        elif et == QtCore.QEvent.MouseMove and self._name \
                and (event.buttons() & QtCore.Qt.LeftButton):
            try:
                pt = event.position().toPoint()
            except AttributeError:
                pt = event.pos()
            if (pt - self._press).manhattanLength() \
                    >= QtWidgets.QApplication.startDragDistance():
                name = self._name
                self._name = None
                drag = QtGui.QDrag(self.table)
                mime = QtCore.QMimeData()
                mime.setData(MIME_COMMAND,
                             QtCore.QByteArray(name.encode("utf-8")))
                drag.setMimeData(mime)
                drag.exec(QtCore.Qt.CopyAction)
                return True
        elif et == QtCore.QEvent.MouseButtonRelease:
            self._name = None
        return False


def enableTableDrag(table):
    """Let a command be dragged out of the table onto a keyboard key."""
    dragger = _CommandDragger(table)
    table._dragger = dragger  # keep a reference alive
    table.viewport().installEventFilter(dragger)


# Role on a list item holding its shortcut, pre-rendered as bracketed tokens for
# the delegate to paint in its own aligned column.
SC_ROLE = QtCore.Qt.UserRole + 1
_MOD_TOKENS = ("Ctrl", "Shift", "Alt", "Meta")


def bracketShortcut(text):
    """Render a Qt shortcut string as bracketed tokens for display:
    'Ctrl+S' -> '[Ctrl] + [S]', a sequence 'G, S' -> '[G], [S]'. A literal '+'
    key survives (its leading modifiers are consumed first, like parse_chord)."""
    if not text:
        return ""
    chords = []
    for chord in text.split(", "):
        parts = chord.split("+")
        tokens = []
        i = 0
        while i < len(parts) - 1 and parts[i] in _MOD_TOKENS:
            tokens.append(parts[i])
            i += 1
        tokens.append("+".join(parts[i:]))
        chords.append(" + ".join("[%s]" % t for t in tokens))
    return ", ".join(chords)


class _CommandDelegate(QtWidgets.QStyledItemDelegate):
    """Paints a row as a fixed-width shortcut column, then the command icon and
    name, so the shortcuts line up in a column of their own."""

    SC_W = 150   # width of the shortcut column (px)

    def paint(self, painter, option, index):
        # Let the style draw the row background and selection, but not the text
        # or icon - we place those ourselves.
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        name = opt.text
        opt.text = ""
        opt.icon = QtGui.QIcon()
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        rect = option.rect
        pad = 4
        left = int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        right = int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        painter.save()

        # A faint divider on the right edge separates the wrapped columns.
        painter.setPen(QtGui.QColor(128, 128, 128, 90))
        painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())

        if option.state & QtWidgets.QStyle.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        # Shortcut right-aligned in its column, so it sits next to the icon/name
        # instead of leaving a wide gap before it.
        sc = index.data(SC_ROLE) or ""
        painter.drawText(QtCore.QRect(rect.left() + pad, rect.top(),
                                      self.SC_W, rect.height()), right, sc)
        x = rect.left() + pad + self.SC_W + pad

        icon = index.data(QtCore.Qt.DecorationRole)
        if icon is not None and not icon.isNull():
            isz = 18
            iy = rect.top() + (rect.height() - isz) // 2
            icon.paint(painter, QtCore.QRect(x, iy, isz, isz))
            x += isz + pad

        name_rect = QtCore.QRect(x, rect.top(), rect.right() - x - pad, rect.height())
        elided = opt.fontMetrics.elidedText(
            name, QtCore.Qt.ElideRight, name_rect.width())
        painter.drawText(name_rect, left, elided)
        painter.restore()


def tableWidget():
    """List of commands, laid out in columns that flow top-to-bottom and wrap to
    the right, so it fills the wide area under the keyboard and scrolls sideways
    when it overflows. Each item shows the command icon, its name and (if any)
    its shortcut; the command name is stored in Qt.UserRole for arming and drag.
    """
    lst = QtGui.QListWidget()
    lst.setFlow(QtGui.QListView.TopToBottom)
    lst.setWrapping(True)
    lst.setResizeMode(QtGui.QListView.Adjust)
    lst.setMovement(QtGui.QListView.Static)
    lst.setGridSize(QtCore.QSize(360, 28))
    lst.setIconSize(QtCore.QSize(20, 20))
    lst.setUniformItemSizes(True)
    lst.setItemDelegate(_CommandDelegate(lst))
    lst.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
    lst.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
    lst.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    lst.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    lst.setMinimumHeight(140)
    return lst

def workbenchCommands(workbench):
    """Command names belonging to a workbench, or None for no filter.

    Returns the set of command object names the workbench puts on its toolbars,
    so the table and keyboard can show only that workbench's own functions. None
    means "do not filter" - used for the "All workbenches" and "Global
    shortcuts" entries and whenever the set can't be determined.
    """
    if not workbench or workbench in ("AllWorkbenches", "GlobalShortcuts"):
        return None
    try:
        wb = Gui.getWorkbench(workbench)
    except Exception:
        return None
    names = set()
    getItems = getattr(wb, "getToolbarItems", None)
    if callable(getItems):
        try:
            for cmds in getItems().values():
                for c in cmds:
                    if c and c != "Separator":
                        names.add(c)
        except Exception:
            pass
    return names or None


def updateTable(wbSelector, table, keyboard=None):
    """Update table widget items."""
    #workbench = wbSelector.itemData(wbSelector.currentIndex())
    wb = wbSelector.selectedItems()
    wb = wb[0]
    workbench = wb.data(QtCore.Qt.UserRole)

    update(workbench)

    # What this left-hand selection shows: a specific workbench's own commands
    # ("wb"), only the global Std_ ones ("global"), or everything ("all").
    if workbench == "GlobalShortcuts":
        mode, allowed = "global", None
    elif workbench in (None, "", "AllWorkbenches"):
        mode, allowed = "all", None
    else:
        allowed = workbenchCommands(workbench)
        mode = "wb" if allowed is not None else "all"

    def _is_global(name):
        return name.startswith("Std_")

    def _in_list(name):
        if mode == "global":
            return _is_global(name)
        if mode == "wb":
            return (not _is_global(name)) and name in allowed
        return True  # all

    # build shortcuts list
    actionList = []
    row = 0
    for i in actions:
        if not _in_list(i):
            continue
        text = actions[i].text()
        text = text.replace("&", "")
        shortcut = actions[i].shortcut().toString()
        if shortcut:
            row += 1
        actionList.append([text, actions[i].objectName(), shortcut])
    App.tableNames = actionList

    # Push the active workbench's shortcuts to the keyboard overlay.
    if keyboard is not None:
        kb_entries = []
        for i in actions:
            sc = actions[i].shortcut().toString()
            if not sc:
                continue
            is_global = _is_global(i)
            # A specific workbench gets its own commands plus every global one
            # (globals always apply, so they are always shown - greyed). The
            # global view shows only globals; the all view shows everything.
            if mode == "wb" and not is_global and i not in allowed:
                continue
            if mode == "global" and not is_global:
                continue
            ic = actions[i].icon()
            kb_entries.append({
                "text": actions[i].text().replace("&", ""),
                "shortcut": sc,
                "icon": ic if (ic and not ic.isNull()) else None,
                "global": is_global,
                "command": actions[i].objectName(),
            })
        keyboard.set_shortcuts(kb_entries, dim_global=(mode == "wb"))

    # Commands that lost their shortcut to another command this session.
    marked = getattr(table, "_marked", None) or set()

    # Which rows the list-filter buttons show: all, only those with a shortcut,
    # or only the empty ones (so a shortcut can be assigned to them). A command
    # that just lost its shortcut stays visible in the "shortcuts" view so the
    # user can spot it and reassign one.
    if __listFilter__ == "shortcuts":
        display = [a for a in actionList if a[2] or a[1] in marked]
        display.sort(key=lambda x: (not (x[1] in marked and not x[2]), x[2]))
    elif __listFilter__ == "empty":
        display = [a for a in actionList if not a[2]]
        display.sort(key=lambda x: x[0].lower())
    else:  # all
        display = sorted(actionList, key=lambda x: x[0].lower())

    tint = QtGui.QColor(239, 159, 39, 60)  # soft amber, session hint
    hint = "Shortcut was reassigned to another command - set a new one."
    table.blockSignals(True)
    table.clear()
    for entry in display:
        name = entry[1]
        cur = actions[name].shortcut().toString()

        item = QtGui.QListWidgetItem()
        item.setText(entry[0])                             # command name (display)
        item.setData(QtCore.Qt.UserRole, name)             # objectName, arm/drag
        item.setData(SC_ROLE, bracketShortcut(cur))        # painted shortcut column
        item.setToolTip(actions[name].toolTip())
        ic = actions[name].icon()
        item.setIcon(ic if (ic and not ic.isNull())
                     else QtGui.QIcon(":/icons/freecad"))

        if name in marked:
            if not cur:
                item.setData(SC_ROLE, "(reassign)")
            item.setBackground(tint)
            item.setToolTip(hint)

        table.addItem(item)
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
    dia.resize(1200, 820)
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

    # btnPrint / btnClose are placed in the right column's header row (see Layout).

    # wbSelector
    wbSelector = wbSelectorWidget()
    wbSelector.setWindowTitle("select workbench")
    wbSelector.setFixedWidth(200)

    # Table widget
    table = tableWidget()
    # Commands that lost their shortcut to another command this session; the list
    # highlights them as "reassign" until the window is closed (then this resets).
    table._marked = set()

    # Search
    search = searchLine(table)

    # Keyboard view (created early so the selection handlers can feed it).
    keyboard = kb.KeyboardLayout()

    # Functions and connections
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
        updateTable(wbSelector, table, keyboard)

    wbSelector.itemSelectionChanged.connect(onCurrentWBchanged)

    updateTable(wbSelector, table, keyboard)

    # Right-list filter buttons: all commands, only those with a shortcut, or
    # only the empty ones (to assign a shortcut to them).
    def setListFilter(filt):
        global __listFilter__
        __listFilter__ = filt
        updateTable(wbSelector, table, keyboard)

    btnAll = QtGui.QPushButton("All")
    btnAll.setToolTip("Show all commands")
    btnAll.clicked.connect(lambda: setListFilter("all"))
    btnShortcuts = QtGui.QPushButton("Shortcuts")
    btnShortcuts.setToolTip("Show only commands that have a shortcut")
    btnShortcuts.clicked.connect(lambda: setListFilter("shortcuts"))
    btnEmpty = QtGui.QPushButton("Empty")
    btnEmpty.setToolTip("Show only commands without a shortcut")
    btnEmpty.clicked.connect(lambda: setListFilter("empty"))
    # btnAll / btnShortcuts / btnEmpty are placed in the controls row (see Layout).

    # --- shortcut assignment via the real keyboard ------------------------
    # Select a command in the list, then press a key combination: it is checked
    # against this workbench and the globals, and on a clash the user chooses
    # which command keeps it.
    armed = {"command": None}

    assignLabel = QtGui.QLabel("Select a command, then press a key combination.")
    assignLabel.setWordWrap(True)
    assignButtons = QtGui.QWidget()
    assignBtnLayout = QtGui.QHBoxLayout(assignButtons)
    assignBtnLayout.setContentsMargins(0, 0, 0, 0)

    def clearAssignButtons():
        while assignBtnLayout.count():
            it = assignBtnLayout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def commandText(name):
        return actions[name].text().replace("&", "") if name in actions else name

    def normalize(text):
        verify.setShortcut(QtGui.QKeySequence(text))
        norm = verify.shortcut().toString()
        verify.setShortcut(QtGui.QKeySequence(""))
        return norm

    def targetWorkbench():
        sel = wbSelector.selectedItems()
        wbname = sel[0].data(QtCore.Qt.UserRole) if sel else None
        if wbname in (None, "", "AllWorkbenches"):
            return "GlobalShortcuts"
        return wbname

    def scopeNames():
        """Commands a new shortcut could clash with: this workbench + globals."""
        sel = wbSelector.selectedItems()
        wbname = sel[0].data(QtCore.Qt.UserRole) if sel else None
        names = set(actions.keys())
        if wbname == "GlobalShortcuts":
            return {n for n in names if n.startswith("Std_")}
        if wbname in (None, "", "AllWorkbenches"):
            return names
        cmds = workbenchCommands(wbname) or set()
        return {n for n in names if n.startswith("Std_")} | (cmds & names)

    def applyAssignments(cmdmap):
        wbname = targetWorkbench()
        database("User", wbname, commands=cmdmap)
        update(wbname)
        updateTable(wbSelector, table, keyboard)

    def disarm():
        armed["command"] = None
        keyboard.set_armed(False)
        clearAssignButtons()
        assignLabel.setText("Select a command, then press a key combination.")
        # Drop the row selection so clicking the SAME command again re-arms it
        # (an unchanged selection would emit no signal). Block signals so this
        # does not re-enter onTableSelection.
        table.blockSignals(True)
        table.clearSelection()
        table.blockSignals(False)

    def commandIcon(name):
        ic = actions[name].icon() if name in actions else None
        return ic if (ic and not ic.isNull()) else None

    def onTableSelection():
        items = table.selectedItems()
        if not items:
            disarm()
            return
        name = items[0].data(QtCore.Qt.UserRole)
        if not name:
            return
        armed["command"] = name
        keyboard.set_armed(True)
        clearAssignButtons()
        assignLabel.setText(
            "Press a key combination for '%s' (Esc to cancel)." % commandText(name))
        current = actions[name].shortcut().toString() if name in actions else ""
        if current:
            btnClear = QtGui.QPushButton("Clear %s" % current)
            ic = commandIcon(name)
            if ic:
                btnClear.setIcon(ic)

            def doClear(_=False, cmd=name):
                applyAssignments({cmd: ""})
                armed["command"] = None
                keyboard.set_armed(False)
                clearAssignButtons()
                assignLabel.setText(
                    "Cleared the shortcut for '%s'." % commandText(cmd))

            btnClear.clicked.connect(doClear)
            assignBtnLayout.addWidget(btnClear)

    def assignShortcut(command, seq_str):
        """Core assignment: assign seq_str to command, asking on a conflict.

        Shared by key-combination capture and drag&drop. command must be a real
        command; seq_str a Qt key-sequence string.
        """
        norm = normalize(seq_str)
        if not norm:
            return
        holders = [n for n in scopeNames()
                   if n != command
                   and normalize(actions[n].shortcut().toString()) == norm]
        if not holders:
            table._marked.discard(command)
            applyAssignments({command: norm})
            armed["command"] = None
            keyboard.set_armed(False)
            clearAssignButtons()
            assignLabel.setText("Assigned %s to '%s'." % (norm, commandText(command)))
            return
        holder = holders[0]
        assignLabel.setText(
            "%s is already used by '%s'. Keep it there, or move it to '%s'?"
            % (norm, commandText(holder), commandText(command)))
        clearAssignButtons()
        btnMove = QtGui.QPushButton("Assign to '%s'" % commandText(command))
        btnKeep = QtGui.QPushButton("Keep on '%s'" % commandText(holder))
        icMove = commandIcon(command)
        if icMove:
            btnMove.setIcon(icMove)
        icKeep = commandIcon(holder)
        if icKeep:
            btnKeep.setIcon(icKeep)

        def doMove():
            table._marked.add(holder)
            table._marked.discard(command)
            applyAssignments({holder: "", command: norm})
            armed["command"] = None
            keyboard.set_armed(False)
            clearAssignButtons()
            assignLabel.setText(
                "Moved %s to '%s'. '%s' now has no shortcut - reassign it if needed."
                % (norm, commandText(command), commandText(holder)))

        btnMove.clicked.connect(doMove)
        btnKeep.clicked.connect(disarm)
        # Keep (leave as-is) left, Assign (confirm) right - like Cancel / OK.
        assignBtnLayout.addWidget(btnKeep)
        assignBtnLayout.addWidget(btnMove)

    def onCapture(seq_str):
        command = armed["command"]
        if command is None:
            return
        if seq_str is None:            # Esc cancelled
            disarm()
            return
        assignShortcut(command, seq_str)

    def onDrop(command, seq_str):
        if command in actions:
            assignShortcut(command, seq_str)

    def onCaptureProgress(partial):
        if armed["command"] is None:
            return
        assignLabel.setText(
            "Recording %s ... (pause to finish, Esc to cancel)" % partial)

    keyboard.set_capture_handler(onCapture)
    keyboard.set_capture_progress(onCaptureProgress)
    keyboard.set_drop_handler(onDrop)
    table.itemSelectionChanged.connect(onTableSelection)
    enableTableDrag(table)

    # Layout: a narrow workbench column on the left; one wide column on the right
    # holding the keyboard with the function list stacked underneath it. Print and
    # Close sit top-right, in line with the keyboard's own Layout/Shape controls.
    keyboard.add_header_widget(btnPrint)
    keyboard.add_header_widget(btnClose)

    # Static filters + find on the left; the assignment / conflict buttons appear
    # on the right only while a command is armed.
    loControls = QtGui.QHBoxLayout()
    loControls.addWidget(btnAll)
    loControls.addWidget(btnShortcuts)
    loControls.addWidget(btnEmpty)
    loControls.addSpacing(10)
    loControls.addWidget(QtGui.QLabel("find"))
    # A search only needs a few letters: cap the width so the field yields the
    # rest of the row to the stretch, and shrinks first when space runs out.
    search.setMaximumWidth(220)
    loControls.addWidget(search)
    loControls.addStretch()
    loControls.addWidget(assignButtons)

    loRight = QtGui.QVBoxLayout()
    loRight.addWidget(keyboard)
    loRight.addWidget(assignLabel)
    loRight.addLayout(loControls)
    loRight.addWidget(table)

    loTop = QtGui.QHBoxLayout()
    loTop.addWidget(wbSelector)
    loTop.addLayout(loRight)

    layout.insertLayout(0, loTop)

    # Size the keyboard once to fill the width a maximised dialog gives it: the
    # widest shape (with numpad) reaches the right edge, narrower shapes leave
    # space free on the right. Fixed afterwards - the dialog opens maximised and
    # is not meant to be resized during use.
    screen = mw.screen() if hasattr(mw, "screen") else None
    if screen is None:
        screen = QtWidgets.QApplication.primaryScreen()
    if screen is not None:
        # 200 px left column + room for margins, spacing and a scrollbar.
        keyboard.fit_to_width(screen.availableGeometry().width() - 280)

    btnClose.setDefault(True)
    btnClose.setFocus()

    return dia


def onPreferences():
    """Open the preferences dialog."""
    dia = preferences()
    dia.showMaximized()


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
