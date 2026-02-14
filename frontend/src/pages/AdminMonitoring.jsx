import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Activity, AlertTriangle, Shield, TrendingUp, TrendingDown, BarChart3, GitCompare, Filter, Zap, Skull, Star, ArrowRightLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';
const RANGES = [{ value: '24h', label: '24h' }, { value: '7d', label: '7j' }, { value: '30d', label: '30j' }, { value: '90d', label: '90j' }];
const PRODUCTS = ['ALL', 'PV', 'PAC', 'ITE'];

function Metric({ label, value, sub, color = 'teal' }) {
  const c = { teal: 'text-teal-400', amber: 'text-amber-400', red: 'text-red-400', emerald: 'text-emerald-400', blue: 'text-blue-400', zinc: 'text-zinc-400' };
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3" data-testid={`metric-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-0.5">{label}</p>
      <p className={`text-xl font-bold ${c[color]}`}>{value}</p>
      {sub && <p className="text-[10px] text-zinc-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function TrendBadge({ value }) {
  if (!value || value === 0) return <span className="text-zinc-600 text-[10px]">—</span>;
  const up = value > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] font-medium ${up ? 'text-emerald-400' : 'text-red-400'}`}>
      {up ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
      {up ? '+' : ''}{value}%
    </span>
  );
}

function QualityBar({ valid, suspicious, invalid }) {
  const t = valid + suspicious + invalid || 1;
  return (
    <div className="flex h-1.5 rounded-full overflow-hidden bg-zinc-800 w-full">
      <div className="bg-emerald-500" style={{ width: `${valid / t * 100}%` }} />
      <div className="bg-amber-500" style={{ width: `${suspicious / t * 100}%` }} />
      <div className="bg-red-500" style={{ width: `${invalid / t * 100}%` }} />
    </div>
  );
}

function ScoreBadge({ score, type }) {
  let color = 'text-zinc-400 bg-zinc-800';
  if (type === 'trust') {
    if (score >= 70) color = 'text-emerald-400 bg-emerald-500/15';
    else if (score >= 40) color = 'text-amber-400 bg-amber-500/15';
    else color = 'text-red-400 bg-red-500/15';
  } else {
    if (score >= 50) color = 'text-red-400 bg-red-500/15';
    else if (score >= 20) color = 'text-amber-400 bg-amber-500/15';
    else color = 'text-emerald-400 bg-emerald-500/15';
  }
  return <span className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${color}`}>{score}</span>;
}

