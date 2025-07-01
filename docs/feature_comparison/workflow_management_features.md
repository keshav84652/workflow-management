# Workflow Management Features

Based on the README.md and source code analysis, the Workflow Management application has the following features:

### High-Level Features

*   **Template-Driven Workflows**: Sophisticated workflow automation with conditional logic.
*   **Role-Based Permissions**: Admin and Member roles.
*   **Advanced Project Management**: Sequential task dependencies and project health tracking.
*   **Comprehensive Task Management**: Kanban boards, time tracking, real-time updates.
*   **Client Portal Integration**: Document checklists with public access and sharing.
*   **Real-Time Analytics**: Advanced dashboard with live statistics and progress tracking.
*   **Calendar & Scheduling**: Task scheduling with deadline management.
*   **Document Management**: File uploads with checklist-based organization.
*   **Modern UI/UX**: Sidebar minimization, partial page refresh, smooth transitions.
*   **Multi-User Collaboration**: Team management with granular permissions and activity feeds.
*   **Recurring Task Engine**: Automatically generates recurring tasks based on rules.

### Detailed Features

*   **Projects**:
    *   Create projects from templates.
    *   Get, update, and delete projects.
    *   Move projects between different statuses (Kanban-style).
    *   Track project health and progress.
    *   Projects are associated with a client.
    *   Projects have a start date, due date, and priority.
    *   Projects can have sequential task dependencies.
*   **Tasks**:
    *   Create, get, update, and delete tasks.
    *   Tasks can be part of a project or standalone.
    *   Tasks have a title, description, due date, priority, and estimated hours.
    *   Tasks can be assigned to users.
    *   Tasks can have comments.
    *   Tasks can be recurring.
    *   Task status can be updated (e.g., "Not Started", "In Progress", "Completed").
    *   Tasks can have dependencies on other tasks.
*   **Clients**:
    *   Create, get, update, and delete clients.
    *   Clients have a name, entity type, email, phone, address, and contact person.
    *   Clients can be associated with multiple projects.
