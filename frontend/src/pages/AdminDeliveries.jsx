import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import { Download, Send, Eye, RefreshCw, Filter, X } from 'lucide-react';

const STATUS_BADGE = {
  pending_csv: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  ready_to_send: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  sending: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  sent: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
};

export default function AdminDeliveries() {
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [deliveries, setDeliveries] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState({ status: '', entity: '', client_id: '' });
  const [showFilters, setShowFilters] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const limit = 50;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', limit);
      params.set('skip', page * limit);
      if (filters.status) params.set('status', filters.status);
      if (filters.entity) params.set('entity', filters.entity);
      if (filters.client_id) params.set('client_id', filters.client_id);

      const [dRes, sRes] = await Promise.all([
        authFetch(`${API}/api/deliveries?${params}`),
        authFetch(`${API}/api/deliveries/stats${filters.entity ? '?entity=' + filters.entity : ''}`)
      ]);

      if (dRes.ok) { const d = await dRes.json(); setDeliveries(d.deliveries || []); setTotal(d.total || 0); }
      if (sRes.ok) setStats(await sRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [page, filters, authFetch]);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (id, action) => {
    setActionLoading(id);
    try {
      if (action === 'send') {
        await authFetch(`${API}/api/deliveries/${id}/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      } else if (action === 'resend') {
        await authFetch(`${API}/api/deliveries/${id}/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ force: true }) });
      } else if (action === 'download') {
        const res = await authFetch(`${API}/api/deliveries/${id}/download`);
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = `delivery_${id}.csv`; a.click(); URL.revokeObjectURL(url);
        }
        setActionLoading(null); return;
      }
      load();
    } catch (e) { console.error(e); }
    setActionLoading(null);
  };

  const StatusPill = ({ status }) => (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGE[status] || 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>
      {status}
    </span>
  );

  return (
    <div data-testid="admin-deliveries">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white">Deliveries</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowFilters(!showFilters)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="filter-toggle-btn">
            <Filter className="w-3 h-3" /> Filtres
          </button>
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="refresh-btn">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Quick stats */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {Object.entries(stats).filter(([k]) => !['total'].includes(k)).map(([k, v]) => (
          <button key={k} onClick={() => { if (['pending_csv','ready_to_send','sending','sent','failed'].includes(k)) { setFilters(f => ({ ...f, status: f.status === k ? '' : k })); setPage(0); }}}
            className={`text-[10px] px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
              filters.status === k ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:border-zinc-700'
            }`} data-testid={`stat-pill-${k}`}>
            {k}: {v}
          </button>
        ))}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 mb-4 flex gap-3 items-end flex-wrap" data-testid="filters-panel">
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Entity</label>
            <select value={filters.entity} onChange={e => { setFilters(f => ({ ...f, entity: e.target.value })); setPage(0); }}
              className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-entity">
              <option value="">Toutes</option>
              <option value="ZR7">ZR7</option>
              <option value="MDL">MDL</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Status</label>
            <select value={filters.status} onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(0); }}
              className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-status">
              <option value="">Tous</option>
              {['pending_csv','ready_to_send','sending','sent','failed'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <button onClick={() => { setFilters({ status: '', entity: '', client_id: '' }); setPage(0); }}
            className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1" data-testid="clear-filters-btn"><X className="w-3 h-3" /> Reset</button>
        </div>
      )}

      {/* Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="deliveries-table">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-3 py-2.5 font-medium">Date</th>
                <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                <th className="text-left px-3 py-2.5 font-medium">Client</th>
                <th className="text-left px-3 py-2.5 font-medium">Produit</th>
                <th className="text-left px-3 py-2.5 font-medium">Status</th>
                <th className="text-left px-3 py-2.5 font-medium">Outcome</th>
                <th className="text-left px-3 py-2.5 font-medium">Sent To</th>
                <th className="text-left px-3 py-2.5 font-medium">Attempts</th>
                <th className="text-right px-3 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
              ) : deliveries.length === 0 ? (
                <tr><td colSpan={9} className="text-center py-8 text-zinc-600">Aucune delivery</td></tr>
              ) : deliveries.map(d => (
                <tr key={d.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors" data-testid={`delivery-row-${d.id}`}>
                  <td className="px-3 py-2 text-zinc-400 whitespace-nowrap">{d.created_at?.slice(0, 16).replace('T', ' ')}</td>
                  <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${d.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{d.entity}</span></td>
                  <td className="px-3 py-2 text-zinc-300 max-w-[140px] truncate">{d.client_name}</td>
                  <td className="px-3 py-2 text-zinc-400">{d.produit}</td>
                  <td className="px-3 py-2"><StatusPill status={d.status} /></td>
                  <td className="px-3 py-2">
                    {d.outcome === 'rejected'
                      ? <span className="text-[10px] px-2 py-0.5 rounded-full border bg-orange-500/10 text-orange-400 border-orange-500/30">rejected</span>
                      : <span className="text-[10px] text-zinc-600">{d.billable ? 'billable' : '-'}</span>}
                  </td>
                  <td className="px-3 py-2 text-zinc-500 max-w-[160px] truncate">{d.sent_to?.join(', ') || '-'}</td>
                  <td className="px-3 py-2 text-zinc-500">{d.send_attempts || 0}</td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => navigate(`/admin/deliveries/${d.id}`)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" title="Détails" data-testid={`view-btn-${d.id}`}>
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      {d.has_csv && (
                        <button onClick={() => handleAction(d.id, 'download')} className="p-1 text-zinc-500 hover:text-cyan-400 rounded" title="Download CSV" data-testid={`download-btn-${d.id}`} disabled={actionLoading === d.id}>
                          <Download className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {d.status === 'ready_to_send' && (
                        <button onClick={() => handleAction(d.id, 'send')} className="p-1 text-zinc-500 hover:text-emerald-400 rounded" title="Send now" data-testid={`send-btn-${d.id}`} disabled={actionLoading === d.id}>
                          <Send className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {d.status === 'sent' && (
                        <button onClick={() => handleAction(d.id, 'resend')} className="p-1 text-zinc-500 hover:text-amber-400 rounded" title="Resend (force)" data-testid={`resend-btn-${d.id}`} disabled={actionLoading === d.id}>
                          <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-3 py-2 border-t border-zinc-800">
          <span className="text-[10px] text-zinc-600">{total} total</span>
          <div className="flex gap-1">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-2 py-1 text-[10px] text-zinc-400 bg-zinc-800 rounded disabled:opacity-30 hover:bg-zinc-700" data-testid="prev-page-btn">Prev</button>
            <span className="px-2 py-1 text-[10px] text-zinc-500">{page + 1} / {Math.max(1, Math.ceil(total / limit))}</span>
            <button disabled={(page + 1) * limit >= total} onClick={() => setPage(p => p + 1)} className="px-2 py-1 text-[10px] text-zinc-400 bg-zinc-800 rounded disabled:opacity-30 hover:bg-zinc-700" data-testid="next-page-btn">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
