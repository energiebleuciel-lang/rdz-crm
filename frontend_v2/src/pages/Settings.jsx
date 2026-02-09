/**
 * Page Paramètres
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Loading, Button, Input, Badge } from '../components/UI';
import { Key, Shield, Copy, Database, CheckCircle, XCircle, Edit, Save } from 'lucide-react';

export default function Settings() {
  const { authFetch } = useAuth();
  const [apiKey, setApiKey] = useState('');
  const [crms, setCrms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showKey, setShowKey] = useState(false);
  const [editingCrm, setEditingCrm] = useState(null);
  const [editCommandes, setEditCommandes] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // API Key
      const keyRes = await authFetch(`${API}/api/settings/api-key`);
      if (keyRes.ok) {
        const data = await keyRes.json();
        setApiKey(data.api_key);
      }
      
      // CRMs
      const crmsRes = await authFetch(`${API}/api/crms`);
      if (crmsRes.ok) {
        const data = await crmsRes.json();
        setCrms(data.crms || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const initCrms = async () => {
    try {
      const res = await authFetch(`${API}/api/crms/init`, { method: 'POST' });
      if (res.ok) {
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const copyApiKey = () => {
    navigator.clipboard.writeText(apiKey);
    alert('Clé API copiée !');
  };

  const startEditCommandes = (crm) => {
    setEditingCrm(crm);
    setEditCommandes(JSON.stringify(crm.commandes || {}, null, 2));
  };

  const saveCommandes = async () => {
    try {
      const commandes = JSON.parse(editCommandes);
      const res = await authFetch(`${API}/api/crms/${editingCrm.id}/commandes`, {
        method: 'PUT',
        body: JSON.stringify(commandes)
      });
      
      if (res.ok) {
        setEditingCrm(null);
        loadData();
        alert('Commandes mises à jour !');
      }
    } catch (e) {
      if (e instanceof SyntaxError) {
        alert('JSON invalide');
      } else {
        alert('Erreur: ' + e.message);
      }
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Paramètres</h1>

      {/* Clé API Globale */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <Key className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-800">Clé API Globale</h2>
              <p className="text-sm text-slate-500">Pour soumettre des leads depuis vos formulaires</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-green-500" />
            <span className="text-sm text-green-600 font-medium">Clé permanente</span>
          </div>
        </div>

        <div className="bg-slate-100 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <code className="font-mono text-sm break-all">
              {showKey ? apiKey : '••••••••••••••••••••••••••••••'}
            </code>
            <div className="flex gap-2 ml-4">
              <button
                onClick={() => setShowKey(!showKey)}
                className="text-slate-500 hover:text-slate-700"
              >
                {showKey ? 'Masquer' : 'Afficher'}
              </button>
              <button
                onClick={copyApiKey}
                className="flex items-center gap-1 text-blue-600 hover:text-blue-800"
              >
                <Copy className="w-4 h-4" />
                Copier
              </button>
            </div>
          </div>
          <p className="text-sm text-slate-500">
            Usage: <code className="bg-white px-2 py-0.5 rounded">Authorization: Token {showKey ? apiKey.slice(0, 20) + '...' : '••••••'}</code>
          </p>
        </div>
      </Card>

      {/* CRMs */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Database className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-800">CRMs Externes</h2>
              <p className="text-sm text-slate-500">Configuration des CRMs de destination</p>
            </div>
          </div>
          {crms.length === 0 && (
            <Button onClick={initCrms}>Initialiser CRMs</Button>
          )}
        </div>

        {crms.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            Aucun CRM configuré. Cliquez sur "Initialiser CRMs" pour ajouter ZR7 et MDL.
          </div>
        ) : (
          <div className="space-y-4">
            {crms.map(crm => (
              <div key={crm.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-slate-800">{crm.name}</h3>
                    <Badge variant="info">{crm.slug.toUpperCase()}</Badge>
                  </div>
                  <button
                    onClick={() => startEditCommandes(crm)}
                    className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    <Edit className="w-4 h-4" />
                    Éditer commandes
                  </button>
                </div>
                
                <p className="text-sm text-slate-500 mb-3">
                  API: <code className="bg-slate-100 px-2 py-0.5 rounded text-xs">{crm.api_url}</code>
                </p>

                {/* Commandes */}
                <div className="bg-slate-50 p-3 rounded">
                  <p className="text-sm font-medium text-slate-700 mb-2">Commandes actives:</p>
                  {Object.keys(crm.commandes || {}).length === 0 ? (
                    <p className="text-sm text-slate-500">Aucune commande configurée</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(crm.commandes || {}).map(([product, depts]) => (
                        <div key={product} className="flex items-center gap-1">
                          <Badge variant="info">{product}</Badge>
                          <span className="text-xs text-slate-500">
                            → {Array.isArray(depts) ? depts.join(', ') : depts}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Modal édition commandes */}
      {editingCrm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setEditingCrm(null)} />
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-4">
              Commandes - {editingCrm.name}
            </h3>
            
            <p className="text-sm text-slate-500 mb-4">
              Format: {"{"}"PRODUIT": ["dept1", "dept2"]{"}"}
            </p>
            
            <textarea
              value={editCommandes}
              onChange={e => setEditCommandes(e.target.value)}
              className="w-full h-48 font-mono text-sm p-4 border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
              placeholder='{"PAC": ["75", "92"], "PV": ["13", "31"]}'
            />
            
            <p className="text-xs text-slate-400 mt-2 mb-4">
              Exemple: un lead PAC du 75 ira vers ce CRM si "75" est dans la liste PAC
            </p>
            
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setEditingCrm(null)}>
                Annuler
              </Button>
              <Button onClick={saveCommandes}>
                <Save className="w-4 h-4" />
                Enregistrer
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
