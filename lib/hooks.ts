'use client';

import { useState, useEffect, useCallback } from 'react';
import { dashboard, tasks, projects, clients, admin } from './api';
import type { Task, Project, Client, User, DashboardStats } from './api';

// Mobile detection hook
export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkScreenWidth = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkScreenWidth();
    window.addEventListener('resize', checkScreenWidth);

    return () => window.removeEventListener('resize', checkScreenWidth);
  }, []);

  return isMobile;
}

// Generic hook for API calls
function useApi<T>(
  apiCall: () => Promise<any>,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiCall();
      if (response.data.success) {
        setData(response.data.data);
      } else {
        setError(response.data.message || 'Failed to fetch data');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, dependencies);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// Dashboard hooks
export const useDashboardStats = () => {
  return useApi<DashboardStats>(() => dashboard.getStats());
};

export const useRecentActivity = (limit: number = 10) => {
  return useApi<Array<any>>(() => dashboard.getRecentActivity(limit), [limit]);
};

// Task hooks
export const useTasks = (params?: { status?: string; project_id?: number; assigned_to?: number }) => {
  return useApi<Task[]>(() => tasks.getAll(params), [params]);
};

export const useTask = (id: number) => {
  return useApi<Task>(() => tasks.getById(id), [id]);
};

export const useTaskMutations = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createTask = async (task: Partial<Task>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await tasks.create(task);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to create task');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to create task';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const updateTask = async (id: number, task: Partial<Task>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await tasks.update(id, task);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to update task');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to update task';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const deleteTask = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const response = await tasks.delete(id);
      if (response.data.success) {
        return { success: true };
      } else {
        setError(response.data.message || 'Failed to delete task');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to delete task';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const updateTaskStatus = async (id: number, status: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await tasks.updateStatus(id, status);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to update task status');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to update task status';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  return {
    createTask,
    updateTask,
    deleteTask,
    updateTaskStatus,
    loading,
    error,
  };
};

// Project hooks
export const useProjects = (params?: { status?: string; client_id?: number }) => {
  return useApi<Project[]>(() => projects.getAll(params), [params]);
};

export const useProject = (id: number) => {
  return useApi<Project>(() => projects.getById(id), [id]);
};

export const useProjectTasks = (id: number) => {
  return useApi<Task[]>(() => projects.getTasks(id), [id]);
};

export const useProjectMutations = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createProject = async (project: Partial<Project>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await projects.create(project);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to create project');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to create project';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const updateProject = async (id: number, project: Partial<Project>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await projects.update(id, project);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to update project');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to update project';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const deleteProject = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const response = await projects.delete(id);
      if (response.data.success) {
        return { success: true };
      } else {
        setError(response.data.message || 'Failed to delete project');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to delete project';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  return {
    createProject,
    updateProject,
    deleteProject,
    loading,
    error,
  };
};

// Client hooks
export const useClients = (params?: { search?: string }) => {
  return useApi<Client[]>(() => clients.getAll(params), [params]);
};

export const useClient = (id: number) => {
  return useApi<Client>(() => clients.getById(id), [id]);
};

export const useClientProjects = (id: number) => {
  return useApi<Project[]>(() => clients.getProjects(id), [id]);
};

export const useClientMutations = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createClient = async (client: Partial<Client>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await clients.create(client);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to create client');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to create client';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const updateClient = async (id: number, client: Partial<Client>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await clients.update(id, client);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to update client');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to update client';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const deleteClient = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const response = await clients.delete(id);
      if (response.data.success) {
        return { success: true };
      } else {
        setError(response.data.message || 'Failed to delete client');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to delete client';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  return {
    createClient,
    updateClient,
    deleteClient,
    loading,
    error,
  };
};

// Admin hooks
export const useUsers = () => {
  return useApi<User[]>(() => admin.getUsers());
};

export const useWorkTypes = () => {
  return useApi<Array<any>>(() => admin.getWorkTypes());
};

export const useAdminMutations = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createUser = async (user: Partial<User>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await admin.createUser(user);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to create user');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to create user';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const updateUser = async (id: number, user: Partial<User>) => {
    try {
      setLoading(true);
      setError(null);
      const response = await admin.updateUser(id, user);
      if (response.data.success) {
        return { success: true, data: response.data.data };
      } else {
        setError(response.data.message || 'Failed to update user');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to update user';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const response = await admin.deleteUser(id);
      if (response.data.success) {
        return { success: true };
      } else {
        setError(response.data.message || 'Failed to delete user');
        return { success: false, message: response.data.message };
      }
    } catch (err: any) {
      const message = err.response?.data?.message || 'Failed to delete user';
      setError(message);
      return { success: false, message };
    } finally {
      setLoading(false);
    }
  };

  return {
    createUser,
    updateUser,
    deleteUser,
    loading,
    error,
  };
};