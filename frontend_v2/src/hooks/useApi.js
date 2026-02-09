/**
 * Hook pour les appels API
 */

import { useState, useCallback } from 'react';
import { useAuth } from './useAuth';

const API = process.env.REACT_APP_BACKEND_URL || '';

export function useApi() {
  const { authFetch } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const request = useCallback(async (endpoint, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const res = await authFetch(`${API}${endpoint}`, options);
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Erreur API');
      }
      
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  const get = useCallback((endpoint) => request(endpoint), [request]);
  
  const post = useCallback((endpoint, body) => 
    request(endpoint, { method: 'POST', body: JSON.stringify(body) }), [request]);
  
  const put = useCallback((endpoint, body) => 
    request(endpoint, { method: 'PUT', body: JSON.stringify(body) }), [request]);
  
  const del = useCallback((endpoint) => 
    request(endpoint, { method: 'DELETE' }), [request]);

  return { get, post, put, del, loading, error };
}

export { API };
