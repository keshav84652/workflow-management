'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { DEFAULT_USER, User } from './data';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; message?: string }>;
  logout: () => Promise<void>;
  selectFirm: (firmId: number) => Promise<{ success: boolean; message?: string }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasChecked, setHasChecked] = useState(false);

  const isAuthenticated = !!user;

  useEffect(() => {
    // Only check once when the component mounts
    if (!hasChecked) {
      checkAuthStatus();
    }
  }, [hasChecked]);

  const checkAuthStatus = async () => {
    if (hasChecked) return; // Prevent multiple checks
    
    try {
      setHasChecked(true);
      // Check if user is logged in (localStorage for demo)
      const storedUser = localStorage.getItem('currentUser');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      } else {
        // Default to first user for demo
        setUser(DEFAULT_USER);
        localStorage.setItem('currentUser', JSON.stringify(DEFAULT_USER));
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(DEFAULT_USER);
      localStorage.setItem('currentUser', JSON.stringify(DEFAULT_USER));
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    try {
      // Simple demo login - accept any credentials
      const userData = DEFAULT_USER;
      setUser(userData);
      localStorage.setItem('currentUser', JSON.stringify(userData));
      
      return { success: true };
    } catch (error: any) {
      console.error('Login error:', error);
      return { 
        success: false, 
        message: 'Login failed. Please try again.' 
      };
    }
  };

  const logout = async () => {
    try {
      localStorage.removeItem('currentUser');
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      setUser(null);
    }
  };

  const selectFirm = async (firmId: number) => {
    try {
      // For demo, just return success
      return { success: true };
    } catch (error: any) {
      console.error('Firm selection error:', error);
      return { 
        success: false, 
        message: 'Failed to select firm' 
      };
    }
  };

  const value = {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    selectFirm,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Higher-order component for protected routes
export const withAuth = <P extends object>(
  Component: React.ComponentType<P>
) => {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading } = useAuth();
    
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      );
    }
    
    if (!isAuthenticated) {
      // Redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      return null;
    }
    
    return <Component {...props} />;
  };
};

// Hook for checking specific permissions
export const usePermissions = () => {
  const { user } = useAuth();
  
  const hasRole = (role: string) => {
    return user?.role === role;
  };
  
  const isAdmin = () => hasRole('admin');
  const isPartner = () => hasRole('partner');
  const isManager = () => hasRole('manager') || isPartner() || isAdmin();
  const isSenior = () => hasRole('senior') || isManager();
  const isStaff = () => hasRole('staff') || isSenior();
  
  const canManageUsers = () => isAdmin() || isPartner();
  const canManageProjects = () => isManager();
  const canManageTasks = () => isSenior();
  const canViewReports = () => isManager();
  
  return {
    hasRole,
    isAdmin,
    isPartner,
    isManager,
    isSenior,
    isStaff,
    canManageUsers,
    canManageProjects,
    canManageTasks,
    canViewReports,
  };
};