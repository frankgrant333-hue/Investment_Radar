#!/bin/bash
# =============================================================
# 📡 Investment Radar — Desktop Shortcut Installer
# =============================================================
# Double-click ONE TIME to:
#   1. Copy Start / Stop / Refresh scripts to your Desktop.
#   2. Attach the custom radar icons.
#   3. Refresh Finder so the new icons show up immediately.
# After running once, you can delete this installer.
# =============================================================

set -e
SCRIPTS_DIR="$HOME/Investment_Radar/scripts"
DESKTOP="$HOME/Desktop"

echo "📡  Installing Investment Radar desktop shortcuts..."
echo ""

if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "❌ Couldn't find $SCRIPTS_DIR"
    read -n 1 -s -p "Press any key to close..."
    exit 1
fi

# ---- Step 1: copy .command files to Desktop ----
for name in Radar_Start Radar_Stop Radar_Refresh; do
    src="$SCRIPTS_DIR/${name}.command"
    dst="$DESKTOP/${name}.command"
    if [ ! -f "$src" ]; then
        echo "❌ Missing: $src"
        continue
    fi
    cp -f "$src" "$dst"
    chmod +x "$dst"
    xattr -d com.apple.quarantine "$dst" 2>/dev/null || true
    echo "✓ Copied ${name}.command to Desktop"
done

# ---- Step 2: attach custom icons ----
# The heredoc-in-command-substitution trick failed silently on my
# first try, so this version writes the Python to a real temp file
# and runs it. Any errors will surface in the terminal instead of
# vanishing into a swallowed subshell.
echo ""
echo "Attaching custom radar icons..."

PY_SCRIPT="$(mktemp -t radar_icon_setup).py"
cat > "$PY_SCRIPT" <<'PYEOF'
"""Attach the radar PNG icons to the three .command files on Desktop."""
import os
import sys

# Diagnostic: which Python are we?
print(f"  python:  {sys.executable}")
print(f"  version: {sys.version.split()[0]}")

try:
    from AppKit import NSImage, NSWorkspace
    print("  AppKit:  OK")
except Exception as e:
    print(f"  AppKit:  IMPORT FAILED — {e.__class__.__name__}: {e}")
    print()
    print("  Falling back to manual instructions (see below).")
    sys.exit(2)

home = os.path.expanduser("~")
mappings = [
    ("Radar_Start",   "Radar_Start_icon.png"),
    ("Radar_Stop",    "Radar_Stop_icon.png"),
    ("Radar_Refresh", "Radar_Refresh_icon.png"),
]

ws = NSWorkspace.sharedWorkspace()
success = 0
for cmd_name, icon_name in mappings:
    icon_path = f"{home}/Investment_Radar/scripts/{icon_name}"
    cmd_path  = f"{home}/Desktop/{cmd_name}.command"
    if not os.path.exists(icon_path):
        print(f"  ⚠  Icon file missing: {icon_path}")
        continue
    if not os.path.exists(cmd_path):
        print(f"  ⚠  Target missing:    {cmd_path}")
        continue
    img = NSImage.alloc().initWithContentsOfFile_(icon_path)
    if img is None:
        print(f"  ⚠  Couldn't load PNG: {icon_name}")
        continue
    ok = ws.setIcon_forFile_options_(img, cmd_path, 0)
    mark = "✓" if ok else "⚠"
    print(f"  {mark}  {cmd_name}.command  ← {icon_name}")
    if ok:
        success += 1

print()
print(f"  Icons attached: {success}/{len(mappings)}")
sys.exit(0 if success == len(mappings) else 1)
PYEOF

/usr/bin/python3 "$PY_SCRIPT"
ICON_EXIT=$?
rm -f "$PY_SCRIPT"

# ---- Refresh Finder so new icons show up ----
killall Finder 2>/dev/null || true
sleep 1

if [ $ICON_EXIT -ne 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo " Some icons couldn't be attached automatically."
    echo " No problem — the shortcuts still WORK, they just show"
    echo " with a generic script icon until you attach them by hand."
    echo ""
    echo " MANUAL ICON ATTACH (30 seconds per icon):"
    echo ""
    echo "   1. Open Finder → go to your Desktop."
    echo "   2. Right-click 'Radar_Start.command' → Get Info."
    echo "   3. In another Finder window, go to:"
    echo "        ~/Investment_Radar/scripts/"
    echo "      and double-click 'Radar_Start_icon.png' to open"
    echo "      it in Preview."
    echo "   4. In Preview, press ⌘+A then ⌘+C to copy the image."
    echo "   5. Back in the Get Info window, click ONCE on the tiny"
    echo "      icon in the top-left corner (it will get a blue"
    echo "      selection highlight)."
    echo "   6. Press ⌘+V to paste. The icon changes immediately."
    echo "   7. Repeat for Radar_Stop.command (use Radar_Stop_icon.png)"
    echo "      and Radar_Refresh.command (use Radar_Refresh_icon.png)."
    echo "═══════════════════════════════════════════════════════"
fi

echo ""
echo "📡  Install complete."
echo ""
echo "You now have three shortcuts on your Desktop:"
echo "  🟢  Radar_Start.command    — launch the dashboard"
echo "  🔴  Radar_Stop.command     — shut it down cleanly"
echo "  🔵  Radar_Refresh.command  — restart with fresh data"
echo ""
echo "Double-click any of them any time. Terminal windows will"
echo "auto-close so you don't accumulate stray Terminals."
echo ""
echo "Closing this window in 5 seconds..."
sleep 5

osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
exit 0
