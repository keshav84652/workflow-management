
### **[PART 1 Of 3] Deep Dive: The Work & Task Management Engine**

#### **1. Introduction: The Core User Experience**

The heart of the CPA WorkflowPilot platform is its **Work Engine**. This is not simply a to-do list; it is a visual, interactive, and context-rich environment where all active client engagements are managed. The primary goal is to provide immediate clarity on three questions: *What is being worked on?*, *Who is working on it?*, and *What is its current status?*.

The engine is built around two fundamental views: the high-level **Kanban Work View** for firm-wide visibility and the granular **Work Item View** for deep, project-specific management.

---

#### **2. The Kanban Work View: The Firm's Dashboard**

This is the main screen users see when they navigate to "Work." It provides a strategic overview of the firm's entire workload, designed for quick assessment and management by exception.

**2.1. Core Purpose**
*   **Visual Workflow Management:** To transform a list of projects into a visual flow, allowing managers to instantly identify bottlenecks and resource allocation issues.
*   **High-Level Status Tracking:** To see the status of every single work item without needing to click into each one.

**2.2. UI Components & Functionality**

*   **Board Columns (Work Statuses):**
    *   The columns on the board are not hardcoded. They are dynamically generated from the firm's custom-defined **Work Statuses** (e.g., "Planned," "Awaiting Info," "In Progress," "In Review," "Completed").
    *   The column headers display the status name and a count of the Work Items currently in that column.
    *   **Logic:** The system queries all `WorkItem` records and groups them by their `status_id`, rendering a column for each status that contains at least one work item (or all defined statuses, depending on a user preference).

*   **Work Cards:**
    *   Each card on the board represents a single `WorkItem` record.
    *   **Displayed Information on Card:**
        *   **Work Title:** (e.g., "Monthly Bookkeeping - May 2025")
        *   **Client Name:** (e.g., "ABC Corporation")
        *   **Assignee(s):** Avatars of the primary users assigned to the work.
        *   **Due Date:** Displayed prominently. It should be color-coded (e.g., red) if the date is in the past.
        *   **Task Progress Bar:** A visual bar showing the ratio of completed tasks to total tasks (e.g., `[|||||---] 5/8`). This is calculated by `COUNT(Tasks where status.is_terminal = true) / COUNT(All Tasks)` for that `work_id`.
        *   **Budget Progress Bar:** A visual bar comparing actual time tracked against the budgeted hours.

**2.3. Core Interactions**

*   **Drag-and-Drop Status Change:**
    *   Users can click and drag a Work Card from one column to another.
    *   **Logic:** When a card is dropped into a new column, the system updates the `status_id` on the corresponding `WorkItem` record. This action immediately triggers the creation of a new `ActivityLog` entry: `"[User Name] changed work status from [Old Status] to [New Status] at [Timestamp]."`.

*   **Advanced Filtering:**
    *   A persistent filter bar is crucial. It allows users to create complex, stacked queries.
    *   **Example Filter Stack:** `Assignee = "David"` AND `Due Date = "This Week"` AND `Client = "ABC Corp"`.
    *   **Logic:** Each filter adds a `WHERE` clause to the database query that populates the Kanban board. The UI must clearly show which filters are currently active.

---

#### **3. The Work Item View: The Project Deep Dive**

Clicking on any Work Card on the Kanban board navigates the user to the detailed Work Item view. This is where the actual work gets done. It is structured with three essential tabs.

**3.1. Tab 1: Timeline**
This is the immutable, unchangeable history of everything that has ever happened to this piece of work. It is the single source of truth.

*   **Functionality:**
    *   Displays a reverse chronological list of all `ActivityLog` entries associated with this `work_id` and all of its child `task_id`s.
    *   **Event Types Displayed:**
        *   **Creation:** "Work created by David from template '1040 Tax Return'."
        *   **Status Changes:** "Catherine changed task 'Prepare Return' status to 'Completed'."
        *   **Comments:** User avatars are shown next to their comments, creating a threaded conversation within the context of the work.
        *   **Client Interactions:** "Email sent to client requesting documents." "Client uploaded 'Bank Statements.pdf'."
        *   **Assignments:** "David assigned task 'Review Return' to Catherine."
    *   Users can add new notes/comments here, and `@mention` colleagues to pull them into the conversation and add the item to their Triage.

**3.2. Tab 2: Tasks (The Checklist)**
This is the most interactive tab, detailing the step-by-step execution of the work.

