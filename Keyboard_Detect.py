# Dynamic keyboard-layout detection for the ShortCuts keyboard view.
#
# Idea: physical key *positions* are layout-independent (identified by scancodes
# / XKB keycodes), while the *character* a position produces depends on the
# active OS keyboard layout. So we map each cell of the on-screen grid to a
# stable keycode once, then ask the OS what character that key currently emits.
#
# No compiled dependencies: everything goes through ctypes.
#   Linux (X11/Wayland): libxkbcommon
#   Windows:             user32 ToUnicodeEx / MapVirtualKeyEx   (scaffolded)
#   macOS:               Carbon UCKeyTranslate                  (scaffolded)
#
# detect_layout() returns a key_labels grid (same shape the widget draws) with
# the character-producing cells filled from the OS. Static cells (Esc, Tab,
# Shift, F-keys, Space, arrows, ...) are passed through unchanged.

import ctypes
import ctypes.util
import platform
import subprocess

# --- The on-screen grid template -------------------------------------------
# None marks a cell whose label is filled dynamically from the OS; a string is
# a fixed positional label that never depends on the keyboard layout.
GRID_TEMPLATE = [
    ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
    [None, None, None, None, None, None, None, None, None, None, None, None, None],
    ["Tab", None, None, None, None, None, None, None, None, None, None, None, None],
    ["ShiftLock", None, None, None, None, None, None, None, None, None, None, None, None],
    ["Shift", None, None, None, None, None, None, None, None, None, None, None, "Shift"],
    ["Ctrl", "Fn", "Win", "Alt", "Space", "Alt Gr", "WinC", "Ctrl", "LEFT", "UP", "DOWN", "RIGHT"],
]

# --- Linux: grid cell -> XKB keycode ---------------------------------------
# XKB keycode = Linux evdev keycode + 8. These positions are stable across
# layouts; only the emitted character changes.
#   (row_idx, col_idx): xkb_keycode
XKB_KEYCODES = {
    # number row
    (1, 0): 49,  # grave / ^
    (1, 1): 10, (1, 2): 11, (1, 3): 12, (1, 4): 13, (1, 5): 14, (1, 6): 15,
    (1, 7): 16, (1, 8): 17, (1, 9): 18, (1, 10): 19,
    (1, 11): 20,  # minus / ß
    (1, 12): 21,  # equal / ´
    # QWERTY/QWERTZ row
    (2, 1): 24, (2, 2): 25, (2, 3): 26, (2, 4): 27, (2, 5): 28, (2, 6): 29,
    (2, 7): 30, (2, 8): 31, (2, 9): 32, (2, 10): 33,
    (2, 11): 34,  # [ / Ü
    (2, 12): 35,  # ] / *
    # home row
    (3, 1): 38, (3, 2): 39, (3, 3): 40, (3, 4): 41, (3, 5): 42, (3, 6): 43,
    (3, 7): 44, (3, 8): 45, (3, 9): 46,
    (3, 10): 47,  # ; / Ö
    (3, 11): 48,  # ' / Ä
    (3, 12): 51,  # backslash / # '
    # bottom letter row
    (4, 1): 94,  # ISO extra key (<>|) - absent on ANSI
    (4, 2): 52, (4, 3): 53, (4, 4): 54, (4, 5): 55, (4, 6): 56, (4, 7): 57,
    (4, 8): 58,
    (4, 9): 59,   # comma
    (4, 10): 60,  # period
    (4, 11): 61,  # slash / -
}

# (4,1): the ISO extra key (<>|). Best-effort form hint only: the XKB keymap
# assigns this keycode a symbol based on the *layout*, not the physical board,
# so some ANSI layouts (e.g. "us") still report a symbol here. Treat
# physical_form as a hint; the manual override is the reliable escape hatch.
ISO_EXTRA_KEYCODE = 94

