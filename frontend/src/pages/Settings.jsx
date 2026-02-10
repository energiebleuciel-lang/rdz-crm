/**
 * Page Paramètres - Configuration système
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Loading, Button, Badge } from '../components/UI';
import { Key, Copy, Database, CheckCircle, Eye, EyeOff, Shield, Server } from 'lucide-react';

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
      
      // API Key (ancienne clé globale - pour info)
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

      {/* Nouveau système v2 - Clés API par Formulaire */}
      <Card className="p-6 border-2 border-green-200 bg-green-50/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-green-100 rounded-xl">
            <Server className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Clés API CRM (v2)</h2>
            <p className="text-sm text-slate-500">Chaque formulaire a sa propre clé API</p>
          </div>
          <Badge variant="success" className="ml-auto">Sécurisé</Badge>
        </div>
        
        <div className="bg-white rounded-lg p-4 space-y-3">
          {/* ZR7 */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                ZR7
              </div>
              <div>
                <h4 className="font-medium text-slate-800">ZR7 Digital</h4>
                <p className="text-xs text-slate-500">app.zr7-digital.fr</p>
              </div>
            </div>
            <Badge variant="info">Par formulaire</Badge>
          </div>
          
          {/* MDL */}
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                MDL
              </div>
              <div>
                <h4 className="font-medium text-slate-800">Maison du Lead</h4>
                <p className="text-xs text-slate-500">maison-du-lead.com</p>
              </div>
            </div>
            <Badge variant="info">Par formulaire</Badge>
          </div>
        </div>
        
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm text-blue-800">
            <Shield className="w-4 h-4 inline mr-1" />
            <strong>Configuration par formulaire</strong> - Chaque formulaire a son propre <code className="bg-blue-100 px-1 rounded">target_crm</code> et <code className="bg-blue-100 px-1 rounded">crm_api_key</code>.
            Les clés ne sont jamais exposées dans les scripts client.
          </p>
          <p className="text-sm text-blue-700 mt-2">
            → Configurez les clés API dans <a href="/forms" className="underline font-medium">Formulaires</a>
          </p>
        </div>
      </Card>

      {/* Ancienne clé API Globale (pour référence) */}
      <Card className="p-6 opacity-75">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-slate-100 rounded-xl">
            <Key className="w-6 h-6 text-slate-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Ancienne Clé API (v1)</h2>
            <p className="text-sm text-slate-500">Utilisée par les anciens scripts - Dépréciée</p>
          </div>
          <Badge variant="warning" className="ml-auto">Dépréciée</Badge>
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
        
        <p className="text-xs text-slate-500 mt-4">
          ⚠️ Les nouveaux scripts v2 n'utilisent plus cette clé. Elle reste disponible pour les anciens formulaires.
        </p>
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
