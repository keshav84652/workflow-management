"""
Jinja2 Template Filters for CPA WorkflowPilot
Provides reusable template filters for formatting data in templates.
"""

from datetime import datetime
from typing import Optional
from flask import Flask, current_app, url_for
from werkzeug.routing import BuildError


def format_currency(amount: Optional[float]) -> str:
    """Format currency amount to string with dollar sign and commas"""
    if amount is None:
        return "$0.00"
    try:
        num_amount = float(amount)
        if num_amount < 0:
            return f"-${abs(num_amount):,.2f}"
        return f"${num_amount:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def format_date(date_obj: Optional[datetime], format_str: str = "%Y-%m-%d") -> str:
    """Format datetime object to readable string"""
    if date_obj is None or date_obj == "":
        return ""
    try:
        return date_obj.strftime(format_str)
    except (AttributeError, TypeError):
        return ""


def format_date_pretty(date_obj: Optional[datetime]) -> str:
    """Format datetime object to pretty readable string"""
    return format_date(date_obj, "%B %d, %Y")


def format_datetime(date_obj: Optional[datetime]) -> str:
    """Format datetime object with time included"""
    return format_date(date_obj, "%Y-%m-%d %H:%M")


def format_percentage(value: Optional[float]) -> str:
    """Format decimal as percentage"""
    if value is None:
        return "0%"
    try:
        return f"{float(value):.1%}"
    except (ValueError, TypeError):
        return "0%"


def pluralize(count: int, singular: str, plural: str = None) -> str:
    """Return singular or plural form based on count"""
    if plural is None:
        plural = singular + 's'
    return singular if count == 1 else plural


def truncate_text(text: str, length: int = 50, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix"""
    if text is None:
        return ""
    if len(text) <= length:
        return text
    return text[:length].rstrip() + suffix


def endpoint_exists(endpoint: str) -> bool:
    """Check if a Flask endpoint exists"""
    try:
        url_for(endpoint)
        return True
    except BuildError:
        return False


def register_template_filters(app: Flask) -> None:
    """Register all template filters with Flask app"""
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['date'] = format_date
    app.jinja_env.filters['date_pretty'] = format_date_pretty
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['percentage'] = format_percentage
    app.jinja_env.filters['pluralize'] = pluralize
    app.jinja_env.filters['truncate'] = truncate_text
    
    # Add global function for templates
    app.jinja_env.globals['endpoint_exists'] = endpoint_exists


__all__ = [
    'format_currency',
    'format_date', 
    'format_date_pretty',
    'format_datetime',
    'format_percentage',
    'pluralize',
    'truncate_text',
    'register_template_filters'
]

