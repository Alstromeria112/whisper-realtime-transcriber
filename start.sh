#!/bin/bash
if [ ! -d ".venv" ]; then
    echo "Creating a virtual environment and installing dependencies..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    echo
    echo "Successfully created a virtual environment and installed dependencies."
    echo
fi

echo "Booting software..."
echo

echo "Activating environment..."
source .venv/bin/activate

echo
echo "Starting WebSocket server..."
echo "WebSocket: ws://localhost:8766"
echo "Web Client: http://localhost:8080"
echo
echo "停止するには Ctrl+C を押してネ"
echo

python main.py
