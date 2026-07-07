#!/bin/bash
# =============================================================
# 📡 Investment Radar — Desktop Shortcut Installer
# =============================================================
# Double-click this file ONE TIME to:
#   1. Copy the Start, Stop, and Refresh scripts to your Desktop.
#   2. Attach the custom radar icons to each one.
#   3. Clear macOS's "downloaded from internet" quarantine flag.
#
# After running this once, you can delete this installer.
# =============================================================

set -e

SCRIPTS_DIR="$HOME/Investment_Radar/scripts"
DESKTOP="$HOME/Desktop"

echo "📡  Installing Investment Radar desktop shortcuts..."
echo ""

if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "❌ Couldn't find $SCRIPTS_DIR"
    echo "   Make sure ~/Investment_Radar exists first."
    read -n 1 -s -p "Press any key to close..."
    exit 1
fi

# ---- Step 1: copy the three .command files ----
for name in Radar_Start Radar_Stop Radar_Refresh; do
    src="$SCRIPTS_DIR/${name}.command"
    dst="$DESKTOP/${name}.command"
    if [ ! -f "$src" ]; then
        echo "❌ Missing: $src"
        continue
    fi
    cp -f "$src" "$dst"
    chmod +x "$dst"
    # Clear macOS quarantine so the OS doesn't nag on first launch
    xattr -d com.apple.quarantine "$dst" 2>/dev/null || true
    echo "✓ Copied ${name}.command to Desktop"
done

# ---- Step 2: attach custom icons via PyObjC ----
# System /usr/bin/python3 ships with AppKit on macOS, no install needed.
#
# We run the Python inline via a heredoc, capture its output and exit
# code, then decide what to print. Keeping the `||` fallback OFF the
# heredoc line is important — combining them causes a bash parse error.
echo ""
echo "Attaching custom radar icons..."

ICON_OUTPUT=$(/usr/bin/python3 <<'PYEOF' 2>&1
import os
try:
    from AppKit import NSImage, NSWorkspace
except ImportError:
    raise SystemExit("AppKit not available on this Python — icons skipped.")

home = os.path.expanduser("~")
mappings = [
    ("Radar_Start",   "Radar_Start_icon.png"),
    ("Radar_Stop",    "Radar_Stop_icon.png"),
    ("Radar_Refresh", "Radar_Refresh_icon.png"),
]

ws = NSWorkspace.sharedWorkspace()
for cmd_name, icon_name in mappings:
    icon_path = f"{home}/Investment_Radar/scripts/{icon_name}"
    cmd_path  = f"{home}/Desktop/{cmd_name}.command"
    if not (os.path.exists(icon_path) and os.path.exists(cmd_path)):
        print(f"  Skipped {cmd_name} — file missing")
        continue
    img = NSImage.alloc().initWithContentsOfFile_(icon_path)
    if img is None:
        print(f"  Couldn't load icon {icon_name}")
        continue
    ok = ws.setIcon_forFile_options_(img, cmd_path, 0)
    mark = "OK " if ok else "!! "
    print(f"  {mark} Icon set for {cmd_name}.command")
PYEOF
)
ICON_EXIT=$?

echo "$ICON_OUTPUT"

if [ $ICON_EXIT -ne 0 ]; then
    echo ""
    echo "Note: icon attach step reported an issue. The shortcuts"
    echo "still work — you can attach the icons manually by right-"
    echo "clicking each .command file on your Desktop, choosing"
    echo "Get Info, and pasting the matching icon PNG from"
    echo "~/Investment_Radar/scripts/ into the small icon square"
    echo "in the top-left of the Get Info window."
fi

# Force Finder to reload its icon cache so the new icons show up
# immediately (otherwise Finder may keep displaying the old generic
# script icon until you log out).
killall Finder 2>/dev/null || true
sleep 1

echo ""
echo "📡  Done!"
echo ""
echo "You should now see three radar-shaped shortcuts on your Desktop:"
echo "  🟢  Radar_Start.command    — launch the dashboard"
echo "  🔴  Radar_Stop.command     — shut it down cleanly"
echo "  🔵  Radar_Refresh.command  — restart with fresh data"
echo ""
echo "Double-click Radar_Start.command to try it."
echo ""
echo "This window will close in 5 seconds..."
sleep 5

osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
exit 0
