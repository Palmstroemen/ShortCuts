# Show a nice keyboard layout, labelled from the active OS keyboard layout, and
# overlay a workbench's shortcuts on it.
#
# Two dropdowns pick the character layout (de/at/fr/...) and the physical shape
# (ANSI/ISO); see Keyboard_Detect and Keyboard_Templates.
#
# Shortcut overlay (see Shortcut_Model):
#   Overview  - every key that carries a shortcut gets corner pips, one per
#               modifier family (fixed corners: top-left none, top-right Ctrl,
#               bottom-left Shift, bottom-right Alt), plus a dot if it starts a
#               key sequence.
#   Focus     - click a modifier key (Ctrl/Shift/Alt) to show only the shortcuts
#               reachable with exactly those modifiers, each key wearing its
#               command icon. Click a sequence-prefix key to show all its
#               continuations. "Overview" resets.

from qt_compat import QtWidgets, QtGui, QtCore

import Keyboard_Detect
import Keyboard_Templates
import Shortcut_Model

# Geometry: a key cell is KEYSIZE plus a GAP; keys are placed in key units.
# Kept compact so a full keyboard - with a numeric keypad later - still fits.
KEYSIZE = 26
GAP = 3
CELL = KEYSIZE + GAP

# Overview corner for each modifier family. Arranged to echo the physical
# modifier positions (Shift above Ctrl on the left, Alt on the right), which
# reads more intuitively: Shift top-left, direct top-right, Ctrl bottom-left,
# Alt bottom-right.
_CORNER = {"shift": "tl", "plain": "tr", "ctrl": "bl", "alt": "br"}
_PIP = 7

# Static key labels that act as modifier toggles, mapped to their family.
_MOD_LABELS = {"Ctrl": "ctrl", "Shift": "shift", "Alt": "alt"}

# Modifier family -> Qt key-sequence token, in canonical order.
_FAMILY_TOKEN = [("ctrl", "Ctrl"), ("shift", "Shift"),
                 ("alt", "Alt"), ("meta", "Meta")]

# Drag payload: a command name dragged from the shortcut list onto a key.
MIME_COMMAND = "application/x-shortcuts-command"


class _DropBoard(QtWidgets.QWidget):
    """The key container, able to receive a command dragged onto a key."""

    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.setAcceptDrops(True)

    def _ok(self, event):
        return (self._owner.drop_handler is not None
                and event.mimeData().hasFormat(MIME_COMMAND))

    def dragEnterEvent(self, event):
        if self._ok(event):
            self._owner._hover_mod = None   # fresh drag: first hover toggles
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._ok(event):
            try:
                pos = event.position().toPoint()
            except AttributeError:
                pos = event.pos()
            self._owner._drag_hover(pos)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self._ok(event):
            event.ignore()
            return
        raw = bytes(event.mimeData().data(MIME_COMMAND))
        command = raw.decode("utf-8", "replace")
        try:
            pos = event.position().toPoint()   # Qt6
        except AttributeError:
            pos = event.pos()
        self._owner._handle_drop(command, pos)
        event.acceptProposedAction()


class _KeyDragger(QtCore.QObject):
    """Starts a drag carrying the command currently shown on a focused key."""

    def __init__(self, owner):
        super().__init__(owner)
        self._cmd = None
        self._press = None

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QtCore.QEvent.MouseButtonPress \
                and event.button() == QtCore.Qt.LeftButton:
            self._cmd = obj.property("kbcommand")
            try:
                self._press = event.position().toPoint()
            except AttributeError:
                self._press = event.pos()
        elif et == QtCore.QEvent.MouseMove and self._cmd \
                and (event.buttons() & QtCore.Qt.LeftButton):
            try:
                pt = event.position().toPoint()
            except AttributeError:
                pt = event.pos()
            if (pt - self._press).manhattanLength() \
                    >= QtWidgets.QApplication.startDragDistance():
                cmd = self._cmd
                self._cmd = None
                drag = QtGui.QDrag(obj)
                mime = QtCore.QMimeData()
                mime.setData(MIME_COMMAND, QtCore.QByteArray(cmd.encode("utf-8")))
                drag.setMimeData(mime)
                drag.exec(QtCore.Qt.CopyAction)
                return True
        elif et == QtCore.QEvent.MouseButtonRelease:
            self._cmd = None
        return False


