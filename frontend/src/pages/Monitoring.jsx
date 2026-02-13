/**
 * Monitoring - Taux de succès par CRM / produit / compte + alertes
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Loading, Badge } from '../components/UI';
import {
  Activity, AlertTriangle, CheckCircle, XCircle, RefreshCw,
  ChevronDown, ChevronUp, Shield, RotateCcw
} from 'lucide-react';

const AlertsPanel = ({ criticals, warnings, threshold }) => {
  const [expanded, setExpanded] = useState(false);
  const all = [...criticals, ...warnings];
  const shown = expanded ? all : all.slice(0, 4);
  return (
    <Card className="p-0 overflow-hidden" data-testid="alerts-section">
      <div className="px-4 py-3 bg-red-50 border-b border-red-100 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-red-500" />
        <span className="text-sm font-semibold text-red-700">
          Alertes actives ({all.length})
        </span>
        <span className="text-xs text-red-400 ml-auto">seuil: {threshold}%</span>
      </div>
      <div className="divide-y">
        {shown.map((a, i) => (
          <div key={i} className={`px-4 py-2.5 flex items-start gap-3 ${a.level === 'critical' ? 'bg-red-50/30' : 'bg-amber-50/30'}`}>
            <span className={`mt-0.5 px-2 py-0.5 text-xs rounded font-bold shrink-0 ${
              a.level === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
            }`}>
              {a.level === 'critical' ? 'CRITIQUE' : 'ATTENTION'}
            </span>
            <div className="min-w-0">
              <p className="text-sm text-slate-700">
                {a.message.replace(a.top_failure_reason, getFailureInfo(a.top_failure_reason).label)}
              </p>
            </div>
          </div>
        ))}
      </div>
      {all.length > 4 && (
        <button onClick={() => setExpanded(!expanded)}
          className="w-full px-4 py-2 text-xs text-slate-500 hover:text-slate-700 hover:bg-slate-50 border-t">
          {expanded ? 'Réduire' : `Voir toutes les alertes (${all.length - 4} de plus)`}
        </button>
      )}
    </Card>
  );
};

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

// Dictionnaire des causes d'échec : label FR + règle métier
const FAILURE_DICT = {
  success:           { label: 'Succès',              rule: 'Lead envoyé et accepté par le CRM (HTTP 201).' },
  duplicate:         { label: 'Doublon CRM',         rule: 'Le CRM a détecté que ce lead existe déjà dans sa base.' },
  failed:            { label: 'Erreur envoi',        rule: 'Le CRM a rejeté le lead (erreur HTTP 4xx hors auth/validation, ou erreur inconnue).' },
  doublon_recent:    { label: 'Doublon interne',     rule: 'Phone + dept identiques dans les 30 derniers jours, lead original déjà livré. Non renvoyé au CRM.' },
  double_submit:     { label: 'Double-clic',         rule: 'Même session + même phone en moins de 5 secondes. Anti double-soumission.' },
  non_livre:         { label: 'Doublon non livré',   rule: 'Phone + dept identiques dans les 30 jours, mais le lead original n\'a jamais été livré. Conservé pour redistribution.' },
  orphan:            { label: 'Orphelin',            rule: 'Le code formulaire envoyé n\'existe pas en base. Aucun routing possible.' },
  no_crm:            { label: 'CRM non configuré',   rule: 'Ni le compte ni le formulaire n\'ont de CRM cible configuré pour ce type de produit.' },
  no_api_key:        { label: 'Clé API manquante',   rule: 'Le CRM cible est défini mais aucune clé API n\'est renseignée.' },
  invalid_phone:     { label: 'Téléphone invalide',  rule: 'Le numéro ne respecte pas le format FR : 10 chiffres, commence par 0, pas de suite/répétition.' },
  missing_required:  { label: 'Champs manquants',    rule: 'Le nom ou le département sont vides. Lead conservé mais non envoyé.' },
  validation_error:  { label: 'Erreur validation',   rule: 'Le CRM a rejeté le payload (champ invalide, format incorrect). HTTP 400.' },
  auth_error:        { label: 'Erreur auth CRM',     rule: 'La clé API est refusée par le CRM. HTTP 403. Vérifier la clé dans les settings du compte.' },
  server_error:      { label: 'Erreur serveur CRM',  rule: 'Le CRM est en panne (HTTP 5xx). Le lead est mis en file d\'attente pour retry automatique.' },
  timeout:           { label: 'Timeout CRM',         rule: 'Le CRM n\'a pas répondu dans les 30 secondes. Retry automatique programmé.' },
  connection_error:  { label: 'Connexion impossible', rule: 'Impossible de contacter le serveur CRM. Vérifier l\'URL ou la disponibilité du service.' },
  queued:            { label: 'En file d\'attente',  rule: 'Le lead a été mis en queue pour retry après une erreur temporaire (timeout, erreur serveur).' },
  pending:           { label: 'En attente',          rule: 'Lead créé, en cours de traitement.' },
  pending_no_order:  { label: 'Pas de commande',     rule: 'Aucune commande active pour ce CRM + produit + département. Lead en attente de redistribution.' },
  pending_retry:     { label: 'Retry en cours',      rule: 'Le lead est en cours de retry après un échec précédent.' },
};

const getFailureInfo = (key) => FAILURE_DICT[key] || { label: key, rule: 'Statut inconnu.' };

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
    auth_error: 'bg-red-100 text-red-700',
    server_error: 'bg-orange-100 text-orange-700',
    timeout: 'bg-orange-100 text-orange-600',
    connection_error: 'bg-red-100 text-red-600',
    pending_retry: 'bg-blue-100 text-blue-600',
  };
  return (
    <div className="flex flex-wrap gap-1.5 mt-1.5">
      {sorted.map(([reason, count]) => {
        const info = getFailureInfo(reason);
        return (
          <span
            key={reason}
            title={info.rule}
            className={`px-2 py-0.5 text-xs rounded-full font-medium cursor-help ${colors[reason] || 'bg-slate-100 text-slate-600'}`}
          >
            {info.label}: {count}
          </span>
        );
      })}
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

const FailureLegend = () => {
  const [open, setOpen] = useState(false);
  const categories = [
    { title: 'Envoi CRM', keys: ['success', 'duplicate', 'failed', 'validation_error', 'auth_error', 'server_error', 'timeout', 'connection_error', 'queued'] },
    { title: 'Doublons internes RDZ', keys: ['doublon_recent', 'double_submit', 'non_livre'] },
    { title: 'Données invalides', keys: ['invalid_phone', 'missing_required', 'orphan'] },
    { title: 'Configuration', keys: ['no_crm', 'no_api_key', 'pending_no_order'] },
  ];
  return (
    <div className="border rounded-lg overflow-hidden" data-testid="failure-legend">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors">
        <span className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <AlertTriangle className="w-4 h-4" /> Dictionnaire des statuts
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>
      {open && (
        <div className="divide-y">
          {categories.map(cat => (
            <div key={cat.title} className="px-4 py-3">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">{cat.title}</h4>
              <div className="space-y-2">
                {cat.keys.map(key => {
                  const info = getFailureInfo(key);
                  return (
                    <div key={key} className="flex items-start gap-3">
                      <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded font-mono text-slate-600 shrink-0 w-32 text-center">{key}</code>
                      <div>
                        <span className="text-sm font-medium text-slate-800">{info.label}</span>
                        <p className="text-xs text-slate-500 mt-0.5">{info.rule}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
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
  const [retrying, setRetrying] = useState(false);
  const [retryResult, setRetryResult] = useState(null);

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

  const retryFailed = async () => {
    if (!confirm('Relancer tous les leads en échec des dernières 24h ?')) return;
    try {
      setRetrying(true);
      setRetryResult(null);
      const res = await authFetch(`${API}/api/monitoring/retry`, {
        method: 'POST',
        body: JSON.stringify({ hours: 24 })
      });
      if (res.ok) {
        const d = await res.json();
        setRetryResult(d.results);
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    } finally {
      setRetrying(false);
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

      {/* Alerts - max 4 visible, expandable */}
      {(criticals.length > 0 || warnings.length > 0) && (
        <AlertsPanel criticals={criticals} warnings={warnings} threshold={data.config.alert_threshold} />
      )}

      {/* Stats tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <StatsTable data={windowData.by_crm} title="Par CRM" icon={Shield} />
        <StatsTable data={windowData.by_product} title="Par Produit" icon={Activity} />
      </div>

      <StatsTable data={windowData.by_account} title="Par Compte" icon={CheckCircle} />

      <StatsTable data={windowData.by_crm_product} title="Par CRM x Produit" icon={Activity} showFailures={true} />

      {/* Légende des statuts */}
      <FailureLegend />

      <p className="text-xs text-slate-400 text-right">
        Dernière mise à jour : {new Date(data.generated_at).toLocaleString('fr-FR')}
      </p>
    </div>
  );
}
