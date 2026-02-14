import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Link } from 'react-router-dom';
import {
  RefreshCw, ChevronLeft, ChevronRight, Search, X, MapPin,
  TrendingUp, TrendingDown, Minus, Users, ShoppingCart, BarChart3
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { getCurrentWeekKey, shiftWeekKey, weekKeyToShort } from '../lib/weekUtils';
import { WeekNavStandard } from '../components/WeekNav';

const STATUS_CFG = {
  no_order: { label: 'Sans commande', cls: 'bg-zinc-700/60 text-zinc-300 border-zinc-600' },
  on_remaining: { label: 'ON', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  saturated: { label: 'Saturé', cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  inactive_blocked: { label: 'Bloqué', cls: 'bg-red-500/15 text-red-400 border-red-500/30' },
};

function Pill({ status }) {
  const cfg = STATUS_CFG[status] || STATUS_CFG.no_order;
  return <span className={`text-[10px] px-2 py-0.5 rounded-full border ${cfg.cls}`}>{cfg.label}</span>;
}

function DeltaBadge({ pct }) {
  if (pct > 0) return <span className="text-emerald-400 text-[10px] flex items-center gap-0.5"><TrendingUp className="w-3 h-3" />+{pct}%</span>;
  if (pct < 0) return <span className="text-red-400 text-[10px] flex items-center gap-0.5"><TrendingDown className="w-3 h-3" />{pct}%</span>;
  return <span className="text-zinc-500 text-[10px] flex items-center gap-0.5"><Minus className="w-3 h-3" />0%</span>;
}

function MiniBar({ value, max }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const color = pct >= 90 ? 'bg-amber-500' : pct >= 50 ? 'bg-teal-500' : 'bg-teal-500/60';
  return (
    <div className="w-16 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

/* ===== DRAWER COMPONENT ===== */
function DeptDrawer({ dept, product, week, onClose, authFetch }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!dept) return;
    setLoading(true);
    authFetch(`${API}/api/departements/${dept}/detail?product=${product}&week=${week}`)
      .then(r => r.json()).then(d => setData(d)).catch(() => {})
      .finally(() => setLoading(false));
  }, [dept, product, week, authFetch]);

  if (!dept) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="dept-drawer">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-[520px] max-w-full bg-zinc-900 border-l border-zinc-800 overflow-y-auto">
        <div className="sticky top-0 bg-zinc-900 border-b border-zinc-800 px-5 py-3 flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-teal-400" />
            <h2 className="text-sm font-semibold text-white">Département {dept}</h2>
            <span className="text-[10px] text-zinc-500">{product}</span>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-400 hover:text-white"><X className="w-4 h-4" /></button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-5 h-5 text-teal-500 animate-spin" />
          </div>
        ) : data ? (
          <div className="p-5 space-y-5">
            {/* KPIs */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Produced', val: data.kpi?.produced_current, prev: data.kpi?.produced_prev },
                { label: 'Billable', val: data.kpi?.billable_current },
                { label: 'Non-billable', val: data.kpi?.non_billable_current },
              ].map(k => (
                <div key={k.label} className="bg-zinc-800/60 rounded-lg p-3 border border-zinc-700/50">
                  <p className="text-[10px] text-zinc-500 mb-1">{k.label}</p>
                  <p className="text-lg font-bold text-white">{k.val ?? 0}</p>
                  {k.prev !== undefined && (
                    <p className="text-[10px] text-zinc-500 mt-0.5">
                      vs {k.prev} <DeltaBadge pct={k.prev > 0 ? Math.round((k.val - k.prev) / k.prev * 100) : (k.val > 0 ? 100 : 0)} />
                    </p>
                  )}
                </div>
              ))}
            </div>
            <div className="bg-zinc-800/60 rounded-lg p-3 border border-zinc-700/50">
              <p className="text-[10px] text-zinc-500 mb-1">Quota semaine</p>
              <p className="text-lg font-bold text-white">{data.kpi?.quota_week_total ?? 0}</p>
            </div>

            {/* Timeseries chart */}
            <div className="bg-zinc-800/40 border border-zinc-700/50 rounded-lg p-3">
              <p className="text-[10px] text-zinc-500 mb-2">Historique 8 semaines</p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={data.timeseries || []} barGap={1}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="week" tick={{ fill: '#71717a', fontSize: 9 }} tickFormatter={w => w.split('-')[1]} />
                  <YAxis tick={{ fill: '#71717a', fontSize: 9 }} width={30} />
                  <Tooltip
                    contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 6, fontSize: 11 }}
                    labelStyle={{ color: '#a1a1aa' }}
                  />
                  <Bar dataKey="produced" fill="#2dd4bf" radius={[2, 2, 0, 0]} name="Produced" />
                  <Bar dataKey="billable" fill="#14b8a6" radius={[2, 2, 0, 0]} name="Billable" />
                  <Bar dataKey="non_billable" fill="#f59e0b" radius={[2, 2, 0, 0]} name="Non-billable" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Clients covering */}
            <div>
              <p className="text-xs font-medium text-zinc-300 mb-2 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-teal-400" /> Clients couvrants ({data.clients_covering?.length ?? 0})
              </p>
              <div className="space-y-2">
                {(data.clients_covering || []).map((c, i) => (
                  <div key={i} className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <Link to={`/admin/clients/${c.client_id}`} className="text-xs font-medium text-teal-400 hover:underline">
                        {c.name || c.client_id}
                      </Link>
                      <Link to={`/admin/commandes/${c.commande_id}`} className="text-[10px] text-zinc-500 hover:text-zinc-300">
                        <ShoppingCart className="w-3 h-3 inline mr-0.5" />Commande
                      </Link>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-[10px]">
                      <div><span className="text-zinc-500">Quota</span><p className="text-zinc-200 font-medium">{c.quota_week || '∞'}</p></div>
                      <div><span className="text-zinc-500">Billable</span><p className="text-zinc-200 font-medium">{c.billable_week}</p></div>
                      <div>
                        <span className="text-zinc-500">Remaining</span>
                        <p className={`font-medium ${c.remaining_week < 0 ? 'text-zinc-400' : c.remaining_week === 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                          {c.remaining_week < 0 ? '∞' : c.remaining_week}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-5 text-zinc-500 text-sm">Aucune donnée</div>
        )}
      </div>
    </div>
  );
}

/* ===== CLIENT COVERAGE TAB ===== */
function ClientCoverageTab({ week, product, authFetch, allClients }) {
  const [clientId, setClientId] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!clientId) return;
    setLoading(true);
    try {
      const r = await authFetch(`${API}/api/clients/${clientId}/coverage?product=${product}&week=${week}`);
      if (r.ok) setData(await r.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [clientId, week, product, authFetch]);

  useEffect(() => { if (clientId) load(); }, [load, clientId]);

  return (
    <div data-testid="client-coverage-tab">
      {/* Client selector */}
      <div className="mb-4">
        <label className="text-[10px] text-zinc-500 block mb-1">Client</label>
        <select
          value={clientId} onChange={e => setClientId(e.target.value)}
          className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-3 py-1.5 border border-zinc-700 min-w-[250px]"
          data-testid="client-select"
        >
          <option value="">Sélectionner un client</option>
          {allClients.map(c => (
            <option key={c.id} value={c.id}>{c.name} ({c.entity})</option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="flex items-center gap-2 py-8 justify-center text-zinc-500 text-xs">
          <RefreshCw className="w-4 h-4 animate-spin" /> Chargement...
        </div>
      )}

      {!loading && data && (
        <>
          {/* Aggregates */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            {[
              { label: 'Produced', val: data.aggregates?.produced_week },
              { label: 'Billable', val: data.aggregates?.billable_week },
              { label: 'Quota', val: data.aggregates?.quota_week },
              { label: 'Remaining', val: data.aggregates?.remaining_week, colored: true },
            ].map(k => (
              <div key={k.label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                <p className="text-[10px] text-zinc-500 mb-1">{k.label}</p>
                <p className={`text-lg font-bold ${
                  k.colored ? (k.val < 0 ? 'text-zinc-400' : k.val === 0 ? 'text-amber-400' : 'text-emerald-400') : 'text-white'
                }`}>{k.val < 0 ? '∞' : k.val ?? 0}</p>
              </div>
            ))}
          </div>

          {/* Dept table */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                  <th className="text-left px-3 py-2 font-medium">Dept</th>
                  <th className="text-left px-3 py-2 font-medium">Produit</th>
                  <th className="text-right px-3 py-2 font-medium">Quota</th>
                  <th className="text-right px-3 py-2 font-medium">Billable</th>
                  <th className="text-right px-3 py-2 font-medium">Remaining</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Commandes</th>
                </tr>
              </thead>
              <tbody>
                {(data.departements || []).map((d, i) => (
                  <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-3 py-2 text-white font-medium">{d.departement}</td>
                    <td className="px-3 py-2 text-zinc-400">{d.produit}</td>
                    <td className="px-3 py-2 text-right text-zinc-300">{d.quota_week || '∞'}</td>
                    <td className="px-3 py-2 text-right text-zinc-300">{d.billable_week}</td>
                    <td className={`px-3 py-2 text-right font-medium ${d.remaining_week < 0 ? 'text-zinc-400' : d.remaining_week === 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {d.remaining_week < 0 ? '∞' : d.remaining_week}
                    </td>
                    <td className="px-3 py-2"><Pill status={d.status} /></td>
                    <td className="px-3 py-2">
                      {(d.commandes || []).map((c, j) => (
                        <Link key={j} to={`/admin/commandes/${c.commande_id}`} className="text-[10px] text-teal-400 hover:underline mr-1">
                          {c.produit}
                        </Link>
                      ))}
                    </td>
                  </tr>
                ))}
                {(!data.departements || data.departements.length === 0) && (
                  <tr><td colSpan={7} className="px-3 py-6 text-center text-zinc-500">Aucun département couvert</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!loading && !data && clientId && (
        <div className="text-zinc-500 text-sm py-8 text-center">Aucune donnée</div>
      )}
      {!clientId && (
        <div className="text-zinc-500 text-sm py-12 text-center">Sélectionnez un client pour voir sa couverture</div>
      )}
    </div>
  );
}

/* ===== MAIN PAGE ===== */
export default function AdminDepartements() {
  const { authFetch } = useAuth();
  const [tab, setTab] = useState('depts');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState([]);
  const [allClients, setAllClients] = useState([]);

  // Filters
  const [product, setProduct] = useState('ALL');
  const [period, setPeriod] = useState('week');
  const [week, setWeek] = useState(getCurrentWeekKey());
  const [searchDept, setSearchDept] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Drawer
  const [drawerDept, setDrawerDept] = useState(null);

  // Sort
  const [sortKey, setSortKey] = useState('departement');
  const [sortDir, setSortDir] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ product, period, week });
      if (searchDept) params.set('departements', searchDept);
      const r = await authFetch(`${API}/api/departements/overview?${params}`);
      if (r.ok) {
        const d = await r.json();
        setData(d.results || []);
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [product, period, week, searchDept, authFetch]);

  const loadClients = useCallback(async () => {
    try {
      const [r1, r2] = await Promise.all([
        authFetch(`${API}/api/clients?entity=ZR7&active_only=false`),
        authFetch(`${API}/api/clients?entity=MDL&active_only=false`),
      ]);
      const c1 = r1.ok ? (await r1.json()).clients || [] : [];
      const c2 = r2.ok ? (await r2.json()).clients || [] : [];
      setAllClients([...c1, ...c2]);
    } catch (e) { console.error(e); }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadClients(); }, [loadClients]);

  const handleWeekNav = (dir) => setWeek(w => shiftWeekKey(w, dir));

  // Filter + sort data
  const filtered = data.filter(r => {
    if (statusFilter && r.status !== statusFilter) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    const va = a[sortKey], vb = b[sortKey];
    if (typeof va === 'string') return va.localeCompare(vb) * sortDir;
    return ((va || 0) - (vb || 0)) * sortDir;
  });

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d * -1);
    else { setSortKey(key); setSortDir(1); }
  };

  // Status counts
  const counts = { no_order: 0, on_remaining: 0, saturated: 0, inactive_blocked: 0 };
  data.forEach(r => { if (counts[r.status] !== undefined) counts[r.status]++; });

  const SortHead = ({ k, label, align }) => (
    <th className={`px-3 py-2 font-medium cursor-pointer hover:text-zinc-300 select-none ${align || 'text-left'}`}
        onClick={() => toggleSort(k)}>
      {label} {sortKey === k ? (sortDir > 0 ? '↑' : '↓') : ''}
    </th>
  );

  return (
    <div data-testid="admin-departements">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <MapPin className="w-5 h-5 text-teal-400" />
          <h1 className="text-lg font-semibold text-white">Départements</h1>
          <span className="text-xs text-zinc-500">{data.length} résultats</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="refresh-btn">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 items-end flex-wrap mb-4" data-testid="dept-filters">
        <div>
          <label className="text-[10px] text-zinc-500 block mb-1">Produit</label>
          <select value={product} onChange={e => setProduct(e.target.value)}
            className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-product">
            <option value="ALL">ALL</option>
            <option value="PV">PV</option>
            <option value="PAC">PAC</option>
            <option value="ITE">ITE</option>
          </select>
        </div>
        <div>
          <label className="text-[10px] text-zinc-500 block mb-1">Période</label>
          <div className="flex rounded-md overflow-hidden border border-zinc-700">
            {['week', 'day'].map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 text-xs ${period === p ? 'bg-teal-500/20 text-teal-400' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'}`}
                data-testid={`period-${p}`}>
                {p === 'week' ? 'Semaine' : 'Jour'}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-[10px] text-zinc-500 block mb-1">Semaine</label>
          <WeekNavStandard week={week} onChange={handleWeekNav} />
        </div>
        <div>
          <label className="text-[10px] text-zinc-500 block mb-1">Département</label>
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input value={searchDept} onChange={e => setSearchDept(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && load()}
              placeholder="75,92,93" className="bg-zinc-800 border border-zinc-700 rounded-md pl-6 pr-2 py-1.5 text-xs text-zinc-300 w-28" data-testid="search-dept" />
          </div>
        </div>
      </div>

      {/* Status pills */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {Object.entries(counts).map(([k, v]) => (
          <button key={k} onClick={() => setStatusFilter(statusFilter === k ? '' : k)}
            className={`text-[10px] px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
              statusFilter === k ? STATUS_CFG[k].cls : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:border-zinc-700'
            }`} data-testid={`status-pill-${k}`}>
            {STATUS_CFG[k].label}: {v}
          </button>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-0 mb-4 border-b border-zinc-800">
        {[
          { id: 'depts', label: 'Départements', icon: MapPin },
          { id: 'coverage', label: 'Client Coverage', icon: Users },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs border-b-2 transition-colors ${
              tab === t.id ? 'text-teal-400 border-teal-400' : 'text-zinc-500 border-transparent hover:text-zinc-300'
            }`} data-testid={`tab-${t.id}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'depts' && (
        <div data-testid="depts-tab">
          {loading ? (
            <div className="flex items-center gap-2 py-12 justify-center text-zinc-500 text-xs">
              <RefreshCw className="w-4 h-4 animate-spin" /> Chargement...
            </div>
          ) : (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto">
              <table className="w-full text-xs" data-testid="dept-table">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                    <SortHead k="departement" label="Dept" />
                    <SortHead k="produit" label="Produit" />
                    <SortHead k="produced_current" label="Produced" align="text-right" />
                    <th className="px-3 py-2 font-medium text-right">Δ</th>
                    <SortHead k="billable_current" label="Billable" align="text-right" />
                    <th className="px-3 py-2 font-medium text-right">Non-bill.</th>
                    <SortHead k="quota_week_total" label="Quota" align="text-right" />
                    <SortHead k="remaining_week" label="Remaining" align="text-right" />
                    <th className="px-3 py-2 font-medium text-center">Status</th>
                    <th className="px-3 py-2 font-medium">Clients</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((r, i) => (
                    <tr key={i}
                      className="border-b border-zinc-800/50 hover:bg-zinc-800/30 cursor-pointer"
                      onClick={() => setDrawerDept(r.departement)}
                      data-testid={`dept-row-${r.departement}-${r.produit}`}
                    >
                      <td className="px-3 py-2 text-white font-medium">{r.departement}</td>
                      <td className="px-3 py-2 text-zinc-400">{r.produit}</td>
                      <td className="px-3 py-2 text-right text-zinc-300">{r.produced_current}</td>
                      <td className="px-3 py-2 text-right">
                        <DeltaBadge pct={r.produced_delta_pct} />
                      </td>
                      <td className="px-3 py-2 text-right text-zinc-300">{r.billable_current}</td>
                      <td className="px-3 py-2 text-right text-zinc-400">{r.non_billable_current}</td>
                      <td className="px-3 py-2 text-right text-zinc-300">{r.quota_week_total || '∞'}</td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <MiniBar value={r.quota_week_total - (r.remaining_week < 0 ? 0 : r.remaining_week)} max={r.quota_week_total} />
                          <span className={`font-medium ${r.remaining_week < 0 ? 'text-zinc-400' : r.remaining_week === 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                            {r.remaining_week < 0 ? '∞' : r.remaining_week}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-center"><Pill status={r.status} /></td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {(r.clients_covering || []).slice(0, 3).map((c, j) => (
                            <span key={j} className="text-[10px] bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded border border-zinc-700 truncate max-w-[80px]" title={c.name}>
                              {c.name}
                            </span>
                          ))}
                          {(r.clients_covering || []).length > 3 && (
                            <span className="text-[10px] text-zinc-500">+{r.clients_covering.length - 3}</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {sorted.length === 0 && (
                    <tr><td colSpan={10} className="px-3 py-8 text-center text-zinc-500">Aucun département trouvé</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'coverage' && (
        <ClientCoverageTab week={week} product={product} authFetch={authFetch} allClients={allClients} />
      )}

      {/* Drawer */}
      <DeptDrawer
        dept={drawerDept}
        product={product}
        week={week}
        onClose={() => setDrawerDept(null)}
        authFetch={authFetch}
      />
    </div>
  );
}
