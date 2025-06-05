#!/bin/bash

echo "Setting up CPA WorkflowPilot MVP..."

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python is not installed or not in PATH"
    exit 1
fi

# Check if pip is available
if command -v pip3 &> /dev/null; then
    PIP_CMD=pip3
elif command -v pip &> /dev/null; then
    PIP_CMD=pip
else
    echo "Error: pip is not installed or not in PATH"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
echo "Using pip: $PIP_CMD"

# Install dependencies
echo "Installing dependencies..."
$PIP_CMD install -r requirements.txt

# Initialize database
echo "Initializing database..."
$PYTHON_CMD init_db.py

echo ""
echo "Setup complete!"
echo ""
echo "To start the application:"
echo "  $PYTHON_CMD app.py"
echo ""
echo "Then visit http://localhost:5000"
echo ""
echo "For admin access: http://localhost:5000/admin"
echo "Default admin password: admin123"