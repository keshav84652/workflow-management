#!/bin/bash

# CPA WorkflowPilot Startup Script
# This script initializes and starts the CPA Workflow Management application

echo "🏢 CPA WorkflowPilot - Starting Application..."
echo "=================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3 and try again"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found"
    echo "Please run this script from the workflow-management directory"
    exit 1
fi

# Check if Flask is available
echo "🔧 Checking dependencies..."
python3 -c "import flask, flask_sqlalchemy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Error: Required Python packages not found"
    echo "Please install Flask and Flask-SQLAlchemy:"
    echo "pip install flask flask-sqlalchemy"
    exit 1
fi

# Check if database exists, if not initialize it
if [ ! -f "instance/workflow.db" ]; then
    echo "🗄️  Database not found. Initializing with demo data..."
    python3 init_db_v2.py
else
    echo "✅ Database found"
fi

echo ""
echo "🚀 Starting CPA WorkflowPilot..."
echo "=================================================="
echo "📍 Application will be available at: http://localhost:5000"
echo "🔐 Demo access code: DEMO2024"
echo "👤 Demo users: Sarah Johnson (Admin), Mike Chen (Member), Emily Davis (Member)"
echo ""
echo "Press Ctrl+C to stop the application"
echo "=================================================="

# Start the application
python3 app.py