# Dead-key keysym names -> the glyph we want to show on the cap.
_DEAD_KEY_GLYPHS = {
    "dead_circumflex": "^",
    "dead_grave": "`",
    "dead_acute": "´",
    "dead_tilde": "~",
    "dead_diaeresis": "¨",
    "dead_macron": "¯",
    "dead_cedilla": "¸",
    "dead_caron": "ˇ",
    "dead_breve": "˘",
    "dead_abovering": "°",
    "dead_doubleacute": "˝",
    "dead_ogonek": "˛",
}


class _XkbRuleNames(ctypes.Structure):
    _fields_ = [
        ("rules", ctypes.c_char_p),
        ("model", ctypes.c_char_p),
        ("layout", ctypes.c_char_p),
        ("variant", ctypes.c_char_p),
        ("options", ctypes.c_char_p),
    ]


def _query_rmlvo():
    """Active layout as RMLVO (rules/model/layout/variant/options) via setxkbmap.

    Returns a dict (possibly partial). Empty on failure -> xkbcommon then falls
    back to its build defaults.
    """
    rmlvo = {}
    try:
        out = subprocess.run(
            ["setxkbmap", "-query"],
            capture_output=True, text=True, timeout=3,
        ).stdout
        for line in out.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                rmlvo[key.strip()] = val.strip()
    except Exception:
        pass
    return rmlvo


def _load_xkbcommon():
    name = ctypes.util.find_library("xkbcommon") or "libxkbcommon.so.0"
    lib = ctypes.CDLL(name)

    lib.xkb_context_new.restype = ctypes.c_void_p
    lib.xkb_context_new.argtypes = [ctypes.c_int]

    lib.xkb_keymap_new_from_names.restype = ctypes.c_void_p
    lib.xkb_keymap_new_from_names.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(_XkbRuleNames), ctypes.c_int,
    ]

    lib.xkb_state_new.restype = ctypes.c_void_p
    lib.xkb_state_new.argtypes = [ctypes.c_void_p]

    lib.xkb_state_key_get_utf8.restype = ctypes.c_int
    lib.xkb_state_key_get_utf8.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t,
    ]

    lib.xkb_state_key_get_one_sym.restype = ctypes.c_uint32
    lib.xkb_state_key_get_one_sym.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

    lib.xkb_keysym_get_name.restype = ctypes.c_int
    lib.xkb_keysym_get_name.argtypes = [
        ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t,
    ]

    # cleanup
    lib.xkb_state_unref.argtypes = [ctypes.c_void_p]
    lib.xkb_keymap_unref.argtypes = [ctypes.c_void_p]
    lib.xkb_context_unref.argtypes = [ctypes.c_void_p]
    return lib


def _keysym_name(lib, state, keycode):
    sym = lib.xkb_state_key_get_one_sym(state, keycode)
    if not sym:
        return ""
    buf = ctypes.create_string_buffer(64)
    n = lib.xkb_keysym_get_name(sym, buf, len(buf))
    if n <= 0:
        return ""
    return buf.value.decode("utf-8", "replace")


def _label_for_keycode(lib, state, keycode):
    """The glyph a key currently emits, formatted for a key cap."""
    buf = ctypes.create_string_buffer(16)
    n = lib.xkb_state_key_get_utf8(state, keycode, buf, len(buf))
    text = buf.value.decode("utf-8", "replace") if n > 0 else ""

    if text and text.isprintable() and text.strip():
        # Letters shown uppercase; symbols/digits as-is. Guard against caps that
        # expand to several chars (e.g. "ß".upper() == "SS") - keep those as-is.
        if len(text) == 1 and text.isalpha():
            upper = text.upper()
            return upper if len(upper) == 1 else text
        return text

    # Dead keys and non-printables emit no UTF-8 -> use the keysym name.
    name = _keysym_name(lib, state, keycode)
    if name in _DEAD_KEY_GLYPHS:
        return _DEAD_KEY_GLYPHS[name]
    if name and name != "NoSymbol":
        # last resort: show a short readable token
        return name[:4]
    return ""


