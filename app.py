"""
Main application entry point for CPA WorkflowPilot
Imports from the new src/ structure
"""

from src.app import create_app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)