*   **Task Structure & Hierarchy:**
    *   **Sections:** Tasks are grouped into logical sections (e.g., "1. Data Collection," "2. Preparation," "3. Review"). These are defined in the source Template.
    *   **Tasks:** Each line item is a `Task` record.
    *   **Subtasks:** Tasks can be nested under a parent task. The UI must visually indent them. A parent task's progress bar can reflect the completion of its subtasks.
        *   **Logic:** A `parent_id` on the `Task` table links a subtask to its parent.

*   **Task Dependencies:**
    *   This is a critical workflow control feature, implementing a "Finish-to-Start" relationship.
    *   **UI Indication:** A successor task that is blocked by an incomplete predecessor task should be visually distinct (e.g., grayed out, with a "lock" icon). The user should not be able to change its status to "In Progress".
    *   **Logic:** The system checks the `TaskDependency` table. Before allowing a status change on a task, it queries to see if any of its `predecessor_id` tasks have a status where `is_terminal = false`. If so, the action is blocked. When a predecessor is completed, the system automatically updates the successor's state to "unblocked" and creates a Timeline entry: `"Task 'Review Return' is now unblocked."`. This may also trigger a notification in the assignee's Triage.

*   **Automators:**
    *   Rules defined in the template execute here.
    *   **Example:** "When all tasks in section 'Preparation' are complete, change the assignee of task 'Review Return' to the user with the 'Manager' role."
    *   **Logic:** These are event-driven triggers. After every task status change, the system checks if the conditions for any relevant automators on that `WorkItem` have been met and executes the corresponding action.

**3.3. Tab 3: Details**
This tab holds the high-level metadata and settings for the Work Item.

*   **Functionality:**
    *   Displays and allows editing of the core `WorkItem` attributes: Title, Client, Assignee, Start/Due Dates.
    *   **Budget vs. Actuals:** A detailed breakdown of the budget.
        *   **Source:** The initial budget is set from the Template.
        *   **Logic:** The view displays budgeted hours/fees vs. the sum of all time entries logged against this Work Item and its tasks. The variance is calculated and displayed, often with color-coding (green for under-budget, red for over-budget).

---

#### **4. Data Model Schema for the Work Engine**

This SQL schema outlines the database structure required to power the features described above.

```sql
-- Work Statuses (drives Kanban columns and task statuses)
CREATE TABLE TaskStatus (
    status_id INT PRIMARY KEY,
    firm_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,          -- e.g., "In Progress", "Needs Review"
    color VARCHAR(7) NOT NULL,          -- e.g., "#FFC107"
    position INT NOT NULL,              -- Order of columns on the Kanban board
    is_terminal BOOLEAN DEFAULT FALSE,  -- True for "Completed", "Archived", etc.
    is_default BOOLEAN DEFAULT FALSE,   -- The status for newly created tasks
    FOREIGN KEY (firm_id) REFERENCES Firm(firm_id)
);

-- The main project or engagement container
CREATE TABLE WorkItem (
    work_id INT PRIMARY KEY,
    firm_id INT NOT NULL,
    client_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    assignee_id INT,                    -- Primary owner of the work item
    status_id INT NOT NULL,             -- Foreign key to TaskStatus, for the Kanban view
    start_date DATE,
    due_date DATE,
    budget_hours DECIMAL(10, 2),
    template_origin_id INT,             -- Link back to the template it was created from
    FOREIGN KEY (firm_id) REFERENCES Firm(firm_id),
    FOREIGN KEY (client_id) REFERENCES Client(client_id),
    FOREIGN KEY (status_id) REFERENCES TaskStatus(status_id)
);

-- Individual checklist items
CREATE TABLE Task (
    task_id INT PRIMARY KEY,
    work_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id INT,
    status_id INT NOT NULL,             -- Foreign key to TaskStatus
    due_date DATE,
    parent_task_id INT NULL,            -- Self-referencing key for subtasks
    FOREIGN KEY (work_id) REFERENCES WorkItem(work_id) ON DELETE CASCADE,
    FOREIGN KEY (assignee_id) REFERENCES User(user_id),
    FOREIGN KEY (status_id) REFERENCES TaskStatus(status_id),
    FOREIGN KEY (parent_task_id) REFERENCES Task(task_id)
);

-- Defines the blocking relationship between tasks
CREATE TABLE TaskDependency (
    dependency_id INT PRIMARY KEY,
    predecessor_task_id INT NOT NULL,   -- The task that must be finished first
    successor_task_id INT NOT NULL,     -- The task that is blocked
    FOREIGN KEY (predecessor_task_id) REFERENCES Task(task_id) ON DELETE CASCADE,
    FOREIGN KEY (successor_task_id) REFERENCES Task(task_id) ON DELETE CASCADE
);
```

