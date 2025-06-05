# CPA WorkflowPilot MVP

A streamlined workflow management application designed specifically for solo CPAs and small accounting firms to manage client work, standardize processes through templates, and ensure no deadline is ever missed.

## Features

✅ **Template-Driven Workflows**: Create and reuse standardized checklists for common services
✅ **Automated Recurring Tasks**: Generate routine work automatically based on schedule rules
✅ **Project Management**: Organize client work with clear progress tracking
✅ **Multi-User Support**: Team collaboration with role-based access (Admin/Member)
✅ **Activity Logging**: Complete audit trail of all actions
✅ **Access Code Authentication**: Simple, secure firm-level access control
✅ **Responsive Design**: Works on desktop and mobile browsers

## Technology Stack

- **Backend**: Python with Flask framework
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Server-side rendered HTML with Bootstrap 5
- **Authentication**: Access code-based (no traditional login required)

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd workflow-management

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# Create database and demo data
python init_db.py
```

This creates a demo firm with sample templates and users. The script will output an access code for testing.

### 3. Run Application

```bash
# Start the Flask development server
python app.py
```

The application will be available at http://localhost:5000

### 4. Login

- Visit http://localhost:5000
- Enter the access code provided by the init script
- Or visit http://localhost:5000/admin for admin functions (password: admin123)

## Usage Guide

### Admin Functions

1. **Generate Access Codes**: Create new firm accounts from the admin panel
2. **Manage Firms**: View all registered firms and their activity

### Core Workflow

1. **Create Templates**: Define repeatable workflows with ordered tasks
   - Add recurring rules for compliance tasks (monthly, quarterly, etc.)
   - Set default assignees for each task

2. **Create Projects**: Start new client work by applying a template
   - Select client name and template
   - Tasks are automatically generated from template

3. **Manage Tasks**: Update task status and track progress
   - Status options: Not Started → In Progress → Needs Review → Completed
   - Real-time status updates with activity logging

4. **Team Management**: Add users and assign tasks
   - Admin role: Manage templates, projects, users
   - Member role: Manage assigned tasks

### Recurring Task Engine

The application automatically generates recurring tasks based on rules:

- **Daily**: Every day
- **Weekly**: Every week  
- **Monthly**: Various options (15th, last day, last business day)
- **Quarterly**: Every quarter (with business day options)
- **Annually**: Every year

Recurring tasks are generated regardless of previous task completion status, ensuring compliance deadlines are never missed.

## Configuration

### Environment Variables

```bash
# Set admin password (default: admin123)
export ADMIN_PASSWORD=your_secure_password

# Set Flask secret key (auto-generated if not set)
export SECRET_KEY=your_secret_key
```

### Database Location

The SQLite database is stored in the `/instance/` directory for security.

## Security Notes

- Access codes provide firm-level security
- Database files are stored outside web-accessible directories
- No sensitive data is logged in activity trails
- Access tokens are securely generated using Python's secrets module

## Project Structure

```
workflow-management/
├── app.py              # Main Flask application
├── models.py           # SQLAlchemy database models
├── utils.py            # Utility functions (recurring tasks, logging)
├── init_db.py          # Database initialization script
├── requirements.txt    # Python dependencies
├── instance/           # SQLite database location
└── templates/          # HTML templates
    ├── base.html       # Base template with navigation
    ├── login.html      # Access code login
    ├── dashboard.html  # Main dashboard
    ├── templates.html  # Template management
    ├── projects.html   # Project management
    ├── tasks.html      # Task management
    └── ...            # Additional templates
```

## Development Notes

This MVP focuses on core workflow management functionality. The following features are intentionally excluded:

- Third-party integrations (email, calendar, document storage)
- Time tracking and billing
- Advanced analytics and reporting
- Client-facing portals
- File uploads and document management

## Support

For issues or questions about CPA WorkflowPilot, the codebase is fully self-contained and documented. Key areas for customization:

- **Recurring Rules**: Modify `utils.py` to add new recurrence patterns
- **User Roles**: Extend the User model for additional permission levels  
- **Templates**: The template system is designed to be highly flexible
- **Activity Logging**: Customize what actions are tracked in `utils.py`

## Production Deployment

For production use:

1. Set strong `SECRET_KEY` and `ADMIN_PASSWORD` environment variables
2. Configure a proper WSGI server (Gunicorn, uWSGI)
3. Set up proper database backups for the SQLite file
4. Configure SSL/HTTPS for secure access
5. Consider upgrading to PostgreSQL for larger teams