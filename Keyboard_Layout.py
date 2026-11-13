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

# Overview corner for each modifier family.
_CORNER = {"plain": "tl", "ctrl": "tr", "shift": "bl", "alt": "br"}
_PIP = 7

# Static key labels that act as modifier toggles, mapped to their family.
_MOD_LABELS = {"Ctrl": "ctrl", "Shift": "shift", "Alt": "alt"}


class KeyboardLayout(QtWidgets.QWidget):
    def __init__(self, manual_override=None):
        super().__init__()

        self.manual_override = manual_override
        self.layout_meta = {}

        self.entries = []          # [{text, shortcut, icon}]
        self.model = None
        self.active_mods = set()   # focused modifier families
        self.active_prefix = None  # focused sequence-prefix ref

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

        self._rebuild()

    # --- public API --------------------------------------------------------

    def set_shortcuts(self, entries):
        """Supply the active workbench's shortcuts and redraw the overlay.

        entries: list of {"text", "shortcut", "icon"(QIcon or None)}.
        """
        self.entries = list(entries or [])
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

        self.model = Shortcut_Model.build(self.entries, labels)

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
        """Return (mode, {ref: entry}, None). mode is overview/mods/prefix."""
        if self.active_prefix is not None and self.model:
            bucket = self.model["prefixes"].get(self.active_prefix)
            targets = {}
            if bucket:
                for item in bucket["entries"]:
                    targets.setdefault(item["ref"], item["entry"])
            return "prefix", targets, None
        if self.active_mods and self.model:
            items = self.model["by_modset"].get(frozenset(self.active_mods), [])
            targets = {}
            for item in items:
                targets.setdefault(item["ref"], item["entry"])
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

        if mode == "overview":
            if rec:
                for family in rec["families"]:
                    corner = _CORNER.get(family)
                    if corner:
                        self._add_pip(button, corner, bw, bh,
                                      Shortcut_Model.FAMILY_COLORS[family])
                if is_prefix:
                    self._add_prefix_dot(button, bw)
            return

        # Focus modes: highlight triggers and targets, dim the rest.
        if mode == "mods" and mod_family in self.active_mods:
            self._fill(button, Shortcut_Model.FAMILY_COLORS[mod_family])
            return
        if mode == "prefix" and is_prefix and ref == self.active_prefix:
            self._fill(button, Shortcut_Model.FAMILY_COLORS["seq"])
            return

        if ref in targets:
            color = (Shortcut_Model.FAMILY_COLORS["seq"] if mode == "prefix"
                     else self._mods_color())
            self._fill(button, color)
            icon = targets[ref].get("icon")
            if icon is not None and not icon.isNull():
                button.setText("")
                button.setIcon(icon)
                button.setIconSize(QtCore.QSize(16, 16))
            button.setToolTip(targets[ref].get("text", ""))
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

    def _fill(self, button, color):
        button.setStyleSheet(
            "QPushButton{background:%s;color:white;border:0.5px solid %s;"
            "min-width:0;min-height:0;padding:0;font-size:8pt;}" % (color, color))

    def _add_pip(self, button, corner, bw, bh, color):
        pip = QtWidgets.QFrame(button)
        pip.setStyleSheet("background:%s;border-radius:2px;" % color)
        pip.setFixedSize(_PIP, _PIP)
        x = 2 if corner in ("tl", "bl") else bw - _PIP - 2
        y = 2 if corner in ("tl", "tr") else bh - _PIP - 2
        pip.move(x, y)
        pip.show()

    def _add_prefix_dot(self, button, bw):
        dot = QtWidgets.QFrame(button)
        dot.setStyleSheet(
            "background:transparent;border:1.5px solid %s;border-radius:5px;"
            % Shortcut_Model.FAMILY_COLORS["seq"])
        dot.setFixedSize(9, 9)
        dot.move(int(bw / 2 - 4), 2)
        dot.show()
