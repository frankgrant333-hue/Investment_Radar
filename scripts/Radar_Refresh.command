#!/bin/bash
# =============================================================
# 📡 Investment Radar — REFRESH (stop + start cleanly)
# =============================================================
# Double-click to shut down the currently-running dashboard and
# immediately boot a fresh one — with fresh data from Yahoo.
# Auto-closes this Terminal after 3 seconds.
# =============================================================

LOG_DIR="$HOME/Investment_Radar/logs"
mkdir -p "$LOG_DIR"

echo "📡  Refreshing Investment Radar..."
echo ""

# ---- Stop old server ----
if [ -f "$LOG_DIR/streamlit.pid" ]; then
    OLD_PID=$(cat "$LOG_DIR/streamlit.pid")
    kill "$OLD_PID" 2>/dev/null
    rm -f "$LOG_DIR/streamlit.pid"
fi
PORT_PID=$(lsof -ti:9000 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    kill "$PORT_PID" 2>/dev/null
    sleep 1
    kill -9 "$PORT_PID" 2>/dev/null || true
    echo "✓ Stopped old server"
fi

# ---- Close old Chrome tabs so Refresh gives a clean slate ----
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
APPLESCRIPT

sleep 1

# ---- Start fresh ----
cd "$HOME/Investment_Radar" 2>/dev/null || exit 1
if [ ! -d "venv" ]; then
    echo "❌ venv missing — can't restart."
    read -n 1 -s
    exit 1
fi
source venv/bin/activate

: > "$LOG_DIR/streamlit.log"

nohup streamlit run radar/app.py \
        --server.port 9000 \
        --server.headless true \
        >"$LOG_DIR/streamlit.log" 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > "$LOG_DIR/streamlit.pid"
disown -a 2>/dev/null || true

echo "✓ Booted fresh instance (PID $STREAMLIT_PID)"
echo "   Chrome will open in ~5 seconds..."

(sleep 5 && open -a "Google Chrome" "http://localhost:9000") &

# Auto-close this terminal
sleep 3
osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
exit 0