export default function AdminMonitoring() {
  const { authFetch, entityScope } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState('7d');
  const [product, setProduct] = useState('ALL');
  const [tab, setTab] = useState('overview');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ range });
      if (product !== 'ALL') params.set('product', product);
      const res = await authFetch(`${API}/api/monitoring/intelligence?${params}`);
      if (res.ok) setData(await res.json());
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [authFetch, range, product, entityScope]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading && !data) return <div className="text-center py-20 text-zinc-500"><Activity className="w-5 h-5 animate-spin mx-auto mb-2" />Chargement...</div>;
  if (!data) return <p className="text-zinc-500 text-center py-10">Aucune donnée</p>;

  const kpis = data.kpis || {};
  const lb = data.lb_stats || {};
  const pq = data.phone_quality || [];
  const dups = data.duplicate_by_source || [];
  const crossMatrix = data.duplicate_cross_matrix || [];
  const rejections = data.rejections_by_source || [];
  const timeBuckets = data.duplicate_time_buckets || {};
  const scores = data.source_scores || [];
  const offenders = data.duplicate_offenders_by_entity || {};
  const cann = data.cannibalization || {};
  const overlap = data.overlap_stats || {};

  const TABS = [
    { id: 'overview', label: 'Vue générale' },
    { id: 'sources', label: 'Sources Intelligence' },
    { id: 'duplicates', label: 'Doublons' },
    { id: 'cannibalization', label: 'Cannibalisation' },
  ];

  return (
    <div data-testid="monitoring-intelligence-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Zap className="w-5 h-5 text-teal-400" />Monitoring Intelligence</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Pilotage stratégique — qualité, doublons, scores</p>
        </div>
        <div className="flex items-center gap-2" data-testid="monitoring-filters">
          <Filter className="w-3.5 h-3.5 text-zinc-500" />
          {RANGES.map(r => (
            <button key={r.value} onClick={() => setRange(r.value)} data-testid={`range-${r.value}`}
              className={`px-2.5 py-1 text-[11px] rounded border transition-colors ${range === r.value ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/50 hover:border-zinc-600'}`}>
              {r.label}
            </button>
          ))}
          <span className="w-px h-4 bg-zinc-700" />
          {PRODUCTS.map(p => (
            <button key={p} onClick={() => setProduct(p)}
              className={`px-2 py-1 text-[11px] rounded border transition-colors ${product === p ? 'bg-blue-500/20 text-blue-400 border-blue-500/40' : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/50 hover:border-zinc-600'}`}>
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-2 mb-4">
        <Metric label="Total" value={kpis.total_leads?.toLocaleString()} color="zinc" />
        <Metric label="Delivered" value={kpis.delivered?.toLocaleString()} color="teal" />
        <Metric label="Valid" value={kpis.valid_total?.toLocaleString()} color="emerald" />
        <Metric label="Deliverability" value={`${kpis.real_deliverability_rate || 0}%`} color="blue" />
        <Metric label="Clean Rate" value={`${kpis.clean_rate || 0}%`} color="emerald" />
        <Metric label="Yield" value={`${kpis.economic_yield || 0}%`} color="teal" />
        <Metric label="LB Stock" value={lb.lb_stock_available || 0} sub={`${lb.lb_usage_rate || 0}% usage`} color="amber" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-zinc-800 pb-2">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} data-testid={`tab-${t.id}`}
            className={`px-3 py-1.5 text-xs rounded-t transition-colors ${tab === t.id ? 'bg-zinc-800 text-teal-400 border-b-2 border-teal-400' : 'text-zinc-500 hover:text-zinc-300'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* === TAB: OVERVIEW === */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Phone Quality by Source */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-phone-quality">
            <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2"><Shield className="w-4 h-4 text-emerald-400" />Phone Quality by Source</h2>
            <div className="space-y-2.5">
              {pq.map((s, i) => (
                <div key={i} className="border-b border-zinc-800/50 pb-2 last:border-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-zinc-300">{s.source_type}</span>
                    <div className="flex items-center gap-2"><span className="text-[10px] text-zinc-500">{s.total_leads}</span><TrendBadge value={s.trend_pct} /></div>
                  </div>
                  <QualityBar valid={s.valid_count} suspicious={s.suspicious_count} invalid={s.invalid_count} />
                  <div className="flex gap-3 mt-1">
                    <span className="text-[10px] text-emerald-400">{s.valid_rate}%</span>
                    <span className="text-[10px] text-amber-400">{s.suspicious_rate}%</span>
                    <span className="text-[10px] text-red-400">{s.invalid_rate}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* LB Replacement + Rejections */}
          <div className="space-y-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-lb-efficiency">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2"><Activity className="w-4 h-4 text-teal-400" />LB Replacement</h2>
              <div className="grid grid-cols-4 gap-2">
                <div><p className="text-[10px] text-zinc-600">Suspicious</p><p className="text-base font-bold text-amber-400">{lb.suspicious_total || 0}</p></div>
                <div><p className="text-[10px] text-zinc-600">Replaced</p><p className="text-base font-bold text-emerald-400">{lb.lb_replaced_count || 0}</p></div>
                <div><p className="text-[10px] text-zinc-600">Delivered</p><p className="text-base font-bold text-red-400">{lb.suspicious_delivered_count || 0}</p></div>
                <div><p className="text-[10px] text-zinc-600">Usage</p><p className="text-base font-bold text-teal-400">{lb.lb_usage_rate || 0}%</p></div>
              </div>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-sm font-semibold text-zinc-300 mb-2 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-red-400" />Rejections Top Sources</h2>
              <div className="space-y-1">
                {rejections.slice(0, 6).map((r, i) => {
                  const top = Object.entries(r.by_reason || {}).sort((a, b) => b[1] - a[1])[0];
                  return (
                    <div key={i} className="flex items-center justify-between text-xs py-0.5">
                      <span className="text-zinc-400 truncate max-w-[150px]">{r.source || '(direct)'}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-zinc-500">{top ? top[0] : ''}</span>
                        <span className="text-red-400 font-mono font-bold">{r.total_rejected}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* === TAB: SOURCES INTELLIGENCE === */}
      {tab === 'sources' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Top Toxic */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-toxic-sources">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2"><Skull className="w-4 h-4 text-red-400" />Top Toxic Sources</h2>
              <div className="space-y-1.5">
                {[...scores].sort((a, b) => b.toxicity_score - a.toxicity_score).filter(s => s.total >= 2).slice(0, 8).map((s, i) => (
                  <div key={i} className="flex items-center justify-between py-1 border-b border-zinc-800/30 last:border-0">
                    <span className="text-xs text-zinc-400 truncate max-w-[160px]">{s.source}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-zinc-500">{s.total}</span>
                      <ScoreBadge score={s.toxicity_score} type="toxicity" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Trusted */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-trusted-sources">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2"><Star className="w-4 h-4 text-emerald-400" />Top Trusted Sources</h2>
              <div className="space-y-1.5">
                {scores.filter(s => s.total >= 2).slice(0, 8).map((s, i) => (
                  <div key={i} className="flex items-center justify-between py-1 border-b border-zinc-800/30 last:border-0">
                    <span className="text-xs text-zinc-400 truncate max-w-[160px]">{s.source}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-zinc-500">{s.total}</span>
                      <ScoreBadge score={s.trust_score} type="trust" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Full Source Table */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-source-ranking">
            <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-blue-400" />Source Intelligence Ranking</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead><tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-1.5">Source</th>
                  <th className="text-right px-1.5">Total</th>
                  <th className="text-right px-1.5">Valid%</th>
                  <th className="text-right px-1.5">Dup%</th>
                  <th className="text-right px-1.5">Deliv%</th>
                  <th className="text-right px-1.5">Rej%</th>
                  <th className="text-center px-1.5">Trust</th>
                  <th className="text-center px-1.5">Toxic</th>
                </tr></thead>
                <tbody>
                  {scores.map((s, i) => (
                    <tr key={i} className="border-b border-zinc-800/30 hover:bg-zinc-800/30">
                      <td className="py-1 text-zinc-300 font-medium">{s.source}</td>
                      <td className="text-right px-1.5 text-zinc-400">{s.total}</td>
                      <td className="text-right px-1.5 text-emerald-400">{s.valid_rate}%</td>
                      <td className={`text-right px-1.5 ${s.duplicate_rate > 10 ? 'text-red-400' : 'text-zinc-400'}`}>{s.duplicate_rate}%</td>
                      <td className="text-right px-1.5 text-blue-400">{s.deliverability_rate}%</td>
                      <td className={`text-right px-1.5 ${s.rejection_rate > 50 ? 'text-red-400' : 'text-zinc-400'}`}>{s.rejection_rate}%</td>
                      <td className="text-center px-1.5"><ScoreBadge score={s.trust_score} type="trust" /></td>
                      <td className="text-center px-1.5"><ScoreBadge score={s.toxicity_score} type="toxicity" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* === TAB: DUPLICATES === */}
      {tab === 'duplicates' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Duplicate Rate by Source */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-duplicate-rate">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2"><GitCompare className="w-4 h-4 text-amber-400" />Rate par Source</h2>
              <div className="space-y-1">
                {dups.filter(d => d.total_leads > 0).slice(0, 12).map((d, i) => (
                  <div key={i} className="flex items-center justify-between py-0.5">
                    <span className="text-xs text-zinc-400 truncate max-w-[160px]">{d.source || '(direct)'}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-zinc-500">{d.total_leads}</span>
                      <span className={`text-xs font-mono font-bold ${d.duplicate_rate > 10 ? 'text-red-400' : d.duplicate_rate > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>{d.duplicate_rate}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Time Buckets */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-time-buckets">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3">Duplicate Delay Distribution</h2>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: '< 1h', key: 'lt_1h', color: 'text-red-400 bg-red-500/10' },
                  { label: '1-24h', key: '1h_24h', color: 'text-amber-400 bg-amber-500/10' },
                  { label: '1-7j', key: '1d_7d', color: 'text-blue-400 bg-blue-500/10' },
                  { label: '> 7j', key: 'gt_7d', color: 'text-emerald-400 bg-emerald-500/10' },
                ].map(b => (
                  <div key={b.key} className={`text-center p-3 rounded-lg ${b.color}`}>
                    <p className="text-lg font-bold">{timeBuckets[b.key] || 0}</p>
                    <p className="text-[10px] mt-0.5">{b.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Offenders by Entity */}
          {Object.keys(offenders).length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-offenders-entity">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3">Offenders par Entity</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(offenders).map(([ent, d]) => (
                  <div key={ent} className="border border-zinc-800 rounded-lg p-3">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${ent === 'ZR7' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-blue-500/15 text-blue-400'}`}>{ent}</span>
                    <div className="grid grid-cols-3 gap-2 mt-2 text-center">
                      <div><p className="text-[10px] text-zinc-500">Total</p><p className="text-sm font-bold text-zinc-300">{d.total_leads}</p></div>
                      <div><p className="text-[10px] text-zinc-500">Dups</p><p className="text-sm font-bold text-amber-400">{d.duplicate_count}</p></div>
                      <div><p className="text-[10px] text-zinc-500">Rate</p><p className="text-sm font-bold text-red-400">{d.duplicate_rate}%</p></div>
                    </div>
                    <div className="flex gap-2 mt-2 text-[10px]">
                      <span className="text-zinc-500">vs LP: <span className="text-amber-400">{d.against_internal_lp}</span></span>
                      <span className="text-zinc-500">vs Prov: <span className="text-amber-400">{d.against_provider}</span></span>
                      <span className="text-zinc-500">Cross-ent: <span className="text-red-400">{d.against_other_entity}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cross Matrix */}
          {crossMatrix.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-cross-matrix">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-red-400" />Cross-Source Conflicts</h2>
              <table className="w-full text-[11px]">
                <thead><tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-1">Source A</th><th className="text-left">Entity A</th>
                  <th className="text-left">Source B</th><th className="text-left">Entity B</th>
                  <th className="text-right">Conflits</th>
                </tr></thead>
                <tbody>
                  {crossMatrix.slice(0, 15).map((m, i) => (
                    <tr key={i} className="border-b border-zinc-800/30">
                      <td className="py-1 text-zinc-300">{m.source_a}</td>
                      <td className={m.entity_a === 'ZR7' ? 'text-emerald-400' : 'text-blue-400'}>{m.entity_a}</td>
                      <td className="text-zinc-300">{m.source_b}</td>
                      <td className={m.entity_b === 'ZR7' ? 'text-emerald-400' : 'text-blue-400'}>{m.entity_b}</td>
                      <td className="text-right text-red-400 font-bold">{m.conflict_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* === TAB: CANNIBALIZATION === */}
      {tab === 'cannibalization' && (
        <div className="space-y-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-cannibalization">
            <h2 className="text-sm font-semibold text-zinc-300 mb-4 flex items-center gap-2"><ArrowRightLeft className="w-4 h-4 text-red-400" />Internal Cannibalization Index</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="text-center">
                <p className="text-[10px] uppercase text-zinc-500">Cross-Entity Dups</p>
                <p className="text-2xl font-bold text-red-400">{cann.cross_entity_duplicate_count || 0}</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] uppercase text-zinc-500">Unique Phones</p>
                <p className="text-2xl font-bold text-zinc-300">{cann.total_unique_phones || 0}</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] uppercase text-zinc-500">Cann. Rate</p>
                <p className="text-2xl font-bold text-amber-400">{cann.cross_entity_duplicate_rate || 0}%</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] uppercase text-zinc-500">Cann. Index</p>
                <p className={`text-2xl font-bold ${(cann.cannibalization_index || 0) > 5 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {cann.cannibalization_index || 0}
                </p>
              </div>
            </div>
            {cann.first_source_distribution && (
              <div>
                <p className="text-[10px] uppercase text-zinc-500 mb-2">First Source Distribution (qui soumet en premier)</p>
                <div className="flex gap-4">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded bg-emerald-500" />
                    <span className="text-xs text-zinc-400">ZR7: <span className="text-emerald-400 font-bold">{cann.first_source_distribution?.ZR7 || 0}</span></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded bg-blue-500" />
                    <span className="text-xs text-zinc-400">MDL: <span className="text-blue-400 font-bold">{cann.first_source_distribution?.MDL || 0}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Client Overlap Stats */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="widget-overlap-stats">
            <h2 className="text-sm font-semibold text-zinc-300 mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-amber-400" />Client Overlap Protection
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-[10px] uppercase text-zinc-500">Shared Clients</p>
                <p className="text-2xl font-bold text-amber-400">{overlap.shared_clients_count || 0}</p>
                <p className="text-[10px] text-zinc-500">{overlap.shared_clients_rate || 0}% du total</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] uppercase text-zinc-500">Overlap Deliveries</p>
                <p className="text-2xl font-bold text-red-400">{overlap.shared_client_deliveries_30d_count || 0}</p>
                <p className="text-[10px] text-zinc-500">{overlap.shared_client_deliveries_30d_rate || 0}% des livraisons</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] uppercase text-zinc-500">Fallback (forced)</p>
                <p className="text-2xl font-bold text-zinc-300">{overlap.overlap_fallback_deliveries_30d_count || 0}</p>
                <p className="text-[10px] text-zinc-500">{overlap.overlap_fallback_deliveries_30d_rate || 0}% fallback</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {data._errors && data._errors.length > 0 && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-xs text-red-400">Erreurs partielles: {data._errors.join(', ')}</p>
        </div>
      )}
    </div>
  );
}
