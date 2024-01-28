# Show a nice keyboar layout

from PySide2 import QtWidgets, QtGui, QtCore

class KeyboardLayout(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        key_1_size = [35, 30, 50, 70, 35, 40]

        # Define key labels for each row
        key_labels = [
            ["Esc","F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
            ["^", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "ß", "´"],
            ["Tab", "Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P", "Ü", "*"],
            ["ShiftLock", "A", "S", "D", "F", "G", "H", "J", "K", "L", "Ö", "Ä", "'"],
            ["Shift", "<", "Y", "X", "C", "V", "B", "N", "M", ",", ".", "-", "Shift"],
            ["Ctrl", "Fn", "Win", "Alt", "Space", "Alt Gr", "WinC", "Ctrl", "LEFT", "UP", "DOWN", "RIGHT"]
        ]

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        key_row = []
        layout.setSpacing(5)
        self.setGeometry(100,100,800,400)

        # Create and layout keys
        key_all_rows = QtWidgets.QVBoxLayout()

        for row_idx, row in enumerate(key_labels):
            key_row.append(QtWidgets.QHBoxLayout())
            key_row[row_idx].setAlignment(QtCore.Qt.AlignLeft)  # Set the alignment to left
            # Creat one row after another
            for col_idx, label in enumerate(row):
                key_button = QtWidgets.QPushButton(label,self)
                if row_idx == 0: key_height = 30
                else:            key_height = 40
                if col_idx == 0: key_button.setFixedSize(key_1_size[row_idx], key_height)  # Set the size based on your preferences
                else:            key_button.setFixedSize(40, key_height)  # Set the size based on your preferences
                key_row[row_idx].addWidget(key_button)
            # and add it to all Rows
            key_all_rows.addLayout(key_row[row_idx])
        layout.insertLayout(0, key_all_rows)
