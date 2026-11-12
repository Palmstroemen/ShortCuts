# Qt binding shim for ShortCuts.
#
# FreeCAD 1.0 is built on PySide6 (Qt 6); earlier releases on PySide2 (Qt 5).
# Import QtWidgets/QtGui/QtCore from here instead of from a specific binding so
# the add-on runs on both, and so it stays testable standalone outside FreeCAD.
#
#     from qt_compat import QtWidgets, QtGui, QtCore
#
# Other modules can migrate to this import over time; nothing forces a one-shot
# port.

try:
    from PySide6 import QtWidgets, QtGui, QtCore  # noqa: F401
    QT_VERSION = 6
except ImportError:  # pragma: no cover - depends on the host's Qt binding
    from PySide2 import QtWidgets, QtGui, QtCore  # noqa: F401
    QT_VERSION = 5