def _detect_linux(force_layout=None, force_variant=None):
    """Return (labels_by_cell, meta) using libxkbcommon. Raises on failure.

    force_layout/force_variant override the active layout, so the view can be
    generated for any installed XKB layout regardless of what is active (for
    remote sessions or exotic hardware where detection picked the wrong one).
    """
    rmlvo = _query_rmlvo()
    if force_layout is not None:
        rmlvo["layout"] = force_layout
        rmlvo["variant"] = force_variant or ""
    lib = _load_xkbcommon()

    ctx = lib.xkb_context_new(0)
    if not ctx:
        raise RuntimeError("xkb_context_new failed")

    def _c(val):
        return val.encode("utf-8") if val else None

    names = _XkbRuleNames(
        rules=_c(rmlvo.get("rules")),
        model=_c(rmlvo.get("model")),
        layout=_c(rmlvo.get("layout")),
        variant=_c(rmlvo.get("variant")),
        options=_c(rmlvo.get("options")),
    )
    keymap = lib.xkb_keymap_new_from_names(ctx, ctypes.byref(names), 0)
    if not keymap:
        lib.xkb_context_unref(ctx)
        raise RuntimeError("xkb_keymap_new_from_names failed")
    state = lib.xkb_state_new(keymap)
    if not state:
        lib.xkb_keymap_unref(keymap)
        lib.xkb_context_unref(ctx)
        raise RuntimeError("xkb_state_new failed")

    labels = {}
    for cell, keycode in XKB_KEYCODES.items():
        labels[cell] = _label_for_keycode(lib, state, keycode)

    iso = bool(labels.get((4, 1), ""))

    lib.xkb_state_unref(state)
    lib.xkb_keymap_unref(keymap)
    lib.xkb_context_unref(ctx)

    meta = {
        "platform": "linux",
        "layout": rmlvo.get("layout", "?"),
        "variant": rmlvo.get("variant", ""),
        "physical_form": "ISO" if iso else "ANSI",
        "forced": force_layout is not None,
    }
    return labels, meta


def _detect_windows(force_layout=None, force_variant=None):
    """Scaffold: ToUnicodeEx(MapVirtualKeyEx(scancode, MAPVK_VSC_TO_VK, hkl)).

    TODO: full implementation. XKB_KEYCODES would be replaced by a
    scancode->cell table; VK_OEM_102 governs ISO vs ANSI. Forcing a specific
    layout would load the matching HKL.
    """
    raise NotImplementedError("Windows detection not yet implemented")


def _detect_macos(force_layout=None, force_variant=None):
    """Scaffold: UCKeyTranslate() with TISCopyCurrentKeyboardInputSource().

    TODO: full implementation via Carbon/HIToolbox through ctypes.
    """
    raise NotImplementedError("macOS detection not yet implemented")


def detect_labels_by_cell(force_layout=None, force_variant=None):
    """OS-detected labels keyed by (row, col). Raises on unsupported/failure."""
    system = platform.system()
    if system == "Linux":
        return _detect_linux(force_layout, force_variant)
    if system == "Windows":
        return _detect_windows(force_layout, force_variant)
    if system == "Darwin":
        return _detect_macos(force_layout, force_variant)
    raise RuntimeError("unsupported platform: %s" % system)


