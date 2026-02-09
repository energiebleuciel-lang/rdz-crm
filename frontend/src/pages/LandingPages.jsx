/**
 * Page Landing Pages - Création LP+Form en duo
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Input, Select, Loading, EmptyState, Badge } from '../components/UI';
import { Globe, Plus, Edit, Trash2, Copy, Code, ExternalLink, Link2, AlertTriangle, Check, Clipboard } from 'lucide-react';

export default function LandingPages() {
  const { authFetch } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const [lps, setLps] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showBriefModal, setShowBriefModal] = useState(false);
  const [editingLp, setEditingLp] = useState(null);
  const [briefData, setBriefData] = useState(null);
  
  const [form, setForm] = useState({
    account_id: '',
    name: '',
    url: '',
    product_type: 'PV',
    form_mode: 'redirect',
    form_url: '',
    tracking_type: 'redirect',
    redirect_url: '/merci',
    source_type: 'native',
    source_name: '',
    crm_api_key: '',
    notes: ''
  });

  useEffect(() => {
    if (selectedCRM) {
      loadData();
    }
  }, [selectedCRM]);

  const loadData = async () => {
    try {
      setLoading(true);
      const accountsRes = await authFetch(`${API}/api/accounts?crm_id=${selectedCRM}`);
      let accountsList = [];
      if (accountsRes.ok) {
        const data = await accountsRes.json();
        accountsList = data.accounts || [];
        setAccounts(accountsList);
      }
      
      const accountIds = accountsList.map(a => a.id);
      const lpsRes = await authFetch(`${API}/api/lps`);
      
      if (lpsRes.ok) {
        const data = await lpsRes.json();
        const filteredLps = (data.lps || []).filter(l => accountIds.includes(l.account_id));
        setLps(filteredLps);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditingLp(null);
    setForm({
      account_id: accounts[0]?.id || '',
      name: '',
      url: '',
      product_type: 'PV',
      form_mode: 'redirect',
      form_url: '',
      tracking_type: 'redirect',
      redirect_url: '/merci',
      source_type: 'native',
      source_name: '',
      crm_api_key: '',
      notes: ''
    });
    setShowModal(true);
  };

  const openEdit = (lp) => {
    setEditingLp(lp);
    setForm({
      account_id: lp.account_id,
      name: lp.name,
      url: lp.url,
      product_type: lp.product_type || 'PV',
      form_mode: lp.form_mode || 'redirect',
      form_url: lp.form_url || '',
      tracking_type: lp.tracking_type || 'redirect',
      redirect_url: lp.redirect_url || '/merci',
      source_type: lp.source_type || 'native',
      source_name: lp.source_name || '',
      crm_api_key: lp.crm_api_key || '',
      notes: lp.notes || ''
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const url = editingLp 
        ? `${API}/api/lps/${editingLp.id}`
        : `${API}/api/lps`;
      
      const res = await authFetch(url, {
        method: editingLp ? 'PUT' : 'POST',
        body: JSON.stringify(form)
      });
      
      if (res.ok) {
        const data = await res.json();
        setShowModal(false);
        loadData();
        
        if (!editingLp && data.codes) {
          alert(`LP + Form créés avec succès!\n\nLP: ${data.codes.lp_code}\nForm: ${data.codes.form_code}\nLiaison: ${data.codes.liaison_code}`);
        }
      } else {
        const err = await res.json();
        alert(err.detail || 'Erreur');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleDelete = async (lp) => {
    if (!window.confirm(`Archiver "${lp.name}" et son formulaire lié ?`)) return;
    
    try {
      const res = await authFetch(`${API}/api/lps/${lp.id}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleDuplicate = async (lp) => {
    try {
      const res = await authFetch(`${API}/api/lps/${lp.id}/duplicate`, {
        method: 'POST'
      });
      
      if (res.ok) {
        const data = await res.json();
        loadData();
        alert(`Dupliqué!\n\nNouvelle LP: ${data.codes.lp_code}\nNouveau Form: ${data.codes.form_code}`);
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const openBrief = async (lp) => {
    try {
      // Vérifier si la LP a le nouveau format (form_id)
      if (!lp.form_id && !lp.form) {
        alert('Cette LP a été créée avec l\'ancien format.\nPour avoir le Brief avec les scripts synchronisés, veuillez dupliquer cette LP ou en créer une nouvelle.');
        return;
      }
      
      const res = await authFetch(`${API}/api/lps/${lp.id}/brief`);
      if (res.ok) {
        const data = await res.json();
        if (data.error) {
          alert('Erreur: ' + data.error);
          return;
        }
        setBriefData(data);
        setShowBriefModal(true);
      } else {
        const err = await res.json();
        alert('Erreur: ' + (err.detail || err.error || 'Impossible de charger le Brief'));
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const [copySuccess, setCopySuccess] = useState(null);

  const copyScript = async (script) => {
    try {
      // Méthode moderne
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(script);
        setCopySuccess('Script copié !');
        setTimeout(() => setCopySuccess(null), 2000);
        return;
      }
      
      // Fallback avec textarea
      const textarea = document.createElement('textarea');
      textarea.value = script;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '-9999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      
      const successful = document.execCommand('copy');
      document.body.removeChild(textarea);
      
      if (successful) {
        setCopySuccess('Script copié !');
        setTimeout(() => setCopySuccess(null), 2000);
      } else {
        throw new Error('execCommand failed');
      }
    } catch (err) {
      console.error('Copy failed:', err);
      // Dernier fallback: ouvrir dans une nouvelle fenêtre
      const blob = new Blob([script], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const newWindow = window.open(url, '_blank');
      if (!newWindow) {
        alert('Impossible de copier. Sélectionnez le texte manuellement.');
      } else {
        setCopySuccess('Script ouvert dans un nouvel onglet');
        setTimeout(() => setCopySuccess(null), 3000);
      }
    }
  };

  const getAccountName = (accountId) => {
    const account = accounts.find(a => a.id === accountId);
    return account?.name || 'N/A';
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Landing Pages</h1>
          <p className="text-sm text-slate-500">
            CRM: <span className="font-medium text-slate-700">{currentCRM?.name}</span>
            <span className="ml-4 text-xs text-amber-600">1 LP = 1 Form (créés ensemble)</span>
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Nouvelle LP + Form
        </Button>
      </div>

      {lps.length === 0 ? (
        <Card className="p-8">
          <EmptyState 
            icon={Globe}
            title="Aucune Landing Page"
            description="Créez votre première LP (le formulaire sera créé automatiquement)"
            action={<Button onClick={openCreate}>Créer LP + Form</Button>}
          />
        </Card>
      ) : (
        <div className="grid gap-4">
          {lps.map(lp => (
            <Card key={lp.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge variant="default">{lp.code}</Badge>
                    <h3 className="font-semibold text-slate-800">{lp.name}</h3>
                    {lp.form_id || lp.form ? (
                      <Badge variant={lp.form_mode === 'embedded' ? 'success' : 'info'}>
                        {lp.form_mode === 'embedded' ? 'Embedded' : 'Redirect'}
                      </Badge>
                    ) : (
                      <Badge variant="warning" className="flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        Ancien format
                      </Badge>
                    )}
                    {lp.product_type && <Badge variant="warning">{lp.product_type}</Badge>}
                  </div>
                  
                  <div className="text-sm text-slate-500 space-y-1">
                    <p>
                      <span className="text-slate-400">LP:</span>{' '}
                      <a href={lp.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                        {lp.url}
                      </a>
                    </p>
                    {lp.form && (
                      <p>
                        <span className="text-slate-400">Form ({lp.form.code}):</span>{' '}
                        <a href={lp.form.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                          {lp.form.url}
                        </a>
                      </p>
                    )}
                    {lp.liaison_code && (
                      <p>
                        <span className="text-slate-400">Liaison:</span>{' '}
                        <code className="bg-slate-100 px-2 py-0.5 rounded text-xs">{lp.liaison_code}</code>
                      </p>
                    )}
                  </div>

                  {/* Stats */}
                  {lp.stats && (
                    <div className="flex gap-6 mt-3 text-sm">
                      <div>
                        <span className="text-slate-400">Visites LP:</span>{' '}
                        <span className="font-medium">{lp.stats.visits || 0}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Clics CTA:</span>{' '}
                        <span className="font-medium">{lp.stats.cta_clicks || 0}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Forms démarrés:</span>{' '}
                        <span className="font-medium">{lp.stats.form_starts || 0}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Leads:</span>{' '}
                        <span className="font-medium text-green-600">{lp.stats.form_submits || 0}</span>
                      </div>
                      {lp.stats.visits > 0 && (
                        <div>
                          <span className="text-slate-400">Conversion:</span>{' '}
                          <span className="font-medium text-blue-600">
                            {((lp.stats.form_submits || 0) / lp.stats.visits * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                <div className="flex gap-2">
                  <button
                    onClick={() => openBrief(lp)}
                    className="px-3 py-1.5 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 text-sm font-medium flex items-center gap-1"
                  >
                    <Code className="w-4 h-4" />
                    Brief
                  </button>
                  <button
                    onClick={() => handleDuplicate(lp)}
                    className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
                    title="Dupliquer"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => openEdit(lp)}
                    className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
                    title="Modifier"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(lp)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    title="Archiver"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal Créer/Éditer LP+Form */}
      <Modal 
        isOpen={showModal} 
        onClose={() => setShowModal(false)}
        title={editingLp ? 'Modifier LP + Form' : 'Nouvelle LP + Form'}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Select
            label="Compte"
            value={form.account_id}
            onChange={e => setForm({...form, account_id: e.target.value})}
            options={accounts.map(a => ({ value: a.id, label: a.name }))}
            required
          />
          
          <Input
            label="Nom de la LP"
            value={form.name}
            onChange={e => setForm({...form, name: e.target.value})}
            placeholder="LP PAC Île-de-France"
            required
          />
          
          <Input
            label="URL de la LP"
            value={form.url}
            onChange={e => setForm({...form, url: e.target.value})}
            placeholder="https://monsite.com/offre-pac"
            required
          />

          <Select
            label="Type de produit"
            value={form.product_type}
            onChange={e => setForm({...form, product_type: e.target.value})}
            options={[
              { value: 'PV', label: 'PV - Panneaux solaires' },
              { value: 'PAC', label: 'PAC - Pompe à chaleur' },
              { value: 'ITE', label: 'ITE - Isolation' }
            ]}
          />

          {/* Mode LP+Form */}
          <div className="border-t pt-4 mt-4">
            <h4 className="font-medium text-slate-700 mb-3">Mode d'affichage du formulaire</h4>
            
            <div className="grid grid-cols-2 gap-4">
              <label 
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  form.form_mode === 'embedded' 
                    ? 'border-green-500 bg-green-50' 
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="form_mode"
                  value="embedded"
                  checked={form.form_mode === 'embedded'}
                  onChange={e => setForm({...form, form_mode: e.target.value, form_url: ''})}
                  className="sr-only"
                />
                <div className="font-medium text-slate-800">Embedded (même page)</div>
                <p className="text-xs text-slate-500 mt-1">
                  Le formulaire est intégré dans la LP.<br/>
                  → 1 seul script à installer
                </p>
              </label>
              
              <label 
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  form.form_mode === 'redirect' 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="form_mode"
                  value="redirect"
                  checked={form.form_mode === 'redirect'}
                  onChange={e => setForm({...form, form_mode: e.target.value})}
                  className="sr-only"
                />
                <div className="font-medium text-slate-800">Redirect (page séparée)</div>
                <p className="text-xs text-slate-500 mt-1">
                  CTA redirige vers une autre page.<br/>
                  → 2 scripts (LP + Form)
                </p>
              </label>
            </div>

            {form.form_mode === 'redirect' && (
              <Input
                label="URL du formulaire (page séparée)"
                value={form.form_url}
                onChange={e => setForm({...form, form_url: e.target.value})}
                placeholder="https://monsite.com/formulaire-pac"
                className="mt-4"
                required
              />
            )}
          </div>

          {/* Tracking post-submit */}
          <div className="border-t pt-4 mt-4">
            <h4 className="font-medium text-slate-700 mb-3">Après soumission du formulaire</h4>
            
            <Select
              label="Action après submit"
              value={form.tracking_type}
              onChange={e => setForm({...form, tracking_type: e.target.value})}
              options={[
                { value: 'redirect', label: 'Redirection vers page merci' },
                { value: 'gtm', label: 'Déclencher GTM conversion (pas de redirection)' },
                { value: 'both', label: 'GTM + Redirection' },
                { value: 'none', label: 'Rien (le formulaire gère)' }
              ]}
            />

            {(form.tracking_type === 'redirect' || form.tracking_type === 'both') && (
              <Input
                label="URL de redirection"
                value={form.redirect_url}
                onChange={e => setForm({...form, redirect_url: e.target.value})}
                placeholder="/merci"
                className="mt-3"
              />
            )}
          </div>

          {/* Source */}
          <div className="border-t pt-4 mt-4">
            <h4 className="font-medium text-slate-700 mb-3">Source de trafic</h4>
            
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Type de source"
                value={form.source_type}
                onChange={e => setForm({...form, source_type: e.target.value})}
                options={[
                  { value: 'native', label: 'Native / Organique' },
                  { value: 'google', label: 'Google Ads' },
                  { value: 'facebook', label: 'Facebook Ads' },
                  { value: 'other', label: 'Autre' }
                ]}
              />
              
              <Input
                label="Nom de la source (optionnel)"
                value={form.source_name}
                onChange={e => setForm({...form, source_name: e.target.value})}
                placeholder="Taboola, Outbrain..."
              />
            </div>
          </div>

          {/* CRM API Key */}
          <div className="border-t pt-4 mt-4">
            <Input
              label="Clé API CRM (ZR7/MDL)"
              value={form.crm_api_key}
              onChange={e => setForm({...form, crm_api_key: e.target.value})}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {editingLp ? 'Enregistrer' : 'Créer LP + Form'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal Brief */}
      <Modal 
        isOpen={showBriefModal} 
        onClose={() => { setShowBriefModal(false); setCopySuccess(null); }}
        title={`Brief - ${briefData?.lp?.code || ''}`}
        size="xl"
      >
        {briefData && (
          <div className="space-y-6">
            {/* Success Toast */}
            {copySuccess && (
              <div className="fixed top-4 right-4 z-[100] bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 animate-pulse">
                <Check className="w-5 h-5" />
                {copySuccess}
              </div>
            )}
            
            {/* Info */}
            <div className="bg-slate-50 p-4 rounded-lg">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">LP:</span>
                  <span className="ml-2 font-medium">{briefData.lp.code}</span>
                  <a href={briefData.lp.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600">
                    <ExternalLink className="w-3 h-3 inline" />
                  </a>
                </div>
                <div>
                  <span className="text-slate-500">Form:</span>
                  <span className="ml-2 font-medium">{briefData.form.code}</span>
                  <a href={briefData.form.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600">
                    <ExternalLink className="w-3 h-3 inline" />
                  </a>
                </div>
                <div>
                  <span className="text-slate-500">Mode:</span>
                  <Badge variant={briefData.mode === 'embedded' ? 'success' : 'info'} className="ml-2">
                    {briefData.mode === 'embedded' ? 'Embedded (1 script)' : 'Redirect (2 scripts)'}
                  </Badge>
                </div>
                <div>
                  <span className="text-slate-500">Liaison:</span>
                  <code className="ml-2 bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">{briefData.liaison_code}</code>
                </div>
              </div>
            </div>

            {/* Scripts */}
            {briefData.mode === 'embedded' ? (
              // Mode Embedded : 1 script combiné
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-slate-800">🟢 Script Unique (LP + Form)</h3>
                  <button
                    onClick={() => copyScript(briefData.scripts.combined)}
                    className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-medium transition-colors"
                  >
                    <Clipboard className="w-4 h-4" />
                    Copier le script
                  </button>
                </div>
                <p className="text-sm text-slate-600 mb-2">
                  À coller sur: <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.lp.url}</code>
                </p>
                <div className="relative">
                  <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-96 select-all">
                    {briefData.scripts.combined}
                  </pre>
                  <p className="text-xs text-slate-500 mt-1">💡 Triple-clic pour sélectionner tout le script</p>
                </div>
              </div>
            ) : (
              // Mode Redirect : 2 scripts
              <>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-slate-800">🔵 Script LP</h3>
                    <button
                      onClick={() => copyScript(briefData.scripts.lp)}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                    >
                      <Clipboard className="w-4 h-4" />
                      Copier Script LP
                    </button>
                  </div>
                  <p className="text-sm text-slate-600 mb-2">
                    À coller sur: <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.lp.url}</code>
                  </p>
                  <div className="relative">
                    <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-64 select-all">
                      {briefData.scripts.lp}
                    </pre>
                    <p className="text-xs text-slate-500 mt-1">💡 Triple-clic pour sélectionner tout le script</p>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-slate-800">🟠 Script Form</h3>
                    <button
                      onClick={() => copyScript(briefData.scripts.form)}
                      className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-colors"
                    >
                      <Clipboard className="w-4 h-4" />
                      Copier Script Form
                    </button>
                  </div>
                  <p className="text-sm text-slate-600 mb-2">
                    À coller sur: <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.form.url}</code>
                  </p>
                  <div className="relative">
                    <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-64 select-all">
                      {briefData.scripts.form}
                    </pre>
                    <p className="text-xs text-slate-500 mt-1">💡 Triple-clic pour sélectionner tout le script</p>
                  </div>
                </div>
              </>
            )}

            {/* Champs disponibles */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3">📋 Champs de lead disponibles</h3>
              <div className="grid grid-cols-3 gap-2 text-xs">
                {Object.entries(briefData.lead_fields || {}).map(([category, fields]) => (
                  <div key={category} className="border rounded p-2">
                    <h4 className="font-medium text-slate-700 capitalize mb-1">{category}</h4>
                    {fields.map(f => (
                      <div key={f.key} className="text-slate-500">
                        <code>{f.key}</code>
                        {f.required && <span className="text-red-500">*</span>}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
