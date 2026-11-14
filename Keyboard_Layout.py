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

        controls = QtWidgets.QHBoxLayout()
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

        # Board: keys are positioned absolutely on this container.
        self.board = QtWidgets.QWidget()
        # min-width/height: 0 so a theme's min-width (FreeCAD sets one) can't
        # override setFixedSize and make keys overlap; padding/margin 0 and a
        # small font keep short caps centered and readable.
        self._base_key_css = (
            "QPushButton { min-width: 0px; min-height: 0px;"
            " padding: 0px; margin: 0px; font-size: 8pt; }"
        )
        self.board.setStyleSheet(self._base_key_css)
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

    def set_capture_handler(self, handler):
        """Register a callback(shortcut_string | None) for captured combos."""
        self.capture_handler = handler

    def set_capture_progress(self, callback):
        """Register a callback(partial_string) shown while a sequence records."""
        self.capture_progress = callback

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
            bw = int(round(key["w"] * CELL - GAP))
            bh = int(round(key["h"] * CELL - GAP))
            button.setFixedSize(bw, bh)
            button.move(int(round(key["x"] * CELL)), int(round(key["y"] * CELL)))

            self._style_key(button, ref, label, bw, bh, mode, targets, focus_entry)
            button.show()

            max_x = max(max_x, key["x"] + key["w"])
            max_y = max(max_y, key["y"] + key["h"])

        self._add_legend()

        self.board.setFixedSize(
            int(round(max_x * CELL - GAP)),
            int(round(max_y * CELL - GAP)),
        )
        self.reset_button.setEnabled(mode != "overview")

        # Switching shape changes the board width (e.g. numpad adds a block), so
        # let the dialog follow: adjustSize() gives the right width, but it also
        # shrinks the height to the keyboard's - so restore the previous height
        # and the neighbouring lists keep their size.
        self.updateGeometry()
        window = self.window()
        if window is not None and window is not self:
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

    def _style_key(self, button, ref, label, bw, bh, mode, targets, _fe):
        rec = self.model["by_key"].get(ref) if self.model else None
        mod_family = _MOD_LABELS.get(label)
        is_prefix = bool(rec and rec["prefix"])

        # Make triggers clickable in every mode.
        if mod_family:
            button.clicked.connect(lambda _=False, f=mod_family: self._toggle_mod(f))
        elif is_prefix:
            button.clicked.connect(lambda _=False, r=ref: self._toggle_prefix(r))

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
            icon = entry.get("icon")
            if icon is not None and not icon.isNull():
                button.setText("")
                button.setIcon(icon)
                button.setIconSize(QtCore.QSize(16, 16))
            button.setToolTip(entry.get("text", ""))
            return

        # Dim the non-participating keys.
        button.setStyleSheet(
            "QPushButton{color:#9a9a9a;border:0.5px solid #c8c8c8;"
            "background:transparent;min-width:0;min-height:0;padding:0;"
            "font-size:8pt;}")

    def _mods_color(self):
        for family in Shortcut_Model.FAMILY_ORDER:
            if family in self.active_mods:
                return Shortcut_Model.FAMILY_COLORS[family]
        return Shortcut_Model.FAMILY_COLORS["ctrl"]

    def _fill(self, button, color, text="white"):
        button.setStyleSheet(
            "QPushButton{background:%s;color:%s;border:0.5px solid %s;"
            "min-width:0;min-height:0;padding:0;font-size:8pt;}"
            % (color, text, color))

    def _frame(self, button, color):
        button.setStyleSheet(
            "QPushButton{border:2px solid %s;background:transparent;"
            "min-width:0;min-height:0;padding:0;font-size:8pt;}" % color)

    def _add_legend(self):
        """A key-shaped legend in the free space above the navigation cluster:
        a sample key (real key look, big "A") spanning the full cluster width,
        with the four family colours in its corners and the family names in
        matching colours above and below - so the corner scheme reads at a
        glance (top-left Shift / top-right direct / bottom-left Ctrl /
        bottom-right Alt)."""
        kx = Keyboard_Templates.NAV_X * CELL
        kw = int(round(Keyboard_Templates.NAV_W * CELL - GAP))
        kh = kw                       # square key
        base_y = int(round(Keyboard_Templates.Y_FUNC * CELL))
        lh = 16                       # label row height
        key_y = base_y + lh + 1

        # The sample key - a plain QPushButton keeps the theme's key background.
        # The board stylesheet pins QPushButton font-size to 8pt, so the big cap
        # must come from the button's own stylesheet; scale it to the key so it
        # stays proportional to the small keys (~1/3 of the key height).
        key = QtWidgets.QPushButton("A", self.board)
        small_key_h = CELL - GAP
        font_pt = max(8, int(round(8.0 * kh / small_key_h)))
        key.setStyleSheet(
            "QPushButton{font-size:%dpt;padding:0;min-width:0;min-height:0;}"
            % font_pt)
        key.setFocusPolicy(QtCore.Qt.NoFocus)
        key.setFixedSize(kw, kh)
        key.move(int(round(kx)), key_y)
        fld = 15
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
                "QLabel{color:%s;font-size:8pt;background:transparent;}"
                % Shortcut_Model.FAMILY_COLORS[family])
            lbl.setFixedSize(lw, lh)
            lbl.move(lx, ly)
            lbl.show()

    def _add_pip(self, button, corner, bw, bh, color):
        pip = QtWidgets.QFrame(button)
        pip.setStyleSheet("background:%s;border-radius:2px;" % color)
        pip.setFixedSize(_PIP, _PIP)
        x = 2 if corner in ("tl", "bl") else bw - _PIP - 2
        y = 2 if corner in ("tl", "tr") else bh - _PIP - 2
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
