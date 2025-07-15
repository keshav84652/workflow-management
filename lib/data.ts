// Real data extracted from the original Flask SQLite database

export interface User {
  id: number
  name: string
  role: 'Admin' | 'Member'
  firm_id: number
  created_at: string
}

export interface Client {
  id: number
  name: string
  email?: string
  phone?: string
  address?: string
  contact_person?: string
  entity_type?: string
  tax_id?: string
  notes?: string
  firm_id: number
  is_active: boolean
  created_at: string
}

export interface Project {
  id: number
  name: string
  client_id: number
  work_type_id?: number
  status: string
  start_date: string
  due_date?: string
  completion_date?: string
  firm_id: number
  template_origin_id?: number
  priority: string
  created_at: string
  current_status_id?: number
  task_dependency_mode: boolean
}

export interface Task {
  id: number
  title: string
  description?: string
  due_date?: string
  estimated_hours?: number
  actual_hours?: number
  status: string
  status_id?: number
  priority: string
  project_id?: number
  firm_id: number
  assignee_id?: number
  template_task_origin_id?: number
  completed_at?: string
  created_at: string
  updated_at?: string
  dependencies?: string
  is_recurring: boolean
  recurrence_rule?: string
  recurrence_interval?: number
  next_due_date?: string
  last_completed?: string
  hourly_rate?: number
  is_billable: boolean
  timer_start?: string
  timer_running: boolean
}

export interface WorkType {
  id: number
  firm_id: number
  name: string
  description?: string
  color: string
  is_active: boolean
  position?: number
  created_at: string
}

export interface Contact {
  id: number
  first_name: string
  last_name: string
  email: string
  phone?: string
  title?: string
  company?: string
  address?: string
  notes?: string
  created_at: string
}

// Real data from the Flask database
export const FIRM_DATA = {
  id: 1,
  name: "Demo CPA Firm",
  access_code: "DEMO2024",
  is_active: true,
  created_at: "2025-06-06 08:41:25.628712"
}

export const USERS_DATA: User[] = [
  {
    id: 1,
    name: "Sarah Johnson",
    role: "Admin",
    firm_id: 1,
    created_at: "2025-06-06 08:41:25.665503"
  },
  {
    id: 2,
    name: "Michael Chen",
    role: "Admin",
    firm_id: 1,
    created_at: "2025-06-06 08:41:25.665507"
  },
  {
    id: 3,
    name: "Emily Rodriguez",
    role: "Member",
    firm_id: 1,
    created_at: "2025-06-06 08:41:25.665508"
  },
  {
    id: 4,
    name: "David Park",
    role: "Member",
    firm_id: 1,
    created_at: "2025-06-06 08:41:25.665509"
  },
  {
    id: 5,
    name: "Test User",
    role: "Member",
    firm_id: 1,
    created_at: "2025-06-28 17:02:06.229722"
  },
  {
    id: 6,
    name: "Test User 2",
    role: "Member",
    firm_id: 1,
    created_at: "2025-06-28 17:05:31.687442"
  }
]

export const CLIENTS_DATA: Client[] = [
  {
    id: 1,
    name: "ABC Corporation",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "Corporation",
    tax_id: "12-3456789",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.689787"
  },
  {
    id: 2,
    name: "Tech Startup LLC",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "LLC",
    tax_id: "98-7654321",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.700575"
  },
  {
    id: 3,
    name: "Retail Business Inc",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "S-Corp",
    tax_id: "11-2233445",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.703563"
  },
  {
    id: 4,
    name: "Local Restaurant",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "Partnership",
    tax_id: "33-4455667",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.704543"
  },
  {
    id: 5,
    name: "Consulting Group",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "LLC",
    tax_id: "55-6677889",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.705465"
  },
  {
    id: 6,
    name: "Individual Client",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "Individual",
    tax_id: "123-45-6789",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.706520"
  },
  {
    id: 7,
    name: "Construction Co",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "LLC",
    tax_id: "77-8899001",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.708318"
  },
  {
    id: 8,
    name: "Healthcare Practice",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "Professional Corp",
    tax_id: "99-0011223",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-06 08:41:25.708856"
  },
  {
    id: 9,
    name: "Individual client",
    email: "",
    phone: "",
    address: "",
    contact_person: "",
    entity_type: "Individual",
    tax_id: "",
    notes: "",
    firm_id: 1,
    is_active: true,
    created_at: "2025-06-14 10:23:51.321673"
  }
]

