#!/bin/bash

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python is not installed or not in PATH"
    exit 1
fi

echo "Starting CPA WorkflowPilot..."
echo "Visit http://localhost:5000 to access the application"
echo "Press Ctrl+C to stop the server"
echo ""

$PYTHON_CMD app.py