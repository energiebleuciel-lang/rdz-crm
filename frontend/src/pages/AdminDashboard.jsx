import { useState, useEffect } from 'react';
import { useApi, API } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { Truck, Users, ShoppingCart, AlertTriangle, Clock, CheckCircle, XCircle, Package, ArrowUpRight } from 'lucide-react';

const ENTITY_COLORS = { ZR7: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', MDL: 'bg-blue-500/10 text-blue-400 border-blue-500/20' };

function StatCard({ label, value, icon: Icon, color = 'text-zinc-400', sub }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-zinc-500 uppercase tracking-wider">{label}</span>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <p className="text-2xl font-semibold text-white">{value ?? '-'}</p>
      {sub && <p className="text-xs text-zinc-600 mt-1">{sub}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const { authFetch } = useAuth();
  const [stats, setStats] = useState(null);
  const [leadStats, setLeadStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const [dRes, lRes] = await Promise.all([
        authFetch(`${API}/api/deliveries/stats`),
        authFetch(`${API}/api/leads/stats`).catch(() => null)
      ]);
      if (dRes.ok) setStats(await dRes.json());
      if (lRes?.ok) setLeadStats(await lRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div data-testid="admin-dashboard">
      <h1 className="text-lg font-semibold text-white mb-6">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Pending CSV" value={stats?.pending_csv} icon={Clock} color="text-amber-400" />
        <StatCard label="Ready to Send" value={stats?.ready_to_send} icon={Package} color="text-cyan-400" />
        <StatCard label="Sent" value={stats?.sent} icon={CheckCircle} color="text-emerald-400" />
        <StatCard label="Failed" value={stats?.failed} icon={XCircle} color="text-red-400" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Total Deliveries" value={stats?.total} icon={Truck} color="text-zinc-400" />
        <StatCard label="Billable" value={stats?.billable} icon={ArrowUpRight} color="text-emerald-400" />
        <StatCard label="Rejected" value={stats?.rejected} icon={AlertTriangle} color="text-orange-400" />
        <StatCard label="Sending" value={stats?.sending} icon={Truck} color="text-blue-400" />
      </div>

      {/* Entity breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {['ZR7', 'MDL'].map(entity => (
          <EntityCard key={entity} entity={entity} />
        ))}
      </div>
    </div>
  );
}

function EntityCard({ entity }) {
  const { authFetch } = useAuth();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    authFetch(`${API}/api/deliveries/stats?entity=${entity}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setStats(d));
  }, [entity]);

  const c = ENTITY_COLORS[entity];
  return (
    <div className={`bg-zinc-900 border rounded-lg p-4 ${c.split(' ').find(s => s.startsWith('border-'))}`} data-testid={`entity-card-${entity.toLowerCase()}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-xs font-bold px-2 py-0.5 rounded border ${c}`}>{entity}</span>
      </div>
      {stats ? (
        <div className="grid grid-cols-3 gap-3 text-center">
          <div><p className="text-lg font-semibold text-white">{stats.sent}</p><p className="text-[10px] text-zinc-500">Sent</p></div>
          <div><p className="text-lg font-semibold text-white">{stats.ready_to_send}</p><p className="text-[10px] text-zinc-500">Ready</p></div>
          <div><p className="text-lg font-semibold text-white">{stats.failed}</p><p className="text-[10px] text-zinc-500">Failed</p></div>
          <div><p className="text-lg font-semibold text-white">{stats.billable}</p><p className="text-[10px] text-zinc-500">Billable</p></div>
          <div><p className="text-lg font-semibold text-white">{stats.rejected}</p><p className="text-[10px] text-zinc-500">Rejected</p></div>
          <div><p className="text-lg font-semibold text-white">{stats.pending_csv}</p><p className="text-[10px] text-zinc-500">Pending</p></div>
        </div>
      ) : <p className="text-xs text-zinc-600">Chargement...</p>}
    </div>
  );
}