export const PROJECTS_DATA: Project[] = [
  {
    id: 2,
    name: "December 2024 Bookkeeping",
    client_id: 2,
    work_type_id: 2,
    status: "Active",
    start_date: "2025-01-01",
    due_date: "2025-01-15",
    completion_date: "",
    firm_id: 1,
    template_origin_id: 2,
    priority: "Medium",
    created_at: "2025-06-06 08:41:25.763163",
    current_status_id: 11,
    task_dependency_mode: true
  },
  {
    id: 3,
    name: "Q4 2024 Payroll",
    client_id: 3,
    work_type_id: 3,
    status: "Active",
    start_date: "2024-12-15",
    due_date: "2025-01-31",
    completion_date: "",
    firm_id: 1,
    template_origin_id: 3,
    priority: "High",
    created_at: "2025-06-06 08:41:25.768664",
    current_status_id: 14,
    task_dependency_mode: true
  },
  {
    id: 4,
    name: "Business Growth Strategy",
    client_id: 4,
    work_type_id: 4,
    status: "Active",
    start_date: "2025-01-01",
    due_date: "2025-02-28",
    completion_date: "",
    firm_id: 1,
    template_origin_id: 4,
    priority: "Medium",
    created_at: "2025-06-06 08:41:25.773983",
    current_status_id: 19,
    task_dependency_mode: true
  },
  {
    id: 6,
    name: "Tech Startup LLC - Tax Return",
    client_id: 2,
    work_type_id: 1,
    status: "Active",
    start_date: "2025-06-16",
    due_date: "",
    completion_date: "",
    firm_id: 1,
    template_origin_id: 1,
    priority: "Medium",
    created_at: "2025-06-16 12:11:45.046304",
    current_status_id: 29,
    task_dependency_mode: true
  }
]

