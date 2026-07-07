#!/bin/bash
# =============================================================
# 📡 Investment Radar — STOP
# =============================================================
# Double-click this file to shut down the dashboard cleanly.
#
# What it does:
#   1. Kills the Streamlit server (whatever is on port 9000).
#   2. Closes any Chrome tabs pointed at the Radar.
#   3. Auto-closes this Terminal window in 3 seconds.
#
# First time you run it, macOS will ask "Terminal wants to control
# Google Chrome." Click Allow — that's how it can close browser tabs.
# =============================================================

echo "📡  Stopping Investment Radar..."
echo ""

# ---- Kill the Streamlit server ----
PID=$(lsof -ti:9000 2>/dev/null)
if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null
    echo "✓ Sent stop signal to Streamlit server (PID $PID)"
    sleep 1
    # Force-kill if it didn't obey the polite kill
    if kill -0 "$PID" 2>/dev/null; then
        kill -9 "$PID" 2>/dev/null
        echo "  Force-killed the stubborn process"
    fi
else
    echo "  Streamlit server wasn't running — nothing to stop."
fi

# ---- Close Chrome tabs pointing at the Radar ----
echo ""
echo "Closing Chrome tabs for the Radar..."
osascript <<'APPLESCRIPT' 2>/dev/null || echo "  (Chrome not open or automation not permitted)"
tell application "Google Chrome"
    set closed_count to 0
    try
        set win_list to windows
        repeat with w in win_list
            set tab_count to (count of tabs of w)
            repeat with i from tab_count to 1 by -1
                try
                    set current_url to URL of tab i of w
                    if current_url contains "localhost:9000" ¬
                        or current_url contains "127.0.0.1:9000" ¬
                        or current_url contains "frank-investment-radar" then
                        close tab i of w
                        set closed_count to closed_count + 1
                    end if
                end try
            end repeat
        end repeat
    end try
    return closed_count
end tell
APPLESCRIPT
echo "✓ Chrome tabs closed"

# ---- Also kill the running Terminal window that the Start script left open ----
# (finds any Terminal window whose title mentions "Radar_Start" and closes it)
osascript <<'APPLESCRIPT' 2>/dev/null || true
tell application "Terminal"
    try
        set win_list to windows
        repeat with w in win_list
            try
                if name of w contains "Radar_Start" then
                    close w
                end if
            end try
        end repeat
    end try
end tell
APPLESCRIPT

echo ""
echo "📡  Investment Radar is fully stopped."
echo ""
echo "This window will close in 3 seconds..."
sleep 3

# Close THIS Terminal window (the Stop one)
osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
exit 0
