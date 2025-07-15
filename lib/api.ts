import axios from 'axios';

// Base API configuration
const api = axios.create({
  baseURL: process.env.NODE_ENV === 'development' ? 'http://localhost:5002/api' : '/api',
  timeout: 10000,
  withCredentials: true, // Important: Send cookies with requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    // Ensure credentials are sent with every request for session management
    config.withCredentials = true;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't automatically redirect on 401 - let the auth context handle it
    // This prevents infinite redirect loops
    return Promise.reject(error);
  }
);

// Types for API responses
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  firm_id: number;
  firm_name: string;
}

export interface Project {
  id: number;
  title: string;
  description: string;
  status: string;
  client_id: number;
  client_name: string;
  created_at: string;
  updated_at: string;
  task_count: number;
  completed_tasks: number;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: string;
  project_id: number;
  project_name: string;
  assigned_to: number;
  assigned_to_name: string;
  due_date: string;
  created_at: string;
  updated_at: string;
}

export interface Client {
  id: number;
  name: string;
  email: string;
  phone: string;
  address: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  overdue_tasks: number;
  total_projects: number;
  active_projects: number;
  total_clients: number;
  recent_activities: Array<{
    id: number;
    message: string;
    timestamp: string;
    user: string;
  }>;
}

// Authentication API
export const auth = {
  login: (credentials: { username: string; password: string }) =>
    api.post<ApiResponse<{ user: User; token: string }>>('/auth/login', credentials),
  
  logout: () => api.post<ApiResponse>('/auth/logout'),
  
  getCurrentUser: () => api.get<ApiResponse<User>>('/auth/me'),
  
  selectFirm: (firmId: number) => api.post<ApiResponse>('/auth/select-firm', { firm_id: firmId }),
};

// Dashboard API
export const dashboard = {
  getStats: () => api.get<ApiResponse<DashboardStats>>('/dashboard/stats'),
  
  getRecentActivity: (limit: number = 10) => 
    api.get<ApiResponse<Array<any>>>(`/dashboard/activity?limit=${limit}`),
};

// Tasks API
export const tasks = {
  getAll: (params?: { status?: string; project_id?: number; assigned_to?: number }) =>
    api.get<ApiResponse<Task[]>>('/tasks', { params }),
  
  getById: (id: number) => api.get<ApiResponse<Task>>(`/tasks/${id}`),
  
  create: (task: Partial<Task>) => api.post<ApiResponse<Task>>('/tasks', task),
  
  update: (id: number, task: Partial<Task>) => 
    api.put<ApiResponse<Task>>(`/tasks/${id}`, task),
  
  delete: (id: number) => api.delete<ApiResponse>(`/tasks/${id}`),
  
  updateStatus: (id: number, status: string) =>
    api.patch<ApiResponse<Task>>(`/tasks/${id}/status`, { status }),
};

// Projects API
export const projects = {
  getAll: (params?: { status?: string; client_id?: number }) =>
    api.get<ApiResponse<Project[]>>('/projects', { params }),
  
  getById: (id: number) => api.get<ApiResponse<Project>>(`/projects/${id}`),
  
  create: (project: Partial<Project>) => api.post<ApiResponse<Project>>('/projects', project),
  
  update: (id: number, project: Partial<Project>) =>
    api.put<ApiResponse<Project>>(`/projects/${id}`, project),
  
  delete: (id: number) => api.delete<ApiResponse>(`/projects/${id}`),
  
  getTasks: (id: number) => api.get<ApiResponse<Task[]>>(`/projects/${id}/tasks`),
};

// Clients API
export const clients = {
  getAll: (params?: { search?: string }) =>
    api.get<ApiResponse<Client[]>>('/clients', { params }),
  
  getById: (id: number) => api.get<ApiResponse<Client>>(`/clients/${id}`),
  
  create: (client: Partial<Client>) => api.post<ApiResponse<Client>>('/clients', client),
  
  update: (id: number, client: Partial<Client>) =>
    api.put<ApiResponse<Client>>(`/clients/${id}`, client),
  
  delete: (id: number) => api.delete<ApiResponse>(`/clients/${id}`),
  
  getProjects: (id: number) => api.get<ApiResponse<Project[]>>(`/clients/${id}/projects`),
};

// Admin API
export const admin = {
  getUsers: () => api.get<ApiResponse<User[]>>('/admin/users'),
  
  createUser: (user: Partial<User>) => api.post<ApiResponse<User>>('/admin/users', user),
  
  updateUser: (id: number, user: Partial<User>) =>
    api.put<ApiResponse<User>>(`/admin/users/${id}`, user),
  
  deleteUser: (id: number) => api.delete<ApiResponse>(`/admin/users/${id}`),
  
  getWorkTypes: () => api.get<ApiResponse<Array<any>>>('/admin/work-types'),
  
  createWorkType: (workType: any) => api.post<ApiResponse<any>>('/admin/work-types', workType),
};

export default api;