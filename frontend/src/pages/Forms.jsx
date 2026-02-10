/**
 * Page Formulaires - Filtrée par CRM sélectionné
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Input, Select, Loading, EmptyState, Badge } from '../components/UI';
import { FileText, Plus, Edit, Trash2, Copy, Code, ExternalLink, Link2, Key, Eye, EyeOff } from 'lucide-react';

export default function Forms() {
  const { authFetch } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const [forms, setForms] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [lps, setLps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showBriefModal, setShowBriefModal] = useState(false);
  const [editingForm, setEditingForm] = useState(null);
  const [briefData, setBriefData] = useState(null);
  const [filter, setFilter] = useState('all');
  const [showApiKey, setShowApiKey] = useState(false);
  
  const [form, setForm] = useState({
    account_id: '',
    name: '',
    url: '',
    product_type: 'PV',
    lp_id: '',
    target_crm: '',  // "zr7" ou "mdl"
    crm_api_key: '', // Clé API pour ce formulaire
    allow_cross_crm: true,
    tracking_type: 'redirect',
    redirect_url: '/merci'
  });

  useEffect(() => {
    if (selectedCRM) {
      loadData();
    }
  }, [selectedCRM]);

  const loadData = async () => {
    try {
      setLoading(true);
      // Charger les comptes filtrés par CRM
      const accountsRes = await authFetch(`${API}/api/accounts?crm_id=${selectedCRM}`);
      let accountsList = [];
      if (accountsRes.ok) {
        const data = await accountsRes.json();
        accountsList = data.accounts || [];
        setAccounts(accountsList);
      }
      
      // Charger les forms et LPs des comptes de ce CRM
      const accountIds = accountsList.map(a => a.id);
      
      const [formsRes, lpsRes] = await Promise.all([
        authFetch(`${API}/api/forms`),
        authFetch(`${API}/api/lps`)
      ]);
      
      if (formsRes.ok) {
        const data = await formsRes.json();
        // Filtrer les forms par comptes du CRM
        const filteredForms = (data.forms || []).filter(f => accountIds.includes(f.account_id));
        setForms(filteredForms);
      }
      if (lpsRes.ok) {
        const data = await lpsRes.json();
        // Filtrer les LPs par comptes du CRM
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
    setEditingForm(null);
    setForm({
      account_id: accounts[0]?.id || '',
      name: '',
      url: '',
      product_type: 'PV',
      lp_id: '',
      target_crm: currentCRM?.slug || '',  // Pré-remplir avec le CRM actuel
      crm_api_key: '',
      allow_cross_crm: true,
      tracking_type: 'redirect',
      redirect_url: '/merci'
    });
    setShowApiKey(false);
    setShowModal(true);
  };

  const openEdit = (formItem) => {
    setEditingForm(formItem);
    setForm({
      account_id: formItem.account_id,
      name: formItem.name,
      url: formItem.url,
      product_type: formItem.product_type,
      lp_id: formItem.lp_id || '',
      target_crm: formItem.target_crm || '',
      crm_api_key: formItem.crm_api_key || '',
      allow_cross_crm: formItem.allow_cross_crm !== false,
      tracking_type: formItem.tracking_type || 'redirect',
      redirect_url: formItem.redirect_url || '/merci'
    });
    setShowApiKey(false);
    setShowModal(true);
  };

  const openBrief = async (formItem) => {
    try {
      const res = await authFetch(`${API}/api/forms/${formItem.id}/brief`);
      if (res.ok) {
        const data = await res.json();
        setBriefData(data);
        setShowBriefModal(true);
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!form.url.startsWith('http')) {
      alert('L\'URL doit commencer par http:// ou https://');
      return;
    }
    
    try {
      const url = editingForm 
        ? `${API}/api/forms/${editingForm.id}`
        : `${API}/api/forms`;
      
      const res = await authFetch(url, {
        method: editingForm ? 'PUT' : 'POST',
        body: JSON.stringify(form)
      });
      
      if (res.ok) {
        setShowModal(false);
        loadData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Erreur');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleDuplicate = async (formItem) => {
    try {
      const res = await authFetch(`${API}/api/forms/${formItem.id}/duplicate`, {
        method: 'POST'
      });
      
      if (res.ok) {
        const data = await res.json();
        alert(`Formulaire dupliqué avec le code ${data.code}`);
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleDelete = async (formItem) => {
    if (!window.confirm(`Archiver le formulaire "${formItem.name}" ?`)) return;
    
    try {
      const res = await authFetch(`${API}/api/forms/${formItem.id}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const copyCode = (code) => {
    navigator.clipboard.writeText(code);
    alert('Code copié !');
  };

  const copyScript = (script) => {
    navigator.clipboard.writeText(script);
    alert('Script copié !');
  };

  const filteredForms = filter === 'all' 
    ? forms 
    : forms.filter(f => f.product_type === filter);

  const productColors = {
    PV: 'bg-amber-500',
    PAC: 'bg-blue-500',
    ITE: 'bg-green-500'
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-slate-800">Formulaires</h1>
            
            {/* Filtres */}
            <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
              {['all', 'PV', 'PAC', 'ITE'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  filter === f 
                    ? 'bg-white text-slate-800 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                {f === 'all' ? 'Tous' : f}
              </button>
            ))}
          </div>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            CRM: <span className="font-medium text-slate-700">{currentCRM?.name}</span>
          </p>
        </div>
        
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Nouveau formulaire
        </Button>
      </div>

      {filteredForms.length === 0 ? (
        <Card className="p-8">
          <EmptyState 
            icon={FileText}
            title="Aucun formulaire"
            description={`Créez votre premier formulaire pour ${currentCRM?.name || 'ce CRM'}`}
            action={<Button onClick={openCreate}>Créer un formulaire</Button>}
          />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredForms.map(formItem => (
            <Card key={formItem.id} className="overflow-hidden">
              {/* Header avec couleur produit */}
              <div className={`${productColors[formItem.product_type]} p-4 text-white`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-sm bg-white/20 px-2 py-0.5 rounded">
                    {formItem.code}
                  </span>
                  <span className="text-sm font-medium">{formItem.product_type}</span>
                </div>
                <h3 className="font-semibold text-lg">{formItem.name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  {formItem.account_logo && (
                    <img 
                      src={formItem.account_logo} 
                      alt={formItem.account_name}
                      className="w-6 h-6 rounded bg-white object-contain"
                    />
                  )}
                  <p className="text-sm opacity-90">{formItem.account_name}</p>
                </div>
              </div>

              {/* Body */}
              <div className="p-4">
                {/* URL */}
                <a 
                  href={formItem.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 mb-4 truncate"
                >
                  <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">{formItem.url}</span>
                </a>

                {/* LP liée */}
                {formItem.lp && (
                  <div className="flex items-center gap-2 text-sm text-slate-600 mb-4 bg-slate-50 p-2 rounded">
                    <Link2 className="w-4 h-4" />
                    <span>LP liée: <strong>{formItem.lp.code}</strong></span>
                  </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-3 gap-2 mb-4">
                  <div className="text-center p-2 bg-slate-50 rounded-lg">
                    <p className="text-lg font-bold text-slate-800">{formItem.stats?.started || 0}</p>
                    <p className="text-xs text-slate-500">Démarrés</p>
                  </div>
                  <div className="text-center p-2 bg-slate-50 rounded-lg">
                    <p className="text-lg font-bold text-slate-800">{formItem.stats?.leads || formItem.stats?.finished || 0}</p>
                    <p className="text-xs text-slate-500">Leads</p>
                  </div>
                  <div className="text-center p-2 bg-slate-50 rounded-lg">
                    <p className="text-lg font-bold text-green-600">{formItem.stats?.conversion || 0}%</p>
                    <p className="text-xs text-slate-500">Conv.</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap gap-2 pt-3 border-t">
                  <button
                    onClick={() => openBrief(formItem)}
                    className="flex items-center gap-1 px-3 py-2 text-sm bg-slate-800 text-white rounded-lg hover:bg-slate-700"
                  >
                    <Code className="w-4 h-4" />
                    Brief
                  </button>
                  <button
                    onClick={() => copyCode(formItem.code)}
                    className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => openEdit(formItem)}
                    className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDuplicate(formItem)}
                    className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(formItem)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg ml-auto"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal Créer/Éditer */}
      <Modal 
        isOpen={showModal} 
        onClose={() => setShowModal(false)}
        title={editingForm ? 'Modifier le formulaire' : 'Nouveau formulaire'}
        size="md"
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
            label="Nom du formulaire"
            value={form.name}
            onChange={e => setForm({...form, name: e.target.value})}
            placeholder="Formulaire PAC Île-de-France"
            required
          />
          
          <Input
            label="URL du formulaire"
            value={form.url}
            onChange={e => setForm({...form, url: e.target.value})}
            placeholder="https://form.monsite.com"
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
          
          <Select
            label="LP liée (optionnel)"
            value={form.lp_id}
            onChange={e => setForm({...form, lp_id: e.target.value})}
            options={[
              { value: '', label: 'Aucune LP liée' },
              ...lps.filter(l => l.account_id === form.account_id).map(l => ({ 
                value: l.id, 
                label: `${l.code} - ${l.name}` 
              }))
            ]}
          />

          <div className="border-t pt-4 mt-4">
            <h4 className="font-medium text-slate-700 mb-3">Configuration API</h4>
            
            <Input
              label="Clé API CRM (ZR7/MDL)"
              value={form.crm_api_key}
              onChange={e => setForm({...form, crm_api_key: e.target.value})}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
            
            <div className="mt-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.allow_cross_crm}
                  onChange={e => setForm({...form, allow_cross_crm: e.target.checked})}
                  className="w-4 h-4 rounded border-slate-300 text-amber-500 focus:ring-amber-500"
                />
                <span className="text-sm text-slate-700">Autoriser le Cross-CRM</span>
              </label>
              <p className="text-xs text-slate-500 mt-1 ml-6">
                Si coché et que le CRM principal n'a pas de commande pour ce lead, essayer de l'envoyer à l'autre CRM
              </p>
            </div>
          </div>

          <div className="border-t pt-4 mt-4">
            <h4 className="font-medium text-slate-700 mb-3">Tracking & Redirection après soumission</h4>
            
            <Select
              label="Que faire après la soumission du lead ?"
              value={form.tracking_type}
              onChange={e => setForm({...form, tracking_type: e.target.value})}
              options={[
                { value: 'redirect', label: 'Redirection vers page merci (sans GTM)' },
                { value: 'gtm', label: 'Déclencher GTM uniquement (pas de redirection)' },
                { value: 'both', label: 'GTM + Redirection' },
                { value: 'none', label: 'Rien (le formulaire gère lui-même)' }
              ]}
            />

            <p className="text-xs text-slate-500 mt-2">
              {form.tracking_type === 'redirect' && '→ Le visiteur sera redirigé vers la page merci après soumission'}
              {form.tracking_type === 'gtm' && '→ Le code GTM conversion du compte sera déclenché (config GTM dans les Comptes)'}
              {form.tracking_type === 'both' && '→ GTM sera déclenché PUIS redirection vers la page merci'}
              {form.tracking_type === 'none' && '→ Le script ne fera rien, votre formulaire doit gérer la suite'}
            </p>
            
            {(form.tracking_type === 'redirect' || form.tracking_type === 'both') && (
              <div className="mt-3 p-3 bg-slate-50 rounded-lg">
                <Input
                  label="URL de redirection après soumission"
                  value={form.redirect_url}
                  onChange={e => setForm({...form, redirect_url: e.target.value})}
                  placeholder="/merci ou https://monsite.com/merci"
                />
                <p className="text-xs text-slate-400 mt-1">
                  Exemple: /merci (relatif) ou https://monsite.com/merci (absolu)
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {editingForm ? 'Enregistrer' : 'Créer'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal Brief */}
      <Modal 
        isOpen={showBriefModal} 
        onClose={() => setShowBriefModal(false)}
        title={`Brief - ${briefData?.form?.code || ''}`}
        size="xl"
      >
        {briefData && (
          <div className="space-y-6">
            {/* Info formulaire */}
            <div className="bg-slate-50 p-4 rounded-lg">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Formulaire:</span>
                  <span className="ml-2 font-medium">{briefData.form.code}</span>
                </div>
                <div>
                  <span className="text-slate-500">URL:</span>
                  <a href={briefData.form.url} target="_blank" rel="noopener noreferrer" className="ml-2 font-mono text-xs text-blue-600 hover:underline">{briefData.form.url}</a>
                </div>
                {briefData.lp?.linked && (
                  <>
                    <div>
                      <span className="text-slate-500">LP liée:</span>
                      <span className="ml-2 font-medium">{briefData.lp.code}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">URL LP:</span>
                      <a href={briefData.lp.url} target="_blank" rel="noopener noreferrer" className="ml-2 font-mono text-xs text-blue-600 hover:underline">{briefData.lp.url}</a>
                    </div>
                    <div className="col-span-2">
                      <span className="text-slate-500">Code liaison (synchronisé):</span>
                      <code className="ml-2 bg-green-100 text-green-700 px-2 py-0.5 rounded font-mono text-xs">{briefData.liaison_code}</code>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Endpoint public */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h4 className="font-medium text-blue-800 mb-2">🔗 Endpoint public pour récupérer le formulaire</h4>
              <code className="block bg-white p-2 rounded text-xs font-mono text-blue-700">
                GET {briefData.api_url}/api/forms/public/{briefData.form.code}
              </code>
            </div>

            {/* Script LP */}
            {briefData.scripts?.lp && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-slate-800">🔵 Script LP</h3>
                  <Button 
                    size="sm" 
                    variant="secondary"
                    onClick={() => copyScript(briefData.scripts.lp)}
                  >
                    <Copy className="w-4 h-4" />
                    Copier
                  </Button>
                </div>
                <p className="text-sm text-slate-600 mb-2">
                  À coller sur: <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.lp.url}</code>
                </p>
                <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-64">
                  {briefData.scripts.lp}
                </pre>
              </div>
            )}

            {/* Script Form */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-slate-800">🟢 Script Formulaire</h3>
                <Button 
                  size="sm" 
                  variant="secondary"
                  onClick={() => copyScript(briefData.scripts.form)}
                >
                  <Copy className="w-4 h-4" />
                  Copier
                </Button>
              </div>
              <p className="text-sm text-slate-600 mb-2">
                À coller sur: <code className="bg-slate-100 px-2 py-0.5 rounded">{briefData.form.url}</code>
              </p>
              <pre className="bg-slate-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-64">
                {briefData.scripts.form}
              </pre>
            </div>

            {/* Champs disponibles */}
            {briefData.lead_fields && (
              <div>
                <h3 className="font-semibold text-slate-800 mb-3">📋 Champs de récupération disponibles</h3>
                <div className="space-y-3">
                  {Object.entries(briefData.lead_fields).map(([category, fields]) => (
                    <div key={category} className="border rounded-lg p-3">
                      <h4 className="font-medium text-slate-700 capitalize mb-2">{category}</h4>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                        {fields.map(field => (
                          <div key={field.key} className={`p-2 rounded ${field.required ? 'bg-red-50 border border-red-200' : 'bg-slate-50'}`}>
                            <code className="font-mono font-medium">{field.key}</code>
                            <span className="text-slate-500 block">{field.label}</span>
                            {field.example && <span className="text-slate-400 text-xs">ex: {field.example}</span>}
                            {field.required && <span className="text-red-600 text-xs block">* Obligatoire</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Stats expliquées */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-2">📊 Statistiques trackées</h3>
              <pre className="bg-slate-100 text-slate-700 p-4 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap">
                {briefData.stats_explanation}
              </pre>
            </div>

            {/* Validation téléphone */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-2">📱 Validation téléphone</h3>
              <div className="flex flex-wrap gap-2">
                {briefData.phone_validation?.rules?.map((rule, i) => (
                  <span key={i} className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full">
                    ✓ {rule}
                  </span>
                ))}
              </div>
              {briefData.phone_validation?.auto_format && (
                <p className="text-xs text-slate-500 mt-2">
                  ℹ️ {briefData.phone_validation.auto_format}
                </p>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
