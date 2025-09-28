/**
 * Authentication Context for Skylapse Dashboard
 * Professional Mountain Timelapse Camera System
 *
 * Provides secure JWT token management, automatic refresh,
 * and authentication state for the entire application.
 */

import React, { createContext, useContext, useEffect, useReducer, useCallback, useMemo } from 'react';
import { apiClient } from '../api/client';
import type { AuthTokens, User } from '../api/types';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  error: string | null;
  lastAuthCheck: number;
}

type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { tokens: AuthTokens; user: User } }
  | { type: 'AUTH_FAILURE'; payload: string }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'TOKEN_REFRESH_SUCCESS'; payload: AuthTokens }
  | { type: 'CLEAR_ERROR' };

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  clearError: () => void;
  refreshTokens: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const initialState: AuthState = {
  isAuthenticated: true, // Development mode - auto-authenticated
  isLoading: false,
  user: { id: 'dev-user', username: 'development', email: 'dev@skylapse.local' },
  accessToken: 'dev-token-for-websocket-connection',
  refreshToken: null,
  error: null,
  lastAuthCheck: Date.now(),
};

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return {
        ...state,
        isLoading: true,
        error: null,
      };

    case 'AUTH_SUCCESS':
      return {
        ...state,
        isAuthenticated: true,
        isLoading: false,
        user: action.payload.user,
        accessToken: action.payload.tokens.access_token,
        refreshToken: action.payload.tokens.refresh_token,
        error: null,
        lastAuthCheck: Date.now(),
      };

    case 'AUTH_FAILURE':
      return {
        ...state,
        isAuthenticated: false,
        isLoading: false,
        user: null,
        accessToken: null,
        refreshToken: null,
        error: action.payload,
        lastAuthCheck: Date.now(),
      };

    case 'AUTH_LOGOUT':
      return {
        ...initialState,
        isLoading: false,
        lastAuthCheck: Date.now(),
      };

    case 'TOKEN_REFRESH_SUCCESS':
      return {
        ...state,
        accessToken: action.payload.access_token,
        refreshToken: action.payload.refresh_token,
        lastAuthCheck: Date.now(),
        error: null,
      };

    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };

    default:
      return state;
  }
}

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Token storage helpers
  const storeTokens = useCallback((tokens: AuthTokens) => {
    localStorage.setItem('skylapse_access_token', tokens.access_token);
    localStorage.setItem('skylapse_refresh_token', tokens.refresh_token);
    localStorage.setItem('skylapse_token_expires',
      (Date.now() + tokens.expires_in * 1000).toString()
    );
  }, []);

  const clearTokens = useCallback(() => {
    localStorage.removeItem('skylapse_access_token');
    localStorage.removeItem('skylapse_refresh_token');
    localStorage.removeItem('skylapse_token_expires');
    localStorage.removeItem('skylapse_user');
  }, []);

  const getStoredTokens = useCallback((): {
    accessToken: string | null;
    refreshToken: string | null;
    isExpired: boolean;
  } => {
    const accessToken = localStorage.getItem('skylapse_access_token');
    const refreshToken = localStorage.getItem('skylapse_refresh_token');
    const expiresAt = localStorage.getItem('skylapse_token_expires');

    const isExpired = expiresAt ? Date.now() > parseInt(expiresAt) : true;

    return { accessToken, refreshToken, isExpired };
  }, []);

  // Mock user fetch for now - in production this would validate the token
  const fetchUser = useCallback(async (): Promise<User> => {
    // TODO: Replace with actual user endpoint when available
    return {
      id: 'mock-user-id',
      username: 'mountain-operator',
      role: 'admin',
      permissions: ['dashboard:read', 'camera:control', 'settings:write'],
    };
  }, []);

  // Login function
  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    dispatch({ type: 'AUTH_START' });

    try {
      const response = await apiClient.capture.login(username, password);
      const tokens = response.data;

      // Store tokens
      storeTokens(tokens);

      // Set token in API client
      apiClient.setAccessToken(tokens.access_token);

      // Fetch user profile
      const user = await fetchUser();
      localStorage.setItem('skylapse_user', JSON.stringify(user));

      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { tokens, user }
      });

      return true;
    } catch (error: any) {
      const errorMessage = error.apiError?.error?.message || 'Login failed. Please check your credentials.';
      dispatch({ type: 'AUTH_FAILURE', payload: errorMessage });
      clearTokens();
      return false;
    }
  }, [storeTokens, clearTokens, fetchUser]);

  // Token refresh function
  const refreshTokens = useCallback(async (): Promise<boolean> => {
    const { refreshToken } = getStoredTokens();

    if (!refreshToken) {
      dispatch({ type: 'AUTH_LOGOUT' });
      return false;
    }

    try {
      const response = await apiClient.capture.refreshToken(refreshToken);
      const tokens = response.data;

      storeTokens(tokens);
      apiClient.setAccessToken(tokens.access_token);

      dispatch({ type: 'TOKEN_REFRESH_SUCCESS', payload: tokens });
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      dispatch({ type: 'AUTH_LOGOUT' });
      clearTokens();
      return false;
    }
  }, [getStoredTokens, storeTokens, clearTokens]);

  // Logout function
  const logout = useCallback(async (): Promise<void> => {
    try {
      // Attempt to notify server of logout
      await apiClient.capture.logout();
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local logout even if server call fails
    }

    // Clear local state regardless of server response
    clearTokens();
    apiClient.setAccessToken(null);
    dispatch({ type: 'AUTH_LOGOUT' });
  }, [clearTokens]);

  // Clear error function
  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' });
  }, []);

  // Initialize authentication state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const { accessToken, refreshToken, isExpired } = getStoredTokens();

      if (!accessToken || !refreshToken) {
        dispatch({ type: 'AUTH_LOGOUT' });
        return;
      }

      // If token is expired, try to refresh
      if (isExpired) {
        const refreshSuccess = await refreshTokens();
        if (!refreshSuccess) {
          return; // refreshTokens already handles logout on failure
        }
      } else {
        // Token is still valid, restore session
        try {
          apiClient.setAccessToken(accessToken);
          const storedUser = localStorage.getItem('skylapse_user');

          if (storedUser) {
            const user = JSON.parse(storedUser);
            const tokens = {
              access_token: accessToken,
              refresh_token: refreshToken,
              expires_in: 3600, // Default value
              token_type: 'Bearer' as const
            };

            dispatch({ type: 'AUTH_SUCCESS', payload: { tokens, user } });
          } else {
            // User data missing, re-fetch
            const user = await fetchUser();
            localStorage.setItem('skylapse_user', JSON.stringify(user));

            const tokens = {
              access_token: accessToken,
              refresh_token: refreshToken,
              expires_in: 3600,
              token_type: 'Bearer' as const
            };

            dispatch({ type: 'AUTH_SUCCESS', payload: { tokens, user } });
          }
        } catch (error) {
          console.error('Failed to restore session:', error);
          dispatch({ type: 'AUTH_LOGOUT' });
          clearTokens();
        }
      }
    };

    initializeAuth();
  }, [getStoredTokens, refreshTokens, clearTokens, fetchUser]);

  // Automatic token refresh before expiration
  useEffect(() => {
    if (!state.isAuthenticated || !state.refreshToken) {
      return;
    }

    const refreshInterval = setInterval(async () => {
      const { isExpired } = getStoredTokens();

      // Refresh token if it expires in the next 5 minutes
      const expiresAt = localStorage.getItem('skylapse_token_expires');
      const shouldRefresh = expiresAt ?
        (parseInt(expiresAt) - Date.now()) < 5 * 60 * 1000 : // 5 minutes
        isExpired;

      if (shouldRefresh) {
        await refreshTokens();
      }
    }, 60000); // Check every minute

    return () => clearInterval(refreshInterval);
  }, [state.isAuthenticated, state.refreshToken, getStoredTokens, refreshTokens]);

  const contextValue = useMemo(() => ({
    ...state,
    login,
    logout,
    clearError,
    refreshTokens,
  }), [state, login, logout, clearError, refreshTokens]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Hook for accessing authentication status without full context
export function useAuthStatus() {
  const { isAuthenticated, isLoading, error } = useAuth();
  return { isAuthenticated, isLoading, error };
}

// Higher-order component for protecting routes
export function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600"></div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center space-y-4">
            <h2 className="text-xl font-semibold text-red-600">Authentication Required</h2>
            <p className="text-gray-600">Please log in to access the Skylapse dashboard.</p>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };
}
