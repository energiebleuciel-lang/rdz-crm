/**
 * Page Paramètres - Clé API et configuration CRMs
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Loading, Button, Badge } from '../components/UI';
import { Key, Copy, Database, CheckCircle, RefreshCw, Eye, EyeOff } from 'lucide-react';

export default function Settings() {
  const { authFetch } = useAuth();
  const [apiKey, setApiKey] = useState('');
  const [crms, setCrms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // API Key
      const keyRes = await authFetch(`${API}/api/config/api-key`);
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
        alert('CRMs initialisés !');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const regenerateKey = async () => {
    if (!window.confirm('Régénérer la clé API ? Les anciens scripts ne fonctionneront plus.')) return;
    
    try {
      const res = await authFetch(`${API}/api/config/api-key/regenerate`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setApiKey(data.api_key);
        alert('Nouvelle clé générée !');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const copyApiKey = async () => {
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = apiKey;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Paramètres</h1>

      {/* Clé API Globale */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-amber-100 rounded-xl">
            <Key className="w-6 h-6 text-amber-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Clé API Globale</h2>
            <p className="text-sm text-slate-500">Utilisée pour authentifier les soumissions de leads</p>
          </div>
        </div>
        
        <div className="bg-slate-900 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <code className="text-green-400 font-mono text-sm">
              {showKey ? apiKey : '••••••••••••••••••••••••••••••••••••••••'}
            </code>
            <div className="flex gap-2">
              <button
                onClick={() => setShowKey(!showKey)}
                className="p-2 text-slate-400 hover:text-white transition-colors"
                title={showKey ? "Masquer" : "Afficher"}
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
              <button
                onClick={copyApiKey}
                className={`p-2 transition-colors ${copied ? 'text-green-400' : 'text-slate-400 hover:text-white'}`}
                title="Copier"
              >
                {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
        
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-slate-500">
            Cette clé doit être incluse dans le header <code className="bg-slate-100 px-1 rounded">Authorization: Token [clé]</code>
          </p>
          <Button variant="secondary" size="sm" onClick={regenerateKey}>
            <RefreshCw className="w-4 h-4" />
            Régénérer
          </Button>
        </div>
      </Card>

      {/* CRMs Configurés */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-xl">
              <Database className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">CRMs Configurés</h2>
              <p className="text-sm text-slate-500">Destinations pour le routage des leads</p>
            </div>
          </div>
          
          {crms.length === 0 && (
            <Button onClick={initCrms}>
              Initialiser CRMs
            </Button>
          )}
        </div>
        
        {crms.length > 0 ? (
          <div className="space-y-3">
            {crms.map(crm => (
              <div key={crm.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                <div>
                  <h3 className="font-medium text-slate-800">{crm.name}</h3>
                  <p className="text-sm text-slate-500">{crm.slug?.toUpperCase()}</p>
                </div>
                <div className="text-right">
                  <Badge variant="success">Actif</Badge>
                  <p className="text-xs text-slate-500 mt-1 truncate max-w-[200px]">
                    {crm.api_url || 'URL non configurée'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-slate-500 py-8">
            Aucun CRM configuré. Cliquez sur "Initialiser CRMs" pour créer MDL et ZR7.
          </p>
        )}
        
        <p className="text-xs text-slate-500 mt-4">
          💡 Pour gérer les commandes par département/produit, allez dans <a href="/commandes" className="text-blue-600 hover:underline">Commandes</a>
        </p>
      </Card>
    </div>
  );
}
