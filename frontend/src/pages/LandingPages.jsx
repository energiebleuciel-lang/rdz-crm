/**
 * Page Landing Pages - Création LP+Form en duo
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Input, Select, Loading, EmptyState, Badge } from '../components/UI';
import { Globe, Plus, Edit, Trash2, Copy, Code, ExternalLink, Link2, AlertTriangle, Check, Clipboard, FileDown } from 'lucide-react';

export default function LandingPages() {
  const { authFetch } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const navigate = useNavigate();
  const [lps, setLps] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showBriefModal, setShowBriefModal] = useState(false);
  const [editingLp, setEditingLp] = useState(null);
  const [briefData, setBriefData] = useState(null);
  const [selectedBriefProduct, setSelectedBriefProduct] = useState('');
  const [selectedBriefMode, setSelectedBriefMode] = useState('separate');
  const [currentBriefLp, setCurrentBriefLp] = useState(null);
  
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

  const openBrief = async (lp, product = null, mode = null) => {
    try {
      // Vérifier si la LP a le nouveau format (form_id)
      if (!lp.form_id && !lp.form) {
        alert('Cette LP a été créée avec l\'ancien format.\nPour avoir le Brief avec les scripts synchronisés, veuillez dupliquer cette LP ou en créer une nouvelle.');
        return;
      }
      
      setCurrentBriefLp(lp);
      
      // Déterminer le mode par défaut : si même URL → Mode B suggéré
      const defaultMode = mode || (lp.url === lp.form?.url ? 'integrated' : 'separate');
      
      // Construire l'URL avec le mode et le produit
      let url = `${API}/api/lps/${lp.id}/brief?mode=${defaultMode}`;
      if (product) {
        url += `&selected_product=${product}`;
      }
      
      const res = await authFetch(url);
      if (res.ok) {
        const data = await res.json();
        if (data.error) {
          alert('Erreur: ' + data.error);
          return;
        }
        setBriefData(data);
        setSelectedBriefProduct(product || lp.product_type || '');
        setSelectedBriefMode(defaultMode);
        setShowBriefModal(true);
      } else {
        const err = await res.json();
        alert('Erreur: ' + (err.detail || err.error || 'Impossible de charger le Brief'));
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };
  
  // Recharger le brief avec un nouveau mode ou produit
  const reloadBrief = async (mode = null, product = null) => {
    if (!currentBriefLp) return;
    
    const newMode = mode || selectedBriefMode;
    const newProduct = product !== undefined ? product : selectedBriefProduct;
    
    if (mode) setSelectedBriefMode(newMode);
    if (product !== undefined) setSelectedBriefProduct(newProduct);
    
    try {
      let url = `${API}/api/lps/${currentBriefLp.id}/brief?mode=${newMode}`;
      if (newProduct) {
        url += `&selected_product=${newProduct}`;
      }
      
      const res = await authFetch(url);
      if (res.ok) {
        const data = await res.json();
        if (!data.error) {
          setBriefData(data);
        }
      }
    } catch (e) {
      console.error('Error reloading brief:', e);
    }
  };
  
  // Alias pour compatibilité
  const reloadBriefWithProduct = (product) => reloadBrief(null, product);

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
        title={editingLp ? 'Modifier LP + Form' : '⚡ Nouvelle LP + Form'}
        size={editingLp ? "lg" : "md"}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* CRÉATION SIMPLIFIÉE - Seulement 3 champs */}
          {!editingLp && (
            <>
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-green-700">
                  ✨ Création rapide en 3 clics. Tout est automatique !
                </p>
              </div>
              
              {accounts.length > 1 && (
                <Select
                  label="Compte"
                  value={form.account_id}
                  onChange={e => setForm({...form, account_id: e.target.value})}
                  options={accounts.map(a => ({ value: a.id, label: a.name }))}
                  required
                />
              )}
              
              <Input
                label="Nom de la LP"
                value={form.name}
                onChange={e => setForm({...form, name: e.target.value})}
                placeholder="Ex: LP PAC Île-de-France"
                required
                autoFocus
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
                  { value: 'PV', label: '☀️ PV - Panneaux solaires' },
                  { value: 'PAC', label: '❄️ PAC - Pompe à chaleur' },
                  { value: 'ITE', label: '🏠 ITE - Isolation' }
                ]}
              />

              <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-600 space-y-1">
                <p className="font-medium text-slate-700">✅ Créé automatiquement :</p>
                <p>• LP avec code unique (LP-XXX)</p>
                <p>• Formulaire lié (PV/PAC/ITE-XXX)</p>
                <p>• Liaison LP ↔ Form</p>
                <p>• Scripts de tracking prêts</p>
              </div>
            </>
          )}

          {/* ÉDITION AVANCÉE - Plus d'options */}
          {editingLp && (
            <>
              <Select
                label="Compte"
                value={form.account_id}
                onChange={e => setForm({...form, account_id: e.target.value})}
                options={accounts.map(a => ({ value: a.id, label: a.name }))}
                required
                disabled
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

              {/* CRM API Key */}
              <div className="border-t pt-4 mt-4">
                <Input
                  label="Clé API CRM (optionnel)"
                  value={form.crm_api_key}
                  onChange={e => setForm({...form, crm_api_key: e.target.value})}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Laissez vide pour utiliser la clé du compte
                </p>
              </div>
            </>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {editingLp ? 'Enregistrer' : '⚡ Créer LP + Form'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal Brief */}
      <Modal 
        isOpen={showBriefModal} 
        onClose={() => { setShowBriefModal(false); setCopySuccess(null); }}
        title={`Brief - ${briefData?.metadata?.liaison_code || briefData?.lp?.code || ''}`}
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
            
            {/* Sélecteur de MODE */}
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
              <h4 className="font-medium text-indigo-800 mb-2">📐 Mode d'intégration</h4>
              <p className="text-sm text-indigo-700 mb-3">
                Choisissez selon votre architecture de pages :
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => reloadBrief('separate')}
                  className={`flex-1 px-4 py-3 rounded-lg font-medium transition-all border-2 ${
                    selectedBriefMode === 'separate'
                      ? 'bg-indigo-500 text-white border-indigo-500'
                      : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'
                  }`}
                >
                  <div className="text-left">
                    <div className="font-semibold">Mode A - Séparé</div>
                    <div className={`text-xs mt-1 ${selectedBriefMode === 'separate' ? 'text-indigo-100' : 'text-slate-500'}`}>
                      LP et Formulaire sur pages distinctes
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => reloadBrief('integrated')}
                  className={`flex-1 px-4 py-3 rounded-lg font-medium transition-all border-2 ${
                    selectedBriefMode === 'integrated'
                      ? 'bg-indigo-500 text-white border-indigo-500'
                      : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'
                  }`}
                >
                  <div className="text-left">
                    <div className="font-semibold">Mode B - Intégré</div>
                    <div className={`text-xs mt-1 ${selectedBriefMode === 'integrated' ? 'text-indigo-100' : 'text-slate-500'}`}>
                      Formulaire intégré dans la LP
                    </div>
                  </div>
                </button>
              </div>
            </div>
            
            {/* Sélecteur de produit */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h4 className="font-medium text-amber-800 mb-2">🎯 Type de produit (URL de redirection)</h4>
              <div className="flex gap-2">
                {['PV', 'PAC', 'ITE'].map(product => {
                  const isSelected = selectedBriefProduct === product;
                  return (
                    <button
                      key={product}
                      onClick={() => reloadBriefWithProduct(product)}
                      className={`px-4 py-2 rounded-lg font-medium transition-all ${
                        isSelected
                          ? product === 'PV' ? 'bg-amber-500 text-white' 
                          : product === 'PAC' ? 'bg-blue-500 text-white'
                          : 'bg-green-500 text-white'
                          : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-400'
                      }`}
                    >
                      {product}
                    </button>
                  );
                })}
              </div>
            </div>
            
            {/* Métadonnées */}
            <div className="bg-slate-50 p-4 rounded-lg">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">LP:</span>
                  <span className="ml-2 font-medium">{briefData.lp?.code}</span>
                  {briefData.lp?.url && (
                    <a href={briefData.lp.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600">
                      <ExternalLink className="w-3 h-3 inline" />
                    </a>
                  )}
                </div>
                <div>
                  <span className="text-slate-500">Form:</span>
                  <span className="ml-2 font-medium">{briefData.form?.code}</span>
                  {briefData.form?.url && (
                    <a href={briefData.form.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600">
                      <ExternalLink className="w-3 h-3 inline" />
                    </a>
                  )}
                </div>
                <div className="col-span-2">
                  <span className="text-slate-500">Liaison:</span>
                  <code className="ml-2 bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">{briefData.metadata?.liaison_code}</code>
                </div>
              </div>
            </div>

            {/* GTM HEAD */}
            {briefData.gtm?.head && (
              <div className="border-2 border-purple-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-purple-800">GTM - À coller dans &lt;head&gt; uniquement</h3>
                  <button
                    onClick={() => copyScript(briefData.gtm.head)}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg font-medium transition-colors"
                  >
                    <Clipboard className="w-4 h-4" />
                    Copier
                  </button>
                </div>
                <div className="bg-red-50 border border-red-200 rounded p-2 mb-2 text-xs text-red-700">
                  ⚠️ Ne jamais mettre ce code dans &lt;body&gt; ou &lt;noscript&gt;
                </div>
                <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-32">
                  {briefData.gtm.head}
                </pre>
              </div>
            )}

            {/* Scripts selon le mode */}
            {selectedBriefMode === 'separate' ? (
              <>
                {/* Mode A - Script LP */}
                <div className="border-2 border-blue-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-blue-800">Script LP - fin de &lt;body&gt;</h3>
                    <button
                      onClick={() => copyScript(briefData.scripts?.lp?.code)}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                    >
                      <Clipboard className="w-4 h-4" />
                      Copier
                    </button>
                  </div>
                  <p className="text-sm text-slate-600 mb-2">
                    À coller sur : <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.lp?.url}</code>
                  </p>
                  <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-48">
                    {briefData.scripts?.lp?.code}
                  </pre>
                  <div className="mt-2 text-xs text-blue-700 bg-blue-50 p-2 rounded">
                    <strong>Auto-bind CTA :</strong> Les liens vers le formulaire sont détectés automatiquement, ou ajoutez <code>data-rdz-cta</code>
                  </div>
                </div>

                {/* Mode A - Script Form */}
                <div className="border-2 border-orange-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-orange-800">Script Form - fin de &lt;body&gt;</h3>
                    <button
                      onClick={() => copyScript(briefData.scripts?.form?.code)}
                      className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-colors"
                    >
                      <Clipboard className="w-4 h-4" />
                      Copier
                    </button>
                  </div>
                  <p className="text-sm text-slate-600 mb-2">
                    À coller sur : <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.form?.url}</code>
                  </p>
                  <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-48">
                    {briefData.scripts?.form?.code}
                  </pre>
                  <div className="mt-2 text-xs text-orange-700 bg-orange-50 p-2 rounded space-y-1">
                    <p><strong>Auto-bind Form Start :</strong> Premier clic/focus détecté automatiquement</p>
                    <p><strong>Soumission :</strong> <code>rdzSubmitLead(&#123;phone, nom, departement, ...&#125;)</code></p>
                  </div>
                </div>
              </>
            ) : (
              /* Mode B - Script unique */
              <div className="border-2 border-green-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-green-800">Script unique LP+Form - fin de &lt;body&gt;</h3>
                  <button
                    onClick={() => copyScript(briefData.scripts?.unique?.code)}
                    className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                  >
                    <Clipboard className="w-4 h-4" />
                    Copier
                  </button>
                </div>
                <p className="text-sm text-slate-600 mb-2">
                  À coller sur : <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.lp?.url}</code>
                </p>
                <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-64">
                  {briefData.scripts?.unique?.code}
                </pre>
                <div className="mt-2 text-xs text-green-700 bg-green-50 p-2 rounded space-y-1">
                  <p><strong>Auto-bind CTA :</strong> Les liens anchor (#formulaire, etc.) sont détectés automatiquement</p>
                  <p><strong>Auto-bind Form Start :</strong> Premier clic/focus détecté automatiquement</p>
                  <p><strong>Soumission :</strong> <code>rdzSubmitLead(&#123;phone, nom, departement, ...&#125;)</code></p>
                </div>
              </div>
            )}

            {/* Instructions */}
            {briefData.instructions && (
              <div className="border rounded-lg p-4 bg-slate-50">
                <h3 className="font-semibold text-slate-800 mb-3">📋 Instructions d'intégration</h3>
                <p className="text-sm text-slate-600 mb-3">{briefData.instructions.summary}</p>
                
                <div className="text-xs space-y-2">
                  <div className="bg-white p-2 rounded border">
                    <strong>Champs requis :</strong> {briefData.instructions.field_names?.required?.join(', ')}
                  </div>
                  <div className="bg-white p-2 rounded border">
                    <strong>Validation téléphone :</strong> 10 chiffres exactement
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
