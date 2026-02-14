import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import { Edit2, X, Check, AlertTriangle, Mail, Globe, Phone, Truck, Eye, Plus, Users } from 'lucide-react';

const DAY_SHORT = ['L', 'M', 'Me', 'J', 'V', 'S', 'D'];

export default function AdminClients() {
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entityFilter, setEntityFilter] = useState('');
  const [editId, setEditId] = useState(null);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const [clientStats, setClientStats] = useState({});
  const [calendar, setCalendar] = useState({});
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ entity: 'ZR7', name: '', email: '', phone: '', delivery_emails: '' });
  const [createSaving, setCreateSaving] = useState(false);
  const [createError, setCreateError] = useState('');

  const handleCreate = async () => {
    if (!createForm.name || !createForm.email) { setCreateError('Nom et email requis'); return; }
    setCreateSaving(true); setCreateError('');
    try {
      const body = { entity: createForm.entity, name: createForm.name, email: createForm.email, phone: createForm.phone,
        delivery_emails: createForm.delivery_emails.split(',').map(s => s.trim()).filter(Boolean),
        auto_send_enabled: true, default_prix_lead: 0, remise_percent: 0 };
      const r = await authFetch(`${API}/api/clients`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!r.ok) { const d = await r.json(); setCreateError(d.detail || 'Erreur'); } else { setShowCreate(false); setCreateForm({ entity: 'ZR7', name: '', email: '', phone: '', delivery_emails: '' }); load(); }
    } catch (e) { setCreateError(e.message); }
    setCreateSaving(false);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const entities = entityFilter ? [entityFilter] : ['ZR7', 'MDL'];
      const results = await Promise.all(entities.map(e => authFetch(`${API}/api/clients?entity=${e}`)));
      let all = [];
      for (const r of results) { if (r.ok) { const d = await r.json(); all = all.concat(d.clients || []); } }
      setClients(all);

      // Load calendar
      const calRes = await authFetch(`${API}/api/settings/delivery-calendar`);
      if (calRes.ok) setCalendar(await calRes.json());

      // Load 7d stats per client (delivery-based)
      const stats = {};
      for (const c of all) {
        const sRes = await authFetch(`${API}/api/deliveries/stats?entity=${c.entity}`).catch(() => null);
        // We get global stats, but we need per-client — use deliveries endpoint
        const dRes = await authFetch(`${API}/api/deliveries?client_id=${c.id}&limit=1`).catch(() => null);
        if (dRes?.ok) {
          const dd = await dRes.json();
          stats[c.id] = { total: dd.total || 0 };
        }
      }
      setClientStats(stats);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [entityFilter, authFetch]);

  useEffect(() => { load(); }, [load]);

  const startEdit = (client) => {
    setEditId(client.id);
    setEditData({
      email: client.email || '',
      delivery_emails: (client.delivery_emails || []).join(', '),
      api_endpoint: client.api_endpoint || '',
      auto_send_enabled: client.auto_send_enabled ?? true,
      active: client.active ?? true,
    });
  };

  const saveEdit = async () => {
    setSaving(true);
    try {
      const body = {
        email: editData.email,
        delivery_emails: editData.delivery_emails.split(',').map(s => s.trim()).filter(Boolean),
        api_endpoint: editData.api_endpoint,
        auto_send_enabled: editData.auto_send_enabled,
        active: editData.active,
      };
      await authFetch(`${API}/api/clients/${editId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      setEditId(null);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const getDeliveryDays = (entity) => {
    const days = calendar[entity]?.enabled_days || [];
    return DAY_SHORT.map((d, i) => ({ name: d, on: days.includes(i) }));
  };

  return (
    <div data-testid="admin-clients">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white">Clients</h1>
        <div className="flex gap-2">
          {['', 'ZR7', 'MDL'].map(e => (
            <button key={e} onClick={() => setEntityFilter(e)}
              className={`px-2.5 py-1 text-[10px] rounded-full border transition-colors ${entityFilter === e ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:border-zinc-700'}`}
              data-testid={`entity-filter-${e || 'all'}`}>
              {e || 'Tous'}
            </button>
          ))}
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-1 px-3 py-1 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30" data-testid="create-client-btn">
            <Plus className="w-3 h-3" /> Ajouter
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="create-client-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2"><Users className="w-4 h-4 text-teal-400" /> Nouveau Client</h2>
            {createError && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-1.5 mb-3">{createError}</div>}
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Entity</label>
                <select value={createForm.entity} onChange={e => setCreateForm(f => ({ ...f, entity: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-entity">
                  <option value="ZR7">ZR7</option><option value="MDL">MDL</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Nom</label>
                <input value={createForm.name} onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-name" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Email</label>
                <input type="email" value={createForm.email} onChange={e => setCreateForm(f => ({ ...f, email: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-email" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Téléphone</label>
                <input value={createForm.phone} onChange={e => setCreateForm(f => ({ ...f, phone: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-phone" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Emails livraison (virgule)</label>
                <input value={createForm.delivery_emails} onChange={e => setCreateForm(f => ({ ...f, delivery_emails: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" placeholder="a@b.com, c@d.com" data-testid="create-delivery-emails" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-xs text-zinc-400">Annuler</button>
              <button onClick={handleCreate} disabled={createSaving || !createForm.name || !createForm.email}
                className="px-3 py-1.5 text-xs bg-teal-500/20 text-teal-400 rounded-md hover:bg-teal-500/30 border border-teal-500/30 disabled:opacity-50" data-testid="create-submit-btn">Créer</button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="clients-table">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-3 py-2.5 font-medium">Nom</th>
                <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                <th className="text-left px-3 py-2.5 font-medium">Tel</th>
                <th className="text-left px-3 py-2.5 font-medium">Canaux</th>
                <th className="text-left px-3 py-2.5 font-medium">Auto Send</th>
                <th className="text-left px-3 py-2.5 font-medium">Jours</th>
                <th className="text-left px-3 py-2.5 font-medium">Livrable</th>
                <th className="text-left px-3 py-2.5 font-medium">Active</th>
                <th className="text-left px-3 py-2.5 font-medium">Deliveries</th>
                <th className="text-right px-3 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
              ) : clients.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Aucun client</td></tr>
              ) : clients.map(c => {
                const days = getDeliveryDays(c.entity);
                const deliverable = c.has_valid_channel;
                return (
                  <tr key={c.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`client-row-${c.id}`}>
                    {editId === c.id ? (
                      <>
                        <td className="px-3 py-2 text-zinc-300">{c.name}</td>
                        <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{c.entity}</span></td>
                        <td className="px-3 py-2 text-zinc-500">{c.phone || '-'}</td>
                        <td className="px-3 py-2"><input value={editData.email} onChange={e => setEditData(d => ({...d, email: e.target.value}))} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300 w-full text-xs" placeholder="email" data-testid="edit-email" /></td>
                        <td className="px-3 py-2">
                          <button onClick={() => setEditData(d => ({...d, auto_send_enabled: !d.auto_send_enabled}))}
                            className={`w-8 h-4 rounded-full relative transition-colors ${editData.auto_send_enabled ? 'bg-emerald-500' : 'bg-zinc-700'}`} data-testid="edit-auto-send-toggle">
                            <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${editData.auto_send_enabled ? 'left-4' : 'left-0.5'}`} />
                          </button>
                        </td>
                        <td className="px-3 py-2 text-zinc-500">-</td>
                        <td className="px-3 py-2">-</td>
                        <td className="px-3 py-2">
                          <button onClick={() => setEditData(d => ({...d, active: !d.active}))}
                            className={`w-8 h-4 rounded-full relative transition-colors ${editData.active ? 'bg-emerald-500' : 'bg-zinc-700'}`} data-testid="edit-active-toggle">
                            <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${editData.active ? 'left-4' : 'left-0.5'}`} />
                          </button>
                        </td>
                        <td className="px-3 py-2">-</td>
                        <td className="px-3 py-2 text-right flex items-center justify-end gap-1">
                          <button onClick={saveEdit} disabled={saving} className="p-1 text-emerald-400 hover:bg-zinc-800 rounded" data-testid="save-edit-btn"><Check className="w-3.5 h-3.5" /></button>
                          <button onClick={() => setEditId(null)} className="p-1 text-zinc-500 hover:bg-zinc-800 rounded" data-testid="cancel-edit-btn"><X className="w-3.5 h-3.5" /></button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-2 text-zinc-300 font-medium cursor-pointer hover:text-teal-400" onClick={() => navigate(`/admin/clients/${c.id}`)}>{c.name}</td>
                        <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{c.entity}</span></td>
                        <td className="px-3 py-2 text-zinc-400 font-mono text-[10px]">{c.phone || '-'}</td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-1.5">
                            {c.email && <Mail className={`w-3 h-3 ${deliverable ? 'text-emerald-400' : 'text-red-400'}`} title={c.email} />}
                            {c.api_endpoint && <Globe className="w-3 h-3 text-cyan-400" title={c.api_endpoint} />}
                            {(c.delivery_emails || []).length > 0 && <span className="text-[9px] text-zinc-500">+{c.delivery_emails.length}</span>}
                          </div>
                        </td>
                        <td className="px-3 py-2">{(c.auto_send_enabled ?? true) ? <span className="text-[10px] text-emerald-400">ON</span> : <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">OFF</span>}</td>
                        <td className="px-3 py-2">
                          <div className="flex gap-0.5">
                            {days.map((d, i) => (
                              <span key={i} className={`w-4 h-4 text-[8px] flex items-center justify-center rounded ${d.on ? 'bg-teal-500/20 text-teal-400' : 'bg-zinc-800 text-zinc-700'}`}>{d.name}</span>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          {deliverable
                            ? <Check className="w-3.5 h-3.5 text-emerald-400" />
                            : <span className="flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-red-400" /><span className="text-[9px] text-red-400/70 max-w-[80px] truncate" title={c.deliverable_reason}>{c.deliverable_reason?.split(':')[0]}</span></span>}
                        </td>
                        <td className="px-3 py-2">{(c.active ?? true) ? <span className="text-[10px] text-emerald-400">Active</span> : <span className="text-[10px] text-red-400">Off</span>}</td>
                        <td className="px-3 py-2 text-zinc-500">{clientStats[c.id]?.total ?? '-'}</td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => navigate(`/admin/deliveries?client_id=${c.id}`)} className="p-1 text-zinc-500 hover:text-cyan-400 rounded" title="Voir deliveries" data-testid={`view-deliveries-btn-${c.id}`}>
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={() => startEdit(c)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" data-testid={`edit-btn-${c.id}`}>
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
