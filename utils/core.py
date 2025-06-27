"""
Core Utilities for CPA WorkflowPilot
Common utility functions for general usage.

NOTE: Service-related functions have been moved to their respective services.
Use service instances directly instead of utility wrappers for clean architecture.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# All business logic functions have been moved to their respective services:
# - create_activity_log() → ActivityLoggingService.create_activity_log()
# - calculate_task_due_date() → TaskService.calculate_task_due_date() 
# - calculate_next_due_date() → TaskService.calculate_next_due_date()
# - process_recurring_tasks() → TaskService.process_recurring_tasks()
# - find_or_create_client() → ClientService.find_or_create_client()

# Use service instances directly for clean, maintainable architecture!