### **[FILE 2 of 3] Deep Dive: The Template and Automation Engine**

#### **1. Introduction: The Engine of Efficiency**

The Template and Automation Engine is the most critical component for driving efficiency and standardization within a CPA firm. Its purpose is to transform the firm's intellectual property—its unique processes and best practices—into digital, repeatable, and automated assets.

This engine is responsible for two primary functions:
1.  **Standardization:** Allowing a firm to define a master "recipe" for any given service (e.g., a 1040 Tax Return, a Monthly Bookkeeping Close, a Client Onboarding).
2.  **Automation:** Using these recipes to automatically create and manage work, eliminating thousands of manual clicks and reducing the risk of human error.

This module is the direct source of the `WorkItem`, `Task`, and `TaskDependency` records that are visualized and managed by the **Work & Task Management Engine (described in File 1)**.

---

#### **2. The Anatomy of a Template**

A **Template** is far more than a simple checklist. It is a complex, multi-layered entity that serves as a blueprint for a `WorkItem`.

**2.1. Core Template Attributes**
*   **Template Name:** A human-readable name (e.g., "Annual Corporate Tax Return (1120-S)").
*   **Description:** A brief explanation of the template's purpose.
*   **Work Type:** A category for the work (e.g., "Tax," "Bookkeeping," "Advisory"). This is used for filtering and reporting.
*   **Recurrence Schedule:** The rule for automation. This is a structured string that the automation engine can parse, such as:
    *   `monthly:15` (Creates work on the 15th of every month)
    *   `quarterly:last_biz_day` (Creates work on the last business day of March, June, September, December)
    *   `annually:01-15` (Creates work every year on January 15th)
    *   If null, the template is not automatically recurring.

**2.2. Template Components**

A Template is composed of several key related entities:

*   **Template Task Sections:** Logical groupings for tasks (e.g., "Preparation," "Review," "Filing"). This is purely for visual organization within the UI.

*   **Template Tasks:** The individual steps of the workflow. Each `TemplateTask` is a rich object with pre-defined attributes that will be used to create the real `Task` when the template is applied:
    *   **Title & Description:** The standard text for the task.
    *   **Relative Due Date:** This is the core of date automation. It is NOT a fixed date but a rule relative to the `WorkItem`'s main start or due date. Examples:
        *   `start_date + 5 days`
        *   `due_date - 10 days`
    *   **Default Assignee (Role-Based):** The task is assigned to a *role* (e.g., "Bookkeeper," "Manager"), not a specific person. When the template is applied, the system assigns the task to the actual user who holds that role for the specific client.
    *   **Dependencies:** Defines which other `TemplateTask`(s) must be completed before this one can begin.

*   **Automators:** "If-This-Then-That" rules that are attached to the template and copied to every Work Item created from it. (See Section 5 for details).

---

#### **3. The Instantiation Process: Creating Work from a Template**

This is the process where a `Template` (the abstract blueprint) becomes a `WorkItem` (a concrete, live project).

**3.1. Trigger**
A user clicks "Create Work," selects a `Template`, a `Client`, and enters the overall `start_date` and `due_date` for the engagement.

**3.2. System Logic (A Step-by-Step Breakdown)**

1.  **Create Work Item:** The system creates a new record in the `WorkItem` table using the provided title, client, dates, and assignee. It links it back to the `template_origin_id`.

2.  **Instantiate Tasks:** The system iterates through every `TemplateTask` associated with the chosen `Template`. For each `TemplateTask`, it performs the following:
    a.  **Create Task Record:** A new record is created in the `Task` table.
    b.  **Calculate Absolute Due Date:** The system reads the `relative_due_date` rule (e.g., `start_date + 5 days`) from the `TemplateTask` and applies it to the `WorkItem`'s `start_date` to calculate and store a concrete `due_date` on the new `Task` record.
    c.  **Resolve Assignee:** The system reads the `default_assignee_role` (e.g., "Manager"). It then looks up which `User` has that role within the firm (or specifically for that client) and populates the `assignee_id` on the new `Task` record.
    d.  **Set Initial Status:** The task's `status_id` is set to the firm's default status (the one where `is_default = true`).

