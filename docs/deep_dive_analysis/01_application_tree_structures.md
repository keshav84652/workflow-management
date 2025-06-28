# Competitor Overview & Application Tree Structures

This document provides a high-level overview of the analyzed applications, including their technology stacks and pruned directory tree structures. The goal is to understand the organizational patterns of each codebase.

---

### **Focalboard**

*   **Description**: A simple and flexible project management tool, often seen as a self-hosted alternative to Trello, Notion, and Asana.
*   **Backend**: Go
*   **Frontend**: React
*   **Key Architectural Pattern**: A traditional monolithic application with a Go backend serving a REST API and a React single-page application (SPA). Real-time updates are handled via WebSockets.

**Pruned Directory Tree:**

```
.
├── server/
│   ├── api/          # API handlers (the "controller" layer)
│   ├── app/          # Core application logic and services
│   ├── model/        # Data structures (Block, Card, Board, etc.)
│   ├── services/     # Business logic services (permissions, notifications)
│   └── store/        # Database abstraction layer (SQL queries)
│       └── sqlstore/
│           └── migrations/
└── webapp/
    └── src/
        ├── blocks/       # Model definitions for the frontend
        ├── components/   # Reusable React components (Kanban, Table, etc.)
        │   ├── kanban/
        │   ├── table/
        │   ├── gallery/
        │   └── calendar/
        ├── pages/        # Top-level page components (BoardPage, LoginPage)
        ├── properties/   # Components for rendering different data types (date, person, etc.)
        └── store/        # Redux state management
```

---

### **OpenProject**

*   **Description**: A comprehensive, feature-rich, enterprise-grade project management tool.
*   **Backend**: Ruby on Rails
*   **Frontend**: Angular
*   **Key Architectural Pattern**: A classic, mature Ruby on Rails monolith. It is highly modular, using a system similar to Rails Engines (`modules/`) to encapsulate core features like costs, webhooks, and meetings. This provides good separation of concerns within the monolith.

**Pruned Directory Tree:**

```
.
├── app/
│   ├── assets/
│   ├── components/     # ViewComponents (server-side rendered UI)
│   ├── controllers/    # Ruby on Rails controllers
│   ├── models/         # ActiveRecord models (WorkPackage, Project, User, etc.)
│   ├── services/       # Service objects for complex business logic
│   └── workers/        # Background jobs
├── frontend/           # Angular frontend source
│   └── src/
│       └── app/
│           ├── core/   # Core services and modules
│           ├── features/ # Feature-specific modules (BIM, Boards, Work Packages)
│           │   ├── boards/
│           │   ├── team-planner/
│           │   └── work-packages/
│           │       ├── components/
│           │       │   ├── wp-card-view/
│           │       │   ├── wp-gantt-chart/
│           │       │   └── wp-table/
│           │       └──
│           └── shared/ # Shared components and directives
├── modules/            # Core features packaged as plugins/engines
│   ├── boards/
│   ├── calendar/
│   ├── costs/
│   ├── documents/
│   ├── gantt/
│   ├── meetings/
│   └── webhooks/
└── db/
    └── migrate/        # Database migrations
```

---

### **Plane**

*   **Description**: A modern, feature-rich project management tool positioned as an open-source alternative to JIRA.
*   **Backend**: Django (Python)
*   **Frontend**: Next.js (React)
*   **Key Architectural Pattern**: A decoupled monorepo containing multiple specialized applications. It uses a Django REST Framework backend, a Next.js frontend, a separate real-time server for collaborative editing, and a distinct admin interface.

**Pruned Directory Tree:**

```
.
├── apiserver/                # Django Backend
│   └── plane/
│       ├── app/              # Core application logic
│       │   ├── permissions/
│       │   ├── serializers/
│       │   ├── views/
│       │   └── urls/
│       ├── bgtasks/          # Celery background tasks (notifications, etc.)
│       ├── db/
│       │   ├── models/       # Django ORM models (Issue, Project, Cycle, etc.)
│       │   └── migrations/
│       └── middleware/
├── web/                      # Next.js Frontend
│   ├── app/                  # Next.js App Router structure
│   │   └── [workspaceSlug]/
│   │       ├── (projects)/   # Main project/issue views
│   │       └── (settings)/   # Workspace/Project settings
│   ├── ce/                   # Community Edition components
│   ├── core/                 # Core components, hooks, and stores
│   ├── ee/                   # Enterprise Edition components
│   └── services/             # Frontend services to interact with the API
├── live/                     # Hocuspocus (Node.js) server for real-time collaboration
│   └── src/
│       └── core/
│           ├── extensions/
│           └── lib/
├── packages/                 # Shared libraries within the monorepo
│   ├── constants/
│   ├── types/
│   ├── ui/
│   └── services/
└── admin/                    # Next.js Admin Panel
    └── app/
```

---

### **Vikunja**

*   **Description**: A modern and lightweight to-do list application that can be scaled for team project management.
*   **Backend**: Go
*   **Frontend**: Vue.js
*   **Key Architectural Pattern**: A traditional monolithic application, similar to Focalboard. It uses a Go backend API and a Vue.js frontend. The structure is clean and follows RESTful principles.

**Pruned Directory Tree:**

```
.
├── frontend/
│   └── src/
│       ├── components/ # Reusable Vue components
│       │   ├── project/
│       │   │   └── views/
│       │   │       ├── ProjectGantt.vue
│       │   │       ├── ProjectKanban.vue
│   │   │   │       └── ProjectTable.vue
│       │   └── tasks/
│       ├── services/   # Frontend services for API interaction
│       ├── stores/     # Pinia state management
│       └── views/      # Top-level page components
└── pkg/                # Go Backend
    ├── cmd/            # CLI commands
    ├── db/             # Database connection and fixtures
    ├── models/         # Core data models (Task, Project, User, etc.)
    ├── modules/        # Feature modules (auth, migration, etc.)
    │   ├── auth/
    │   │   ├── ldap/
    │   │   └── openid/
    │   └── migration/
    ├── notifications/  # Email notification system
    ├── routes/         # API routing and handlers
    └── user/           # User management logic
```
