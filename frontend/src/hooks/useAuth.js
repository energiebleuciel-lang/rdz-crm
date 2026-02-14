/**
 * Hook d'authentification avec RBAC + Entity Scope
 * - Permissions granulaires (source de vérité)
 * - Entity scope pour super_admin (ZR7/MDL/BOTH)
 * - Persistance localStorage
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API = process.env.REACT_APP_BACKEND_URL || '';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [entityScope, setEntityScopeState] = useState(
    () => localStorage.getItem('entityScope') || null
  );

  useEffect(() => {
    if (token) {
      checkSession();
    } else {
      setLoading(false);
    }
  }, []);

  const checkSession = async () => {
    try {
      const res = await fetch(`${API}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
        // Initialize entity scope
        if (data.role === 'super_admin') {
          if (!entityScope) {
            const stored = localStorage.getItem('entityScope') || 'BOTH';
            setEntityScopeState(stored);
          }
        } else {
          // Non-super_admin: force to user's entity
          setEntityScopeState(data.entity || 'ZR7');
          localStorage.setItem('entityScope', data.entity || 'ZR7');
        }
      } else {
        logout();
      }
    } catch (e) {
      console.error('Session check failed:', e);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const res = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur de connexion');
    }

    const data = await res.json();
    localStorage.setItem('token', data.token);
    setToken(data.token);
    setUser(data.user);

    // Set entity scope
    if (data.user.role === 'super_admin') {
      const stored = localStorage.getItem('entityScope') || 'BOTH';
      setEntityScopeState(stored);
    } else {
      const ent = data.user.entity || 'ZR7';
      setEntityScopeState(ent);
      localStorage.setItem('entityScope', ent);
    }

    return data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const setEntityScope = useCallback((scope) => {
    if (user?.role !== 'super_admin') return;
    const val = scope.toUpperCase();
    if (['ZR7', 'MDL', 'BOTH'].includes(val)) {
      setEntityScopeState(val);
      localStorage.setItem('entityScope', val);
    }
  }, [user]);

  // Fetch with auth + entity scope header
  const authFetch = useCallback(async (url, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (user?.role === 'super_admin' && entityScope) {
      headers['X-Entity-Scope'] = entityScope;
    }

    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
      logout();
      throw new Error('Session expirée');
    }

    return res;
  }, [token, user, entityScope]);

  // Permission check helper
  const hasPermission = useCallback((key) => {
    if (!user) return false;
    if (user.role === 'super_admin') return true;
    return user.permissions?.[key] === true;
  }, [user]);

  // Effective entity for the current scope
  const effectiveEntity = user?.role === 'super_admin' ? entityScope : (user?.entity || 'ZR7');

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      logout,
      authFetch,
      hasPermission,
      entityScope: effectiveEntity,
      setEntityScope,
      isSuperAdmin: user?.role === 'super_admin',
      isAdmin: user?.role === 'admin' || user?.role === 'super_admin',
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
