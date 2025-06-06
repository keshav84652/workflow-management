@echo off
title CPA WorkflowPilot

echo 🏢 CPA WorkflowPilot - Starting Application...
echo ==================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "app.py" (
    echo ❌ Error: app.py not found
    echo Please run this script from the workflow-management directory
    pause
    exit /b 1
)

REM Check if Flask is available
echo 🔧 Checking dependencies...
python -c "import flask, flask_sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Required Python packages not found
    echo Please install Flask and Flask-SQLAlchemy:
    echo pip install flask flask-sqlalchemy
    pause
    exit /b 1
)

REM Check if database exists, if not initialize it
if not exist "instance\workflow.db" (
    echo 🗄️  Database not found. Initializing with demo data...
    python init_db_v2.py
) else (
    echo ✅ Database found
)

echo.
echo 🚀 Starting CPA WorkflowPilot...
echo ==================================================
echo 📍 Application will be available at: http://localhost:5000
echo 🔐 Demo access code: DEMO2024
echo 👤 Demo users: Sarah Johnson (Admin), Mike Chen (Member), Emily Davis (Member)
echo.
echo Press Ctrl+C to stop the application
echo ==================================================

REM Start the application
python app.py

pause