3.  **Instantiate Dependencies:** After all `Task` records have been created, the system iterates through the dependency definitions in the template. For each defined relationship, it creates a new record in the `TaskDependency` table, linking the `predecessor_task_id` to the `successor_task_id`.

4.  **Log Activity:** A single entry is added to the `ActivityLog` for the new `WorkItem`: `"[User Name] created work from template '[Template Name]'."`

---

#### **4. The Recurring Work Automation Engine**

This engine runs in the background to ensure scheduled work is never missed.

**4.1. Trigger**
A system-level scheduled job (e.g., a cron job or a scheduled task) that runs once per day, typically at midnight UTC.

**4.2. System Logic**

1.  **Fetch Recurring Templates:** The job queries the `Template` table for all records where `recurrence_rule` is not null.

2.  **Evaluate Rules:** For each template, the job's logic parses the `recurrence_rule` string and compares it to the current date.
    *   **Example:** If the rule is `quarterly:last_biz_day` and today is June 30, 2025, the condition is met.

3.  **Create Work:** If the rule's condition is met, the system triggers the full **Instantiation Process** described in Section 3. The `start_date` and `due_date` for the new `WorkItem` are calculated based on the recurrence period (e.g., for a monthly job, the start is the 1st of the month and the due date is the last day).

4.  **Prevent Duplicates:** After successfully creating the `WorkItem`, the system updates a `last_run_date` field on the `Template` record to the current date to ensure it doesn't run again tomorrow.

---

#### **5. In-Workflow Automators: The "If-This-Then-That" Engine**

Automators are rules that trigger actions *during* a project's lifecycle, further reducing manual intervention.

**5.1. The Automator Structure**
Each automator is stored as a record with three parts: a **Trigger**, a **Condition**, and an **Action**.
*   **Trigger:** The event that causes the system to evaluate the rule. (e.g., "Task Status is Updated").
*   **Condition:** The specific criteria that must be true for the action to fire. (e.g., "New Status is 'Completed' AND Task Section is 'Prep'").
*   **Action:** The operation the system performs. (e.g., "Change Work Item Status to 'In Review'").

