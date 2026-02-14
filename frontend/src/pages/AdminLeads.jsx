import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, RefreshCw, Filter, X, Search } from 'lucide-react';

const STATUS_BADGE = {
  new: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  routed: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  livre: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  no_open_orders: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  hold_source: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  pending_config: 'bg-violet-500/10 text-violet-400 border-violet-500/30',
  duplicate: 'bg-zinc-700/50 text-zinc-400 border-zinc-600',
  invalid: 'bg-red-500/10 text-red-400 border-red-500/30',
};

export default function AdminLeads() {
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [searchText, setSearchText] = useState('');
  const [filters, setFilters] = useState({
    entity: searchParams.get('entity') || '',
    produit: searchParams.get('produit') || '',
    status: searchParams.get('status') || '',
    departement: searchParams.get('departement') || '',
    source: searchParams.get('source') || '',
    client_id: searchParams.get('client_id') || '',
  });
  const [showFilters, setShowFilters] = useState(Object.values(filters).some(Boolean));
  const limit = 50;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', limit);
      params.set('skip', page * limit);
      Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
      if (searchText) params.set('search', searchText);

      const [lRes, sRes] = await Promise.all([
        authFetch(`${API}/api/leads/list?${params}`),
        authFetch(`${API}/api/leads/stats${filters.entity ? '?entity=' + filters.entity : ''}`)
      ]);
      if (lRes.ok) { const d = await lRes.json(); setLeads(d.leads || []); setTotal(d.total || 0); }
      if (sRes.ok) setStats(await sRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [page, filters, searchText, authFetch]);

  useEffect(() => { load(); }, [load]);

  const setFilter = (key, val) => {
    setFilters(f => ({ ...f, [key]: val }));
    setPage(0);
    const sp = new URLSearchParams(searchParams);
    if (val) sp.set(key, val); else sp.delete(key);
    setSearchParams(sp, { replace: true });
  };

  const clearFilters = () => {
    setFilters({ entity: '', produit: '', status: '', departement: '', source: '', client_id: '' });
    setSearchText('');
    setPage(0);
    setSearchParams({}, { replace: true });
  };

  return (
    <div data-testid="admin-leads">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white">Leads</h1>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input value={searchText} onChange={e => setSearchText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && load()}
              placeholder="Phone, nom, email..." className="bg-zinc-800 border border-zinc-700 rounded-md pl-7 pr-3 py-1.5 text-xs text-zinc-300 w-48" data-testid="search-input" />
          </div>
          <button onClick={() => setShowFilters(!showFilters)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="filter-toggle-btn">
            <Filter className="w-3 h-3" /> Filtres
          </button>
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="refresh-btn">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stat pills */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {Object.entries(stats).filter(([k]) => k !== 'total').map(([k, v]) => (
          <button key={k} onClick={() => setFilter('status', filters.status === k ? '' : k)}
            className={`text-[10px] px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
              filters.status === k ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:border-zinc-700'
            }`} data-testid={`stat-pill-${k}`}>{k}: {v}</button>
        ))}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 mb-4 flex gap-3 items-end flex-wrap" data-testid="filters-panel">
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Entity</label>
            <select value={filters.entity} onChange={e => setFilter('entity', e.target.value)} className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-entity">
              <option value="">Toutes</option><option value="ZR7">ZR7</option><option value="MDL">MDL</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Status</label>
            <select value={filters.status} onChange={e => setFilter('status', e.target.value)} className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-status">
              <option value="">Tous</option>
              {['new','routed','livre','no_open_orders','hold_source','pending_config','duplicate','invalid'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Produit</label>
            <select value={filters.produit} onChange={e => setFilter('produit', e.target.value)} className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-produit">
              <option value="">Tous</option><option value="PV">PV</option><option value="PAC">PAC</option><option value="ISO">ISO</option><option value="ITE">ITE</option><option value="POELE">POELE</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Dept</label>
            <input value={filters.departement} onChange={e => setFilter('departement', e.target.value)} placeholder="ex: 75" className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700 w-16" data-testid="filter-dept" />
          </div>
          <button onClick={clearFilters} className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1" data-testid="clear-filters-btn"><X className="w-3 h-3" /> Reset</button>
        </div>
      )}

      {/* Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="leads-table">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-3 py-2.5 font-medium">Date</th>
                <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                <th className="text-left px-3 py-2.5 font-medium">Phone</th>
                <th className="text-left px-3 py-2.5 font-medium">Nom</th>
                <th className="text-left px-3 py-2.5 font-medium">Dept</th>
                <th className="text-left px-3 py-2.5 font-medium">Produit</th>
                <th className="text-left px-3 py-2.5 font-medium">Status</th>
                <th className="text-left px-3 py-2.5 font-medium">Client assigné</th>
                <th className="text-left px-3 py-2.5 font-medium">Source</th>
                <th className="text-right px-3 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
              ) : leads.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Aucun lead</td></tr>
              ) : leads.map(l => (
                <tr key={l.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors" data-testid={`lead-row-${l.id}`}>
                  <td className="px-3 py-2 text-zinc-500 whitespace-nowrap text-[10px]">{l.created_at?.slice(5, 16).replace('T', ' ')}</td>
                  <td className="px-3 py-2">{l.entity ? <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${l.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{l.entity}</span> : <span className="text-zinc-700">-</span>}</td>
                  <td className="px-3 py-2 text-zinc-300 font-mono text-[10px]">{l.phone}</td>
                  <td className="px-3 py-2 text-zinc-300">{l.nom} {l.prenom && <span className="text-zinc-500">{l.prenom}</span>}</td>
                  <td className="px-3 py-2 text-zinc-400">{l.departement}</td>
                  <td className="px-3 py-2 text-zinc-400">{l.produit || '-'}</td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGE[l.status] || 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>{l.status}</span>
                  </td>
                  <td className="px-3 py-2 text-zinc-400 max-w-[130px] truncate">{l.delivered_to_client_name || l.delivery_client_name || '-'}</td>
                  <td className="px-3 py-2 text-zinc-600 max-w-[100px] truncate text-[10px]">{l.source || l.lp_code || '-'}</td>
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => navigate(`/admin/leads/${l.id}`)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" data-testid={`view-lead-btn-${l.id}`}>
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
