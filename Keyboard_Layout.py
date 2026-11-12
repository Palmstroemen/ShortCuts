# Show a nice keyboard layout, labelled from the active OS keyboard layout.
#
# Two dropdowns: the character layout (de/at/fr/...) and the physical shape
# (ANSI/ISO). The shape can only be guessed from software, so it is selectable;
# see Keyboard_Detect and Keyboard_Templates.

from qt_compat import QtWidgets

import Keyboard_Detect
import Keyboard_Templates

# Geometry: a key cell is KEYSIZE plus a GAP; keys are placed in key units.
KEYSIZE = 38
GAP = 5
CELL = KEYSIZE + GAP


class KeyboardLayout(QtWidgets.QWidget):
    def __init__(self, manual_override=None):
        super().__init__()

        self.manual_override = manual_override
        self.layout_meta = {}

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

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Layout:"))
        controls.addWidget(self.layout_selector)
        controls.addSpacing(10)
        controls.addWidget(QtWidgets.QLabel("Shape:"))
        controls.addWidget(self.shape_selector)
        controls.addStretch()
        outer.addLayout(controls)

        # Board: keys are positioned absolutely on this container.
        self.board = QtWidgets.QWidget()
        outer.addWidget(self.board)
        outer.addStretch()

        self._rebuild()

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

    def _rebuild(self, *args):
        """Detect labels for the chosen layout and draw the chosen shape."""
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

        # Clear previously drawn keys.
        for button in self.board.findChildren(QtWidgets.QPushButton):
            button.setParent(None)
            button.deleteLater()

        max_x = max_y = 0.0
        for key in keys:
            label = key.get("label")
            if label is None:
                label = labels.get(key["id"], "") or "?"
            button = QtWidgets.QPushButton(label, self.board)
            button.setGeometry(
                int(round(key["x"] * CELL)),
                int(round(key["y"] * CELL)),
                int(round(key["w"] * CELL - GAP)),
                int(round(key["h"] * CELL - GAP)),
            )
            button.show()
            max_x = max(max_x, key["x"] + key["w"])
            max_y = max(max_y, key["y"] + key["h"])

        self.board.setFixedSize(
            int(round(max_x * CELL - GAP)),
            int(round(max_y * CELL - GAP)),
        )
