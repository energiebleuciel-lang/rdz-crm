import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Edit2, X, Check, AlertTriangle } from 'lucide-react';

export default function AdminClients() {
  const { authFetch } = useAuth();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entityFilter, setEntityFilter] = useState('');
  const [editId, setEditId] = useState(null);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = entityFilter ? `?entity=${entityFilter}` : '';
      const res = await authFetch(`${API}/api/clients${params}`);
      if (res.ok) { const d = await res.json(); setClients(d.clients || []); }
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
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="clients-table">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-3 py-2.5 font-medium">Nom</th>
                <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                <th className="text-left px-3 py-2.5 font-medium">Email</th>
                <th className="text-left px-3 py-2.5 font-medium">API Endpoint</th>
                <th className="text-left px-3 py-2.5 font-medium">Auto Send</th>
                <th className="text-left px-3 py-2.5 font-medium">Deliverable</th>
                <th className="text-left px-3 py-2.5 font-medium">Active</th>
                <th className="text-right px-3 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
              ) : clients.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-8 text-zinc-600">Aucun client</td></tr>
              ) : clients.map(c => (
                <tr key={c.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`client-row-${c.id}`}>
                  {editId === c.id ? (
                    <>
                      <td className="px-3 py-2 text-zinc-300">{c.name}</td>
                      <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{c.entity}</span></td>
                      <td className="px-3 py-2"><input value={editData.email} onChange={e => setEditData(d => ({...d, email: e.target.value}))} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300 w-full text-xs" data-testid="edit-email" /></td>
                      <td className="px-3 py-2"><input value={editData.api_endpoint} onChange={e => setEditData(d => ({...d, api_endpoint: e.target.value}))} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300 w-full text-xs" data-testid="edit-api-endpoint" /></td>
                      <td className="px-3 py-2">
                        <button onClick={() => setEditData(d => ({...d, auto_send_enabled: !d.auto_send_enabled}))}
                          className={`w-8 h-4 rounded-full relative transition-colors ${editData.auto_send_enabled ? 'bg-emerald-500' : 'bg-zinc-700'}`} data-testid="edit-auto-send-toggle">
                          <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${editData.auto_send_enabled ? 'left-4' : 'left-0.5'}`} />
                        </button>
                      </td>
                      <td className="px-3 py-2">{c.has_valid_channel ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <AlertTriangle className="w-3.5 h-3.5 text-red-400" />}</td>
                      <td className="px-3 py-2">
                        <button onClick={() => setEditData(d => ({...d, active: !d.active}))}
                          className={`w-8 h-4 rounded-full relative transition-colors ${editData.active ? 'bg-emerald-500' : 'bg-zinc-700'}`} data-testid="edit-active-toggle">
                          <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${editData.active ? 'left-4' : 'left-0.5'}`} />
                        </button>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={saveEdit} disabled={saving} className="p-1 text-emerald-400 hover:bg-zinc-800 rounded" data-testid="save-edit-btn"><Check className="w-3.5 h-3.5" /></button>
                          <button onClick={() => setEditId(null)} className="p-1 text-zinc-500 hover:bg-zinc-800 rounded" data-testid="cancel-edit-btn"><X className="w-3.5 h-3.5" /></button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-2 text-zinc-300">{c.name}</td>
                      <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{c.entity}</span></td>
                      <td className="px-3 py-2 text-zinc-400 max-w-[180px] truncate">{c.email}</td>
                      <td className="px-3 py-2 text-zinc-500 max-w-[140px] truncate">{c.api_endpoint || '-'}</td>
                      <td className="px-3 py-2">{(c.auto_send_enabled ?? true) ? <span className="text-[10px] text-emerald-400">ON</span> : <span className="text-[10px] text-amber-400">OFF</span>}</td>
                      <td className="px-3 py-2">{c.has_valid_channel ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <AlertTriangle className="w-3.5 h-3.5 text-red-400" title="Non livrable" />}</td>
                      <td className="px-3 py-2">{(c.active ?? true) ? <span className="text-[10px] text-emerald-400">Active</span> : <span className="text-[10px] text-red-400">Inactive</span>}</td>
                      <td className="px-3 py-2 text-right">
                        <button onClick={() => startEdit(c)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" data-testid={`edit-btn-${c.id}`}>
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
