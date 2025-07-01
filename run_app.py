#!/usr/bin/env python3
"""
Application Startup Script for CPA WorkflowPilot
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the app
if __name__ == '__main__':
    from src.app import create_app
    
    print("🚀 Starting CPA WorkflowPilot...")
    print(f"📁 Project root: {project_root}")
    print(f"🐍 Python version: {sys.version}")
    
    app = create_app()
    
    print("✅ Application initialized successfully!")
    print("🌐 Open your browser to: http://localhost:5002")
    print("📋 Use Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5004, use_reloader=False)