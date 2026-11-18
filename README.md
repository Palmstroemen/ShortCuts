# ShortCuts

Manage, visualise and learn FreeCAD keyboard shortcuts.

This is a maintained fork of the original *ShortCuts* add-on by triplus, kept
working on current FreeCAD (1.x, Qt6) and extended with a keyboard view, direct
assignment and a printable cheat sheet.

![Keyboard view](Resources/icons/ShortCuts.svg)

## Features

- **Command list per workbench** — pick a workbench from the list (or
  *All workbenches* / *Global shortcuts*) and see its commands with their
  shortcuts. Filter to show all commands, only the ones that have a shortcut,
  or only the empty ones. A search box narrows the list.
- **Keyboard view** — the shortcuts drawn on the physical keyboard, laid out
  for the active keyboard layout. An overview marks each key with coloured
  corner pips per modifier family (Ctrl / Shift / Alt), fills the direct
  (no-modifier) shortcuts, and greys always-active global shortcuts. Click a
  modifier key — or press a real Ctrl / Shift / Alt — to focus that layer and
  see just those shortcuts with their command icons. Keys that start a
  two-step sequence (e.g. `G, S`) are marked too.
- **Assign shortcuts on the keyboard** — drag a command onto a key, or arm a
  command and press a key combination, to (re)assign its shortcut. Conflicts
  with an existing workbench or global shortcut are shown so you can decide
  which one to keep.
- **Printable cheat sheet** — the *Print* button opens a print preview with the
  current keyboard view and a formatted, paginated shortcut list for the
  selected workbench, ready to print or save as PDF.
- **Command overlay** — the original quick overlay: press **Shift+Q** to pop up
  the configured commands near the cursor.

## Installation

### Addon Manager (recommended)

Once published, install *ShortCuts* from FreeCAD's **Tools → Addon manager**.

### Manual

Clone or copy this repository into your FreeCAD `Mod` directory, so that
`InitGui.py` sits at `.../Mod/ShortCuts/InitGui.py`:

- Linux: `~/.local/share/FreeCAD/Mod/ShortCuts/`
- macOS: `~/Library/Application Support/FreeCAD/Mod/ShortCuts/`
- Windows: `%APPDATA%\FreeCAD\Mod\ShortCuts\`

Restart FreeCAD afterwards.

## Usage

Open the manager from **Tools → Accessories → Shortcuts Manager**. To invoke the
quick command overlay, press **Shift+Q**.

## License

LGPL-2.1-or-later. See [License/lgpl-2.1.txt](License/lgpl-2.1.txt).
