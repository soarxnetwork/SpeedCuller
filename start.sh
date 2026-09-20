#!/bin/bash
# ==============================================================================
# Speed Culler - 1-Click Launch Script
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PORT=5500
URL="http://127.0.0.1:$PORT"

echo "=========================================================="
echo "           ⚡ SPEED CULLER - PHOTO CATEGORIZER            "
echo "=========================================================="
echo "Directory: $DIR"

# Check if server is already running on port 5500
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "✓ Speed Culler server is already running on port $PORT."
    echo "Opening $URL in default browser..."
    open "$URL"
    exit 0
fi

echo "Starting Speed Culler server on $URL..."
# Open browser after 1 second
(sleep 1 && open "$URL") &

# Run server (standard library only, no pip installs needed)
python3 server.py
