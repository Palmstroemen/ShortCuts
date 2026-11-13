# Map a workbench's shortcuts onto the physical keyboard model.
#
# Input: a list of shortcut entries (command text, the Qt key-sequence string,
# and an optional icon). Output: a model that says, for each physical key,
# which modifier families use it and whether it starts a key sequence - plus
# lookups for the focus views (one exact modifier set, or one sequence prefix).
#
# This module is pure Python: no FreeCAD, no Qt. The renderer (Keyboard_Layout)
# and a standalone test can both drive it. Keys are addressed by a "ref": an XKB
# key name for character keys (AD01 = the Q position, as in Keyboard_Detect /
# Keyboard_Templates) or a static label ("F5", "Space", "Enter") for the rest.

import re

# Shortcut modifiers we recognise. AltGr is intentionally absent: it is not a
# usable application-shortcut modifier (on Windows it equals Ctrl+Alt and is
# otherwise reserved for typing characters). See the design discussion.
_MODS = {"Ctrl": "ctrl", "Shift": "shift", "Alt": "alt", "Meta": "meta"}

# Overview corner slots map these families to fixed positions, so the eye learns
# "top-right = Ctrl". "plain" = a shortcut with no modifier. "meta" has no corner
# (rare in FreeCAD); it still counts as "occupied".
FAMILY_ORDER = ["plain", "ctrl", "shift", "alt", "meta"]
FAMILY_COLORS = {
    "plain": "#888780",   # gray
    "ctrl": "#378ADD",    # blue
    "shift": "#EF9F27",   # amber
    "alt": "#639922",     # green
    "meta": "#D4537E",    # pink
    "seq": "#7F77DD",     # purple - sequence prefix / completions
}

# Qt key tokens that are not single characters -> the static label the templates
# use for that key. Character keys (letters, digits, symbols) are resolved from
# the active layout instead, so they are layout-correct.
_NAMED_KEYS = {
    "Space": "Space",
    "Return": "Enter", "Enter": "Enter",
    "Tab": "Tab",
    "Esc": "Esc", "Escape": "Esc",
    "Backspace": "⌫",
    "Left": "←", "Right": "→", "Up": "↑", "Down": "↓",
    "PgUp": "⇞", "PgDown": "⇟", "PageUp": "⇞", "PageDown": "⇟",
}

_FKEY = re.compile(r"^F([1-9]|1[0-9]|2[0-4])$")


def parse_chord(text):
    """Parse one chord ("Ctrl+Shift+S") into {mods: frozenset, key: token}.

    Leading tokens that are known modifiers are consumed; whatever remains is the
    key (rejoined with '+', so a literal '+' key survives).
    """
    parts = text.split("+")
    mods = set()
    idx = 0
    while idx < len(parts) - 1 and parts[idx] in _MODS:
        mods.add(_MODS[parts[idx]])
        idx += 1
    return {"mods": frozenset(mods), "key": "+".join(parts[idx:])}


def parse_sequence(text):
    """Parse a Qt key-sequence string into a list of chords.

    A sequence has its chords separated by ", " (e.g. "G, S"). Returns [] for an
    empty shortcut.
    """
    text = (text or "").strip()
    if not text:
        return []
    return [parse_chord(part) for part in text.split(", ")]


def _label_to_id(labels):
    """Reverse the detected {name: label} into {label: name} for char lookup."""
    rev = {}
    for name, label in labels.items():
        if label and label not in rev:
            rev[label] = name
    return rev


def resolve_ref(token, label_to_id):
    """A Qt key token -> a physical key ref, or None if we can't place it.

    Character tokens resolve through the active layout's labels (so "Z" lands on
    whichever key shows Z); named keys and function keys resolve to their static
    label.
    """
    if not token:
        return None
    if token in label_to_id:
        return label_to_id[token]
    if len(token) == 1:
        up = token.upper()
        if up in label_to_id:
            return label_to_id[up]
    if _FKEY.match(token):
        return token
    if token in _NAMED_KEYS:
        return _NAMED_KEYS[token]
    return None


def _families_of(mods):
    return set(mods) if mods else {"plain"}


def build(entries, labels):
    """Build the keyboard shortcut model.

    entries: list of {"text", "shortcut", "icon"(optional)}.
    labels:  {xkb_name: cap} from Keyboard_Detect.

    Returns a dict:
      by_key:    ref -> {"families": set, "prefix": bool, "entries": [entry...]}
      by_modset: frozenset(families) -> [{"ref", "entry", "chord"}]  (single chord)
      prefixes:  prefix_ref -> {"entries": [{"ref", "entry", "chord"}], "unplaced": [...]}
      unplaced:  entries whose key could not be mapped (for diagnostics)
    """
    label_to_id = _label_to_id(labels)
    by_key = {}
    by_modset = {}
    prefixes = {}
    unplaced = []

    def key_rec(ref):
        rec = by_key.get(ref)
        if rec is None:
            rec = {"families": set(), "prefix": False, "entries": []}
            by_key[ref] = rec
        return rec

    for entry in entries:
        chords = parse_sequence(entry.get("shortcut"))
        if not chords:
            continue

        if len(chords) == 1:
            chord = chords[0]
            ref = resolve_ref(chord["key"], label_to_id)
            if ref is None:
                unplaced.append(entry)
                continue
            rec = key_rec(ref)
            rec["families"].update(_families_of(chord["mods"]))
            rec["entries"].append(entry)
            by_modset.setdefault(chord["mods"], []).append(
                {"ref": ref, "entry": entry, "chord": chord})
        else:
            first = chords[0]
            prefix_ref = resolve_ref(first["key"], label_to_id)
            comp = chords[1]
            comp_ref = resolve_ref(comp["key"], label_to_id)
            if prefix_ref is None:
                unplaced.append(entry)
                continue
            rec = key_rec(prefix_ref)
            rec["prefix"] = True
            bucket = prefixes.setdefault(
                prefix_ref, {"entries": [], "unplaced": []})
            item = {"ref": comp_ref, "entry": entry, "chord": comp}
            if comp_ref is None:
                bucket["unplaced"].append(item)
            else:
                bucket["entries"].append(item)

    return {
        "by_key": by_key,
        "by_modset": by_modset,
        "prefixes": prefixes,
        "unplaced": unplaced,
    }