class KeyboardLayout(QtWidgets.QWidget):
    def __init__(self, manual_override=None):
        super().__init__()

        self.manual_override = manual_override
        self.layout_meta = {}

        self.entries = []          # [{text, shortcut, icon, global}]
        self.dim_global = False    # grey out global shortcuts (specific-WB view)
        self.model = None
        self.active_mods = set()   # focused modifier families
        self.active_prefix = None  # focused sequence-prefix ref
        self.capture_armed = False # real keys record a combo instead of toggling
        self.capture_handler = None
        self.capture_progress = None  # optional callback(partial_string)
        self.drop_handler = None      # callback(command, seq_string) for drag&drop
        self._key_dragger = _KeyDragger(self)  # drags a command off a focused key
        self._hover_mod = None        # modifier key last hovered during a drag
        self.capture_chords = []      # chords collected for the current sequence
        # A plain (modifier-less) chord may start a key sequence ("G, S"), so we
        # wait briefly for a following chord before finalising; a modifier chord
        # (Ctrl+S) is unambiguous and finalises at once.
        self.capture_timer = QtCore.QTimer(self)
        self.capture_timer.setSingleShot(True)
        self.capture_timer.setInterval(500)
        self.capture_timer.timeout.connect(self._emit_capture)

        outer = QtWidgets.QVBoxLayout()
        self.setLayout(outer)

        # Character layout: "Automatic" plus the system and common layouts.
        self.layout_choices = Keyboard_Detect.available_layouts()
        self.layout_selector = QtWidgets.QComboBox()
        for choice in self.layout_choices:
            self.layout_selector.addItem(choice["name"])
        self.layout_selector.currentIndexChanged.connect(self._rebuild)

        # Physical shape: Automatic / ANSI / ISO.
        self.shape_choices = Keyboard_Templates.template_choices()
        self.shape_selector = QtWidgets.QComboBox()
        for choice in self.shape_choices:
            self.shape_selector.addItem(choice["name"])
        self.shape_selector.currentIndexChanged.connect(self._rebuild)

        # Reset the overlay back to the overview.
        self.reset_button = QtWidgets.QPushButton("Overview")
        self.reset_button.setToolTip("Clear the focus and show all shortcuts")
        self.reset_button.clicked.connect(self._reset_focus)

        self._controls = controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Layout:"))
        controls.addWidget(self.layout_selector)
        controls.addSpacing(10)
        controls.addWidget(QtWidgets.QLabel("Shape:"))
        controls.addWidget(self.shape_selector)
        controls.addSpacing(10)
        controls.addWidget(self.reset_button)
        controls.addStretch()
        outer.addLayout(controls)

        # Separate the controls from the keyboard so the combo boxes don't read
        # as part of it.
        outer.addSpacing(8)
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        outer.addWidget(separator)
        outer.addSpacing(8)

        # Board: keys are positioned absolutely on this container; it also
        # receives commands dragged from the shortcut list onto a key.
        self.board = _DropBoard(self)
        # Key geometry is instance state so fit_to_width() can scale the whole
        # board to the available width once, at open; fonts and icons scale with
        # the key size so larger keys stay legible.
        self.keysize = KEYSIZE
        self.cell = CELL
        self.font_pt = 8
        self.icon_px = 16
        # min-width/height: 0 so a theme's min-width (FreeCAD sets one) can't
        # override setFixedSize and make keys overlap; padding/margin 0 and a
        # small font keep short caps centered and readable.
        self.board.setStyleSheet(self._base_key_css())
        outer.addWidget(self.board)
        outer.addStretch()

        # Let the real Ctrl/Shift/Alt keys toggle the focus layers, as if their
        # on-screen key were clicked. An application-wide filter catches them
        # whatever holds focus inside the dialog; Qt drops it when we are
        # destroyed.
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._rebuild()

    # --- real keyboard: toggle layers, or capture a combo for assignment ---

    def eventFilter(self, obj, event):
        """React to physical key presses.

        Normally the Ctrl/Shift/Alt keys toggle the focus layers. When armed for
        capture (a command is selected for assignment), the next full key
        combination is reported to the capture handler instead, and Esc cancels.
        """
        if event.type() != QtCore.QEvent.KeyPress or event.isAutoRepeat():
            return False
        # Don't interfere with text entry (search box, shortcut cell editor).
        if isinstance(QtWidgets.QApplication.focusWidget(), QtWidgets.QLineEdit):
            return False

        key = event.key()
        bare_mods = (QtCore.Qt.Key_Control, QtCore.Qt.Key_Shift,
                     QtCore.Qt.Key_Alt, QtCore.Qt.Key_Meta, QtCore.Qt.Key_AltGr)

        if self.capture_armed and self.capture_handler is not None:
            if key in bare_mods:
                return False  # wait for the non-modifier key, keep modifiers held
            if key == QtCore.Qt.Key_Escape:
                self._reset_capture()
                self.capture_handler(None)
                return True
            chord = self._chord_string(event)
            mod_mask = (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
                        | QtCore.Qt.AltModifier | QtCore.Qt.MetaModifier)
            has_mod = bool(event.modifiers() & mod_mask)
            self.capture_chords.append(chord)
            # A lone modifier chord, or a full 4-chord sequence, is complete now.
            # A plain first/next chord might still grow, so wait out the timer.
            if (len(self.capture_chords) == 1 and has_mod) \
                    or len(self.capture_chords) >= 4:
                self._emit_capture()
            else:
                if self.capture_progress is not None:
                    self.capture_progress(", ".join(self.capture_chords))
                self.capture_timer.start()
            return True

        family = {QtCore.Qt.Key_Control: "ctrl", QtCore.Qt.Key_Shift: "shift",
                  QtCore.Qt.Key_Alt: "alt"}.get(key)
        if family is not None:
            self._toggle_mod(family)
        return False

    # --- public API --------------------------------------------------------

    def _chord_string(self, event):
        """The Qt key-sequence string for a single key event (one chord)."""
        try:
            seq = QtGui.QKeySequence(event.keyCombination())
        except Exception:
            try:
                seq = QtGui.QKeySequence(
                    int(event.modifiers()) | int(event.key()))
            except Exception:
                seq = QtGui.QKeySequence(
                    int(event.modifiers().value) | int(event.key()))
        return seq.toString()

    def _emit_capture(self):
        """Finalise the collected chords and report them to the handler."""
        self.capture_timer.stop()
        chords = self.capture_chords
        self.capture_chords = []
        if chords and self.capture_handler is not None:
            self.capture_handler(", ".join(chords))

    def _reset_capture(self):
        """Drop any half-recorded sequence (cancel or disarm)."""
        self.capture_timer.stop()
        self.capture_chords = []

    def add_header_widget(self, widget):
        """Place a widget at the right end of the top control row.

        The row ends with a stretch, so widgets added here sit right-aligned,
        in line with the Layout / Shape / Overview controls.
        """
        self._controls.addWidget(widget)

    def _base_key_css(self):
        return ("QPushButton { min-width: 0px; min-height: 0px;"
                " padding: 0px; margin: 0px; font-size: %dpt; }" % self.font_pt)

    def fit_to_width(self, avail_px):
        """Scale the key size once so the widest shape (the one with a numpad)
        fills avail_px, then redraw; fonts and icons scale with the keys.

        Meant to be called once, at open. The size then stays fixed - the dialog
        is maximised and not resized during use. Narrower shapes (no numpad) keep
        this key size and simply leave space free on the right.
        """
        units = 0.0
        for tmpl in Keyboard_Templates.TEMPLATES.values():
            for key in tmpl["keys"]:
                units = max(units, key["x"] + key["w"])
        if units <= 0 or avail_px <= 0:
            return
        cell = (avail_px + GAP) / units
        cell = max(float(CELL), min(cell, 72.0))  # never below the compact default
        self.cell = cell
        self.keysize = cell - GAP
        scale = cell / CELL
        self.font_pt = max(8, int(round(8 * scale)))
        self.icon_px = max(16, int(round(16 * scale)))
        self.board.setStyleSheet(self._base_key_css())
        self._rebuild()

    def set_capture_handler(self, handler):
        """Register a callback(shortcut_string | None) for captured combos."""
        self.capture_handler = handler

    def set_capture_progress(self, callback):
        """Register a callback(partial_string) shown while a sequence records."""
        self.capture_progress = callback

    def set_drop_handler(self, handler):
        """Register a callback(command, seq_string) for a command dropped on a key."""
        self.drop_handler = handler

    def _compose_seq(self, label):
        """Build a key-sequence string from the active modifier layer + a key cap."""
        tokens = [token for family, token in _FAMILY_TOKEN
                  if family in self.active_mods]
        tokens.append(label)
        return "+".join(tokens)

    def _handle_drop(self, command, pos):
        """A command was dropped at board position pos; assign it to that key."""
        if self.drop_handler is None:
            return
        btn = self.board.childAt(pos)
        while btn is not None and not btn.property("kbref"):
            btn = btn.parentWidget()
        if btn is None:
            return
        label = btn.property("kblabel")
        if not label or label in _MOD_LABELS:
            return  # dropping on a modifier key (or a non-key) does nothing yet
        self.drop_handler(command, self._compose_seq(label))

    def _drag_hover(self, pos):
        """While dragging, hovering an on-screen modifier key toggles that layer.

        Each time the pointer enters a modifier key its family flips in the drop
        set, so any combination (e.g. Ctrl+Alt) can be built by passing over the
        keys - without holding a physical modifier, which Qt would read as a
        copy/move drag gesture.
        """
        btn = self.board.childAt(pos)
        while btn is not None and not btn.property("kbref"):
            btn = btn.parentWidget()
        ref = btn.property("kbref") if btn is not None else None
        family = _MOD_LABELS.get(btn.property("kblabel")) if btn is not None else None
        here = ref if family is not None else None
        if here == self._hover_mod:
            return  # still on the same key (or still not on a modifier)
        self._hover_mod = here
        if family is None:
            return
        mods = set(self.active_mods)
        mods.discard(family) if family in mods else mods.add(family)
        self.active_mods = mods
        self.active_prefix = None
        self._refocus()

    def _refocus(self):
        """Re-style the existing keys for the current layer without rebuilding.

        Rebuilding deletes and recreates the buttons, which is unsafe while a
        drag (whose source may be one of those buttons) is in progress.
        """
        if not self.model:
            return
        mode, targets, focus_entry = self._focus_targets()
        for btn in self.board.findChildren(QtWidgets.QPushButton):
            ref = btn.property("kbref")
            if not ref:
                continue  # the legend's sample key
            label = btn.property("kblabel")
            for child in btn.findChildren(QtWidgets.QFrame):
                child.setParent(None)
                child.deleteLater()
            btn.setIcon(QtGui.QIcon())
            btn.setText(label)
            btn.setToolTip("")
            btn.setProperty("kbcommand", None)
            self._style_key(btn, ref, label, btn.width(), btn.height(),
                            mode, targets, focus_entry, connect=False)
        self.reset_button.setEnabled(mode != "overview")

    def set_armed(self, armed):
        """Arm/disarm real-keyboard capture (vs. the modifier-toggle mode)."""
        self.capture_armed = bool(armed)
        if not self.capture_armed:
            self._reset_capture()

    def set_shortcuts(self, entries, dim_global=False):
        """Supply the active workbench's shortcuts and redraw the overlay.

        entries: list of {"text", "shortcut", "icon"(QIcon or None), "global"}.
        dim_global: when True, entries flagged "global" are drawn greyed, to show
        the key is already taken by an always-active shortcut.
        """
        self.entries = list(entries or [])
        self.dim_global = dim_global
        self.active_prefix = None   # refs may have changed; keep modifier focus
        self._rebuild()

    # --- selection helpers -------------------------------------------------

    def _selected_layout(self):
        idx = self.layout_selector.currentIndex()
        if 0 <= idx < len(self.layout_choices):
            return self.layout_choices[idx]
        return {"layout": None, "variant": ""}

    def _selected_shape(self):
        idx = self.shape_selector.currentIndex()
        if 0 <= idx < len(self.shape_choices):
            return self.shape_choices[idx]["id"]
        return None

    def _reset_focus(self):
        self.active_mods = set()
        self.active_prefix = None
        self._rebuild()

    def _toggle_mod(self, family):
        if family in self.active_mods:
            self.active_mods.discard(family)
        else:
            self.active_mods.add(family)
        self.active_prefix = None
        self._rebuild()

    def _toggle_prefix(self, ref):
        self.active_prefix = None if self.active_prefix == ref else ref
        self.active_mods = set()
        self._rebuild()

    # --- rendering ---------------------------------------------------------

    def _rebuild(self, *args):
        """Detect labels for the chosen layout, draw the shape, overlay shortcuts."""
        layout = self._selected_layout()
        labels, self.layout_meta = Keyboard_Detect.detect_layout(
            manual_override=self.manual_override,
            layout=layout["layout"],
            variant=layout["variant"],
        )

        shape_id = self._selected_shape()
        if shape_id is None:
            shape_id = Keyboard_Templates.default_template(self.layout_meta)
        keys = Keyboard_Templates.TEMPLATES[shape_id]["keys"]

        self.model = Shortcut_Model.build(
            self.entries, labels, treat_global=self.dim_global)

        # Clear everything previously drawn (buttons and pips).
        for child in self.board.findChildren(QtWidgets.QWidget):
            child.setParent(None)
            child.deleteLater()

        # Work out the current focus mode and its target set.
        mode, targets, focus_entry = self._focus_targets()

        max_x = max_y = 0.0
        for key in keys:
            is_char = "id" in key
            ref = key["id"] if is_char else key["label"]
            label = labels.get(ref, "") or "?" if is_char else key["label"]

            button = QtWidgets.QPushButton(label, self.board)
            # setFixedSize (not setGeometry) so a theme's min-width/padding can't
            # enlarge the cap and eat the gaps.
            bw = int(round(key["w"] * self.cell - GAP))
            bh = int(round(key["h"] * self.cell - GAP))
            button.setFixedSize(bw, bh)
            button.move(int(round(key["x"] * self.cell)),
                        int(round(key["y"] * self.cell)))
            button.setProperty("kbref", ref)
            button.setProperty("kblabel", label)
            button.installEventFilter(self._key_dragger)

            self._style_key(button, ref, label, bw, bh, mode, targets, focus_entry)
            button.show()

            max_x = max(max_x, key["x"] + key["w"])
            max_y = max(max_y, key["y"] + key["h"])

        self._add_legend()

        self.board.setFixedSize(
            int(round(max_x * self.cell - GAP)),
            int(round(max_y * self.cell - GAP)),
        )
        self.reset_button.setEnabled(mode != "overview")

        # Switching shape changes the board width (e.g. numpad adds a block), so
        # let the dialog follow: adjustSize() gives the right width, but it also
        # shrinks the height to the keyboard's - so restore the previous height
        # and the neighbouring lists keep their size.
        self.updateGeometry()
        window = self.window()
        if (window is not None and window is not self
                and not window.isMaximized()):
            keep_height = window.height()
            window.adjustSize()
            window.resize(window.width(), keep_height)

    def _focus_targets(self):
        """Return (mode, {ref: (entry, is_global)}, None).

        mode is overview/mods/prefix. A workbench shortcut wins a cell over a
        global one so the key shows the workbench command, not the greyed global.
        """
        def place(targets, item):
            ref, is_global = item["ref"], item["global"]
            if ref not in targets or (targets[ref][1] and not is_global):
                targets[ref] = (item["entry"], is_global)

        if self.active_prefix is not None and self.model:
            bucket = self.model["prefixes"].get(self.active_prefix)
            targets = {}
            if bucket:
                for item in bucket["entries"]:
                    place(targets, item)
            return "prefix", targets, None
        if self.active_mods and self.model:
            items = self.model["by_modset"].get(frozenset(self.active_mods), [])
            targets = {}
            for item in items:
                place(targets, item)
            return "mods", targets, None
        return "overview", {}, None

    def _style_key(self, button, ref, label, bw, bh, mode, targets, _fe,
                   connect=True):
        rec = self.model["by_key"].get(ref) if self.model else None
        mod_family = _MOD_LABELS.get(label)
        is_prefix = bool(rec and rec["prefix"])

        # Make triggers clickable in every mode (only on first build - a restyle
        # reuses the button and must not stack a second connection).
        if connect:
            if mod_family:
                button.clicked.connect(
                    lambda _=False, f=mod_family: self._toggle_mod(f))
            elif is_prefix:
                button.clicked.connect(
                    lambda _=False, r=ref: self._toggle_prefix(r))

        # Modifier keys always wear their colour: a frame normally, a solid fill
        # while their layer is active - in every mode, so they read as the
        # coloured controls they are.
        if mod_family:
            color = Shortcut_Model.FAMILY_COLORS[mod_family]
            if mode == "mods" and mod_family in self.active_mods:
                self._fill(button, color)
            else:
                self._frame(button, color)
            return

        if mode == "overview":
            if rec:
                # Workbench shortcuts get their family colour; a family used only
                # by a global shortcut gets the grey "occupied" pip.
                grey = rec["families_global"] - rec["families"]
                for family in rec["families"]:
                    corner = _CORNER.get(family)
                    if corner:
                        self._add_pip(button, corner, bw, bh,
                                      Shortcut_Model.FAMILY_COLORS[family])
                for family in grey:
                    corner = _CORNER.get(family)
                    if corner:
                        self._add_pip(button, corner, bw, bh,
                                      Shortcut_Model.FAMILY_COLORS["global"])
                if is_prefix:
                    self._add_prefix_dot(button, bw, bh)
            return

        # Focus modes: highlight the active prefix and targets, dim the rest.
        if mode == "prefix" and is_prefix and ref == self.active_prefix:
            self._fill(button, Shortcut_Model.FAMILY_COLORS["seq"])
            return

        if ref in targets:
            entry, is_global = targets[ref]
            if is_global:
                self._fill(button, Shortcut_Model.FAMILY_COLORS["global"],
                           text="#555555")
            else:
                color = (Shortcut_Model.FAMILY_COLORS["seq"] if mode == "prefix"
                         else self._mods_color())
                self._fill(button, color)
                # This key holds a (non-global) shortcut in the focused layer,
                # so it can be dragged onto another key to move it.
                button.setProperty("kbcommand", entry.get("command"))
            icon = entry.get("icon")
            if icon is not None and not icon.isNull():
                button.setText("")
                button.setIcon(icon)
                button.setIconSize(QtCore.QSize(self.icon_px, self.icon_px))
            button.setToolTip(entry.get("text", ""))
            return

        # Dim the non-participating keys.
        button.setStyleSheet(
            "QPushButton{color:#9a9a9a;border:0.5px solid #c8c8c8;"
            "background:transparent;min-width:0;min-height:0;padding:0;"
            "font-size:%dpt;}" % self.font_pt)

    def _mods_color(self):
        for family in Shortcut_Model.FAMILY_ORDER:
            if family in self.active_mods:
                return Shortcut_Model.FAMILY_COLORS[family]
        return Shortcut_Model.FAMILY_COLORS["ctrl"]

    def _fill(self, button, color, text="white"):
        button.setStyleSheet(
            "QPushButton{background:%s;color:%s;border:0.5px solid %s;"
            "min-width:0;min-height:0;padding:0;font-size:%dpt;}"
            % (color, text, color, self.font_pt))

    def _frame(self, button, color):
        button.setStyleSheet(
            "QPushButton{border:2px solid %s;background:transparent;"
            "min-width:0;min-height:0;padding:0;font-size:%dpt;}"
            % (color, self.font_pt))

    def _add_legend(self):
        """A key-shaped legend in the free space above the navigation cluster:
        a sample key (real key look, big "A") spanning the full cluster width,
        with the four family colours in its corners and the family names in
        matching colours above and below - so the corner scheme reads at a
        glance (top-left Shift / top-right direct / bottom-left Ctrl /
        bottom-right Alt)."""
        scale = self.cell / CELL      # the legend grows with the keyboard
        kx = Keyboard_Templates.NAV_X * self.cell
        kw = int(round(Keyboard_Templates.NAV_W * self.cell - GAP))
        kh = kw                       # square key
        base_y = int(round(Keyboard_Templates.Y_FUNC * self.cell))
        lh = int(round(16 * scale))   # label row height
        key_y = base_y + lh + 1

        # The sample key - a plain QPushButton keeps the theme's key background.
        # The board stylesheet pins QPushButton font-size, so the big cap must
        # come from the button's own stylesheet; scale it to the key so it stays
        # proportional to the small keys (~1/3 of the key height).
        key = QtWidgets.QPushButton("A", self.board)
        small_key_h = self.cell - GAP
        font_pt = max(8, int(round(8.0 * kh / small_key_h)))
        key.setStyleSheet(
            "QPushButton{font-size:%dpt;padding:0;min-width:0;min-height:0;}"
            % font_pt)
        key.setFocusPolicy(QtCore.Qt.NoFocus)
        key.setFixedSize(kw, kh)
        key.move(int(round(kx)), key_y)
        fld = int(round(15 * scale))
        for family, corner in (("shift", "tl"), ("plain", "tr"),
                               ("ctrl", "bl"), ("alt", "br")):
            swatch = QtWidgets.QFrame(key)
            swatch.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            swatch.setStyleSheet(
                "background:%s;border-radius:2px;"
                % Shortcut_Model.FAMILY_COLORS[family])
            swatch.setFixedSize(fld, fld)
            sx = 3 if corner in ("tl", "bl") else kw - fld - 3
            sy = 3 if corner in ("tl", "tr") else kh - fld - 3
            swatch.move(sx, sy)
            swatch.show()
        key.show()

        # Family names outside the key: above the two top corners, below the two
        # bottom ones, each in its family colour.
        half = int(kw / 2)
        left = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        right = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        rows = [
            ("Shift", "shift", int(round(kx)), base_y, half, left),
            ("direct", "plain", int(round(kx)) + half, base_y, kw - half, right),
            ("Ctrl", "ctrl", int(round(kx)), key_y + kh + 1, half, left),
            ("Alt", "alt", int(round(kx)) + half, key_y + kh + 1, kw - half, right),
        ]
        for text, family, lx, ly, lw, align in rows:
            lbl = QtWidgets.QLabel(text, self.board)
            lbl.setAlignment(align)
            lbl.setStyleSheet(
                "QLabel{color:%s;font-size:%dpt;background:transparent;}"
                % (Shortcut_Model.FAMILY_COLORS[family],
                   max(8, int(round(8 * scale)))))
            lbl.setFixedSize(lw, lh)
            lbl.move(lx, ly)
            lbl.show()

    def _add_pip(self, button, corner, bw, bh, color):
        pip = QtWidgets.QFrame(button)
        pip.setStyleSheet("background:%s;border-radius:2px;" % color)
        size = max(_PIP, int(round(_PIP * self.cell / CELL)))
        pip.setFixedSize(size, size)
        x = 2 if corner in ("tl", "bl") else bw - size - 2
        y = 2 if corner in ("tl", "tr") else bh - size - 2
        pip.move(x, y)
        pip.show()

    def _add_prefix_dot(self, button, bw, bh):
        # A translucent purple tint laid over the cap marks a key that starts a
        # key sequence (e.g. G in G, S). Transparent to clicks so the key still
        # toggles its prefix layer.
        size = max(min(bw, bh) - 6, 12)
        ov = QtWidgets.QFrame(button)
        ov.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        ov.setStyleSheet("background:rgba(127,119,221,0.33);border-radius:4px;")
        ov.setFixedSize(size, size)
        ov.move(int((bw - size) / 2), int((bh - size) / 2))
        ov.show()
