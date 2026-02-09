/**
 * Page Comptes
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Input, Select, Loading, EmptyState, Badge } from '../components/UI';
import { Building, Plus, Edit, Trash2, Image } from 'lucide-react';

export default function Accounts() {
  const { authFetch } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [crms, setCrms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [form, setForm] = useState({
    name: '',
    crm_id: '',
    domain: '',
    logo_main_url: '',
    logo_secondary_url: '',
    logo_mini_url: '',
    primary_color: '#3B82F6',
    secondary_color: '#1E40AF'
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [accountsRes, crmsRes] = await Promise.all([
        authFetch(`${API}/api/accounts`),
        authFetch(`${API}/api/crms`)
      ]);
      
      if (accountsRes.ok) {
        const data = await accountsRes.json();
        setAccounts(data.accounts || []);
      }
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

  const openCreate = () => {
    setEditingAccount(null);
    setForm({
      name: '',
      crm_id: crms[0]?.id || '',
      domain: '',
      logo_main_url: '',
      logo_secondary_url: '',
      logo_mini_url: '',
      primary_color: '#3B82F6',
      secondary_color: '#1E40AF'
    });
    setShowModal(true);
  };

  const openEdit = (account) => {
    setEditingAccount(account);
    setForm({
      name: account.name,
      crm_id: account.crm_id,
      domain: account.domain || '',
      logo_main_url: account.logo_main_url || '',
      logo_secondary_url: account.logo_secondary_url || '',
      logo_mini_url: account.logo_mini_url || '',
      primary_color: account.primary_color || '#3B82F6',
      secondary_color: account.secondary_color || '#1E40AF'
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

  const getCrmName = (crmId) => {
    const crm = crms.find(c => c.id === crmId);
    return crm?.name || 'N/A';
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Comptes</h1>
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
            description="Créez votre premier compte pour commencer"
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
                    <Badge variant="info">{getCrmName(account.crm_id)}</Badge>
                  </div>
                </div>
                
                <div className="flex gap-2">
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
        title={editingAccount ? 'Modifier le compte' : 'Nouveau compte'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Nom du compte"
            value={form.name}
            onChange={e => setForm({...form, name: e.target.value})}
            required
          />
          
          <Select
            label="CRM cible"
            value={form.crm_id}
            onChange={e => setForm({...form, crm_id: e.target.value})}
            options={crms.map(c => ({ value: c.id, label: c.name }))}
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