**5.2. Implementation Logic**
The system uses an event-listener pattern. After a user performs an action (like changing a task's status), the application's business logic layer fires an event. The Automator Engine "listens" for these events.

1.  **Event Fired:** User completes the last task in the "Prep" section. The event `task.status.updated` is fired.
2.  **Check for Automators:** The engine queries for any `AutomatorRule` records linked to the parent `WorkItem` that listen for this trigger.
3.  **Evaluate Condition:** It finds a rule: `WHEN task.status.updated IF all_tasks_in_section('Prep').status == 'Completed' THEN change_work_status('In Review')`. The condition is evaluated and returns `true`.
4.  **Execute Action:** The engine performs the action, changing the `WorkItem`'s status and creating a corresponding `ActivityLog` entry: `"Automator changed work status to 'In Review'."`

---

#### **6. Database Schema for the Template & Automation Engine**

```sql
-- Template blueprint for creating work
CREATE TABLE Template (
    template_id INT PRIMARY KEY,
    firm_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    recurrence_rule VARCHAR(255) NULL, -- e.g., "monthly:1st", "annually:04-15"
    last_run_date DATE NULL,           -- Used by the scheduler to prevent duplicates
    FOREIGN KEY (firm_id) REFERENCES Firm(firm_id)
);

-- Individual tasks within a template
CREATE TABLE TemplateTask (
    template_task_id INT PRIMARY KEY,
    template_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    section_name VARCHAR(100),            -- For visual grouping, e.g., "Preparation"
    due_date_rule VARCHAR(255),           -- e.g., "start_date + 5", "due_date - 10"
    default_assignee_role VARCHAR(100),   -- e.g., "Bookkeeper", "Manager"
    predecessor_template_task_id INT NULL, -- Dependency defined at the template level
    FOREIGN KEY (template_id) REFERENCES Template(template_id) ON DELETE CASCADE,
    FOREIGN KEY (predecessor_template_task_id) REFERENCES TemplateTask(template_task_id)
);

-- Rules for in-workflow automation
CREATE TABLE AutomatorRule (
    rule_id INT PRIMARY KEY,
    template_id INT NOT NULL,
    trigger_event VARCHAR(100) NOT NULL,    -- e.g., "task.status.updated"
    condition_logic TEXT NOT NULL,          -- e.g., "task.status == 'Completed' AND section == 'Prep'"
    action_type VARCHAR(100) NOT NULL,      -- e.g., "CHANGE_WORK_STATUS", "CHANGE_ASSIGNEE"
    action_params TEXT NOT NULL,            -- e.g., "{ 'new_status': 'In Review' }" (as JSON)
    FOREIGN KEY (template_id) REFERENCES Template(template_id) ON DELETE CASCADE
);
```

---

### **[FILE 3 of 3] Deep Dive: The Triage and Communication Engine**

#### **1. Introduction: The Central Nervous System**

The Triage and Communication Engine is arguably the most transformative module for a CPA firm. Traditional firms run on fragmented email inboxes, where critical information gets lost, context is siloed, and client requests become untraceable. This module fundamentally changes that paradigm.

**Core Philosophy:** Communication is not a separate activity; it is an integral part of the work itself. Every email, comment, and client request is an event to be processed, assigned, and archived against the relevant work, creating an unshakeable audit trail. The goal is to make the user's Triage the *only* inbox they need to manage.

This engine feeds into and interacts directly with the **Work & Task Management Engine (File 1)** and the **Template & Automation Engine (File 2)**.

---

#### **2. The Triage View: A Unified & Actionable Inbox**

The Triage is a user-specific view that consolidates every item demanding their attention into a single, manageable list.

**2.1. Sources of Triage Items**

The Triage is populated from three distinct sources, each creating a `TriageItem` record in the database:

1.  **External Communication (Emails):**
    *   When a user connects their email account (e.g., Gmail, Office 365), incoming emails appear as items in their Triage.
    *   **Logic:** The system polls the user's email server via API. It identifies which emails are from known `Client` or `Contact` records and may highlight them visually.

2.  **Internal Communication (@Mentions):**
    *   When a user types `@David` in a comment on a Work Item or Task timeline, a Triage item is created for David.
    *   **Content:** The Triage item contains the comment text and a direct link back to the exact Work Item or Task where the comment was made. This provides immediate context.

3.  **System Notifications:**
    *   The system itself generates Triage items to inform users of important automated events.
    *   **Examples:**
        *   "Your task 'Review Return' is now unblocked because Catherine completed 'Prepare Return'."
        *   "A new work item 'Monthly Bookkeeping - August 2025' has been created for you by the recurring work schedule."
        *   "A client has commented on your request for 'Bank Statements'."

**2.2. The Triage Workflow: Processing Each Item**

Every item in the Triage must be actioned. The UI provides a set of tools to "process" each item, ensuring nothing is forgotten.

*   **Action 1: Clear**
    *   **Purpose:** For FYI items that require no further action.
    *   **Logic:** Marks the `TriageItem` status as "Cleared" and removes it from the main view. It does *not* delete the original email from the user's email server.

*   **Action 2: Create a Task**
    *   **Purpose:** To turn a communication into a specific, actionable task.
    *   **User Flow:** User clicks "Create Task" -> selects an existing `WorkItem` -> enters task details (or they are auto-populated from the email subject).
    *   **Logic:** Creates a new `Task` record linked to the chosen `WorkItem`. The original email's content is added as the first comment on the task's new timeline. The `TriageItem` is then cleared.

*   **Action 3: Add to Timeline**
    *   **Purpose:** To store a key communication for context without creating a new task.
    *   **User Flow:** User clicks "Add to Work" -> selects an existing `WorkItem`.
    *   **Logic:** Creates a new `ActivityLog` record linked to the chosen `WorkItem`. The `event_type` is 'EMAIL_ARCHIVED' and the `event_details` contain the full body of the email. The `TriageItem` is then cleared.

*   **Action 4: Create New Work**
    *   **Purpose:** The most powerful action, turning a single email into a full project.
    *   **User Flow:** User clicks "Create Work" -> selects a `Client` -> selects a `Template` -> sets dates.
    *   **Logic:** This triggers the full **Instantiation Process (File 2, Section 3)**. The original email is attached as the very first `ActivityLog` entry on the newly created `WorkItem`'s timeline, providing the origin story for the entire project. The `TriageItem` is then cleared.

---

#### **3. Client-Facing Communication: The Secure Portal**

This feature eliminates the insecure and untraceable back-and-forth of emailing documents. It treats client requests as a formal, trackable part of the workflow.

**3.1. Functionality**
*   **Client Tasks:** Within a Template or Work Item, a task can be designated a "Client Task." This is a task for the *client* to complete, not an internal staff member.
*   **Sending a Request:** When a user sets the status of a Client Task to "Send to Client," the system performs a series of automated actions:
    1.  Generates a cryptographically secure, unique, and time-sensitive URL token.
    2.  Stores this token in a dedicated `ClientRequest` table, linking it to the `task_id` and `work_id`.
    3.  Composes an email to the client using a pre-defined email template.
    4.  Inserts the unique link into the email and sends it to the `Client`'s primary contact email.
    5.  Updates the internal task status to "Waiting for Client."

**3.2. The Client Experience**
*   The client receives a professionally branded email.
*   They click the link and are taken to a simple, secure web portal. **No login or password is required.** The security is handled by the unique token in the URL.
*   On this portal, they can:
    *   See the list of items being requested (e.g., "Upload your May bank statement," "Upload your credit card statement").
    *   Upload files directly.
    *   Add comments or ask questions.
    *   Check off items as they complete them.

**3.3. Closing the Loop: The Return Automation**
*   When the client uploads a file or posts a comment, the file/comment is automatically attached to the correct `Task` and appears on the `WorkItem` timeline. An `@mention` notification is created in the Triage of the task assignee.
*   When the client marks all items as complete, the system automatically changes the status of the internal `Task` to "Completed."
*   This status change can then trigger further **Automators (File 2, Section 5)**, such as notifying the bookkeeper that they can now begin their work. This creates a seamless, automated handoff between the client and the firm.

---

#### **4. Database Schema for the Communication Layer**

This schema focuses on the tables that enable the Triage, client requests, and the unified timeline.

```sql
-- Represents an item in a user's Triage inbox
CREATE TABLE TriageItem (
    triage_id INT PRIMARY KEY,
    firm_id INT NOT NULL,
    user_id INT NOT NULL,               -- The user whose Triage this item belongs to
    item_type VARCHAR(50) NOT NULL,     -- 'EMAIL', '@MENTION', 'NOTIFICATION'
    content TEXT,                       -- The body of the email or comment
    status VARCHAR(50) DEFAULT 'Active',-- 'Active' or 'Cleared'
    created_at DATETIME NOT NULL,
    linked_work_id INT NULL,            -- Optional link if it's been added to work
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

-- The immutable log of all actions, central to all communication
CREATE TABLE ActivityLog (
    log_id INT PRIMARY KEY,
    firm_id INT NOT NULL,
    work_id INT NOT NULL,
    task_id INT NULL,                   -- Optional, if the event is task-specific
    user_id INT NULL,                   -- The internal user who performed the action
    client_contact_id INT NULL,         -- The external client contact who performed an action (e.g., upload)
    event_type VARCHAR(100) NOT NULL,   -- e.g., 'STATUS_CHANGE', 'COMMENT', 'FILE_UPLOADED_BY_CLIENT'
    event_details TEXT,                 -- e.g., "Status changed to 'Completed'", or the text of the comment
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (work_id) REFERENCES WorkItem(work_id)
);

-- Securely manages client-facing requests
CREATE TABLE ClientRequest (
    request_id INT PRIMARY KEY,
    task_id INT NOT NULL UNIQUE,        -- Each request is tied to one client task
    secure_token VARCHAR(255) NOT NULL UNIQUE, -- The token for the secure URL
    client_email VARCHAR(255) NOT NULL, -- The email the request was sent to
    status VARCHAR(50) DEFAULT 'Sent',  -- 'Sent', 'Viewed', 'Completed'
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,       -- For security, the link should expire
    FOREIGN KEY (task_id) REFERENCES Task(task_id) ON DELETE CASCADE
);

-- Stores files uploaded by clients or staff
CREATE TABLE Attachment (
    attachment_id INT PRIMARY KEY,
    log_id INT NOT NULL,                -- Links the file to the timeline event when it was uploaded
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,    -- Path to the file in cloud storage (e.g., S3)
    file_size_bytes INT,
    uploaded_by_user_id INT NULL,
    uploaded_by_client_contact_id INT NULL,
    FOREIGN KEY (log_id) REFERENCES ActivityLog(log_id)
);
```

---

### **Conclusion: A Unified, Intelligent System**

By deeply integrating these three engines—**Work Management**, **Templates & Automation**, and **Triage & Communication**—the platform transcends being a simple tool. It becomes the firm's central operating system.

*   The **Triage Engine** captures all communication.
*   The **Template Engine** defines what to do with it.
*   The **Work Engine** visualizes and manages its execution.

This interconnectedness ensures that no task is dropped, no communication is lost, and every stakeholder has complete visibility into the status of the work, creating a more efficient, profitable, and less stressful accounting practice.