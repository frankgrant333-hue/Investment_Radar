#!/bin/bash
# =============================================================
# 📡 Investment Radar — START
# =============================================================
# Double-click this file to launch the dashboard. A Terminal
# window opens and stays open while the server runs; Chrome
# opens automatically at http://localhost:9000 after a few seconds.
#
# To stop cleanly, double-click "Radar_Stop.command" instead of
# using Ctrl+C in this window.
# =============================================================

cd ~/Investment_Radar 2>/dev/null || {
    echo "❌ Couldn't find ~/Investment_Radar folder."
    echo ""
    echo "Press any key to close this window..."
    read -n 1 -s
    exit 1
}

# Make sure the venv exists — otherwise nothing else works
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found at ~/Investment_Radar/venv/"
    echo ""
    echo "You probably need to (re-)create it. Ask Claude to walk you"
    echo "through it, or run these commands manually in Terminal:"
    echo ""
    echo "  cd ~/Investment_Radar"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    echo "Press any key to close this window..."
    read -n 1 -s
    exit 1
fi

# If the server is already running, just open a new browser tab
if lsof -ti:9000 >/dev/null 2>&1; then
    echo "⚠️  Investment Radar is already running on port 9000."
    echo "   Opening a Chrome tab to it now."
    open -a "Google Chrome" "http://localhost:9000"
    sleep 2
    echo ""
    echo "You can close this window."
    exit 0
fi

# Activate the venv
source venv/bin/activate

echo "📡  Starting Investment Radar..."
echo ""
echo "   Chrome will open in ~5 seconds."
echo "   Leave THIS Terminal window open while you use the Radar."
echo "   To stop, double-click 📡 Radar_Stop.command on your Desktop."
echo ""

# Open Chrome once the server has had time to boot
(sleep 5 && open -a "Google Chrome" "http://localhost:9000") &

# Run streamlit (blocks until stopped)
#   --server.headless true : don't let Streamlit auto-open its
#     own browser tab, since we're doing it explicitly above.
streamlit run radar/app.py --server.port 9000 --server.headless true
