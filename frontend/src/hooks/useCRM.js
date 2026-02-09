/**
 * Context pour la sélection du CRM actif
 * Permet de filtrer toutes les données par CRM
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { API } from './useApi';
import { useAuth } from './useAuth';

const CRMContext = createContext(null);

export function CRMProvider({ children }) {
  const { authFetch, user } = useAuth();
  const [crms, setCrms] = useState([]);
  const [selectedCRM, setSelectedCRM] = useState(null);
  const [loading, setLoading] = useState(true);

  // Charger les CRMs au démarrage
  useEffect(() => {
    if (user) {
      loadCRMs();
    }
  }, [user]);

  const loadCRMs = async () => {
    try {
      setLoading(true);
      const res = await authFetch(`${API}/api/crms`);
      if (res.ok) {
        const data = await res.json();
        const crmList = data.crms || [];
        setCrms(crmList);
        
        // Restaurer la sélection depuis localStorage ou prendre le premier
        const savedCRM = localStorage.getItem('selectedCRM');
        if (savedCRM && crmList.find(c => c.id === savedCRM)) {
          setSelectedCRM(savedCRM);
        } else if (crmList.length > 0) {
          setSelectedCRM(crmList[0].id);
        }
      }
    } catch (e) {
      console.error('Erreur chargement CRMs:', e);
    } finally {
      setLoading(false);
    }
  };

  const selectCRM = (crmId) => {
    setSelectedCRM(crmId);
    localStorage.setItem('selectedCRM', crmId);
  };

  // Obtenir le CRM actuel
  const currentCRM = crms.find(c => c.id === selectedCRM);

  return (
    <CRMContext.Provider value={{
      crms,
      selectedCRM,
      selectCRM,
      currentCRM,
      loading,
      reloadCRMs: loadCRMs
    }}>
      {children}
    </CRMContext.Provider>
  );
}

export function useCRM() {
  const context = useContext(CRMContext);
  if (!context) {
    throw new Error('useCRM must be used within CRMProvider');
  }
  return context;
}
