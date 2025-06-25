# CPA WorkflowPilot - Professional Edition

A comprehensive workflow management application designed specifically for CPA firms, built with enterprise-grade architecture patterns inspired by leading open-source project management tools.

## 🚀 Features

### ✅ **Complete Feature Set (All Implemented)**
- **Template-Driven Workflows**: Sophisticated workflow automation with conditional logic
- **Role-Based Permissions**: Admin and Member roles (additional roles planned for future releases)
- **Advanced Project Management**: Sequential task dependencies and project health tracking
- **Comprehensive Task Management**: Kanban boards, time tracking, real-time updates
- **Client Portal Integration**: Document checklists with public access and sharing
- **Real-Time Analytics**: Advanced dashboard with live statistics and progress tracking
- **Calendar & Scheduling**: Task scheduling with deadline management
- **Document Management**: File uploads with checklist-based organization
- **Modern UI/UX**: Sidebar minimization, partial page refresh, smooth transitions
- **Multi-User Collaboration**: Team management with granular permissions and activity feeds

### 🆕 **Enterprise Architecture (Updated 2024)**
- **Complete Service Layer**: AuthService, DocumentService, AdminService, DashboardService, ProjectService, TaskService, ClientService
- **Modular Flask Architecture**: Clean separation with domain-specific Blueprints
- **Business Logic Separation**: All business operations isolated in service classes
- **Consistent Error Handling**: Standardized return patterns across all services
- **Type Safety**: Comprehensive type hints throughout the codebase
- **Professional Code Quality**: Cleaned debug artifacts and consistent documentation
- **Scalable Architecture**: Ready for enterprise deployment and team development

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

The application features a modern, maintainable architecture with complete service layer separation:

### Current Project Structure
```
workflow-management/
├── app.py                      # Flask application entry point
├── config.py                   # Environment-based configuration
├── core.py                     # Database extensions and utilities
├── models/                     # Organized data models
│   ├── auth.py                # User, Firm, ActivityLog models
│   ├── projects.py            # Project, Template, WorkType models
│   ├── tasks.py               # Task, TaskComment models
│   ├── clients.py             # Client, Contact models
│   ├── documents.py           # Document and checklist models
│   └── misc.py                # Utility models
├── services/                   # Complete business logic layer
│   ├── auth_service.py        # Authentication & session management
│   ├── admin_service.py       # Administrative operations
│   ├── dashboard_service.py   # Dashboard data aggregation
│   ├── document_service.py    # Document & checklist operations
│   ├── project_service.py     # Project management logic
│   ├── task_service.py        # Task operations & workflows
│   └── client_service.py      # Client management
├── blueprints/                 # Route handlers by domain
│   ├── auth.py                # Authentication routes
│   ├── admin.py               # Admin panel routes
│   ├── dashboard.py           # Dashboard routes
│   ├── projects.py            # Project management routes
│   ├── tasks.py               # Task management routes
│   ├── clients.py             # Client management routes
│   ├── documents.py           # Document routes
│   └── [other blueprints]     # Additional feature routes
├── templates/                  # Jinja2 templates by domain
├── static/                     # CSS, JS, images
└── instance/                   # Database and uploads
```

### Service Layer Architecture
The application implements a complete service layer pattern that separates business logic from HTTP request handling:

#### **AuthService**
- User authentication and session management
- Firm access code validation
- Demo access tracking
- Session security and persistence

#### **DocumentService** 
- Document checklist creation and management
- File upload validation and processing
- Client access control for document sharing
- Checklist item operations (CRUD)

#### **AdminService**
- System administration and firm management
- Template creation and management
- User management and role assignment
- Access code generation

#### **DashboardService**
- Dashboard data aggregation and analytics
- Project progress calculations
- Team workload analysis
- Deadline and overdue task tracking

#### **ProjectService & TaskService**
- Project lifecycle management
- Task workflow automation
- Template-based project creation
- Kanban board operations

#### **ClientService**
- Client and contact management
- Client-project relationships
- Client communication tracking

### Key Architecture Patterns

#### **Service Layer Pattern**
- Complete separation of business logic from HTTP request handling
- Consistent error handling and return patterns across all services
- Type-safe method signatures with comprehensive documentation
- Testable business operations isolated from web framework dependencies

#### **Domain-Driven Organization**
- Models organized by business domain (auth, projects, tasks, clients, documents)
- Blueprints aligned with business capabilities
- Service classes focused on specific business areas
- Clear boundaries between different application concerns

#### **Data Access Patterns**
- Repository-like methods in service classes for data access
- Firm-level security enforced at the service layer
- Consistent session management and user context handling
- Optimized database queries with proper error handling

#### **Error Handling & Validation**
- Standardized error response format across all services
- Input validation at service layer boundaries
- Comprehensive exception handling with rollback support
- User-friendly error messages for client consumption

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