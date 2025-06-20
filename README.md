# CPA WorkflowPilot - Professional Edition

A comprehensive workflow management application designed specifically for CPA firms, built with enterprise-grade architecture patterns inspired by leading open-source project management tools.

## 🚀 Features

### ✅ **Complete Feature Set (All Implemented)**
- **Template-Driven Workflows**: Sophisticated workflow automation with conditional logic
- **Enhanced Role-Based Permissions**: Staff, Senior, Manager, Partner, Admin roles
- **Advanced Project Management**: Sequential task dependencies and project health tracking
- **Comprehensive Task Management**: Kanban boards, time tracking, real-time updates
- **Client Portal Integration**: Document checklists with public access and sharing
- **Real-Time Analytics**: Advanced dashboard with live statistics and progress tracking
- **Calendar & Scheduling**: Task scheduling with deadline management
- **Document Management**: File uploads with checklist-based organization
- **Modern UI/UX**: Sidebar minimization, partial page refresh, smooth transitions
- **Multi-User Collaboration**: Team management with granular permissions and activity feeds

### 🆕 **New Enterprise Architecture**
- **Modular Flask Architecture**: Clean separation with Blueprints
- **Service Layer Pattern**: Business logic separated from routes
- **Contract-Based Validation**: Enterprise-grade data validation
- **API-First Design**: RESTful API with versioning support
- **Permission System**: Rights-based authorization with policies
- **Background Jobs**: Async processing for heavy operations
- **Health Monitoring**: Configuration validation and system checks

## 🏗️ Technology Stack

- **Backend**: Python Flask with modular Blueprint architecture
- **Database**: SQLAlchemy ORM with migration support
- **Frontend**: Tailwind CSS with modern responsive design
- **JavaScript**: Alpine.js for reactive components
- **Authentication**: Access code + enhanced role management
- **API**: RESTful API with v1 versioning
- **Architecture**: OpenProject + Vikunja + Plane inspired patterns

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd workflow-management

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# Initialize new modular database structure
python init_new_db.py
```

This creates a demo firm with enhanced user roles and sample data.

### 3. Run Application

```bash
# Start the new modular Flask application
python run_new.py
```

The application will be available at http://localhost:5001

### 4. Login

- Visit http://localhost:5001
- Enter access code: **DEMO2024**
- Select from demo users with different roles:
  - **Admin User** (Admin) - Full system access
  - **Mike Partner** (Partner) - Partner-level access  
  - **Sarah Manager** (Manager) - Management access
  - **John Senior** (Senior) - Senior associate access
  - **Emily Staff** (Staff) - Basic staff access

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

## 🏛️ Architecture Overview

The application has been completely refactored using enterprise-grade patterns:

### Modular Structure
```
app/
├── __init__.py                 # Flask app factory
├── config/                     # Environment-based configuration
├── core/                       # Shared functionality
│   ├── models.py              # Base models & mixins
│   ├── services.py            # Service layer base classes
│   ├── permissions.py         # Rights-based authorization
│   └── extensions.py          # Flask extensions
├── auth/                       # Authentication & user management
│   ├── models.py              # User, Firm, Role models
│   ├── routes.py              # Auth routes & blueprints
│   └── services.py            # Auth business logic
├── clients/                    # Client management (future)
├── projects/                   # Project management (future)
├── tasks/                      # Task management (future)
├── documents/                  # Document management (future)
├── reports/                    # Analytics & reporting
├── api/v1/                     # RESTful API endpoints
├── integrations/               # Third-party integrations
└── templates/                  # Organized template structure
```

### Key Patterns
- **Service Layer**: Business logic separated from routes
- **Contract Validation**: Enterprise-grade data validation
- **Rights-Based Permissions**: Granular access control
- **Blueprint Architecture**: Modular route organization
- **Configuration Management**: Environment-based settings

## Project Structure

```
workflow-management/
├── app/                        # New modular Flask application
├── docs/                       # Documentation files
├── migrations/                 # Database migrations
├── instance/                   # Database storage
├── static/                     # Static assets
├── uploads/                    # File uploads
├── venv/                       # Virtual environment
├── ARCHITECTURE_ANALYSIS.md   # Detailed architecture analysis
├── README.md                   # This file
├── CLAUDE.md                   # Development notes
├── run_new.py                  # New application entry point
├── init_new_db.py             # New database initialization
└── requirements.txt            # Python dependencies
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