import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { UserCog, Plus, X, Check, Shield, Eye, EyeOff } from 'lucide-react';

const ROLE_COLORS = {
  super_admin: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  admin: 'bg-teal-500/15 text-teal-400 border-teal-500/30',
  ops: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  viewer: 'bg-zinc-700/30 text-zinc-400 border-zinc-600/30',
};

const PERM_GROUPS = [
  { label: 'Dashboard', keys: ['dashboard.view'] },
  { label: 'Leads', keys: ['leads.view', 'leads.edit_status', 'leads.add_note', 'leads.delete'] },
  { label: 'Clients', keys: ['clients.view', 'clients.create', 'clients.edit', 'clients.delete'] },
  { label: 'Commandes', keys: ['commandes.view', 'commandes.create', 'commandes.edit_quota', 'commandes.edit_lb_target', 'commandes.activate_pause', 'commandes.delete'] },
  { label: 'Deliveries', keys: ['deliveries.view', 'deliveries.resend'] },
  { label: 'Billing', keys: ['billing.view', 'billing.manage'] },
  { label: 'Navigation', keys: ['departements.view', 'activity.view'] },
  { label: 'Admin', keys: ['settings.access', 'providers.access', 'users.manage', 'monitoring.lb.view'] },
];

export default function AdminUsers() {
  const { authFetch } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [presets, setPresets] = useState({});
  const [showCreate, setShowCreate] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [form, setForm] = useState({ email: '', password: '', nom: '', entity: 'ZR7', role: 'viewer', permissions: {} });
  const [saving, setSaving] = useState(false);
  const [showPwd, setShowPwd] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [uRes, pRes] = await Promise.all([
        authFetch(`${API}/api/auth/users`),
        authFetch(`${API}/api/auth/permission-keys`)
      ]);
      if (uRes.ok) { const d = await uRes.json(); setUsers(d.users || []); }
      if (pRes.ok) { const d = await pRes.json(); setPresets(d.presets || {}); }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  const applyPreset = (role) => {
    const perms = presets[role] || {};
    setForm(f => ({ ...f, role, permissions: { ...perms } }));
  };

  const openCreate = () => {
    const defaultPerms = presets['viewer'] || {};
    setForm({ email: '', password: '', nom: '', entity: 'ZR7', role: 'viewer', permissions: { ...defaultPerms } });
    setEditUser(null);
    setShowCreate(true);
  };

  const openEdit = (u) => {
    setForm({
      email: u.email, password: '', nom: u.nom || '',
      entity: u.entity || 'ZR7', role: u.role || 'viewer',
      permissions: { ...(u.permissions || presets[u.role] || {}) }
    });
    setEditUser(u);
    setShowCreate(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editUser) {
        const body = { nom: form.nom, entity: form.entity, role: form.role, permissions: form.permissions };
        if (form.is_active !== undefined) body.is_active = form.is_active;
        await authFetch(`${API}/api/auth/users/${editUser.id}`, {
          method: 'PUT', body: JSON.stringify(body)
        });
      } else {
        await authFetch(`${API}/api/auth/users`, {
          method: 'POST', body: JSON.stringify(form)
        });
      }
      setShowCreate(false);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const toggleActive = async (u) => {
    await authFetch(`${API}/api/auth/users/${u.id}`, {
      method: 'PUT', body: JSON.stringify({ is_active: !(u.is_active ?? u.active ?? true) })
    });
    load();
  };

  const togglePerm = (key) => {
    setForm(f => ({ ...f, permissions: { ...f.permissions, [key]: !f.permissions[key] } }));
  };

  const shortKey = (k) => k.split('.').pop();

  return (
    <div data-testid="admin-users">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white flex items-center gap-2">
          <UserCog className="w-5 h-5 text-teal-400" /> Utilisateurs
        </h1>
        <button onClick={openCreate} className="flex items-center gap-1 px-3 py-1 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30" data-testid="create-user-btn">
          <Plus className="w-3 h-3" /> Nouveau
        </button>
      </div>

      {/* Users table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-xs" data-testid="users-table">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-500">
              <th className="text-left px-3 py-2.5 font-medium">Email</th>
              <th className="text-left px-3 py-2.5 font-medium">Nom</th>
              <th className="text-left px-3 py-2.5 font-medium">Entity</th>
              <th className="text-left px-3 py-2.5 font-medium">Role</th>
              <th className="text-left px-3 py-2.5 font-medium">Status</th>
              <th className="text-right px-3 py-2.5 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
            ) : users.map(u => {
              const active = u.is_active ?? u.active ?? true;
              return (
                <tr key={u.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`user-row-${u.id}`}>
                  <td className="px-3 py-2 text-zinc-300">{u.email}</td>
                  <td className="px-3 py-2 text-zinc-400">{u.nom || '-'}</td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${u.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>
                      {u.entity || '-'}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${ROLE_COLORS[u.role] || ROLE_COLORS.viewer}`}>
                      {u.role} {u.role === 'super_admin' && <Shield className="w-2.5 h-2.5 inline ml-0.5" />}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <button onClick={() => toggleActive(u)} className={`text-[10px] px-1.5 py-0.5 rounded ${active ? 'text-emerald-400' : 'text-red-400'}`}>
                      {active ? 'Actif' : 'Inactif'}
                    </button>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => openEdit(u)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" data-testid={`edit-user-${u.id}`}>
                      <UserCog className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Create/Edit Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="user-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-2xl max-h-[85vh] overflow-y-auto">
            <h2 className="text-sm font-semibold text-white mb-4">
              {editUser ? `Modifier: ${editUser.email}` : 'Nouvel utilisateur'}
            </h2>

            <div className="space-y-3 mb-4">
              {!editUser && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1">Email</label>
                    <input value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="user-email" />
                  </div>
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1">Mot de passe</label>
                    <div className="relative">
                      <input type={showPwd ? 'text' : 'password'} value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))}
                        className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300 pr-8" data-testid="user-password" />
                      <button onClick={() => setShowPwd(!showPwd)} className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500">
                        {showPwd ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Nom</label>
                  <input value={form.nom} onChange={e => setForm(f => ({...f, nom: e.target.value}))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="user-nom" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Entity</label>
                  <select value={form.entity} onChange={e => setForm(f => ({...f, entity: e.target.value}))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="user-entity">
                    <option value="ZR7">ZR7</option>
                    <option value="MDL">MDL</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Role (preset)</label>
                  <select value={form.role} onChange={e => applyPreset(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="user-role">
                    <option value="super_admin">super_admin</option>
                    <option value="admin">admin</option>
                    <option value="ops">ops</option>
                    <option value="viewer">viewer</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Permissions grid */}
            <div className="border border-zinc-800 rounded-lg p-3 mb-4">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2 font-medium">Permissions (override du preset)</p>
              <div className="space-y-2">
                {PERM_GROUPS.map(group => (
                  <div key={group.label} className="flex items-start gap-2">
                    <span className="text-[10px] text-zinc-500 w-20 pt-0.5 shrink-0">{group.label}</span>
                    <div className="flex flex-wrap gap-1">
                      {group.keys.map(key => (
                        <button key={key} onClick={() => togglePerm(key)}
                          data-testid={`perm-${key}`}
                          className={`px-1.5 py-0.5 text-[9px] rounded border transition-colors ${
                            form.permissions[key]
                              ? 'bg-teal-500/15 text-teal-400 border-teal-500/30'
                              : 'bg-zinc-800/50 text-zinc-600 border-zinc-700/50'
                          }`}>
                          {shortKey(key)}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-xs text-zinc-400">Annuler</button>
              <button onClick={handleSave} disabled={saving || (!editUser && (!form.email || !form.password))}
                className="px-3 py-1.5 text-xs bg-teal-500/20 text-teal-400 rounded-md hover:bg-teal-500/30 border border-teal-500/30 disabled:opacity-50"
                data-testid="save-user-btn">
                {editUser ? 'Enregistrer' : 'Créer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
