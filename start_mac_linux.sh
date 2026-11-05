#!/bin/bash
# Run with:  bash start_mac_linux.sh   (Mac or Linux)
cd "$(dirname "$0")"
echo "Installing packages (only slow the first time)..."
python3 -m pip install -r requirements.txt
echo "Starting the app. Your browser will open in a moment."
python3 -m streamlit run app.py
