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
# detect_layout() returns a dict of labels keyed by XKB key name (AD01 = the
# "Q" position, etc.); the physical templates reference those names, so the
# character caps follow the active layout regardless of the drawn shape.

import ctypes
import ctypes.util
import os
import platform
import subprocess

# --- Linux: XKB key name -> XKB keycode ------------------------------------
# XKB keycode = Linux evdev keycode + 8. These positions are stable across
# layouts; only the emitted character changes. The names are the standard XKB
# ones (AEnn = number row, ADnn = QWERTY row, ACnn = home row, ABnn = bottom
# row, TLDE = grave, BKSL = backslash, LSGT = the ISO <>| key).
KEYCODES = {
    "TLDE": 49,
    "AE01": 10, "AE02": 11, "AE03": 12, "AE04": 13, "AE05": 14, "AE06": 15,
    "AE07": 16, "AE08": 17, "AE09": 18, "AE10": 19, "AE11": 20, "AE12": 21,
    "AD01": 24, "AD02": 25, "AD03": 26, "AD04": 27, "AD05": 28, "AD06": 29,
    "AD07": 30, "AD08": 31, "AD09": 32, "AD10": 33, "AD11": 34, "AD12": 35,
    "AC01": 38, "AC02": 39, "AC03": 40, "AC04": 41, "AC05": 42, "AC06": 43,
    "AC07": 44, "AC08": 45, "AC09": 46, "AC10": 47, "AC11": 48, "BKSL": 51,
    "LSGT": 94,
    "AB01": 52, "AB02": 53, "AB03": 54, "AB04": 55, "AB05": 56, "AB06": 57,
    "AB07": 58, "AB08": 59, "AB09": 60, "AB10": 61,
}

# LSGT is the ISO extra key (<>|). Best-effort form hint only: the XKB keymap
# assigns it a symbol based on the *layout*, not the physical board, so some
# ANSI layouts (e.g. "us") still report a symbol here. Treat physical_form as a
# hint; the shape dropdown is the reliable escape hatch.
ISO_EXTRA_KEY = "LSGT"

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


def _ensure_xkb_config_root():
    """Point libxkbcommon at the system XKB data if its default path is invalid.

    A bundled libxkbcommon - e.g. the one inside a FreeCAD AppImage - can carry
    a compiled-in XKB data path from its build host that does not exist on the
    user's machine, which makes xkb_context_new fail and detection silently fall
    back. If XKB_CONFIG_ROOT is unset or points nowhere, aim it at the system
    data directory. libxkbcommon reads this env var at context creation.
    """
    root = os.environ.get("XKB_CONFIG_ROOT")
    if root and os.path.isdir(root):
        return
    for candidate in ("/usr/share/X11/xkb", "/usr/local/share/X11/xkb",
                      "/etc/X11/xkb", "/usr/X11R6/lib/X11/xkb"):
        if os.path.isdir(candidate):
            os.environ["XKB_CONFIG_ROOT"] = candidate
            return


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
    _ensure_xkb_config_root()
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
    for name, keycode in KEYCODES.items():
        labels[name] = _label_for_keycode(lib, state, keycode)

    iso = bool(labels.get(ISO_EXTRA_KEY, ""))

    lib.xkb_state_unref(state)
    lib.xkb_keymap_unref(keymap)
    lib.xkb_context_unref(ctx)

    # A broken/empty keymap yields no glyphs at all; prefer the fallback over a
    # keyboard full of blanks.
    if not any(labels.get(name) for name in KEYCODES):
        raise RuntimeError("xkb produced no key labels (empty keymap)")

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

    TODO: full implementation. KEYCODES would be replaced by a
    name->scancode table; VK_OEM_102 governs ISO vs ANSI. Forcing a specific
    layout would load the matching HKL.
    """
    raise NotImplementedError("Windows detection not yet implemented")


def _detect_macos(force_layout=None, force_variant=None):
    """Scaffold: UCKeyTranslate() with TISCopyCurrentKeyboardInputSource().

    TODO: full implementation via Carbon/HIToolbox through ctypes.
    """
    raise NotImplementedError("macOS detection not yet implemented")


def detect_labels_by_name(force_layout=None, force_variant=None):
    """OS-detected labels keyed by XKB key name. Raises on unsupported/failure."""
    system = platform.system()
    if system == "Linux":
        return _detect_linux(force_layout, force_variant)
    if system == "Windows":
        return _detect_windows(force_layout, force_variant)
    if system == "Darwin":
        return _detect_macos(force_layout, force_variant)
    raise RuntimeError("unsupported platform: %s" % system)


def detect_layout(manual_override=None, layout=None, variant=None):
    """Return (labels_by_name, meta).

    labels_by_name maps each XKB key name (AD01, AC10, ...) to the character the
    active (or forced) layout produces there; the physical templates look caps
    up by these names. On any failure the German QWERTZ fallback is returned and
    meta['source'] says so.

    layout/variant: force a specific XKB layout instead of the active one (the
    manual-selection path). manual_override: optional dict {name: "label"} to
    force individual caps.
    """
    try:
        labels, meta = detect_labels_by_name(layout, variant)
        meta["source"] = "manual" if layout is not None else "os"
    except Exception as exc:
        labels = dict(_FALLBACK_LABELS)
        meta = {"source": "fallback", "error": str(exc),
                "physical_form": "ISO", "layout": "de"}

    if manual_override:
        labels.update(manual_override)

    return labels, meta


# German QWERTZ fallback (matches the previously hard-coded labels).
_FALLBACK_LABELS = {
    "TLDE": "^", "AE01": "1", "AE02": "2", "AE03": "3", "AE04": "4",
    "AE05": "5", "AE06": "6", "AE07": "7", "AE08": "8", "AE09": "9",
    "AE10": "0", "AE11": "ß", "AE12": "´",
    "AD01": "Q", "AD02": "W", "AD03": "E", "AD04": "R", "AD05": "T",
    "AD06": "Z", "AD07": "U", "AD08": "I", "AD09": "O", "AD10": "P",
    "AD11": "Ü", "AD12": "+",
    "AC01": "A", "AC02": "S", "AC03": "D", "AC04": "F", "AC05": "G",
    "AC06": "H", "AC07": "J", "AC08": "K", "AC09": "L", "AC10": "Ö",
    "AC11": "Ä", "BKSL": "#",
    "LSGT": "<", "AB01": "Y", "AB02": "X", "AB03": "C", "AB04": "V",
    "AB05": "B", "AB06": "N", "AB07": "M", "AB08": ",", "AB09": ".",
    "AB10": "-",
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
    labels, meta = detect_layout()
    print("meta:", meta)
    for name in KEYCODES:
        print("  %-5s %s" % (name, labels.get(name, "")))
