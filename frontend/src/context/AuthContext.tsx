/**
 * AuthContext — global auth state.
 * Stores the current user and access token, handles login/register/logout/refresh.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import axios from 'axios';
import type { User } from '../types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Silently refresh access token using httpOnly refresh cookie. */
  refresh: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const API_BASE = import.meta.env.VITE_API_URL ?? '';

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    isLoading: true,
  });

  // Attempt silent refresh on mount to restore session after page reload
  useEffect(() => {
    refresh().finally(() => {
      setState((s) => ({ ...s, isLoading: false }));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refresh = useCallback(async (): Promise<string | null> => {
    try {
      const res = await axios.post(
        `${API_BASE}/api/auth/refresh`,
        {},
        { withCredentials: true }
      );
      const { access_token, user } = res.data as { access_token: string; user: User };
      setState({ user, accessToken: access_token, isLoading: false });
      return access_token;
    } catch {
      setState({ user: null, accessToken: null, isLoading: false });
      return null;
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await axios.post(
      `${API_BASE}/api/auth/login`,
      { email, password },
      { withCredentials: true }
    );
    const { access_token, user } = res.data as { access_token: string; user: User };
    setState({ user, accessToken: access_token, isLoading: false });
  }, []);

  const register = useCallback(async (email: string, password: string, name?: string) => {
    const res = await axios.post(
      `${API_BASE}/api/auth/register`,
      { email, password, name },
      { withCredentials: true }
    );
    const { access_token, user } = res.data as { access_token: string; user: User };
    setState({ user, accessToken: access_token, isLoading: false });
  }, []);

  const logout = useCallback(async () => {
    try {
      await axios.post(
        `${API_BASE}/api/auth/logout`,
        {},
        {
          withCredentials: true,
          headers: state.accessToken
            ? { Authorization: `Bearer ${state.accessToken}` }
            : {},
        }
      );
    } catch {
      // ignore errors — clear state regardless
    }
    setState({ user: null, accessToken: null, isLoading: false });
  }, [state.accessToken]);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
