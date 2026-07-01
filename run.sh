#!/bin/bash
# Quick start script for Boudica Code
export BOUDICA_API_KEY="bdk_d69ed3b10d687b678b69c8efc29a0537a26dcdd13afd4f46e64498d5b4ad"
export BOUDICA_USER_ID='sibain@omniindex.io'
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Run the CLI
echo ""
python3 "$SCRIPT_DIR/src/main.py"
