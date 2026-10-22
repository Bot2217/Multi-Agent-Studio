#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Installing deps..."
pip install -r requirements.txt
echo ""
echo "Starting Agent Studio UI at http://localhost:8501"
streamlit run app.py
