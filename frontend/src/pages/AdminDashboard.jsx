import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import {
  Truck, CheckCircle, XCircle, Clock, Package, ArrowUpRight, AlertTriangle,
  CalendarCheck, CalendarX, Users, ShoppingCart, Archive
} from 'lucide-react';
import { getCurrentWeekKey, shiftWeekKey } from '../lib/weekUtils';
import { WeekNavStandard } from '../components/WeekNav';

function Stat({ label, value, icon: Icon, color = 'text-zinc-400' }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-3" data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-zinc-500 uppercase tracking-wider">{label}</span>
        <Icon className={`w-3.5 h-3.5 ${color}`} />
      </div>
      <p className="text-xl font-semibold text-white">{value ?? '-'}</p>
    </div>
  );
}

export default function AdminDashboard() {
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [week, setWeek] = useState(getCurrentWeekKey());

  useEffect(() => {
    setLoading(true);
    (async () => {
      try {
        const res = await authFetch(`${API}/api/leads/dashboard-stats?week=${week}`);
        if (res.ok) setData(await res.json());
      } catch (e) { console.error(e); }
      setLoading(false);
    })();
  }, [week]);

  const handleWeekNav = (dir) => setWeek(w => shiftWeekKey(w, dir));

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!data) return <p className="text-zinc-500 text-center py-8">Erreur chargement</p>;

  const ds = data.delivery_stats || {};
  const ls = data.lead_stats || {};
  const cal = data.calendar || {};

  return (
    <div data-testid="admin-dashboard" className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-white">Cockpit</h1>
        <WeekNavStandard week={week} onChange={handleWeekNav} />
      </div>

      {/* Calendar status banner */}
      <div className="flex gap-3">
        {['ZR7', 'MDL'].map(entity => {
          const c = cal[entity] || {};
          const on = c.is_delivery_day;
          return (
            <div key={entity} className={`flex-1 flex items-center gap-3 px-4 py-2.5 rounded-lg border ${on ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'}`} data-testid={`calendar-banner-${entity.toLowerCase()}`}>
              {on ? <CalendarCheck className="w-4 h-4 text-emerald-400" /> : <CalendarX className="w-4 h-4 text-red-400" />}
              <span className={`text-xs font-bold ${entity === 'ZR7' ? 'text-emerald-400' : 'text-blue-400'}`}>{entity}</span>
              <span className={`text-xs ${on ? 'text-emerald-300' : 'text-red-300'}`}>{on ? 'Livraisons actives' : c.reason || 'Jour OFF'}</span>
            </div>
          );
        })}
      </div>

      {/* Delivery stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
        <Stat label="Pending CSV" value={ds.pending_csv || 0} icon={Clock} color="text-amber-400" />
        <Stat label="Ready" value={ds.ready_to_send || 0} icon={Package} color="text-cyan-400" />
        <Stat label="Sent" value={ds.sent || 0} icon={CheckCircle} color="text-emerald-400" />
        <Stat label="Failed" value={ds.failed || 0} icon={XCircle} color="text-red-400" />
        <Stat label="Billable" value={ds.billable || 0} icon={ArrowUpRight} color="text-emerald-400" />
        <Stat label="Rejected" value={ds.rejected || 0} icon={AlertTriangle} color="text-orange-400" />
      </div>

      {/* Blocked stock + Lead stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5">
        <Stat label="No Open Orders" value={ls.no_open_orders || 0} icon={Archive} color="text-amber-500" />
        <Stat label="Hold Source" value={ls.hold_source || 0} icon={Archive} color="text-orange-500" />
        <Stat label="Pending Config" value={ls.pending_config || 0} icon={Archive} color="text-violet-400" />
        <Stat label="Routed" value={ls.routed || 0} icon={Truck} color="text-cyan-400" />
        <Stat label="Livre" value={ls.livre || 0} icon={CheckCircle} color="text-emerald-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top Clients 7d */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="top-clients-section">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Users className="w-3.5 h-3.5" /> Top Clients (sem.)</h2>
          {(data.top_clients_7d || []).length === 0 ? <p className="text-[10px] text-zinc-600">Aucun</p> : (
            <div className="space-y-2">
              {data.top_clients_7d.map((tc, i) => (
                <div key={i} className="flex items-center justify-between text-xs cursor-pointer hover:bg-zinc-800/50 rounded px-2 py-1.5 -mx-2 transition-colors"
                  onClick={() => navigate(`/admin/deliveries?client_id=${tc.client_id}`)}>
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${tc.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{tc.entity}</span>
                    <span className="text-zinc-300 truncate">{tc.client_name}</span>
                  </div>
                  <div className="flex gap-3 text-[10px] shrink-0">
                    <span className="text-emerald-400">{tc.billable_7d}b</span>
                    {tc.rejected_7d > 0 && <span className="text-orange-400">{tc.rejected_7d}r</span>}
                    {tc.failed_7d > 0 && <span className="text-red-400">{tc.failed_7d}f</span>}
                    {tc.ready_7d > 0 && <span className="text-cyan-400">{tc.ready_7d}w</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Clients a probleme */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="problem-clients-section">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2"><AlertTriangle className="w-3.5 h-3.5 text-red-400" /> Clients non livrables</h2>
          {(data.problem_clients || []).length === 0 ? <p className="text-[10px] text-emerald-400">Tous livrables</p> : (
            <div className="space-y-2">
              {data.problem_clients.map((pc, i) => (
                <div key={i} className="text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${pc.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{pc.entity}</span>
                    <span className="text-zinc-300">{pc.name}</span>
                  </div>
                  <p className="text-[10px] text-red-400/70 ml-6 mt-0.5">{pc.reason}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Commandes proches fin */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="low-quota-section">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2"><ShoppingCart className="w-3.5 h-3.5 text-amber-400" /> Quotas faibles</h2>
          {(data.low_quota_commandes || []).length === 0 ? <p className="text-[10px] text-emerald-400">Tous OK</p> : (
            <div className="space-y-2">
              {data.low_quota_commandes.map((lq, i) => (
                <div key={i} className="text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${lq.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{lq.entity}</span>
                    <span className="text-zinc-300">{lq.client_name}</span>
                    <span className="text-zinc-600">{lq.produit}</span>
                  </div>
                  <span className="text-amber-400 font-mono">{lq.remaining}/{lq.quota}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Blocked stock breakdown */}
      {(data.blocked_stock || []).length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="blocked-stock-section">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Archive className="w-3.5 h-3.5 text-violet-400" /> Stock bloque (par entity/produit)</h2>
          <div className="flex flex-wrap gap-2">
            {data.blocked_stock.map((b, i) => (
              <div key={i} className="bg-zinc-800 rounded-md px-2.5 py-1.5 text-[10px] flex items-center gap-1.5">
                <span className={`font-bold ${b.entity === 'ZR7' ? 'text-emerald-400' : 'text-blue-400'}`}>{b.entity}</span>
                <span className="text-zinc-500">{b.produit || '?'}</span>
                <span className={`font-medium ${b.status === 'no_open_orders' ? 'text-amber-400' : b.status === 'hold_source' ? 'text-orange-400' : 'text-violet-400'}`}>{b.status}</span>
                <span className="text-white font-semibold">{b.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
