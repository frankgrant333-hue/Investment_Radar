#!/bin/bash
# =============================================================
# 📡 Investment Radar — START
# =============================================================
# Double-click this to launch the dashboard.
#
# Streamlit runs in the BACKGROUND, so this Terminal window
# closes itself after a few seconds — no more window pile-up.
# The dashboard log is saved to ~/Investment_Radar/logs/streamlit.log
# in case you ever need to check what happened.
# =============================================================

LOG_DIR="$HOME/Investment_Radar/logs"
mkdir -p "$LOG_DIR"

# Best-effort clean up any error output from previous runs
: > "$LOG_DIR/streamlit.log"

cd "$HOME/Investment_Radar" 2>/dev/null || {
    echo "❌ Couldn't find ~/Investment_Radar folder."
    echo "Press any key to close..."
    read -n 1 -s
    exit 1
}

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found at ~/Investment_Radar/venv/"
    echo "Ask Claude to help you set it up."
    read -n 1 -s -p "Press any key to close..."
    exit 1
fi

# ---- Already running? just open a browser tab ----
if lsof -ti:9000 >/dev/null 2>&1; then
    echo "⚠️  Investment Radar is already running."
    echo "   Opening a Chrome tab to http://localhost:9000..."
    open -a "Google Chrome" "http://localhost:9000"
    sleep 2
    # Close this terminal — nothing more to do
    osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
    exit 0
fi

# ---- Launch Streamlit as a detached background process ----
# `nohup` = keep running after this terminal closes
# `disown -a` = drop the job from bash's job table so terminal
# can exit cleanly without prompting "process still running".
source venv/bin/activate

echo "📡  Booting Investment Radar in the background..."

nohup arch -arm64 streamlit run radar/app.py \
        --server.port 9000 \
        --server.headless true \
        >"$LOG_DIR/streamlit.log" 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > "$LOG_DIR/streamlit.pid"
disown -a 2>/dev/null || true

echo "   Server PID: $STREAMLIT_PID"
echo "   Log:        $LOG_DIR/streamlit.log"
echo ""
echo "   Chrome will open in ~5 seconds."
echo "   To stop, double-click 📡 Radar_Stop.command on your Desktop."
echo ""

# Kick off a browser tab in the background (in case Streamlit didn't)
(sleep 5 && open -a "Google Chrome" "http://localhost:9000") &

# Give the user a couple of seconds to read the message
sleep 4

# Auto-close this terminal window so you don't accumulate dead
# terminals across the day.
osascript -e 'tell application "Terminal" to close (front window)' 2>/dev/null &
exit 0
