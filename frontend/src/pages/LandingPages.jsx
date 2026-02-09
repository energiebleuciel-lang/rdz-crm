/**
 * Page Landing Pages - Filtrée par CRM sélectionné
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Input, Select, Loading, EmptyState, Badge } from '../components/UI';
import { Globe, Plus, Edit, Trash2, Copy, Eye, ExternalLink } from 'lucide-react';

export default function LandingPages() {
  const { authFetch } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const [lps, setLps] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingLp, setEditingLp] = useState(null);
  const [form, setForm] = useState({
    account_id: '',
    name: '',
    url: '',
    source_type: 'native',
    source_name: '',
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
      // Charger les comptes filtrés par CRM
      const accountsRes = await authFetch(`${API}/api/accounts?crm_id=${selectedCRM}`);
      let accountsList = [];
      if (accountsRes.ok) {
        const data = await accountsRes.json();
        accountsList = data.accounts || [];
        setAccounts(accountsList);
      }
      
      // Charger les LPs et filtrer par comptes du CRM
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
      source_type: 'native',
      source_name: '',
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
      source_type: lp.source_type || 'native',
      source_name: lp.source_name || '',
      notes: lp.notes || ''
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!form.url.startsWith('http')) {
      alert('L\'URL doit commencer par http:// ou https://');
      return;
    }
    
    try {
      const url = editingLp 
        ? `${API}/api/lps/${editingLp.id}`
        : `${API}/api/lps`;
      
      const res = await authFetch(url, {
        method: editingLp ? 'PUT' : 'POST',
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

  const handleDuplicate = async (lp) => {
    try {
      const res = await authFetch(`${API}/api/lps/${lp.id}/duplicate`, {
        method: 'POST'
      });
      
      if (res.ok) {
        const data = await res.json();
        alert(`LP dupliquée avec le code ${data.code}`);
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleDelete = async (lp) => {
    if (!window.confirm(`Archiver la LP "${lp.name}" ?`)) return;
    
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

  const copyCode = (code) => {
    navigator.clipboard.writeText(code);
    alert('Code copié !');
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Landing Pages</h1>
          <p className="text-sm text-slate-500">
            CRM: <span className="font-medium text-slate-700">{currentCRM?.name}</span>
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Nouvelle LP
        </Button>
      </div>

      {lps.length === 0 ? (
        <Card className="p-8">
          <EmptyState 
            icon={Globe}
            title="Aucune Landing Page"
            description="Créez votre première LP pour commencer le tracking"
            action={<Button onClick={openCreate}>Créer une LP</Button>}
          />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {lps.map(lp => (
            <Card key={lp.id} className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm bg-slate-100 px-2 py-0.5 rounded">
                      {lp.code}
                    </span>
                    <button 
                      onClick={() => copyCode(lp.code)}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                  <h3 className="font-semibold text-slate-800">{lp.name}</h3>
                  <p className="text-xs text-slate-500">{lp.account_name}</p>
                </div>
                <Badge variant={lp.status === 'active' ? 'success' : 'default'}>
                  {lp.status}
                </Badge>
              </div>

              {/* URL */}
              <a 
                href={lp.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 mb-4 truncate"
              >
                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{lp.url}</span>
              </a>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-xl font-bold text-slate-800">{lp.stats?.visits || 0}</p>
                  <p className="text-xs text-slate-500">Visites</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-xl font-bold text-slate-800">{lp.stats?.cta_clicks || 0}</p>
                  <p className="text-xs text-slate-500">Clics CTA</p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-3 border-t">
                <button
                  onClick={() => openEdit(lp)}
                  className="flex-1 flex items-center justify-center gap-1 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  <Edit className="w-4 h-4" />
                  Éditer
                </button>
                <button
                  onClick={() => handleDuplicate(lp)}
                  className="flex-1 flex items-center justify-center gap-1 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  <Copy className="w-4 h-4" />
                  Dupliquer
                </button>
                <button
                  onClick={() => handleDelete(lp)}
                  className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Modal */}
      <Modal 
        isOpen={showModal} 
        onClose={() => setShowModal(false)}
        title={editingLp ? 'Modifier la LP' : 'Nouvelle Landing Page'}
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
            placeholder="LP Google Ads PAC"
            required
          />
          
          <Input
            label="URL de la LP"
            value={form.url}
            onChange={e => setForm({...form, url: e.target.value})}
            placeholder="https://lp.monsite.com"
            required
          />
          
          <Select
            label="Source de trafic"
            value={form.source_type}
            onChange={e => setForm({...form, source_type: e.target.value})}
            options={[
              { value: 'native', label: 'Native' },
              { value: 'google', label: 'Google Ads' },
              { value: 'facebook', label: 'Facebook Ads' },
              { value: 'other', label: 'Autre' }
            ]}
          />
          
          {form.source_type === 'other' && (
            <Input
              label="Nom de la source"
              value={form.source_name}
              onChange={e => setForm({...form, source_name: e.target.value})}
              placeholder="Taboola, Outbrain..."
            />
          )}

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {editingLp ? 'Enregistrer' : 'Créer'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
