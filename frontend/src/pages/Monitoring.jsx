/**
 * Monitoring - Taux de succès par CRM / produit / compte + alertes
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Loading, Badge } from '../components/UI';
import {
  Activity, AlertTriangle, CheckCircle, XCircle, RefreshCw,
  ChevronDown, ChevronUp, Shield
} from 'lucide-react';

const RateBar = ({ rate, total, success, failed }) => {
  const color = rate >= 90 ? 'bg-green-500' : rate >= 70 ? 'bg-amber-500' : 'bg-red-500';
  const textColor = rate >= 90 ? 'text-green-700' : rate >= 70 ? 'text-amber-700' : 'text-red-700';
  return (
    <div className="flex items-center gap-3 min-w-0">
      <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.max(rate, 1)}%` }} />
      </div>
      <span className={`text-sm font-bold ${textColor} w-14 text-right shrink-0`}>{rate}%</span>
      <span className="text-xs text-slate-400 w-20 text-right shrink-0">{success}/{total}</span>
    </div>
  );
};

const FailureBreakdown = ({ failures }) => {
  if (!failures || Object.keys(failures).length === 0) return null;
  const sorted = Object.entries(failures).sort((a, b) => b[1] - a[1]);
  const colors = {
    failed: 'bg-red-100 text-red-700',
    doublon_recent: 'bg-orange-100 text-orange-700',
    double_submit: 'bg-yellow-100 text-yellow-700',
    orphan: 'bg-slate-100 text-slate-600',
    no_crm: 'bg-slate-100 text-slate-600',
    no_api_key: 'bg-amber-100 text-amber-700',
    invalid_phone: 'bg-pink-100 text-pink-700',
    missing_required: 'bg-purple-100 text-purple-700',
    validation_error: 'bg-red-100 text-red-600',
    non_livre: 'bg-blue-100 text-blue-700',
  };
  return (
    <div className="flex flex-wrap gap-1.5 mt-1.5">
      {sorted.map(([reason, count]) => (
        <span key={reason} className={`px-2 py-0.5 text-xs rounded-full font-medium ${colors[reason] || 'bg-slate-100 text-slate-600'}`}>
          {reason}: {count}
        </span>
      ))}
    </div>
  );
};

const StatsTable = ({ data, title, icon: Icon, showFailures = true }) => {
  const [expanded, setExpanded] = useState(true);
  if (!data || data.length === 0) return null;

  // Filter out test accounts and noise
  const filtered = data.filter(s => s.total > 0 && !s.label.startsWith('Test Account'));

  return (
    <div className="border rounded-lg overflow-hidden" data-testid={`monitoring-table-${title.toLowerCase().replace(/\s/g,'-')}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <Icon className="w-4 h-4" /> {title}
          <Badge variant="default">{filtered.length}</Badge>
        </span>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>
      {expanded && (
        <div className="divide-y">
          {filtered.map((s, i) => (
            <div key={i} className="px-4 py-3 hover:bg-slate-50/50">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-slate-800 text-sm">{s.label}</span>
                {s.failed > 0 && (
                  <span className="text-xs text-red-500 font-medium">{s.failed} fail{s.failed > 1 ? 's' : ''}</span>
                )}
              </div>
              <RateBar rate={s.success_rate} total={s.total} success={s.success} failed={s.failed} />
              {showFailures && <FailureBreakdown failures={s.failures} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default function Monitoring() {
  const { authFetch } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [window, setWindow] = useState('24h');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await authFetch(`${API}/api/monitoring/stats`);
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error('Monitoring load error:', e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;
  if (!data) return <div className="p-8 text-center text-slate-500">Erreur de chargement</div>;

  const windowData = window === '24h' ? data.window_24h : data.window_7d;
  const alerts = data.alerts || [];
  const filteredAlerts = alerts.filter(a =>
    !a.label.startsWith('Test Account') && a.label !== '?' && a.value !== 'none'
    && (a.total === null || a.total >= 3)
  );
  const criticals = filteredAlerts.filter(a => a.level === 'critical');
  const warnings = filteredAlerts.filter(a => a.level === 'warning');

  // Global totals from by_crm
  const totals = (windowData.by_crm || []).reduce((acc, s) => {
    acc.total += s.total;
    acc.success += s.success;
    return acc;
  }, { total: 0, success: 0 });
  const globalRate = totals.total > 0 ? Math.round(totals.success / totals.total * 100 * 10) / 10 : 0;

  return (
    <div className="space-y-6" data-testid="monitoring-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Activity className="w-6 h-6" /> Monitoring
          </h1>
          <p className="text-sm text-slate-500">Taux de succès et alertes en temps réel</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Window toggle */}
          <div className="flex bg-slate-100 rounded-lg p-0.5" data-testid="window-toggle">
            {['24h', '7j'].map(w => (
              <button
                key={w}
                onClick={() => setWindow(w)}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  window === w ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {w}
              </button>
            ))}
          </div>
          <button
            onClick={loadData}
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg"
            data-testid="refresh-btn"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg ${globalRate >= 80 ? 'bg-green-100' : globalRate >= 50 ? 'bg-amber-100' : 'bg-red-100'}`}>
              <Activity className={`w-5 h-5 ${globalRate >= 80 ? 'text-green-600' : globalRate >= 50 ? 'text-amber-600' : 'text-red-600'}`} />
            </div>
            <div>
              <p className="text-xs text-slate-500">Taux global</p>
              <p className="text-2xl font-bold text-slate-800">{globalRate}%</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-100">
              <CheckCircle className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-slate-500">Envoyés</p>
              <p className="text-2xl font-bold text-slate-800">{totals.success}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-red-100">
              <XCircle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-xs text-slate-500">Fails</p>
              <p className="text-2xl font-bold text-slate-800">{totals.total - totals.success}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg ${criticals.length > 0 ? 'bg-red-100' : warnings.length > 0 ? 'bg-amber-100' : 'bg-green-100'}`}>
              <AlertTriangle className={`w-5 h-5 ${criticals.length > 0 ? 'text-red-600' : warnings.length > 0 ? 'text-amber-600' : 'text-green-600'}`} />
            </div>
            <div>
              <p className="text-xs text-slate-500">Alertes</p>
              <p className="text-2xl font-bold text-slate-800">{criticals.length + warnings.length}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Alerts */}
      {(criticals.length > 0 || warnings.length > 0) && (
        <Card className="p-0 overflow-hidden" data-testid="alerts-section">
          <div className="px-4 py-3 bg-red-50 border-b border-red-100 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <span className="text-sm font-semibold text-red-700">
              Alertes actives ({criticals.length + warnings.length})
            </span>
            <span className="text-xs text-red-400 ml-auto">seuil: {data.config.alert_threshold}%</span>
          </div>
          <div className="divide-y">
            {[...criticals, ...warnings].map((a, i) => (
              <div key={i} className={`px-4 py-3 flex items-start gap-3 ${a.level === 'critical' ? 'bg-red-50/30' : 'bg-amber-50/30'}`}>
                <span className={`mt-0.5 px-2 py-0.5 text-xs rounded font-bold shrink-0 ${
                  a.level === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                }`}>
                  {a.level === 'critical' ? 'CRITIQUE' : 'ATTENTION'}
                </span>
                <div className="min-w-0">
                  <p className="text-sm text-slate-700">{a.message}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{a.dimension}: {a.value}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Stats tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <StatsTable data={windowData.by_crm} title="Par CRM" icon={Shield} />
        <StatsTable data={windowData.by_product} title="Par Produit" icon={Activity} />
      </div>

      <StatsTable data={windowData.by_account} title="Par Compte" icon={CheckCircle} />

      <StatsTable data={windowData.by_crm_product} title="Par CRM x Produit" icon={Activity} showFailures={true} />

      <p className="text-xs text-slate-400 text-right">
        Dernière mise à jour : {new Date(data.generated_at).toLocaleString('fr-FR')}
      </p>
    </div>
  );
}
