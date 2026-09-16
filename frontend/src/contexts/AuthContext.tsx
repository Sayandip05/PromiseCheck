import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, UserProfile, WorkspaceContext, UserMeResponse } from '../lib/api';

interface AuthContextType {
  user: UserProfile | null;
  activeWorkspace: WorkspaceContext | null;
  workspaces: WorkspaceContext[];
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  loginWithGoogle: (credentialOrEmail?: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  setActiveWorkspace: (ws: WorkspaceContext) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceContext | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceContext[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Rehydrate authentication state on app load
  useEffect(() => {
    const rehydrateSession = async () => {
      try {
        let profile: UserMeResponse;
        try {
          profile = await api.auth.me();
        } catch {
          // If access token is expired or not in memory, attempt refresh via HttpOnly cookie
          const tokenData = await api.auth.refresh();
          profile = {
            id: tokenData.user.id,
            email: tokenData.user.email,
            full_name: tokenData.user.full_name,
            is_active: tokenData.user.is_active,
            created_at: tokenData.user.created_at,
            active_workspace: tokenData.active_workspace,
            workspaces: tokenData.workspaces,
          };
        }

        setUser({
          id: profile.id,
          email: profile.email,
          full_name: profile.full_name,
          is_active: profile.is_active,
          created_at: profile.created_at,
        });
        setActiveWorkspace(profile.active_workspace);
        setWorkspaces(profile.workspaces || []);
      } catch {
        setUser(null);
        setActiveWorkspace(null);
        setWorkspaces([]);
      } finally {
        setIsLoading(false);
      }
    };

    rehydrateSession();
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api.auth.login({ email, password });
    setUser(data.user);
    setActiveWorkspace(data.active_workspace);
    setWorkspaces(data.workspaces || []);
  };

  const register = async (email: string, password: string, fullName: string) => {
    const data = await api.auth.register({ email, password, full_name: fullName });
    setUser(data.user);
    setActiveWorkspace(data.active_workspace);
    setWorkspaces(data.workspaces || []);
  };

  const loginWithGoogle = async (credentialOrEmail?: string, fullName?: string) => {
    const payload =
      credentialOrEmail && credentialOrEmail.includes('.')
        ? { credential: credentialOrEmail }
        : {
            email: credentialOrEmail || 'founder@acme.corp',
            full_name: fullName || 'Acme Founder',
          };
    const data = await api.auth.google(payload);
    setUser(data.user);
    setActiveWorkspace(data.active_workspace);
    setWorkspaces(data.workspaces || []);
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // Ignore network errors on logout
    }
    setUser(null);
    setActiveWorkspace(null);
    setWorkspaces([]);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeWorkspace,
        workspaces,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        loginWithGoogle,
        logout,
        setActiveWorkspace,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
