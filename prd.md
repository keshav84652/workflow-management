This document is crafted to be the single source of truth.

---

### **Product Requirements Document (PRD): CPA WorkflowPilot**
**Version:** 1.0
**Date:** 2025-06-06
---

### **1. Executive Summary**

**1.1. Product Vision**
To be the simplest, most intuitive workflow management application for solo CPAs and small accounting firms. WorkflowPilot will serve as the central operating system for managing client work, standardizing processes through templates, and ensuring no deadline is ever missed.

**1.2. Problem Statement**
Small CPA firms are overwhelmed by administrative tasks and the mental load of tracking hundreds of deadlines across dozens of clients. Current solutions are often fragmented (spreadsheets, calendars, notes) or overly complex and expensive enterprise systems. This leads to inefficiency, increased risk of error, and significant stress during peak seasons.

**1.3. Solution Overview**
A standalone, secure web application focused on three core pillars:
1.  **Template-Driven Workflows:** Standardize and replicate best-practice checklists.
2.  **Automated Recurring Tasks:** Reliably generate routine work without manual intervention.
3.  **Centralized Visibility:** Provide a clear, actionable view of all ongoing work and team responsibilities.

**1.4. Target Audience**
*   **Primary:** Individual CPAs managing 5-25 clients.
*   **Secondary:** Small CPA firms (2-10 employees) needing to standardize processes and manage team workloads.

---

### **2. Strategic Goals & Success Metrics**

**2.1. Business Goals**
*   Achieve first live user deployment within a 4-week development sprint.
*   Secure 10 pilot firms to provide feedback on the MVP.
*   Establish a stable, scalable foundation for future feature enhancements (e.g., time tracking, billing).

**2.2. User Goals**
*   **Clarity:** Eliminate anxiety by providing a clear view of all tasks, due dates, and statuses.
*   **Efficiency:** Reduce time spent on administrative setup by at least 50% through the use of templates.
*   **Reliability:** Ensure 100% of recurring tasks are generated on schedule, preventing missed deadlines.

**2.3. Success Metrics (MVP)**
*   **Adoption:** >5 templates created per firm within the first week of use.
*   **Engagement:** >80% of tasks managed through the platform (vs. outside tools).
*   **User Satisfaction:** Net Promoter Score (NPS) of >9 from pilot users on the task management feature.

---

### **3. Personas & User Stories**

**3.1. Persona: Catherine, the Solo CPA**
*   **As Catherine, I want to...** create workflow templates for my core services (e.g., "1040 Tax Season," "Monthly Bookkeeping"), **so that I can** standardize my process and save hours of setup time for each new client engagement.
*   **As Catherine, I want to...** set up complex recurring tasks (e.g., "every last business day of the quarter"), **so that I** never have to manually remember to schedule critical compliance work.
*   **As Catherine, I want to...** see a complete, timestamped log of every action taken on a project, **so that I** have a clear audit trail for client inquiries or internal reviews.

**3.2. Persona: David, the Small Firm Manager**
*   **As David, I want to...** create a project for a new client by applying a pre-built template, **so that I can** delegate tasks to my team members with confidence that our firm's best practices are being followed.
*   **As David, I want to...** view a central dashboard filtered by assignee, **so that I can** assess team workload and reassign tasks to prevent bottlenecks.
*   **As David, I want to...** edit a template and have the option to apply those changes to all active projects using that template, **so that I can** adapt our firm's processes in real-time.

---

### **4. Functional Requirements (MVP)**

**4.1. Authentication & User Management**
*   **Access Code Authentication:**
    *   The system will use a simple, secure access token model. There will be no traditional email/password login for this MVP.
    *   **Admin Interface:** A secure admin area to generate, view, and revoke unique access codes. Each code represents access for one firm.
*   **User Roles (within a firm):**
    *   `Admin`: Manages firm settings, templates, and users.
    *   `Member`: Manages assigned projects and tasks.
