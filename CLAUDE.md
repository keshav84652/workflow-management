# CPA WorkflowPilot - Claude Development Notes

## Project Overview
This is a comprehensive CPA Workflow Management MVP application built with Flask, SQLite, and Bootstrap 5. The application provides template-driven workflows, client management, task tracking, and team collaboration features specifically designed for CPA firms.

## Development Commands
- **Run Application**: `python app.py`
- **Initialize Database**: `python init_db.py`
- **Test Environment**: Run `python app.py` and visit `http://localhost:5000`
- **Login**: Use access code `DEMO2024` to access the demo firm

## Git Workflow
- Regular commits are made throughout development
- Each major feature gets its own commit with descriptive messages
- All commits include Claude Code attribution in the footer

## Key Features Implemented
- ✅ User authentication with access codes and user selection
- ✅ Client management with contact information and entity types
- ✅ Project management with template-driven workflows
- ✅ Task management with independent tasks support
- ✅ Advanced dashboard with KPIs, charts, and analytics
- ✅ Calendar view for task scheduling and deadlines
- ✅ Comprehensive filtering and search capabilities
- ✅ Activity logging and change tracking
- ✅ Professional CPA-focused UI/UX design

## Current Development Session Tasks
When working on this project, systematically complete all pending tasks:
1. Always check todo status first with TodoRead
2. Work on high-priority feedback issues immediately
3. Implement remaining features in priority order
4. Make git commits after each major feature completion
5. Update todo status as work progresses
6. Test features thoroughly before marking complete

## Database Models
- **Firm**: Organization/company entity
- **User**: Team members with roles (Admin/Member)
- **Client**: Client entities with contact info and entity types
- **Project**: Work engagements linked to clients and templates
- **Task**: Work items (can be project-linked or independent)
- **Template**: Reusable workflow definitions
- **ActivityLog**: Change tracking and audit trail

## Special Implementation Notes
- Tasks can be independent (no project) or project-linked
- All queries include firm_id filtering for multi-tenancy
- Overdue detection uses task.is_overdue property
- Client names shown prominently using project.client_name property
- Team workload includes both project and independent tasks
- Calendar view supports both task types with proper navigation

## Authentication Flow
1. User enters firm access code
2. System shows user selection screen
3. User selects their profile
4. Full application access granted with session management

## Development Standards
- Use Bootstrap 5 for all UI components
- Follow professional CPA color scheme (navy, blue, green)
- Implement proper error handling and flash messages
- Include activity logging for all major actions
- Support both project and independent task workflows
- Maintain responsive design for mobile/tablet use