def detect_layout(manual_override=None, layout=None, variant=None):
    """Return (key_labels, meta).

    key_labels is a list-of-lists in the same shape the widget draws. Dynamic
    cells are filled from the OS; static cells come from GRID_TEMPLATE. On any
    failure the German QWERTZ fallback is returned and meta['source'] says so.

    layout/variant: force a specific XKB layout instead of the active one (the
    manual-selection path). manual_override: optional dict {(row, col): "label"}
    to force individual caps.
    """
    try:
        labels_by_cell, meta = detect_labels_by_cell(layout, variant)
        meta["source"] = "manual" if layout is not None else "os"
    except Exception as exc:
        labels_by_cell = dict(_FALLBACK_LABELS)
        meta = {"source": "fallback", "error": str(exc),
                "physical_form": "ISO", "layout": "de"}

    if manual_override:
        labels_by_cell.update(manual_override)

    grid = []
    for r, row in enumerate(GRID_TEMPLATE):
        out_row = []
        for c, cell in enumerate(row):
            if cell is None:
                out_row.append(labels_by_cell.get((r, c), "") or "?")
            else:
                out_row.append(cell)
        grid.append(out_row)
    return grid, meta


# German QWERTZ fallback (matches the previously hard-coded labels).
_FALLBACK_LABELS = {
    (1, 0): "^", (1, 1): "1", (1, 2): "2", (1, 3): "3", (1, 4): "4",
    (1, 5): "5", (1, 6): "6", (1, 7): "7", (1, 8): "8", (1, 9): "9",
    (1, 10): "0", (1, 11): "ß", (1, 12): "´",
    (2, 1): "Q", (2, 2): "W", (2, 3): "E", (2, 4): "R", (2, 5): "T",
    (2, 6): "Z", (2, 7): "U", (2, 8): "I", (2, 9): "O", (2, 10): "P",
    (2, 11): "Ü", (2, 12): "*",
    (3, 1): "A", (3, 2): "S", (3, 3): "D", (3, 4): "F", (3, 5): "G",
    (3, 6): "H", (3, 7): "J", (3, 8): "K", (3, 9): "L", (3, 10): "Ö",
    (3, 11): "Ä", (3, 12): "'",
    (4, 1): "<", (4, 2): "Y", (4, 3): "X", (4, 4): "C", (4, 5): "V",
    (4, 6): "B", (4, 7): "N", (4, 8): "M", (4, 9): ",", (4, 10): ".",
    (4, 11): "-",
}


# Curated common layouts for the manual dropdown (code, variant, display name).
COMMON_LAYOUTS = [
    ("us", "", "US (QWERTY)"),
    ("de", "", "German (QWERTZ)"),
    ("at", "", "Austrian"),
    ("ch", "", "Swiss"),
    ("gb", "", "UK"),
    ("fr", "", "French (AZERTY)"),
    ("es", "", "Spanish"),
    ("it", "", "Italian"),
    ("us", "dvorak", "US Dvorak"),
    ("us", "colemak", "US Colemak"),
]


def available_layouts():
    """Layout choices for the manual dropdown.

    Returns a list of dicts {"layout", "variant", "name"}. The first entry is
    the automatic one (layout None). Then the layouts actually configured on the
    system (from setxkbmap), then the curated common set, de-duplicated.
    """
    choices = [{"layout": None, "variant": "", "name": "Automatic (detected)"}]
    seen = set()

    rmlvo = _query_rmlvo() if platform.system() == "Linux" else {}
    sys_layouts = [x for x in rmlvo.get("layout", "").split(",") if x]
    sys_variants = rmlvo.get("variant", "").split(",")
    for i, code in enumerate(sys_layouts):
        variant = sys_variants[i] if i < len(sys_variants) else ""
        key = (code, variant)
        if key in seen:
            continue
        seen.add(key)
        name = code if not variant else "%s (%s)" % (code, variant)
        choices.append({"layout": code, "variant": variant,
                        "name": "System: " + name})

    for code, variant, name in COMMON_LAYOUTS:
        key = (code, variant)
        if key in seen:
            continue
        seen.add(key)
        choices.append({"layout": code, "variant": variant, "name": name})

    return choices


if __name__ == "__main__":
    grid, meta = detect_layout()
    print("meta:", meta)
    for row in grid:
        print(" ".join("%-4s" % c for c in row))
