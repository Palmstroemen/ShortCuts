# Show a nice keyboard layout, labelled from the active OS keyboard layout.

from qt_compat import QtWidgets, QtCore
import Keyboard_Detect


class KeyboardLayout(QtWidgets.QWidget):
    def __init__(self, manual_override=None):
        super().__init__()

        key_1_size = [35, 30, 50, 70, 35, 40]

        # Key labels detected from the OS keyboard layout (falls back to German
        # QWERTZ if detection is unavailable). manual_override forces specific
        # caps for remote sessions / exotic hardware; see Keyboard_Detect.
        key_labels, self.layout_meta = Keyboard_Detect.detect_layout(manual_override)

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        key_row = []
        layout.setSpacing(5)
        self.setGeometry(100, 100, 800, 400)

        # Create and layout keys
        key_all_rows = QtWidgets.QVBoxLayout()

        for row_idx, row in enumerate(key_labels):
            key_row.append(QtWidgets.QHBoxLayout())
            key_row[row_idx].setAlignment(QtCore.Qt.AlignLeft)  # Set the alignment to left
            # Creat one row after another
            for col_idx, label in enumerate(row):
                key_button = QtWidgets.QPushButton(label, self)
                if row_idx == 0: key_height = 30
                else:            key_height = 40
                if col_idx == 0: key_button.setFixedSize(key_1_size[row_idx], key_height)  # Set the size based on your preferences
                else:            key_button.setFixedSize(40, key_height)  # Set the size based on your preferences
                key_row[row_idx].addWidget(key_button)
            # and add it to all Rows
            key_all_rows.addLayout(key_row[row_idx])
        layout.insertLayout(0, key_all_rows)
