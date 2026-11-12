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

# Horizontal placement of the clusters to the right of the main block (units).
# Equal gaps on both sides keep the arrow cluster visually separate from the
# keyboard and the numpad.
MAIN_RIGHT = 15.0          # right edge of the main block
CLUSTER_GAP = 0.75
NAV_X = MAIN_RIGHT + CLUSTER_GAP
NAV_W = 3
NAV_H = 0.67               # arrow keys ~2/3 of a normal key (room above them)
NUMPAD_X = NAV_X + NAV_W + CLUSTER_GAP


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
    # Compact 3x2 block of half-height keys: Page Up / Up / Page Down over
    # Left / Down / Right.
    x0 = NAV_X
    bottom = Y_MOD + 1.0 - NAV_H       # keep the cluster's foot on the mod row
    top = bottom - NAV_H
    return [
        S(x0, top, "⇞", h=NAV_H),          # Page Up
        S(x0 + 1, top, "↑", h=NAV_H),      # Up
        S(x0 + 2, top, "⇟", h=NAV_H),      # Page Down
        S(x0, bottom, "←", h=NAV_H),       # Left
        S(x0 + 1, bottom, "↓", h=NAV_H),   # Down
        S(x0 + 2, bottom, "→", h=NAV_H),   # Right
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


def _numpad():
    """Standard 17-key numeric keypad, placed right of the navigation cluster.

    All keys are static: the keypad emits the same digits/operators regardless
    of the character layout.
    """
    nx = NUMPAD_X
    return [
        S(nx, Y_NUM, "Num"), S(nx + 1, Y_NUM, "/"),
        S(nx + 2, Y_NUM, "*"), S(nx + 3, Y_NUM, "-"),
        S(nx, Y_QWERTY, "7"), S(nx + 1, Y_QWERTY, "8"),
        S(nx + 2, Y_QWERTY, "9"), S(nx + 3, Y_QWERTY, "+", h=2.0),
        S(nx, Y_HOME, "4"), S(nx + 1, Y_HOME, "5"), S(nx + 2, Y_HOME, "6"),
        S(nx, Y_BOTTOM, "1"), S(nx + 1, Y_BOTTOM, "2"),
        S(nx + 2, Y_BOTTOM, "3"), S(nx + 3, Y_BOTTOM, "Enter", h=2.0),
        S(nx, Y_MOD, "0", w=2.0), S(nx + 2, Y_MOD, "."),
    ]


TEMPLATES = {
    "ansi": {"name": "ANSI (US-style)", "keys": _ansi_keys()},
    "ansi_full": {"name": "ANSI + numpad", "keys": _ansi_keys() + _numpad()},
    "iso": {"name": "ISO (EU-style)", "keys": _iso_keys()},
    "iso_full": {"name": "ISO + numpad", "keys": _iso_keys() + _numpad()},
}


def template_choices():
    """Choices for the shape dropdown: Automatic first, then the templates."""
    choices = [{"id": None, "name": "Automatic (detected)"}]
    for key, tmpl in TEMPLATES.items():
        choices.append({"id": key, "name": tmpl["name"]})
    return choices


def default_template(meta):
    """Pick a template id from detection metadata (ISO vs ANSI best-effort).

    Defaults to the tenkeyless form; the numpad variants are opt-in since the
    presence of a keypad can't be detected.
    """
    return "ansi" if meta.get("physical_form") == "ANSI" else "iso"
