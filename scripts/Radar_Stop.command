#!/bin/bash
# =============================================================
# 📡 Investment Radar — STOP
# =============================================================
# Double-click to shut down the dashboard cleanly.
#
# What it does:
#   1. Kills the Streamlit server (by PID file, then by port).
#   2. Closes any Chrome tabs pointed at the Radar.
#   3. Closes this Terminal window in 2 seconds.
#
# First time you run it, macOS will ask "Terminal wants to
# control Google Chrome." Click Allow — that permission is
# how the script can close browser tabs for you.
# =============================================================

LOG_DIR="$HOME/Investment_Radar/logs"

echo "📡  Stopping Investment Radar..."
echo ""

# ---- Kill by saved PID (fast + reliable) ----
if [ -f "$LOG_DIR/streamlit.pid" ]; then
    PID=$(cat "$LOG_DIR/streamlit.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null
        echo "✓ Stopped server (PID $PID)"
    fi
    rm -f "$LOG_DIR/streamlit.pid"
fi

# ---- Belt-and-braces: also kill by port 9000 ----
PORT_PID=$(lsof -ti:9000 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    kill "$PORT_PID" 2>/dev/null
    sleep 1
    kill -9 "$PORT_PID" 2>/dev/null || true
    echo "✓ Confirmed port 9000 is clear"
elif [ -z "$PID" ]; then
    echo "  (Streamlit wasn't running)"
fi

# ---- Close Chrome tabs pointing at the Radar ----
osascript <<'APPLESCRIPT' 2>/dev/null || echo "  (Chrome not open or automation not permitted)"
tell application "Google Chrome"
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
                    end if
                end try
            end repeat
        end repeat
    end try
end tell
APPLESCRIPT
echo "✓ Closed Radar Chrome tabs"

echo ""
echo "📡  Investment Radar is fully stopped."
echo "   This window closes in 2 seconds..."
sleep 2

# ---- Close this Terminal window ----
osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
exit 0
