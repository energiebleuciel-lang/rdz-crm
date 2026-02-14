import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Activity, AlertTriangle, Shield, TrendingUp, TrendingDown, BarChart3, GitCompare, Filter, Zap } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

const RANGES = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7 jours' },
  { value: '30d', label: '30 jours' },
  { value: '90d', label: '90 jours' },
];

const PRODUCTS = ['ALL', 'PV', 'PAC', 'ITE'];

function Metric({ label, value, sub, color = 'teal' }) {
  const colors = {
    teal: 'text-teal-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
    emerald: 'text-emerald-400',
    blue: 'text-blue-400',
    zinc: 'text-zinc-400',
  };
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid={`metric-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colors[color]}`}>{value}</p>
      {sub && <p className="text-[11px] text-zinc-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function TrendBadge({ value }) {
  if (!value || value === 0) return <span className="text-zinc-600 text-xs">—</span>;
  const up = value > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${up ? 'text-emerald-400' : 'text-red-400'}`}>
      {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {up ? '+' : ''}{value}%
    </span>
  );
}

function QualityBar({ valid, suspicious, invalid }) {
  const total = valid + suspicious + invalid || 1;
  return (
    <div className="flex h-2 rounded-full overflow-hidden bg-zinc-800 w-full">
      <div className="bg-emerald-500" style={{ width: `${valid / total * 100}%` }} />
      <div className="bg-amber-500" style={{ width: `${suspicious / total * 100}%` }} />
      <div className="bg-red-500" style={{ width: `${invalid / total * 100}%` }} />
    </div>
  );
}

export default function AdminMonitoring() {
  const { authFetch, entityScope } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState('7d');
  const [product, setProduct] = useState('ALL');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ range });
      if (product !== 'ALL') params.set('product', product);
      const res = await authFetch(`${API}/api/monitoring/intelligence?${params}`);
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error('Monitoring fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [authFetch, range, product, entityScope]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading && !data) {
    return (
      <div className="text-center py-20 text-zinc-500">
        <Activity className="w-6 h-6 animate-spin mx-auto mb-2" />
        Chargement...
      </div>
    );
  }

  if (!data) return <p className="text-zinc-500 text-center py-10">Aucune donnée</p>;

  const kpis = data.kpis || {};
  const lb = data.lb_stats || {};
  const pq = data.phone_quality || [];
  const dups = data.duplicate_by_source || [];
  const crossMatrix = data.duplicate_cross_matrix || [];
  const rejections = data.rejections_by_source || [];
  const delayBuckets = data.duplicate_delay_buckets || {};

  return (
    <div data-testid="monitoring-intelligence-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Zap className="w-6 h-6 text-teal-400" />
            Monitoring Intelligence
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Qualité, doublons, performance par source</p>
        </div>
        <div className="flex items-center gap-2" data-testid="monitoring-filters">
          <Filter className="w-4 h-4 text-zinc-500" />
          {RANGES.map(r => (
            <button key={r.value} onClick={() => setRange(r.value)}
              className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                range === r.value
                  ? 'bg-teal-500/20 text-teal-400 border-teal-500/40'
                  : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/50 hover:border-zinc-600'
              }`} data-testid={`range-${r.value}`}>
              {r.label}
            </button>
          ))}
          <span className="w-px h-5 bg-zinc-700 mx-1" />
          {PRODUCTS.map(p => (
            <button key={p} onClick={() => setProduct(p)}
              className={`px-2 py-1 text-xs rounded-md border transition-colors ${
                product === p
                  ? 'bg-blue-500/20 text-blue-400 border-blue-500/40'
                  : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/50 hover:border-zinc-600'
              }`}>
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
        <Metric label="Total Leads" value={kpis.total_leads?.toLocaleString()} color="zinc" />
        <Metric label="Delivered" value={kpis.delivered?.toLocaleString()} color="teal" />
        <Metric label="Valid" value={kpis.valid_total?.toLocaleString()} color="emerald" />
        <Metric label="Deliverability" value={`${kpis.real_deliverability_rate}%`} color="blue" />
        <Metric label="Clean Rate" value={`${kpis.clean_rate}%`} color="emerald" />
        <Metric label="Economic Yield" value={`${kpis.economic_yield}%`} color="teal" />
        <Metric label="LB Stock" value={lb.lb_stock_available} sub={`${lb.lb_usage_rate || 0}% usage`} color="amber" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Phone Quality by Source */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-phone-quality">
          <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            Phone Quality by Source
          </h2>
          <div className="space-y-3">
            {pq.map((s, i) => (
              <div key={i} className="border-b border-zinc-800/50 pb-2 last:border-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-zinc-300">{s.source_type}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-zinc-500">{s.total_leads} leads</span>
                    <TrendBadge value={s.trend_pct} />
                  </div>
                </div>
                <QualityBar valid={s.valid_count} suspicious={s.suspicious_count} invalid={s.invalid_count} />
                <div className="flex gap-3 mt-1">
                  <span className="text-[10px] text-emerald-400">{s.valid_rate}% valid</span>
                  <span className="text-[10px] text-amber-400">{s.suspicious_rate}% susp</span>
                  <span className="text-[10px] text-red-400">{s.invalid_rate}% inv</span>
                </div>
              </div>
            ))}
            {pq.length === 0 && <p className="text-xs text-zinc-600">Aucune donnée</p>}
          </div>
        </div>

        {/* Duplicate Rate by Source */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-duplicate-rate">
          <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-amber-400" />
            Duplicate Rate by Source
          </h2>
          <div className="space-y-1.5">
            {dups.filter(d => d.total_leads > 0).slice(0, 10).map((d, i) => (
              <div key={i} className="flex items-center justify-between py-1 border-b border-zinc-800/30 last:border-0">
                <span className="text-xs text-zinc-400 truncate max-w-[180px]">{d.source || '(direct)'}</span>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-zinc-500">{d.total_leads} leads</span>
                  <span className={`text-xs font-mono font-bold ${d.duplicate_rate > 10 ? 'text-red-400' : d.duplicate_rate > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {d.duplicate_rate}%
                  </span>
                </div>
              </div>
            ))}
          </div>
          {/* Delay buckets */}
          {(delayBuckets.lt_24h > 0 || delayBuckets['1d_7d'] > 0 || delayBuckets.gt_7d > 0) && (
            <div className="mt-3 pt-3 border-t border-zinc-800">
              <p className="text-[10px] uppercase text-zinc-600 mb-1.5">Delay Distribution</p>
              <div className="flex gap-2">
                <span className="text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded">&lt;24h: {delayBuckets.lt_24h}</span>
                <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">1-7d: {delayBuckets['1d_7d']}</span>
                <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">&gt;7d: {delayBuckets.gt_7d}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* LB Replacement Efficiency */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-lb-efficiency">
          <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-teal-400" />
            LB Replacement Efficiency
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] uppercase text-zinc-600">Suspicious Total</p>
              <p className="text-lg font-bold text-amber-400">{lb.suspicious_total || 0}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase text-zinc-600">LB Replaced</p>
              <p className="text-lg font-bold text-emerald-400">{lb.lb_replaced_count || 0}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase text-zinc-600">Susp. Delivered</p>
              <p className="text-lg font-bold text-red-400">{lb.suspicious_delivered_count || 0}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase text-zinc-600">LB Usage Rate</p>
              <p className="text-lg font-bold text-teal-400">{lb.lb_usage_rate || 0}%</p>
            </div>
          </div>
        </div>

        {/* Cross-Source Duplicate Matrix */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-cross-matrix">
          <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            Cross-Source Conflicts
          </h2>
          {crossMatrix.length > 0 ? (
            <div className="space-y-1.5">
              {crossMatrix.slice(0, 8).map((m, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-zinc-800/30 last:border-0">
                  <span className="text-xs text-zinc-400">
                    {m.source_a || '(none)'} <span className="text-zinc-600">vs</span> {m.source_b || '(none)'}
                  </span>
                  <span className="text-xs font-bold text-red-400">{m.conflict_count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-600">Aucun conflit détecté</p>
          )}
        </div>
      </div>

      {/* Source Intelligence Ranking */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-source-ranking">
        <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-blue-400" />
          Source Intelligence Ranking
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-2 pr-4">Source</th>
                <th className="text-right px-2">Total</th>
                <th className="text-right px-2">Rejetés</th>
                <th className="text-right px-2">Raison principale</th>
              </tr>
            </thead>
            <tbody>
              {rejections.slice(0, 15).map((r, i) => {
                const topReason = Object.entries(r.by_reason || {}).sort((a, b) => b[1] - a[1])[0];
                return (
                  <tr key={i} className="border-b border-zinc-800/30 hover:bg-zinc-800/30">
                    <td className="py-1.5 pr-4 text-zinc-300 font-medium">{r.source || '(direct)'}</td>
                    <td className="text-right px-2 text-zinc-400">{r.total_rejected}</td>
                    <td className="text-right px-2">
                      <span className="text-red-400 font-mono">{r.total_rejected}</span>
                    </td>
                    <td className="text-right px-2 text-zinc-500">
                      {topReason ? `${topReason[0]} (${topReason[1]})` : '—'}
                    </td>
                  </tr>
                );
              })}
              {rejections.length === 0 && (
                <tr><td colSpan={4} className="py-4 text-center text-zinc-600">Aucun rejet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {data._errors && data._errors.length > 0 && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-xs text-red-400">Erreurs partielles: {data._errors.join(', ')}</p>
        </div>
      )}
    </div>
  );
}
