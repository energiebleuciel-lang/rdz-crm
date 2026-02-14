import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import { Plus, Edit2, X, Check, Eye, Activity } from 'lucide-react';
import { getCurrentWeekKey, shiftWeekKey } from '../lib/weekUtils';
import { WeekNavStandard } from '../components/WeekNav';

export default function AdminCommandes() {
  const { authFetch, entityScope, isSuperAdmin, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [commandes, setCommandes] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entityFilter, setEntityFilter] = useState('');
  const [week, setWeek] = useState(getCurrentWeekKey());
  const [editId, setEditId] = useState(null);
  const [editData, setEditData] = useState({});
  const [showCreate, setShowCreate] = useState(false);
  const [createData, setCreateData] = useState({ entity: 'ZR7', client_id: '', produit: 'PV', departements: '*', quota_semaine: 50, lb_target_pct: 20, priorite: 1 });
  const [saving, setSaving] = useState(false);

  const handleWeekNav = (dir) => setWeek(w => shiftWeekKey(w, dir));

  // Resolve entities to query based on scope + local filter
  const getEntitiesToLoad = useCallback(() => {
    if (entityFilter) return [entityFilter];
    if (entityScope === 'BOTH') return ['ZR7', 'MDL'];
    return [entityScope || 'ZR7'];
  }, [entityFilter, entityScope]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const entities = getEntitiesToLoad();
      const results = await Promise.all(
        entities.map(e => authFetch(`${API}/api/commandes?entity=${e}&week=${week}`))
      );
      let allCmds = [];
      for (const r of results) {
        if (r.ok) { const d = await r.json(); allCmds = allCmds.concat(d.commandes || []); }
      }
      setCommandes(allCmds);

      // Load clients for all visible entities
      const clResults = await Promise.all(
        entities.map(e => authFetch(`${API}/api/clients?entity=${e}`))
      );
      let allCl = [];
      for (const r of clResults) {
        if (r.ok) { const d = await r.json(); allCl = allCl.concat(d.clients || []); }
      }
      setClients(allCl);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [entityFilter, week, authFetch, getEntitiesToLoad]);

  useEffect(() => { load(); }, [load]);

  const clientName = (id) => clients.find(c => c.id === id)?.name || id?.slice(0, 8);

  const startEdit = (cmd) => {
    setEditId(cmd.id);
    setEditData({
      quota_semaine: cmd.quota_semaine || 0,
      lb_target_pct: Math.round((cmd.lb_target_pct || 0) * 100),
      priorite: cmd.priorite || 1,
      active: cmd.active ?? true,
      departements: (cmd.departements || []).join(', '),
    });
  };

  const saveEdit = async () => {
    setSaving(true);
    try {
      const body = {
        quota_semaine: Number(editData.quota_semaine),
        lb_target_pct: Number(editData.lb_target_pct) / 100,
        priorite: Number(editData.priorite),
        active: editData.active,
        departements: editData.departements.split(',').map(s => s.trim()).filter(Boolean),
      };
      await authFetch(`${API}/api/commandes/${editId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      setEditId(null);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      const body = {
        ...createData,
        quota_semaine: Number(createData.quota_semaine),
        lb_target_pct: Number(createData.lb_target_pct) / 100,
        priorite: Number(createData.priorite),
        departements: createData.departements.split(',').map(s => s.trim()).filter(Boolean),
      };
      delete body.lb_percent_max;
      await authFetch(`${API}/api/commandes`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      setShowCreate(false);
      load();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  return (
    <div data-testid="admin-commandes">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white">Commandes</h1>
        <div className="flex gap-2 items-center">
          <WeekNavStandard week={week} onChange={handleWeekNav} />
          {isSuperAdmin && entityScope === 'BOTH' && ['', 'ZR7', 'MDL'].map(e => (
            <button key={e} onClick={() => setEntityFilter(e)}
              className={`px-2.5 py-1 text-[10px] rounded-full border transition-colors ${entityFilter === e ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:border-zinc-700'}`}>
              {e || 'Toutes'}
            </button>
          ))}
          {hasPermission('commandes.create') && (
            <button onClick={() => setShowCreate(true)} className="flex items-center gap-1 px-3 py-1 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30" data-testid="create-commande-btn">
              <Plus className="w-3 h-3" /> Nouvelle
            </button>
          )}
        </div>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="create-commande-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-sm font-semibold text-white mb-4">Nouvelle Commande</h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Entity</label>
                  <select value={createData.entity} onChange={e => setCreateData(d => ({...d, entity: e.target.value}))} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-entity">
                    <option value="ZR7">ZR7</option>
                    <option value="MDL">MDL</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Produit</label>
                  <select value={createData.produit} onChange={e => setCreateData(d => ({...d, produit: e.target.value}))} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-produit">
                    <option value="PV">PV</option>
                    <option value="PAC">PAC</option>
                    <option value="ISO">ISO</option>
                    <option value="POELE">POELE</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Client</label>
                <select value={createData.client_id} onChange={e => setCreateData(d => ({...d, client_id: e.target.value}))} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-client">
                  <option value="">Choisir...</option>
                  {clients.filter(c => !createData.entity || c.entity === createData.entity).map(c => <option key={c.id} value={c.id}>{c.name} ({c.entity})</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Departements (virgule ou * pour tous)</label>
                <input value={createData.departements} onChange={e => setCreateData(d => ({...d, departements: e.target.value}))} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" placeholder="01, 13, 75 ou *" data-testid="create-departements" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Quota/sem</label>
                  <input type="number" value={createData.quota_semaine} onChange={e => setCreateData(d => ({...d, quota_semaine: e.target.value}))} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-quota" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">LB Target %</label>
                  <input type="number" min="0" max="100" value={createData.lb_target_pct} onChange={e => setCreateData(d => ({...d, lb_target_pct: e.target.value}))} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-lb-target" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Priorite</label>
                  <input type="number" value={createData.priorite} onChange={e => setCreateData(d => ({...d, priorite: e.target.value}))} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="create-priorite" />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-xs text-zinc-400">Annuler</button>
              <button onClick={handleCreate} disabled={saving || !createData.client_id} className="px-3 py-1.5 text-xs bg-teal-500/20 text-teal-400 rounded-md hover:bg-teal-500/30 border border-teal-500/30 disabled:opacity-50" data-testid="create-submit-btn">Creer</button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="commandes-table">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-3 py-2.5 font-medium">Client</th>
                <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                <th className="text-left px-3 py-2.5 font-medium">Produit</th>
                <th className="text-left px-3 py-2.5 font-medium">Depts</th>
                <th className="text-left px-3 py-2.5 font-medium">Quota</th>
                <th className="text-left px-3 py-2.5 font-medium">Delivered</th>
                <th className="text-left px-3 py-2.5 font-medium">Restant</th>
                <th className="text-left px-3 py-2.5 font-medium">LB Target</th>
                <th className="text-left px-3 py-2.5 font-medium">Active</th>
                <th className="text-right px-3 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
              ) : commandes.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Aucune commande</td></tr>
              ) : commandes.map(cmd => {
                const delivered = cmd.leads_delivered_this_week ?? 0;
                const remaining = Math.max(0, (cmd.quota_semaine || 0) - delivered);
                const pct = cmd.quota_semaine > 0 ? Math.round(delivered / cmd.quota_semaine * 100) : 0;
                return (
                  <tr key={cmd.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`commande-row-${cmd.id}`}>
                    {editId === cmd.id ? (
                      <>
                        <td className="px-3 py-2 text-zinc-300">{clientName(cmd.client_id)}</td>
                        <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cmd.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{cmd.entity}</span></td>
                        <td className="px-3 py-2 text-zinc-400">{cmd.produit}</td>
                        <td className="px-3 py-2"><input value={editData.departements} onChange={e => setEditData(d => ({...d, departements: e.target.value}))} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300 w-24 text-xs" /></td>
                        <td className="px-3 py-2"><input type="number" value={editData.quota_semaine} onChange={e => setEditData(d => ({...d, quota_semaine: e.target.value}))} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300 w-16 text-xs" /></td>
                        <td className="px-3 py-2 text-zinc-400">{delivered}</td>
                        <td className="px-3 py-2 text-zinc-400">-</td>
                        <td className="px-3 py-2"><input type="number" min="0" max="100" value={editData.lb_target_pct} onChange={e => setEditData(d => ({...d, lb_target_pct: e.target.value}))} className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-zinc-300 w-14 text-xs" /></td>
                        <td className="px-3 py-2">
                          <button onClick={() => setEditData(d => ({...d, active: !d.active}))} className={`w-8 h-4 rounded-full relative transition-colors ${editData.active ? 'bg-emerald-500' : 'bg-zinc-700'}`}>
                            <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${editData.active ? 'left-4' : 'left-0.5'}`} />
                          </button>
                        </td>
                        <td className="px-3 py-2 text-right flex items-center justify-end gap-1">
                          <button onClick={saveEdit} disabled={saving} className="p-1 text-emerald-400 hover:bg-zinc-800 rounded"><Check className="w-3.5 h-3.5" /></button>
                          <button onClick={() => setEditId(null)} className="p-1 text-zinc-500 hover:bg-zinc-800 rounded"><X className="w-3.5 h-3.5" /></button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-2 text-zinc-300">{clientName(cmd.client_id)}</td>
                        <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cmd.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{cmd.entity}</span></td>
                        <td className="px-3 py-2 text-zinc-400">{cmd.produit}</td>
                        <td className="px-3 py-2 text-zinc-500 max-w-[100px] truncate" title={(cmd.departements||[]).join(', ')}>{(cmd.departements||[]).slice(0, 3).join(', ')}{(cmd.departements||[]).length > 3 ? '...' : ''}</td>
                        <td className="px-3 py-2 text-zinc-300">{cmd.quota_semaine}</td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <span className="text-zinc-300">{delivered}</span>
                            <div className="w-12 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                              <div className={`h-full rounded-full transition-all ${pct >= 100 ? 'bg-red-500' : pct >= 75 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{width: `${Math.min(100, pct)}%`}} />
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-zinc-400">{remaining}</td>
                        <td className="px-3 py-2 text-zinc-500">{Math.round((cmd.lb_target_pct || 0) * 100)}%</td>
                        <td className="px-3 py-2">{(cmd.active ?? true) ? <span className="text-[10px] text-emerald-400">Active</span> : <span className="text-[10px] text-red-400">Closed</span>}</td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => navigate(`/admin/commandes/${cmd.id}`)} className="p-1 text-zinc-500 hover:text-cyan-400 rounded" title="Détails" data-testid={`view-cmd-btn-${cmd.id}`}>
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={() => startEdit(cmd)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" data-testid={`edit-cmd-btn-${cmd.id}`}>
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
