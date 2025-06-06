# CPA WorkflowPilot - Advanced Features Roadmap

## Overview
This document outlines the technical approach and implementation strategy for the next phase of CPA WorkflowPilot features. All core functionality has been completed, and these represent advanced workflow management capabilities.

---

## 1. Work Type-Based Status System 🎯 **[IN PROGRESS]**

### **Current State**
- Fixed statuses: "Not Started", "In Progress", "Needs Review", "Completed"
- Single workflow for all project types

### **Implemented Approach**
**Work Type-Specific Status Management**: CPA service line customization following KarbonHQ pattern

**Technical Implementation:**
```sql
-- Work Types (Tax, Bookkeeping, Payroll, Advisory)
CREATE TABLE work_type (
    id INTEGER PRIMARY KEY,
    firm_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,        -- "Tax Preparation", "Monthly Bookkeeping"
    description TEXT,
    color VARCHAR(7) NOT NULL,         -- Visual distinction
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (firm_id) REFERENCES firm (id)
);

-- Custom statuses per work type
CREATE TABLE task_status (
    id INTEGER PRIMARY KEY,
    firm_id INTEGER NOT NULL,
    work_type_id INTEGER NOT NULL,     -- Links to specific work type
    name VARCHAR(50) NOT NULL,         -- "Awaiting Info", "In Review", "Filed"
    color VARCHAR(7) NOT NULL,         -- Hex color
    position INTEGER NOT NULL,         -- Order in workflow
    is_terminal BOOLEAN DEFAULT FALSE, -- Marks completion
    is_default BOOLEAN DEFAULT FALSE,  -- Default for new tasks
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (firm_id) REFERENCES firm (id),
    FOREIGN KEY (work_type_id) REFERENCES work_type (id)
);

-- Client Contact Management (Many-to-Many)
CREATE TABLE contact (
    id INTEGER PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    title VARCHAR(100),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE client_contact (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES client (id),
    FOREIGN KEY (contact_id) REFERENCES contact (id)
);
```

**Default Work Types & Workflows:**
- **Tax Preparation**: Awaiting Documents → In Preparation → In Review → Ready for Filing → Filed → Completed
- **Monthly Bookkeeping**: Awaiting Bank Info → Data Entry → Reconciliation → Manager Review → Completed  
- **Payroll Processing**: Data Collection → Processing → Review & Approval → Submitted → Completed
- **Advisory Services**: Planning → Research → Client Meeting → Report Preparation → Delivered

**Features:**
- **Service line segregation** - Different workflows for different CPA services
- **Team efficiency** - Relevant statuses only for specific work types
- **Scalable growth** - Easy addition of new service lines
- **Smart Kanban filtering** - Work type-specific column sets
- **AI integration ready** - Structured for future email automation

**Kanban Board Enhancements:**
- **Work type filtering** - Show only relevant status columns
- **Horizontal scrolling** - Handle 6+ status workflows
- **Unified dashboard** - Cross-work-type overview option
- **Color coding** - Visual distinction by work type and status

**Implementation Status**: ✅ **ACTIVE DEVELOPMENT**

---

## 2. Enhanced Quick Filters ⚡

### **Current State**
- Basic quick filters: Due Today, Due Soon, Overdue, Hide Completed
- Limited date-based filtering

### **Proposed Approach**
**Intelligent Time-Based Filtering** with CPA workflow awareness

**New Quick Filters:**
- **This Week** - Tasks due within 7 days
- **Next Week** - Tasks due 8-14 days from now
- **This Month** - Current month deadlines
- **Quarter End** - Tasks due within 30 days of quarter end
- **Tax Season** - January-April focused filtering
- **My Tasks** - Current user's assignments
- **Unassigned** - Tasks needing assignment
- **High Priority Only** - Critical tasks filter
- **Recently Updated** - Tasks changed in last 3 days
- **Overdue by Client** - Group overdue tasks by client

**Technical Implementation:**
```javascript
const quickFilters = {
    thisWeek: () => filterByDateRange(today, addDays(today, 7)),
    quarterEnd: () => filterByDateRange(today, getQuarterEnd()),
    taxSeason: () => filterByMonthRange(1, 4), // Jan-Apr
    myTasks: () => filterByAssignee(currentUserId),
    recentlyUpdated: () => filterByUpdateDate(subtractDays(today, 3))
};
```

