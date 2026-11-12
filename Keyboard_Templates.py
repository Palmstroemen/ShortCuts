# Physical keyboard templates for the ShortCuts keyboard view.
#
# A template is a flat list of keys positioned in "key units" (1 unit = one
# standard key cell), each with x, y, width and height. This is the model
# keyboard-layout editors use; it expresses the real differences between
# physical forms - the tall ISO Enter, the extra ISO <>| key, a wide space bar,
# the arrow cluster - that cannot be derived reliably from software (see
# Keyboard_Detect). The character keys carry an XKB key *name* ("id"); the
# renderer fills their caps from the detected layout. Static keys carry a fixed
# "label".
#
# To tailor a shape to specific hardware, copy a template and adjust its keys.

# Row baselines (y, in units).
Y_FUNC = 0.0
Y_NUM = 1.25
Y_QWERTY = 2.25
Y_HOME = 3.25
Y_BOTTOM = 4.25
Y_MOD = 5.25

FUNC_H = 0.8  # function keys are a little shorter


def C(x, y, key_id, w=1.0, h=1.0):
    """A character key; its cap is filled from the detected layout by key_id."""
    return {"x": x, "y": y, "w": w, "h": h, "id": key_id}


def S(x, y, label, w=1.0, h=1.0):
    """A static key with a fixed positional label."""
    return {"x": x, "y": y, "w": w, "h": h, "label": label}


def _function_row():
    keys = [S(0, Y_FUNC, "Esc", h=FUNC_H)]
    # F1-F4, F5-F8, F9-F12 in three groups.
    xs = [1.5, 2.5, 3.5, 4.5, 6.0, 7.0, 8.0, 9.0, 10.5, 11.5, 12.5, 13.5]
    for i, x in enumerate(xs):
        keys.append(S(x, Y_FUNC, "F%d" % (i + 1), h=FUNC_H))
    return keys


def _number_row():
    keys = [C(0, Y_NUM, "TLDE")]
    for i in range(12):
        keys.append(C(1 + i, Y_NUM, "AE%02d" % (i + 1)))
    keys.append(S(13, Y_NUM, "⌫", w=2.0))  # Backspace
    return keys


def _modifier_row():
    # Generic PC bottom row: wide space between the modifier keys.
    return [
        S(0.00, Y_MOD, "Ctrl", w=1.25),
        S(1.25, Y_MOD, "Win", w=1.25),
        S(2.50, Y_MOD, "Alt", w=1.25),
        S(3.75, Y_MOD, "Space", w=6.25),
        S(10.00, Y_MOD, "AltGr", w=1.25),
        S(11.25, Y_MOD, "Win", w=1.25),
        S(12.50, Y_MOD, "Menu", w=1.25),
        S(13.75, Y_MOD, "Ctrl", w=1.25),
    ]


def _nav_cluster():
    # Arrows as the usual inverted T, with Page Up/Down stacked beside them.
    x0 = 15.5
    return [
        S(x0, Y_MOD, "←", h=1.0),             # Left
        S(x0 + 1, Y_MOD, "↑", h=0.5),         # Up
        S(x0 + 1, Y_MOD + 0.5, "↓", h=0.5),   # Down
        S(x0 + 2, Y_MOD, "→", h=1.0),         # Right
        S(x0 + 3, Y_MOD, "⇞", h=0.5),         # Page Up
        S(x0 + 3, Y_MOD + 0.5, "⇟", h=0.5),   # Page Down
    ]


def _ansi_keys():
    keys = _function_row() + _number_row()
    # QWERTY row: Tab, 12 keys, backslash.
    keys.append(S(0, Y_QWERTY, "Tab", w=1.5))
    for i in range(12):
        keys.append(C(1.5 + i, Y_QWERTY, "AD%02d" % (i + 1)))
    keys.append(C(13.5, Y_QWERTY, "BKSL", w=1.5))
    # Home row: Caps, 11 keys, wide Enter.
    keys.append(S(0, Y_HOME, "Caps", w=1.75))
    for i in range(11):
        keys.append(C(1.75 + i, Y_HOME, "AC%02d" % (i + 1)))
    keys.append(S(12.75, Y_HOME, "Enter", w=2.25))
    # Bottom row: wide left Shift, 10 keys, wide right Shift (no ISO <> key).
    keys.append(S(0, Y_BOTTOM, "Shift", w=2.25))
    for i in range(10):
        keys.append(C(2.25 + i, Y_BOTTOM, "AB%02d" % (i + 1)))
    keys.append(S(12.25, Y_BOTTOM, "Shift", w=2.75))
    return keys + _modifier_row() + _nav_cluster()


def _iso_keys():
    keys = _function_row() + _number_row()
    # QWERTY row: Tab, 12 keys, then the tall Enter (spans this row and home).
    keys.append(S(0, Y_QWERTY, "Tab", w=1.5))
    for i in range(12):
        keys.append(C(1.5 + i, Y_QWERTY, "AD%02d" % (i + 1)))
    keys.append(S(13.5, Y_QWERTY, "Enter", w=1.5, h=2.0))
    # Home row: Caps (wider than Tab, so the row sits slightly right of QWERTY -
    # the usual keyboard stagger), 11 keys + the extra BKSL (# key, a touch
    # narrow so the row still meets the Enter); Enter already placed.
    keys.append(S(0, Y_HOME, "Caps", w=1.75))
    for i in range(11):
        keys.append(C(1.75 + i, Y_HOME, "AC%02d" % (i + 1)))
    keys.append(C(12.75, Y_HOME, "BKSL", w=0.75))
    # Bottom row: short left Shift, the ISO <> key, 10 keys, wide right Shift.
    keys.append(S(0, Y_BOTTOM, "Shift", w=1.25))
    keys.append(C(1.25, Y_BOTTOM, "LSGT"))
    for i in range(10):
        keys.append(C(2.25 + i, Y_BOTTOM, "AB%02d" % (i + 1)))
    keys.append(S(12.25, Y_BOTTOM, "Shift", w=2.75))
    return keys + _modifier_row() + _nav_cluster()


TEMPLATES = {
    "ansi": {"name": "ANSI (US-style)", "keys": _ansi_keys()},
    "iso": {"name": "ISO (EU-style)", "keys": _iso_keys()},
}


def template_choices():
    """Choices for the shape dropdown: Automatic first, then the templates."""
    choices = [{"id": None, "name": "Automatic (detected)"}]
    for key, tmpl in TEMPLATES.items():
        choices.append({"id": key, "name": tmpl["name"]})
    return choices


def default_template(meta):
    """Pick a template id from detection metadata (ISO vs ANSI best-effort)."""
    return "ansi" if meta.get("physical_form") == "ANSI" else "iso"
