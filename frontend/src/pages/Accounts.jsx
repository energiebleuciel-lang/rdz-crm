/**
 * Page Comptes - Filtrée par CRM sélectionné
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Input, Select, Loading, EmptyState, Badge } from '../components/UI';
import { Building, Plus, Edit, Trash2, Image, Code, ChevronDown, ChevronUp, FileText, Clipboard, Check, FileDown } from 'lucide-react';

export default function Accounts() {
  const { authFetch } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [showGtmSection, setShowGtmSection] = useState(false);
  const [showLegalSection, setShowLegalSection] = useState(false);
  
  // Mini Brief
  const [showMiniBriefModal, setShowMiniBriefModal] = useState(false);
  const [miniBriefAccount, setMiniBriefAccount] = useState(null);
  const [briefOptions, setBriefOptions] = useState([]);
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [generatedBrief, setGeneratedBrief] = useState(null);
  const [copySuccess, setCopySuccess] = useState(null);
  
  const [form, setForm] = useState({
    name: '',
    crm_id: '',
    domain: '',
    logo_main_url: '',
    logo_secondary_url: '',
    logo_mini_url: '',
    primary_color: '#3B82F6',
    secondary_color: '#1E40AF',
    cgu_text: '',
    privacy_policy_text: '',
    legal_mentions_text: '',
    gtm_head: '',
    gtm_body: '',
    gtm_conversion: '',
    default_tracking_type: 'redirect'
  });

  useEffect(() => {
    if (selectedCRM) {
      loadData();
    }
  }, [selectedCRM]);

  const loadData = async () => {
    try {
      setLoading(true);
      // Filtrer les comptes par CRM sélectionné
      const res = await authFetch(`${API}/api/accounts?crm_id=${selectedCRM}`);
      if (res.ok) {
        const data = await res.json();
        setAccounts(data.accounts || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditingAccount(null);
    setShowGtmSection(false);
    setShowLegalSection(false);
    setForm({
      name: '',
      crm_id: selectedCRM, // Utiliser le CRM sélectionné par défaut
      domain: '',
      logo_main_url: '',
      logo_secondary_url: '',
      logo_mini_url: '',
      primary_color: '#3B82F6',
      secondary_color: '#1E40AF',
      cgu_text: '',
      privacy_policy_text: '',
      legal_mentions_text: '',
      gtm_head: '',
      gtm_body: '',
      gtm_conversion: '',
      default_tracking_type: 'redirect'
    });
    setShowModal(true);
  };

  const openEdit = (account) => {
    setEditingAccount(account);
    setShowGtmSection(!!account.gtm_head || !!account.gtm_body || !!account.gtm_conversion);
    setShowLegalSection(!!account.cgu_text || !!account.privacy_policy_text || !!account.legal_mentions_text);
    setForm({
      name: account.name,
      crm_id: account.crm_id,
      domain: account.domain || '',
      logo_main_url: account.logo_main_url || '',
      logo_secondary_url: account.logo_secondary_url || '',
      logo_mini_url: account.logo_mini_url || '',
      primary_color: account.primary_color || '#3B82F6',
      secondary_color: account.secondary_color || '#1E40AF',
      cgu_text: account.cgu_text || '',
      privacy_policy_text: account.privacy_policy_text || '',
      legal_mentions_text: account.legal_mentions_text || '',
      gtm_head: account.gtm_head || '',
      gtm_body: account.gtm_body || '',
      gtm_conversion: account.gtm_conversion || '',
      default_tracking_type: account.default_tracking_type || 'redirect'
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const url = editingAccount 
        ? `${API}/api/accounts/${editingAccount.id}`
        : `${API}/api/accounts`;
      
      const res = await authFetch(url, {
        method: editingAccount ? 'PUT' : 'POST',
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

  const handleDelete = async (account) => {
    if (!window.confirm(`Supprimer le compte "${account.name}" ?`)) return;
    
    try {
      const res = await authFetch(`${API}/api/accounts/${account.id}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        loadData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Erreur');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const getTrackingLabel = (type) => {
    switch(type) {
      case 'gtm': return 'GTM';
      case 'redirect': return 'Redirection';
      case 'both': return 'GTM + Redirection';
      default: return 'Redirection';
    }
  };

  // Mini Brief Functions
  const openMiniBrief = async (account) => {
    try {
      setMiniBriefAccount(account);
      setGeneratedBrief(null);
      setSelectedOptions([]);
      
      const res = await authFetch(`${API}/api/accounts/${account.id}/brief-options`);
      if (res.ok) {
        const data = await res.json();
        setBriefOptions(data.options || []);
        // Pré-sélectionner les options qui ont une valeur
        const preSelected = (data.options || [])
          .filter(opt => opt.has_value)
          .map(opt => opt.key);
        setSelectedOptions(preSelected);
        setShowMiniBriefModal(true);
      } else {
        alert('Erreur lors du chargement des options');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const toggleOption = (key) => {
    setSelectedOptions(prev => 
      prev.includes(key) 
        ? prev.filter(k => k !== key)
        : [...prev, key]
    );
    // Reset generated brief when selection changes
    setGeneratedBrief(null);
  };

  const generateMiniBrief = async () => {
    if (selectedOptions.length === 0) {
      alert('Sélectionnez au moins un élément');
      return;
    }
    
    try {
      const res = await authFetch(`${API}/api/accounts/${miniBriefAccount.id}/mini-brief`, {
        method: 'POST',
        body: JSON.stringify({ selections: selectedOptions })
      });
      
      if (res.ok) {
        const data = await res.json();
        setGeneratedBrief(data);
      } else {
        alert('Erreur lors de la génération');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const copyToClipboard = async (text, label) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopySuccess(label);
      setTimeout(() => setCopySuccess(null), 2000);
    } catch (e) {
      alert('Impossible de copier');
    }
  };

  const copyAllBrief = () => {
    if (!generatedBrief || !generatedBrief.items) return;
    
    let fullText = `=== MINI BRIEF - ${miniBriefAccount?.name} ===\n\n`;
    
    generatedBrief.items.forEach(item => {
      fullText += `--- ${item.label} ---\n`;
      fullText += item.value + '\n\n';
    });
    
    copyToClipboard(fullText, 'all');
  };

  // Group options by category
  const groupedOptions = briefOptions.reduce((acc, opt) => {
    if (!acc[opt.category]) acc[opt.category] = [];
    acc[opt.category].push(opt);
    return acc;
  }, {});

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Comptes</h1>
          <p className="text-sm text-slate-500">
            CRM: <span className="font-medium text-slate-700">{currentCRM?.name}</span>
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Nouveau compte
        </Button>
      </div>

      {accounts.length === 0 ? (
        <Card className="p-8">
          <EmptyState 
            icon={Building}
            title="Aucun compte"
            description={`Créez votre premier compte pour ${currentCRM?.name || 'ce CRM'}`}
            action={<Button onClick={openCreate}>Créer un compte</Button>}
          />
        </Card>
      ) : (
        <div className="grid gap-4">
          {accounts.map(account => (
            <Card key={account.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  {account.logo_main_url ? (
                    <img 
                      src={account.logo_main_url} 
                      alt={account.name}
                      className="w-12 h-12 object-contain rounded-lg border"
                    />
                  ) : (
                    <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                      <Building className="w-6 h-6 text-slate-400" />
                    </div>
                  )}
                  <div>
                    <h3 className="font-semibold text-slate-800">{account.name}</h3>
                    <p className="text-sm text-slate-500">{account.domain || 'Pas de domaine'}</p>
                    <div className="flex gap-2 mt-1">
                      {(account.gtm_head || account.gtm_body) && (
                        <Badge variant="success">GTM configuré</Badge>
                      )}
                      <Badge variant="default">{getTrackingLabel(account.default_tracking_type)}</Badge>
                    </div>
                  </div>
                </div>
                
                <div className="flex gap-2">
                  <button
                    onClick={() => openMiniBrief(account)}
                    className="px-3 py-1.5 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 text-sm font-medium flex items-center gap-1"
                    title="Générer Mini Brief"
                  >
                    <FileDown className="w-4 h-4" />
                    Brief
                  </button>
                  <button
                    onClick={() => openEdit(account)}
                    className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(account)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Logos preview */}
              <div className="mt-4 flex gap-4">
                {account.logo_main_url && (
                  <div className="text-center">
                    <img src={account.logo_main_url} alt="Logo principal" className="h-8 object-contain" />
                    <p className="text-xs text-slate-400 mt-1">Principal</p>
                  </div>
                )}
                {account.logo_secondary_url && (
                  <div className="text-center">
                    <img src={account.logo_secondary_url} alt="Logo secondaire" className="h-8 object-contain" />
                    <p className="text-xs text-slate-400 mt-1">Secondaire</p>
                  </div>
                )}
                {account.logo_mini_url && (
                  <div className="text-center">
                    <img src={account.logo_mini_url} alt="Mini logo" className="h-8 object-contain" />
                    <p className="text-xs text-slate-400 mt-1">Mini</p>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal Créer/Éditer */}
      <Modal 
        isOpen={showModal} 
        onClose={() => setShowModal(false)}
        title={editingAccount ? 'Modifier le compte' : `Nouveau compte (${currentCRM?.name})`}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Nom du compte"
            value={form.name}
            onChange={e => setForm({...form, name: e.target.value})}
            required
          />
          
          <Input
            label="Domaine (optionnel)"
            value={form.domain}
            onChange={e => setForm({...form, domain: e.target.value})}
            placeholder="exemple.com"
          />

          <div className="border-t pt-4 mt-4">
            <h4 className="font-medium text-slate-700 mb-3 flex items-center gap-2">
              <Image className="w-4 h-4" />
              Logos
            </h4>
            <div className="grid gap-3">
              <Input
                label="Logo principal (URL)"
                value={form.logo_main_url}
                onChange={e => setForm({...form, logo_main_url: e.target.value})}
                placeholder="https://..."
              />
              <Input
                label="Logo secondaire (URL)"
                value={form.logo_secondary_url}
                onChange={e => setForm({...form, logo_secondary_url: e.target.value})}
                placeholder="https://..."
              />
              <Input
                label="Mini logo / Favicon (URL)"
                value={form.logo_mini_url}
                onChange={e => setForm({...form, logo_mini_url: e.target.value})}
                placeholder="https://..."
              />
            </div>
          </div>

          <div className="border-t pt-4 mt-4">
            <h4 className="font-medium text-slate-700 mb-3">Couleurs</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-600 mb-1">Couleur principale</label>
                <input
                  type="color"
                  value={form.primary_color}
                  onChange={e => setForm({...form, primary_color: e.target.value})}
                  className="w-full h-10 rounded cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Couleur secondaire</label>
                <input
                  type="color"
                  value={form.secondary_color}
                  onChange={e => setForm({...form, secondary_color: e.target.value})}
                  className="w-full h-10 rounded cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Section GTM */}
          <div className="border-t pt-4 mt-4">
            <button
              type="button"
              onClick={() => setShowGtmSection(!showGtmSection)}
              className="w-full flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <span className="font-medium text-slate-700 flex items-center gap-2">
                <Code className="w-4 h-4" />
                Configuration GTM & Tracking
              </span>
              {showGtmSection ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showGtmSection && (
              <div className="mt-4 space-y-4 p-4 bg-slate-50 rounded-lg">
                <Select
                  label="Type de tracking par défaut"
                  value={form.default_tracking_type}
                  onChange={e => setForm({...form, default_tracking_type: e.target.value})}
                  options={[
                    { value: 'redirect', label: 'Redirection vers page merci' },
                    { value: 'gtm', label: 'GTM uniquement (pas de redirection)' },
                    { value: 'both', label: 'GTM + Redirection' }
                  ]}
                />

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Code GTM - HEAD
                    <span className="text-slate-400 font-normal ml-2">(à coller dans &lt;head&gt;)</span>
                  </label>
                  <textarea
                    value={form.gtm_head}
                    onChange={e => setForm({...form, gtm_head: e.target.value})}
                    placeholder="<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){...})</script>
<!-- End Google Tag Manager -->"
                    className="w-full h-24 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Code GTM - BODY
                    <span className="text-slate-400 font-normal ml-2">(à coller après &lt;body&gt;)</span>
                  </label>
                  <textarea
                    value={form.gtm_body}
                    onChange={e => setForm({...form, gtm_body: e.target.value})}
                    placeholder="<!-- Google Tag Manager (noscript) -->
<noscript><iframe src='...'></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->"
                    className="w-full h-24 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Code GTM - Conversion
                    <span className="text-slate-400 font-normal ml-2">(déclenché à la soumission du lead)</span>
                  </label>
                  <textarea
                    value={form.gtm_conversion}
                    onChange={e => setForm({...form, gtm_conversion: e.target.value})}
                    placeholder="gtag('event', 'conversion', {'send_to': 'AW-XXXXXXXXX/XXXXXXXX'});
// ou
dataLayer.push({'event': 'formSubmit'});"
                    className="w-full h-20 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-xs"
                  />
                </div>

                <p className="text-xs text-slate-500">
                  💡 Ces codes seront automatiquement inclus dans les scripts générés pour vos formulaires.
                </p>
              </div>
            )}
          </div>

          {/* Section Textes Légaux (CGU, Privacy) */}
          <div className="border-t pt-4 mt-4">
            <button
              type="button"
              onClick={() => setShowLegalSection(!showLegalSection)}
              className="w-full flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <span className="font-medium text-slate-700 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Textes Légaux (CGU, Confidentialité)
              </span>
              {showLegalSection ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showLegalSection && (
              <div className="mt-4 space-y-4 p-4 bg-slate-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Conditions Générales d'Utilisation (CGU)
                  </label>
                  <textarea
                    value={form.cgu_text}
                    onChange={e => setForm({...form, cgu_text: e.target.value})}
                    placeholder="Entrez vos CGU ici...

Article 1 - Objet
Ces conditions générales régissent...

Article 2 - Services
..."
                    className="w-full h-32 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Politique de Confidentialité
                  </label>
                  <textarea
                    value={form.privacy_policy_text}
                    onChange={e => setForm({...form, privacy_policy_text: e.target.value})}
                    placeholder="Entrez votre politique de confidentialité ici...

Nous collectons les données suivantes :
- Nom et prénom
- Numéro de téléphone
- Adresse email
..."
                    className="w-full h-32 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Mentions Légales (optionnel)
                  </label>
                  <textarea
                    value={form.legal_mentions_text}
                    onChange={e => setForm({...form, legal_mentions_text: e.target.value})}
                    placeholder="Raison sociale, SIRET, adresse..."
                    className="w-full h-24 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>

                <p className="text-xs text-slate-500">
                  💡 Ces textes seront automatiquement inclus dans le Brief et affichés en bas de page via des boutons cliquables.
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {editingAccount ? 'Enregistrer' : 'Créer'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
