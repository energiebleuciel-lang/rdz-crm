import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { ArrowLeft, Truck, Eye, Power, Clock, BarChart3 } from 'lucide-react';
import { ActivityBlock } from './AdminActivity';

const DEL_BADGE = {
  pending_csv: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  ready_to_send: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  sent: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
};

export default function AdminCommandeDetail() {
  const { id } = useParams();
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [cmd, setCmd] = useState(null);
  const [stats, setStats] = useState(null);
  const [deliveries, setDeliveries] = useState([]);
  const [delTotal, setDelTotal] = useState(0);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [tab, setTab] = useState('config');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, sRes] = await Promise.all([
        authFetch(`${API}/api/commandes/${id}/stats`),
        authFetch(`${API}/api/commandes?entity=ZR7`).then(async r => {
          // We need to find our commande from the list to get full data
          if (!r.ok) return null;
          const d = await r.json();
          let found = (d.commandes || []).find(c => c.id === id);
          if (!found) {
            const mdl = await authFetch(`${API}/api/commandes?entity=MDL`);
            if (mdl.ok) { const m = await mdl.json(); found = (m.commandes || []).find(c => c.id === id); }
          }
          return found;
        })
      ]);
      if (cRes.ok) setStats(await cRes.json());
      if (sRes) {
        setCmd(sRes);
        if (sRes.client_id) {
          const clRes = await authFetch(`${API}/api/clients/${sRes.client_id}`);
          if (clRes.ok) { const d = await clRes.json(); setClient(d.client || d); }
        }
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [id, authFetch]);

  const loadDeliveries = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/commandes/${id}/deliveries?limit=50`);
      if (res.ok) { const d = await res.json(); setDeliveries(d.deliveries || []); setDelTotal(d.total || 0); }
    } catch (e) { console.error(e); }
  }, [id, authFetch]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (tab === 'deliveries') loadDeliveries(); }, [tab, loadDeliveries]);

  const toggleActive = async () => {
    setToggling(true);
    try {
      await authFetch(`${API}/api/commandes/${id}/toggle`, { method: 'POST' });
      load();
    } catch (e) { console.error(e); }
    setToggling(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!cmd) return <div className="text-zinc-500 text-center py-8">Commande non trouvée</div>;

  const c = cmd;
  const s = stats || {};
  const cw = s.current_week || {};
  const pct = cw.quota > 0 ? Math.round(cw.delivered / cw.quota * 100) : 0;

  const TABS = [
    { key: 'config', label: 'Configuration', icon: BarChart3 },
    { key: 'deliveries', label: `Deliveries (${delTotal || '...'})`, icon: Truck },
    { key: 'activity', label: 'Historique', icon: Clock },
  ];

  return (
    <div data-testid="commande-detail">
      <button onClick={() => navigate('/admin/commandes')} className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 mb-4" data-testid="back-btn">
        <ArrowLeft className="w-3.5 h-3.5" /> Commandes
      </button>

      {/* Header */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4" data-testid="commande-header">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-white">{c.client_name || 'Commande'}</h1>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>{c.entity}</span>
            <span className="text-xs text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded">{c.produit}</span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${c.active ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-red-500/10 text-red-400 border-red-500/30'}`}>
              {c.active ? 'ACTIVE' : 'INACTIVE'}
            </span>
          </div>
          <button onClick={toggleActive} disabled={toggling}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border disabled:opacity-50 ${c.active ? 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'}`}
            data-testid="toggle-active-btn">
            <Power className="w-3 h-3" /> {c.active ? 'Désactiver' : 'Activer'}
          </button>
        </div>

        {/* Quota bar */}
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-zinc-500">Quota semaine: {cw.delivered || 0} / {cw.quota || 0}</span>
              <span className={`text-[10px] font-medium ${pct >= 100 ? 'text-red-400' : pct >= 75 ? 'text-amber-400' : 'text-emerald-400'}`}>{pct}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-zinc-800 overflow-hidden">
              <div className={`h-full rounded-full transition-all ${pct >= 100 ? 'bg-red-500' : pct >= 75 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(100, pct)}%` }} />
            </div>
          </div>
          <div className="text-right">
            <p className="text-lg font-semibold text-white">{c.quota_remaining ?? '-'}</p>
            <p className="text-[10px] text-zinc-500">restant</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors ${tab === t.key ? 'bg-teal-500/15 text-teal-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'}`}
            data-testid={`tab-${t.key}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {/* Config tab */}
      {tab === 'config' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="tab-content-config">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Routing</h2>
            <dl className="space-y-2 text-xs">
              {[
                ['ID', c.id],
                ['Client', c.client_name],
                ['Entity', c.entity],
                ['Produit', c.produit],
                ['Priorité', c.priorite],
                ['Quota/semaine', c.quota_semaine],
                ['LB target', `${Math.round((c.lb_target_pct || 0) * 100)}%`],
                ['Auto-renew', c.auto_renew ? 'Oui' : 'Non'],
                ['Prix/lead', `${c.prix_lead || 0} EUR`],
                ['Remise', `${c.remise_percent || 0}%`],
                ['Créé', c.created_at?.slice(0, 10)],
                ['MAJ', c.updated_at?.slice(0, 19).replace('T', ' ')],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2">
                  <dt className="text-zinc-500">{k}</dt>
                  <dd className="text-zinc-300 text-right">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="space-y-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Départements ({(c.departements || []).length})</h2>
              <div className="flex flex-wrap gap-1">
                {(c.departements || []).map(d => (
                  <span key={d} className="text-[10px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded font-mono">{d}</span>
                ))}
              </div>
            </div>

            {/* Weekly stats */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Historique quotas (4 sem.)</h2>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-emerald-400">Semaine en cours</span>
                  <span className="text-white font-medium">{cw.delivered} / {cw.quota}</span>
                </div>
                {(s.last_4_weeks || []).map((w, i) => (
                  <div key={i} className="flex justify-between text-xs">
                    <span className="text-zinc-500">S{w.week_offset}</span>
                    <span className="text-zinc-400">{w.delivered}</span>
                  </div>
                ))}
                <div className="flex justify-between text-xs pt-2 border-t border-zinc-800">
                  <span className="text-zinc-500">Total livré</span>
                  <span className="text-white font-medium">{s.total_delivered}</span>
                </div>
              </div>
            </div>

            {/* Client link */}
            {client && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2">Client</h2>
                <p className="text-sm text-white">{client.name}</p>
                <p className="text-[10px] text-zinc-500 mt-1">{client.email} | {client.phone || '-'}</p>
                <button onClick={() => navigate(`/admin/clients/${client.id}`)} className="text-[10px] text-teal-400 hover:text-teal-300 mt-2" data-testid="view-client-btn">Voir fiche client</button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Deliveries tab */}
      {tab === 'deliveries' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden" data-testid="tab-content-deliveries">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-3 py-2.5 font-medium">Date</th>
                <th className="text-left px-3 py-2.5 font-medium">Client</th>
                <th className="text-left px-3 py-2.5 font-medium">Status</th>
                <th className="text-left px-3 py-2.5 font-medium">Outcome</th>
                <th className="text-left px-3 py-2.5 font-medium">Sent To</th>
                <th className="text-left px-3 py-2.5 font-medium">Billable</th>
                <th className="text-right px-3 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {deliveries.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-zinc-600">Aucune delivery</td></tr>
              ) : deliveries.map(d => (
                <tr key={d.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                  <td className="px-3 py-2 text-zinc-400 text-[10px]">{d.created_at?.slice(5, 16).replace('T', ' ')}</td>
                  <td className="px-3 py-2 text-zinc-300">{d.client_name}</td>
                  <td className="px-3 py-2"><span className={`text-[10px] px-2 py-0.5 rounded-full border ${DEL_BADGE[d.status] || ''}`}>{d.status}</span></td>
                  <td className="px-3 py-2">
                    {d.outcome === 'rejected' ? <span className="text-[10px] px-2 py-0.5 rounded-full border bg-orange-500/10 text-orange-400 border-orange-500/30">rejected</span>
                      : d.outcome === 'removed' ? <span className="text-[10px] px-2 py-0.5 rounded-full border bg-red-500/10 text-red-300 border-red-500/30">removed</span>
                      : <span className="text-[10px] text-zinc-600">accepted</span>}
                  </td>
                  <td className="px-3 py-2 text-zinc-500 text-[10px] max-w-[140px] truncate">{d.sent_to?.join(', ') || '-'}</td>
                  <td className="px-3 py-2">{d.billable ? <span className="text-[10px] text-emerald-400">Oui</span> : <span className="text-[10px] text-zinc-600">Non</span>}</td>
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => navigate(`/admin/deliveries/${d.id}`)} className="p-1 text-zinc-500 hover:text-teal-400 rounded"><Eye className="w-3 h-3" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-3 py-2 border-t border-zinc-800 text-[10px] text-zinc-600">{delTotal} deliveries liées</div>
        </div>
      )}

      {/* Activity tab */}
      {tab === 'activity' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="tab-content-activity">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Historique modifications</h2>
          <ActivityBlock entityType="commande" entityId={id} />
        </div>
      )}
    </div>
  );
}
