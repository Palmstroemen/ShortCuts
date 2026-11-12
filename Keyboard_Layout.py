# Show a nice keyboard layout, labelled from the active OS keyboard layout.
# A dropdown lets the user override the detected layout (for remote sessions,
# exotic hardware, or when several layouts are active).

from qt_compat import QtWidgets, QtCore
import Keyboard_Detect


class KeyboardLayout(QtWidgets.QWidget):
    def __init__(self, manual_override=None):
        super().__init__()

        self.key_1_size = [35, 30, 50, 70, 35, 40]
        self.manual_override = manual_override
        self.layout_meta = {}

        outer = QtWidgets.QVBoxLayout()
        self.setLayout(outer)
        self.setGeometry(100, 100, 800, 400)

        # Layout chooser: "Automatic" plus the system and common layouts.
        self.choices = Keyboard_Detect.available_layouts()
        self.selector = QtWidgets.QComboBox()
        for choice in self.choices:
            self.selector.addItem(choice["name"])
        self.selector.currentIndexChanged.connect(self._on_layout_changed)

        chooser_row = QtWidgets.QHBoxLayout()
        chooser_row.addWidget(QtWidgets.QLabel("Keyboard layout:"))
        chooser_row.addWidget(self.selector)
        chooser_row.addStretch()
        outer.insertLayout(0, chooser_row)

        # Container that holds the (rebuildable) key grid.
        self.key_rows = QtWidgets.QVBoxLayout()
        outer.insertLayout(1, self.key_rows)

        self._rebuild()

    def _selected_choice(self):
        idx = self.selector.currentIndex()
        if 0 <= idx < len(self.choices):
            return self.choices[idx]
        return {"layout": None, "variant": ""}

    def _on_layout_changed(self, _index):
        self._rebuild()

    def _rebuild(self):
        """Detect labels for the selected layout and redraw the key grid."""
        choice = self._selected_choice()
        key_labels, self.layout_meta = Keyboard_Detect.detect_layout(
            manual_override=self.manual_override,
            layout=choice["layout"],
            variant=choice["variant"],
        )

        _clear_layout(self.key_rows)

        # Create and layout keys, one row after another.
        for row_idx, row in enumerate(key_labels):
            row_layout = QtWidgets.QHBoxLayout()
            row_layout.setSpacing(5)
            row_layout.setAlignment(QtCore.Qt.AlignLeft)
            for col_idx, label in enumerate(row):
                key_button = QtWidgets.QPushButton(label, self)
                key_height = 30 if row_idx == 0 else 40
                if col_idx == 0:
                    key_button.setFixedSize(self.key_1_size[row_idx], key_height)
                else:
                    key_button.setFixedSize(40, key_height)
                row_layout.addWidget(key_button)
            self.key_rows.addLayout(row_layout)


def _clear_layout(layout):
    """Recursively remove and delete everything in a Qt layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)  # remove from display at once
            widget.deleteLater()
        child = item.layout()
        if child is not None:
            _clear_layout(child)
