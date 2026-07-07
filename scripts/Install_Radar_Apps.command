#!/bin/bash
# =============================================================
# 📡 Investment Radar — Install .app Bundles to Desktop
# =============================================================
# Double-click ONE TIME to:
#   1. Remove the old Radar_*.command files from your Desktop.
#   2. Copy Radar Start / Stop / Refresh .app bundles to Desktop.
#   3. Clear macOS's downloaded-from-internet flag.
#   4. Refresh Finder so the icons show up immediately.
# =============================================================

APPS_DIR="$HOME/Investment_Radar/scripts/apps"
DESKTOP="$HOME/Desktop"

echo "📡  Installing Radar app bundles..."
echo ""

# ---- Step 1: clean up the old .command files ----
for old in Radar_Start.command Radar_Stop.command Radar_Refresh.command; do
    if [ -f "$DESKTOP/$old" ]; then
        rm -f "$DESKTOP/$old"
        echo "✓ Removed old $old from Desktop"
    fi
done

# ---- Step 2: copy the three .app bundles ----
if [ ! -d "$APPS_DIR" ]; then
    echo "❌ Couldn't find $APPS_DIR"
    echo "   The apps folder should have been created earlier."
    read -n 1 -s -p "Press any key to close..."
    exit 1
fi

for app in "Radar Start.app" "Radar Stop.app" "Radar Refresh.app"; do
    src="$APPS_DIR/$app"
    dst="$DESKTOP/$app"
    if [ ! -d "$src" ]; then
        echo "❌ Missing: $src"
        continue
    fi
    # Wipe old copy first so we're not stacking stale files
    rm -rf "$dst"
    cp -R "$src" "$dst"
    # Clear macOS's quarantine flag so double-click "just works"
    xattr -dr com.apple.quarantine "$dst" 2>/dev/null || true
    # Make sure the executable inside is actually executable
    chmod +x "$dst"/Contents/MacOS/* 2>/dev/null
    echo "✓ Copied '$app' to Desktop"
done

# ---- Step 3: refresh Finder icon cache ----
killall Finder 2>/dev/null || true
sleep 1

echo ""
echo "📡  Done!"
echo ""
echo "Three radar-shaped app icons should now be on your Desktop:"
echo "  🟢  Radar Start.app     — launch the dashboard"
echo "  🔴  Radar Stop.app      — shut it down cleanly"
echo "  🔵  Radar Refresh.app   — restart with fresh data"
echo ""
echo "Double-click any of them any time. They run silently —"
echo "no Terminal window opens or lingers. A macOS notification"
echo "at the top-right corner confirms what happened."
echo ""
echo "First-time gotchas macOS might throw at you:"
echo "  * Gatekeeper: 'Radar Start' is from an unidentified"
echo "    developer. Right-click the app → Open → Open. One time."
echo "  * Automation prompt: 'Radar Stop wants to control"
echo "    Google Chrome' — click OK. That's how it closes tabs."
echo ""
echo "Closing this window in 6 seconds..."
sleep 6

osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
exit 0