export const TASKS_DATA: Task[] = [
  {
    id: 7,
    title: "Download bank statements",
    description: "Task from Monthly Bookkeeping Package template",
    due_date: "2025-01-01",
    estimated_hours: 0.25,
    actual_hours: 0.0,
    status: "Completed",
    priority: "Medium",
    project_id: 2,
    firm_id: 1,
    assignee_id: 3,
    completed_at: "2025-06-16 10:41:04.589601",
    created_at: "2025-06-06 08:41:25.764569",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 8,
    title: "Categorize transactions",
    description: "Task from Monthly Bookkeeping Package template",
    due_date: "2025-01-02",
    estimated_hours: 3.0,
    actual_hours: 0.0,
    status: "Completed",
    priority: "Medium",
    project_id: 2,
    firm_id: 1,
    assignee_id: 2,
    completed_at: "2025-06-16 10:41:06.751653",
    created_at: "2025-06-06 08:41:25.765358",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 9,
    title: "Reconcile bank accounts",
    description: "Task from Monthly Bookkeeping Package template",
    due_date: "2025-01-03",
    estimated_hours: 2.0,
    actual_hours: 0.0,
    status: "Completed",
    priority: "Medium",
    project_id: 2,
    firm_id: 1,
    assignee_id: 4,
    completed_at: "2025-06-20 16:46:28.266287",
    created_at: "2025-06-06 08:41:25.766126",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 10,
    title: "Generate financial statements",
    description: "Task from Monthly Bookkeeping Package template",
    due_date: "2025-01-04",
    estimated_hours: 1.0,
    actual_hours: 0.0,
    status: "Completed",
    priority: "Medium",
    project_id: 2,
    firm_id: 1,
    assignee_id: 3,
    created_at: "2025-06-06 08:41:25.766919",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 11,
    title: "Review and finalize",
    description: "Task from Monthly Bookkeeping Package template",
    due_date: "2025-01-05",
    estimated_hours: 0.5,
    actual_hours: 0.0,
    status: "In Progress",
    priority: "Medium",
    project_id: 2,
    firm_id: 1,
    assignee_id: 4,
    created_at: "2025-06-06 08:41:25.767720",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 12,
    title: "Collect timesheets",
    description: "Task from Bi-Weekly Payroll template",
    due_date: "2024-12-15",
    estimated_hours: 0.5,
    actual_hours: 0.0,
    status: "Completed",
    priority: "High",
    project_id: 3,
    firm_id: 1,
    assignee_id: 3,
    completed_at: "2025-06-11 12:30:09.128815",
    created_at: "2025-06-06 08:41:25.769991",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 13,
    title: "Calculate payroll",
    description: "Task from Bi-Weekly Payroll template",
    due_date: "2024-12-16",
    estimated_hours: 1.5,
    actual_hours: 0.0,
    status: "Completed",
    priority: "High",
    project_id: 3,
    firm_id: 1,
    assignee_id: 3,
    completed_at: "2025-06-25 18:37:59.982291",
    created_at: "2025-06-06 08:41:25.770790",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 14,
    title: "Review calculations",
    description: "Task from Bi-Weekly Payroll template",
    due_date: "2024-12-16",
    estimated_hours: 0.5,
    actual_hours: 0.0,
    status: "In Progress",
    priority: "High",
    project_id: 3,
    firm_id: 1,
    assignee_id: 2,
    created_at: "2025-06-06 08:41:25.771570",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 15,
    title: "Process payroll",
    description: "Task from Bi-Weekly Payroll template",
    due_date: "2024-12-17",
    estimated_hours: 0.75,
    actual_hours: 0.0,
    status: "Not Started",
    priority: "High",
    project_id: 3,
    firm_id: 1,
    assignee_id: 3,
    created_at: "2025-06-06 08:41:25.772313",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  },
  {
    id: 16,
    title: "File payroll taxes",
    description: "Task from Bi-Weekly Payroll template",
    due_date: "2024-12-18",
    estimated_hours: 0.5,
    actual_hours: 0.0,
    status: "Not Started",
    priority: "High",
    project_id: 3,
    firm_id: 1,
    assignee_id: 3,
    created_at: "2025-06-06 08:41:25.773071",
    is_recurring: false,
    is_billable: true,
    timer_running: false
  }
]

export const WORK_TYPES_DATA: WorkType[] = [
  {
    id: 1,
    firm_id: 1,
    name: "Tax Return",
    description: "Individual and business tax return preparation",
    color: "#dc2626",
    is_active: true,
    position: 1,
    created_at: "2025-06-06 08:41:25.730000"
  },
  {
    id: 2,
    firm_id: 1,
    name: "Monthly Bookkeeping",
    description: "Regular bookkeeping and financial maintenance",
    color: "#059669",
    is_active: true,
    position: 2,
    created_at: "2025-06-06 08:41:25.731000"
  },
  {
    id: 3,
    firm_id: 1,
    name: "Payroll Processing",
    description: "Bi-weekly and monthly payroll processing",
    color: "#3b82f6",
    is_active: true,
    position: 3,
    created_at: "2025-06-06 08:41:25.732000"
  },
  {
    id: 4,
    firm_id: 1,
    name: "Business Advisory",
    description: "Strategic business consultation and planning",
    color: "#f59e0b",
    is_active: true,
    position: 4,
    created_at: "2025-06-06 08:41:25.733000"
  },
  {
    id: 5,
    firm_id: 1,
    name: "Year-End Close",
    description: "Year-end financial closing procedures",
    color: "#7c3aed",
    is_active: true,
    position: 5,
    created_at: "2025-06-06 08:41:25.734000"
  }
]

// Default user for authentication simulation
export const DEFAULT_USER = USERS_DATA[0] // Sarah Johnson (Admin)

// Session simulation
export let currentUser: User = DEFAULT_USER
export const getCurrentUser = () => currentUser
export const setCurrentUser = (user: User) => {
  currentUser = user
}