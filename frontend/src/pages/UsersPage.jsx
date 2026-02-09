/**
 * Page Utilisateurs - Gestion des accès et permissions
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Input, Select, Loading, Badge } from '../components/UI';
import { Users, Plus, Edit, Trash2, Shield, Check, X, Clock } from 'lucide-react';

const SECTIONS = [
  { key: 'dashboard', label: 'Tableau de bord' },
  { key: 'accounts', label: 'Comptes' },
  { key: 'lps', label: 'Landing Pages' },
  { key: 'forms', label: 'Formulaires' },
  { key: 'leads', label: 'Leads' },
  { key: 'commandes', label: 'Commandes' },
  { key: 'settings', label: 'Paramètres' },
  { key: 'users', label: 'Utilisateurs' }
];

const ROLES = [
  { value: 'admin', label: 'Administrateur', color: 'bg-purple-500' },
  { value: 'editor', label: 'Éditeur', color: 'bg-blue-500' },
  { value: 'viewer', label: 'Lecteur', color: 'bg-slate-500' }
];

export default function UsersPage() {
  const { authFetch } = useAuth();
  const [users, setUsers] = useState([]);
  const [activityLogs, setActivityLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [tab, setTab] = useState('users'); // users, activity
  
  const [form, setForm] = useState({
    email: '',
    password: '',
    nom: '',
    role: 'viewer',
    permissions: {
      dashboard: true, accounts: false, lps: true, forms: true,
      leads: true, commandes: false, settings: false, users: false
    }
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const [usersRes, logsRes] = await Promise.all([
        authFetch(`${API}/api/auth/users`),
        authFetch(`${API}/api/auth/activity-logs?limit=50`)
      ]);

      if (usersRes.ok) {
        const data = await usersRes.json();
        setUsers(data.users || []);
      }
      
      if (logsRes.ok) {
        const data = await logsRes.json();
        setActivityLogs(data.logs || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setEditingUser(null);
    setForm({
      email: '',
      password: '',
      nom: '',
      role: 'viewer',
      permissions: {
        dashboard: true, accounts: false, lps: true, forms: true,
        leads: true, commandes: false, settings: false, users: false
      }
    });
    setShowModal(true);
  };

  const openEdit = (user) => {
    setEditingUser(user);
    setForm({
      email: user.email,
      password: '',
      nom: user.nom,
      role: user.role,
      permissions: user.permissions || {
        dashboard: true, accounts: false, lps: true, forms: true,
        leads: true, commandes: false, settings: false, users: false
      }
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const url = editingUser 
        ? `${API}/api/auth/users/${editingUser.id}`
        : `${API}/api/auth/users`;
      
      const body = editingUser 
        ? { nom: form.nom, role: form.role, permissions: form.permissions }
        : form;
      
      const res = await authFetch(url, {
        method: editingUser ? 'PUT' : 'POST',
        body: JSON.stringify(body)
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

  const toggleActive = async (user) => {
    if (!window.confirm(`${user.active !== false ? 'Désactiver' : 'Réactiver'} cet utilisateur ?`)) return;
    
    try {
      const res = await authFetch(`${API}/api/auth/users/${user.id}`, {
        method: 'PUT',
        body: JSON.stringify({ active: user.active === false })
      });

      if (res.ok) {
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handlePermissionChange = (key, checked) => {
    setForm({
      ...form,
      permissions: { ...form.permissions, [key]: checked }
    });
  };

  const actionLabels = {
    login: 'Connexion',
    logout: 'Déconnexion',
    create: 'Création',
    update: 'Modification',
    delete: 'Suppression',
    view: 'Consultation',
    export: 'Export',
    retry: 'Relance'
  };

  const entityLabels = {
    user: 'Utilisateur',
    account: 'Compte',
    lp: 'Landing Page',
    form: 'Formulaire',
    lead: 'Lead',
    commande: 'Commande',
    system: 'Système'
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Utilisateurs</h1>
          <p className="text-sm text-slate-500 mt-1">Gestion des accès et permissions</p>
        </div>
        
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Nouvel utilisateur
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setTab('users')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
            tab === 'users' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-600'
          }`}
        >
          <Users className="w-4 h-4" />
          Utilisateurs ({users.length})
        </button>
        <button
          onClick={() => setTab('activity')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
            tab === 'activity' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-600'
          }`}
        >
          <Clock className="w-4 h-4" />
          Journal d'activité
        </button>
      </div>

      {tab === 'users' ? (
        /* Liste des utilisateurs */
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Utilisateur</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Email</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Rôle</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Permissions</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Statut</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => {
                  const role = ROLES.find(r => r.value === user.role) || ROLES[2];
                  const permissions = user.permissions || {};
                  const activePerms = Object.entries(permissions).filter(([_, v]) => v).length;
                  
                  return (
                    <tr key={user.id} className="border-t hover:bg-slate-50">
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full ${role.color} flex items-center justify-center text-white font-bold`}>
                            {user.nom?.charAt(0)?.toUpperCase() || '?'}
                          </div>
                          <span className="font-medium">{user.nom}</span>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-slate-600">{user.email}</td>
                      <td className="p-4">
                        <Badge variant={user.role === 'admin' ? 'success' : 'info'}>
                          {role.label}
                        </Badge>
                      </td>
                      <td className="p-4">
                        <span className="text-sm text-slate-600">{activePerms}/{SECTIONS.length} sections</span>
                      </td>
                      <td className="p-4">
                        <Badge variant={user.active !== false ? 'success' : 'secondary'}>
                          {user.active !== false ? 'Actif' : 'Désactivé'}
                        </Badge>
                      </td>
                      <td className="p-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => openEdit(user)}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                            title="Modifier"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => toggleActive(user)}
                            className={`p-1.5 rounded ${
                              user.active !== false 
                                ? 'text-red-600 hover:bg-red-50' 
                                : 'text-green-600 hover:bg-green-50'
                            }`}
                            title={user.active !== false ? 'Désactiver' : 'Réactiver'}
                          >
                            {user.active !== false ? <X className="w-4 h-4" /> : <Check className="w-4 h-4" />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        /* Journal d'activité */
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Date</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Utilisateur</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Action</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Type</th>
                  <th className="text-left p-4 text-sm font-medium text-slate-600">Détails</th>
                </tr>
              </thead>
              <tbody>
                {activityLogs.map(log => (
                  <tr key={log.id} className="border-t hover:bg-slate-50">
                    <td className="p-4 text-sm text-slate-500">
                      {new Date(log.created_at).toLocaleString('fr-FR')}
                    </td>
                    <td className="p-4">
                      <span className="font-medium">{log.user_nom || log.user_email}</span>
                    </td>
                    <td className="p-4">
                      <Badge variant={
                        log.action === 'delete' ? 'danger' :
                        log.action === 'create' ? 'success' :
                        log.action === 'login' ? 'info' : 'default'
                      }>
                        {actionLabels[log.action] || log.action}
                      </Badge>
                    </td>
                    <td className="p-4 text-sm text-slate-600">
                      {entityLabels[log.entity_type] || log.entity_type}
                    </td>
                    <td className="p-4 text-sm text-slate-500">
                      {log.entity_name || log.entity_id?.slice(0, 8) || '-'}
                    </td>
                  </tr>
                ))}
                {activityLogs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-500">
                      Aucune activité enregistrée
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Modal Créer/Modifier */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingUser ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur'}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Nom complet"
              value={form.nom}
              onChange={e => setForm({...form, nom: e.target.value})}
              required
            />
            
            <Select
              label="Rôle"
              value={form.role}
              onChange={e => setForm({...form, role: e.target.value})}
              options={ROLES.map(r => ({ value: r.value, label: r.label }))}
            />
          </div>
          
          {!editingUser && (
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Email"
                type="email"
                value={form.email}
                onChange={e => setForm({...form, email: e.target.value})}
                required
              />
              
              <Input
                label="Mot de passe"
                type="password"
                value={form.password}
                onChange={e => setForm({...form, password: e.target.value})}
                required
              />
            </div>
          )}

          {/* Permissions */}
          <div className="border-t pt-4">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-5 h-5 text-slate-600" />
              <h4 className="font-medium text-slate-700">Permissions par section</h4>
            </div>
            
            <div className="grid grid-cols-2 gap-2">
              {SECTIONS.map(section => (
                <label
                  key={section.key}
                  className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors ${
                    form.permissions[section.key] 
                      ? 'bg-green-50 border border-green-200' 
                      : 'bg-slate-50 border border-slate-200'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={form.permissions[section.key] || false}
                    onChange={e => handlePermissionChange(section.key, e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-green-500 focus:ring-green-500"
                  />
                  <span className={form.permissions[section.key] ? 'text-green-700 font-medium' : 'text-slate-600'}>
                    {section.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="secondary" onClick={() => setShowModal(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {editingUser ? 'Enregistrer' : 'Créer'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
