#!/bin/bash
# =============================================================
# 📡 Investment Radar — REFRESH (stop + restart cleanly)
# =============================================================
# Double-click to shut down the currently-running dashboard
# and immediately start a fresh instance. Useful when:
#   - the dashboard seems stuck or slow
#   - you edited a code file and want to see the change
#   - you want to force fresh data from Yahoo
# =============================================================

echo "📡  Refreshing Investment Radar..."
echo ""

# ---- Step 1: kill the old server ----
PID=$(lsof -ti:9000 2>/dev/null)
if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null
    sleep 1
    kill -9 "$PID" 2>/dev/null || true
    echo "✓ Stopped old server (PID $PID)"
else
    echo "  (no old server was running)"
fi

# Close the old Terminal + Chrome tabs so we start fresh
osascript <<'APPLESCRIPT' 2>/dev/null || true
tell application "Google Chrome"
    try
        set win_list to windows
        repeat with w in win_list
            set tab_count to (count of tabs of w)
            repeat with i from tab_count to 1 by -1
                try
                    set url_val to URL of tab i of w
                    if url_val contains "localhost:9000" ¬
                        or url_val contains "127.0.0.1:9000" then
                        close tab i of w
                    end if
                end try
            end repeat
        end repeat
    end try
end tell

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

sleep 2

# ---- Step 2: start fresh ----
cd ~/Investment_Radar 2>/dev/null || {
    echo "❌ Couldn't find ~/Investment_Radar folder."
    echo "Press any key to close..."
    read -n 1 -s
    exit 1
}

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment missing. See Radar_Start.command output."
    read -n 1 -s
    exit 1
fi

source venv/bin/activate

echo ""
echo "📡  Booting fresh instance..."
echo "   Chrome will open in ~5 seconds."
echo "   Leave this window open while you use the Radar."
echo ""

(sleep 5 && open -a "Google Chrome" "http://localhost:9000") &
streamlit run radar/app.py --server.port 9000 --server.headless true
