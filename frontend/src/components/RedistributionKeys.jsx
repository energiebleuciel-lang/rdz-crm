/**
 * Composant pour gérer les 6 clés API de redistribution inter-CRM
 * Utilisé dans la page Paramètres
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Button } from '../components/UI';
import { Key, Eye, EyeOff, Save, RefreshCw } from 'lucide-react';

const PRODUCTS = ['PV', 'PAC', 'ITE'];
const CRMS = [
  { slug: 'zr7', name: 'ZR7 Digital', color: 'blue' },
  { slug: 'mdl', name: 'Maison du Lead', color: 'purple' }
];

export default function RedistributionKeys() {
  const { authFetch } = useAuth();
  const [keys, setKeys] = useState({
    zr7: { PV: '', PAC: '', ITE: '' },
    mdl: { PV: '', PAC: '', ITE: '' }
  });
  const [showKeys, setShowKeys] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      setLoading(true);
      const res = await authFetch(`${API}/api/config/redistribution-keys`);
      if (res.ok) {
        const data = await res.json();
        setKeys(data.keys || {
          zr7: { PV: '', PAC: '', ITE: '' },
          mdl: { PV: '', PAC: '', ITE: '' }
        });
      }
    } catch (e) {
      console.error('Erreur chargement clés:', e);
    } finally {
      setLoading(false);
    }
  };

  const saveKeys = async () => {
    try {
      setSaving(true);
      setMessage(null);
      
      const res = await authFetch(`${API}/api/config/redistribution-keys`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys })
      });
      
      if (res.ok) {
        setMessage({ type: 'success', text: 'Clés enregistrées avec succès !' });
      } else {
        const err = await res.json();
        setMessage({ type: 'error', text: err.detail || 'Erreur lors de la sauvegarde' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const updateKey = (crm, product, value) => {
    setKeys(prev => ({
      ...prev,
      [crm]: {
        ...prev[crm],
        [product]: value
      }
    }));
  };

  const toggleShowKey = (crm, product) => {
    const key = `${crm}-${product}`;
    setShowKeys(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-gradient-to-br from-orange-100 to-red-100 rounded-xl">
          <Key className="w-6 h-6 text-orange-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Clés API Redistribution Inter-CRM</h2>
          <p className="text-sm text-slate-500">
            Utilisées pour envoyer un lead d'un CRM vers l'autre (6 clés par produit)
          </p>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`mb-4 p-3 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      {/* Explication */}
      <div className="mb-6 p-4 bg-slate-50 rounded-lg border border-slate-200">
        <p className="text-sm text-slate-600">
          <strong>Comment ça marche :</strong> Quand un lead de ZR7 est redistribué vers MDL, 
          la clé "Vers MDL" correspondant au produit est utilisée. Le CRM de destination reçoit 
          le lead avec sa propre clé API → permettant le décompte correct.
        </p>
      </div>

      {/* Grille des clés */}
      <div className="space-y-6">
        {CRMS.map(crm => (
          <div key={crm.slug} className="border border-slate-200 rounded-xl overflow-hidden">
            {/* Header CRM */}
            <div className={`px-4 py-3 ${
              crm.color === 'blue' 
                ? 'bg-gradient-to-r from-blue-50 to-blue-100 border-b border-blue-200' 
                : 'bg-gradient-to-r from-purple-50 to-purple-100 border-b border-purple-200'
            }`}>
              <h3 className={`font-semibold ${
                crm.color === 'blue' ? 'text-blue-800' : 'text-purple-800'
              }`}>
                Vers {crm.name} ({crm.slug.toUpperCase()})
              </h3>
              <p className="text-xs text-slate-500">
                Clés utilisées quand l'autre CRM envoie un lead vers {crm.name}
              </p>
            </div>

            {/* Clés par produit */}
            <div className="p-4 space-y-3">
              {PRODUCTS.map(product => {
                const keyId = `${crm.slug}-${product}`;
                const isVisible = showKeys[keyId];
                const value = keys[crm.slug]?.[product] || '';
                
                return (
                  <div key={product} className="flex items-center gap-3">
                    <div className="w-16">
                      <span className={`inline-flex items-center justify-center px-2 py-1 text-xs font-bold rounded ${
                        product === 'PV' ? 'bg-yellow-100 text-yellow-700' :
                        product === 'PAC' ? 'bg-green-100 text-green-700' :
                        'bg-orange-100 text-orange-700'
                      }`}>
                        {product}
                      </span>
                    </div>
                    
                    <div className="flex-1 relative">
                      <input
                        type={isVisible ? 'text' : 'password'}
                        value={value}
                        onChange={(e) => updateKey(crm.slug, product, e.target.value)}
                        placeholder={`Clé API ${product} pour ${crm.slug.toUpperCase()}`}
                        className="w-full px-3 py-2 pr-10 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                      />
                      <button
                        type="button"
                        onClick={() => toggleShowKey(crm.slug, product)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                      >
                        {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    
                    {value && (
                      <span className="text-xs text-green-600">✓</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Bouton sauvegarder */}
      <div className="mt-6 flex justify-end">
        <Button onClick={saveKeys} disabled={saving}>
          {saving ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Enregistrement...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Enregistrer les clés
            </>
          )}
        </Button>
      </div>
    </Card>
  );
}