**CPA-Specific Features:**
- **Tax deadline awareness** (April 15, October 15, etc.)
- **Month-end close** filters (last 3 business days)
- **Compliance deadlines** integration
- **Client year-end** filtering

**Implementation Priority**: Medium - UI enhancement with business logic

---

## 3. Bulk Task Assignment 👥

### **Current State**
- ✅ **Already Implemented** in project edit view
- Basic bulk assignment to single user
- Prompt-based user selection

### **Enhanced Approach**
**Advanced Assignment Workflows** for complex project management

**Current Features (Completed):**
- Bulk assign all project tasks to one user
- User selection prompt in project edit view
- Activity logging for bulk assignments

**Potential Enhancements:**
- **Role-based assignment** (assign all "Review" tasks to Partners)
- **Workload balancing** (distribute tasks evenly among team)
- **Skill-based assignment** (match tasks to user expertise)
- **Assignment templates** (predefined assignment patterns)

**Implementation Status**: ✅ **COMPLETE** - Core functionality implemented

---

## 4. Recurring Tasks System 🔄

### **Current State**
- Static task creation from templates
- No automated recurring functionality

### **Proposed Approach**
**Automated Workflow Engine** for regular CPA processes

**Technical Architecture:**
```sql
-- Recurring task definitions
CREATE TABLE recurring_tasks (
    id INTEGER PRIMARY KEY,
    firm_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    recurrence_pattern VARCHAR(20) NOT NULL, -- monthly, quarterly, yearly
    recurrence_interval INTEGER DEFAULT 1,   -- every N periods
    start_date DATE NOT NULL,
    end_date DATE,                          -- optional end date
    next_due_date DATE NOT NULL,
    assignee_id INTEGER,
    priority VARCHAR(10) DEFAULT 'Medium',
    project_template_id INTEGER,             -- optional template link
    is_active BOOLEAN DEFAULT TRUE,
    last_generated DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Recurrence Patterns:**
- **Monthly**: Monthly close procedures, client check-ins
- **Quarterly**: Quarterly reviews, estimated payments
- **Yearly**: Annual audits, tax planning sessions
- **Custom**: Every N weeks/months for specific workflows

**CPA-Specific Recurring Tasks:**
- **Monthly close** (1st-5th of each month)
- **Quarterly filings** (15th of Jan, Apr, Jul, Oct)
- **Annual tax prep** (Dec-Apr annual cycle)
- **Client review meetings** (quarterly/semi-annual)
- **Compliance deadlines** (various frequencies)

**Automation Features:**
- **Background job processor** (runs daily at midnight)
- **Task auto-generation** based on due dates
- **Template integration** (create full project workflows)
- **Smart scheduling** (avoid weekends/holidays)
- **Notification system** for upcoming recurring items

**Implementation Priority**: Medium-High - Critical for CPA workflow automation

---

## 5. Task Dependencies System 🔗

### **Current State**
- Independent task management
- No workflow blocking/sequencing

### **Proposed Approach**
**Workflow Orchestration** with dependency management

**Technical Implementation:**
```sql
-- Task dependency relationships
CREATE TABLE task_dependencies (
    id INTEGER PRIMARY KEY,
    predecessor_task_id INTEGER NOT NULL,
    successor_task_id INTEGER NOT NULL,
    dependency_type VARCHAR(20) DEFAULT 'finish_to_start',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (predecessor_task_id) REFERENCES task (id),
    FOREIGN KEY (successor_task_id) REFERENCES task (id)
);
```

**Dependency Types:**
- **Finish-to-Start** (most common): Task B starts after Task A finishes
- **Start-to-Start**: Task B starts when Task A starts
- **Finish-to-Finish**: Task B finishes when Task A finishes
- **Start-to-Finish**: Task B finishes when Task A starts (rare)

**CPA Workflow Dependencies:**
- **Client data collection** → **Tax preparation** → **Review** → **Filing**
- **Bank reconciliation** → **Financial statements** → **Management review**
- **Payroll processing** → **Quarterly filings** → **Annual reconciliation**
- **Audit fieldwork** → **Audit report** → **Management letter**

**Visual Features:**
- **Dependency visualization** (Gantt-style view)
- **Critical path highlighting** (longest dependency chain)
- **Blocking task warnings** (what's holding up the workflow)
- **Auto-scheduling** (adjust dates based on dependencies)

**Business Logic:**
- **Automatic status inheritance** (can't start until predecessor completes)
- **Dependency validation** (prevent circular dependencies)
- **Timeline recalculation** when predecessor dates change
- **Notification system** for unblocked tasks

**Implementation Priority**: Low-Medium - Advanced workflow feature

---

## 6. Additional Features (Lower Priority)

### **File Attachments** 📎
- **Document storage** for task-specific files
- **Version control** for document revisions
- **Integration** with existing file systems
- **Security** with access controls

### **Subtask System** 📋
- **Hierarchical task breakdown** for complex workflows
- **Progress rollup** from subtasks to parent tasks
- **Nested assignment** and status tracking
- **Template integration** for standard breakdowns

### **Enhanced Time Tracking** ⏱️
- **Built-in timer** for active time tracking
- **Billing rate integration** for client invoicing
- **Time allocation** across multiple tasks
- **Reporting dashboard** for time analytics

### **Mobile Optimization** 📱
- **Responsive design** improvements for tablet/phone
- **Touch-optimized** interactions
- **Offline capability** for field work
- **Push notifications** for mobile devices

---

## Implementation Recommendations

### **Phase 1 (Current - 2-3 weeks)** ✅ **IN PROGRESS**
1. **Work Type-Based Status System** - Database restructure and custom workflow management
2. **Client Contact Management** - Many-to-many relationship system
3. **Enhanced Kanban Board** - Work type filtering and custom status support

### **Phase 2 (Short-term - 4-6 weeks)**
1. **Enhanced Quick Filters** - CPA-specific time-based filtering
2. **Recurring Tasks System** - Critical for CPA automation
3. **Admin Interface** - Work type and status management UI

### **Phase 3 (Medium-term - 2-3 months)**
1. **Task Dependencies** - Complex workflow orchestration
2. **File Attachments** - Infrastructure and security considerations
3. **Enhanced Time Tracking** - Billing system integration

### **Phase 4 (Long-term - 3-6 months)** 🔮 **FUTURE**
1. **AI-Assisted Email Integration** - Smart email processing and automation
2. **External Integrations** - QuickBooks, Xero, banking connections
3. **Mobile Optimization** - Comprehensive responsive design overhaul

---

## Known Issues & Bug Fixes

### **Z-Index Dropdown Issues** 🐛
**Priority**: Low (after medium features)
**Description**: Multi-select dropdown menus in task filtering occasionally render behind table elements
**Symptoms**: 
- Overdue date indicators appear on top of assignee dropdown
- "No tasks found" banner overlays dropdown menus
- Elements flicker between layers on hover

**Technical Root Cause**: 
- Complex CSS stacking context conflicts between Bootstrap dropdowns and table elements
- Position relative/absolute conflicts in responsive table layouts

**Proposed Solution**:
- Implement proper CSS containment strategy
- Use CSS `isolation: isolate` for dropdown containers
- Portal-based dropdown rendering to document body
- Restructure table layout to avoid stacking context issues

---

## Technical Considerations

### **Database Migrations**
- Plan for **backward compatibility** during status system migration
- **Data migration scripts** for existing tasks and projects
- **Rollback procedures** for failed migrations

### **Performance Impact**
- **Indexing strategy** for new dependency queries
- **Caching mechanisms** for recurring task calculations
- **Background job processing** for automated task generation

### **User Experience**
- **Progressive disclosure** for advanced features
- **Training materials** for new workflow capabilities
- **Feature toggles** for gradual rollout

### **Testing Strategy**
- **Automated tests** for dependency logic
- **Load testing** for recurring task generation
- **User acceptance testing** with real CPA workflows

---

*This roadmap provides a comprehensive approach to evolving CPA WorkflowPilot into a sophisticated workflow management platform while maintaining its ease of use and CPA-specific focus.*