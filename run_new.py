#!/usr/bin/env python3
"""
New Flask Application Entry Point
Test the refactored modular architecture
"""

import os
from app import create_app

# Create Flask application
app = create_app('development')

if __name__ == '__main__':
    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)
    
    # Run application
    app.run(debug=True, host='localhost', port=5001)