*   **Multi-User Firm Structure:** Users are associated with a single firm account, allowing for team collaboration.

**4.2. Template Management (Critical Priority)**
*   Full CRUD (Create, Read, Update, Delete) functionality for workflow templates.
*   A template consists of an ordered checklist of `Template Tasks`.
*   Each `Template Task` includes a title, description, and default assignee (optional).

**4.3. Project Management**
*   **Project Creation:** Projects must be created from an existing template. The creation process involves selecting a template, assigning a client name, and setting a project start date. This will auto-generate all tasks from the template.
*   **Project Dashboard:** A central view of all active projects, filterable by client and status (`Active`, `Completed`, `Archived`).

**4.4. Task Management**
*   **Task Attributes:** Title, Description, Due Date, Assignee, Status (`Not Started`, `In Progress`, `Needs Review`, `Completed`).
*   Tasks exist within a project and are initially generated from a template.
*   Users can update the status, assignee, and due date of any task.

**4.5. Recurring Task Engine (Critical Priority)**
*   **Independent Generation:** Recurring tasks are defined within templates and generate new instances based on their schedule, **regardless of whether the previous instance was completed**. This is crucial for compliance workflows (e.g., a new "Pay Sales Tax" task must be created each month, even if last month's is still open).
*   **Recurrence Patterns:** Support for daily, weekly, monthly, quarterly, and annual recurrences, with specific rules (e.g., "On the 15th of the month," "On the last business day of the quarter").
*   **Resilient Spawning:** If the application is not accessed for a period, upon next use it must retroactively create all missed recurring tasks and flag them as "Overdue."

**4.6. Activity Log**
*   An immutable, timestamped log must be automatically recorded for all significant events.
*   **Tracked Events:** Project/Task creation, status changes, due date changes, assignee changes.
*   Each log entry must record the action, the user who performed it, and the timestamp.
*   The activity log must be viewable at both the project and individual task level.

---

### **5. Non-Functional Requirements**

*   **Technology Stack:** Python/Flask backend, SQLite database with SQLAlchemy, Bootstrap 5 frontend.
*   **Performance:** All dashboard and project views must load in under 2 seconds for a firm with 5,000 active tasks.
*   **Security:** Access tokens must be securely stored. The SQLite database file should be placed in a non-web-accessible directory (`instance/`).
*   **Usability:** The interface must be clean, intuitive, and responsive for both desktop and mobile web browsers.

---

### **6. Out of Scope for MVP**

To ensure rapid delivery, the following features are explicitly **NOT** included in the MVP:
*   Third-party integrations (Email, Calendar, Document Storage, etc.).
*   Time tracking, invoicing, and billing.
*   Advanced analytics and external reporting dashboards.
*   Client-facing portals or logins.
*   File uploads and document management.

---

### **7. Data Model (Proposed SQLAlchemy Schema)**

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Firm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    # A single access code grants access to the entire firm for simplicity in the MVP
    access_code = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    users = db.relationship('User', backref='firm', lazy=True)
    templates = db.relationship('Template', backref='firm', lazy=True)
    projects = db.relationship('Project', backref='firm', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Member')  # 'Admin' or 'Member'
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    tasks = db.relationship('Task', backref='assignee', lazy=True)

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    template_tasks = db.relationship('TemplateTask', backref='template', lazy=True, cascade="all, delete-orphan")

class TemplateTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    # Recurrence rule stored as a string, e.g., "monthly:15" or "quarterly:last_biz_day"
    recurrence_rule = db.Column(db.String(100)) 
    template_id = db.Column(db.Integer, db.ForeignKey('template.id'), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='Active', nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    template_origin_id = db.Column(db.Integer, db.ForeignKey('template.id'))
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Not Started', nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # If this task was generated from a recurring rule, we link it back
    template_task_origin_id = db.Column(db.Integer, db.ForeignKey('template_task.id'))

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
```