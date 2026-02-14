import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Filter, X, ExternalLink } from 'lucide-react';
import { getCurrentWeekKey, shiftWeekKey } from '../lib/weekUtils';
import { WeekNavStandard } from '../components/WeekNav';

const ACTION_LABELS = {
  reject_lead: 'Rejet lead',
  lead_removed_from_delivery: 'Retrait lead',
  send_delivery: 'Envoi delivery',
  resend_delivery: 'Renvoi delivery',
  delivery_failed: 'Echec envoi',
  order_activate: 'Commande activée',
  order_deactivate: 'Commande désactivée',
  client_auto_send_change: 'Auto-send modifié',
  rotate_provider_key: 'Rotation clé provider',
  crm_update: 'MAJ CRM',
  note_added: 'Note ajoutée',
  delivery_rejected: 'Delivery rejetée',
};
const ACTION_COLORS = {
  reject_lead: 'text-orange-400',
  lead_removed_from_delivery: 'text-red-400',
  send_delivery: 'text-emerald-400',
  resend_delivery: 'text-amber-400',
  delivery_failed: 'text-red-500',
  order_activate: 'text-emerald-400',
  order_deactivate: 'text-zinc-500',
  client_auto_send_change: 'text-cyan-400',
  rotate_provider_key: 'text-violet-400',
  crm_update: 'text-cyan-400',
  note_added: 'text-zinc-300',
  delivery_rejected: 'text-orange-400',
};
const ENTITY_TYPE_COLORS = {
  delivery: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  lead: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  client: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  commande: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  provider: 'bg-violet-500/10 text-violet-400 border-violet-500/30',
};

export default function AdminActivity() {
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [week, setWeek] = useState(getCurrentWeekKey());
  const [filters, setFilters] = useState({ action: '', entity_type: '', entity: '' });
  const [showFilters, setShowFilters] = useState(false);
  const limit = 50;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', limit);
      params.set('skip', page * limit);
      if (filters.action) params.set('action', filters.action);
      if (filters.entity_type) params.set('entity_type', filters.entity_type);
      if (filters.entity) params.set('entity', filters.entity);

      const [eRes, aRes] = await Promise.all([
        authFetch(`${API}/api/event-log?${params}`),
        authFetch(`${API}/api/event-log/actions`)
      ]);
      if (eRes.ok) { const d = await eRes.json(); setEvents(d.events || []); setTotal(d.total || 0); }
      if (aRes.ok) { const d = await aRes.json(); setActions(d.actions || []); }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [page, filters, authFetch]);

  useEffect(() => { load(); }, [load]);

  const getLink = (event) => {
    const et = event.entity_type;
    const eid = event.entity_id;
    const rel = event.related || {};
    if (et === 'delivery') return { label: 'Delivery', path: `/admin/deliveries/${eid}` };
    if (et === 'lead') return { label: 'Lead', path: `/admin/leads/${eid}` };
    if (et === 'client') return { label: 'Client', path: `/admin/clients/${eid}` };
    if (rel.lead_id) return { label: 'Lead', path: `/admin/leads/${rel.lead_id}` };
    if (rel.client_id) return { label: 'Client', path: `/admin/clients/${rel.client_id}` };
    return null;
  };

  return (
    <div data-testid="admin-activity">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white">Activity Log</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowFilters(!showFilters)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="filter-toggle-btn">
            <Filter className="w-3 h-3" /> Filtres
          </button>
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="refresh-btn">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {showFilters && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 mb-4 flex gap-3 items-end flex-wrap" data-testid="filters-panel">
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Action</label>
            <select value={filters.action} onChange={e => { setFilters(f => ({ ...f, action: e.target.value })); setPage(0); }}
              className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-action">
              <option value="">Toutes</option>
              {actions.map(a => <option key={a} value={a}>{ACTION_LABELS[a] || a}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Type</label>
            <select value={filters.entity_type} onChange={e => { setFilters(f => ({ ...f, entity_type: e.target.value })); setPage(0); }}
              className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-entity-type">
              <option value="">Tous</option>
              {['delivery', 'lead', 'client', 'commande', 'provider'].map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Entity</label>
            <select value={filters.entity} onChange={e => { setFilters(f => ({ ...f, entity: e.target.value })); setPage(0); }}
              className="bg-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1.5 border border-zinc-700" data-testid="filter-entity">
              <option value="">Toutes</option><option value="ZR7">ZR7</option><option value="MDL">MDL</option>
            </select>
          </div>
          <button onClick={() => { setFilters({ action: '', entity_type: '', entity: '' }); setPage(0); }}
            className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1" data-testid="clear-filters-btn"><X className="w-3 h-3" /> Reset</button>
        </div>
      )}

      {/* Timeline */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="event-timeline">
        {loading ? (
          <div className="text-center py-8 text-zinc-600 text-xs">Chargement...</div>
        ) : events.length === 0 ? (
          <div className="text-center py-8 text-zinc-600 text-xs">Aucun événement</div>
        ) : (
          <div className="space-y-3">
            {events.map((e, i) => {
              const link = getLink(e);
              const details = e.details || {};
              const related = e.related || {};
              return (
                <div key={e.id || i} className="flex gap-3 text-xs" data-testid={`event-row-${e.id}`}>
                  <div className="w-1.5 shrink-0 relative">
                    <div className={`w-1.5 h-1.5 rounded-full mt-1.5 ${ACTION_COLORS[e.action] || 'text-zinc-500'} bg-current`} />
                    {i < events.length - 1 && <div className="absolute top-3 left-[2.5px] w-px bg-zinc-800 h-[calc(100%+0.75rem)]" />}
                  </div>
                  <div className="flex-1 pb-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`font-medium ${ACTION_COLORS[e.action] || 'text-zinc-400'}`}>{ACTION_LABELS[e.action] || e.action}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${ENTITY_TYPE_COLORS[e.entity_type] || 'bg-zinc-800 text-zinc-500 border-zinc-700'}`}>{e.entity_type}</span>
                      {e.entity && <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${e.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{e.entity}</span>}
                      <span className="text-[10px] text-zinc-600">{e.created_at?.slice(0, 19).replace('T', ' ')}</span>
                      <span className="text-[10px] text-zinc-700">{e.user}</span>
                      {link && (
                        <button onClick={() => navigate(link.path)} className="text-[10px] text-teal-500 hover:text-teal-400 flex items-center gap-0.5">
                          <ExternalLink className="w-2.5 h-2.5" /> {link.label}
                        </button>
                      )}
                    </div>
                    {/* Details */}
                    <div className="mt-0.5 text-zinc-500 flex gap-3 flex-wrap">
                      {details.reason && <span>Raison: {details.reason}</span>}
                      {details.detail && <span>"{details.detail}"</span>}
                      {details.error && <span className="text-red-400/70">{details.error}</span>}
                      {details.sent_to && <span>To: {details.sent_to.join(', ')}</span>}
                      {details.old_value !== undefined && <span>Ancien: {String(details.old_value)}</span>}
                      {details.new_value !== undefined && <span>Nouveau: {String(details.new_value)}</span>}
                      {related.client_name && <span className="text-zinc-600">{related.client_name}</span>}
                      {related.produit && <span className="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded">{related.produit}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-800">
          <span className="text-[10px] text-zinc-600">{total} total</span>
          <div className="flex gap-1">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-2 py-1 text-[10px] text-zinc-400 bg-zinc-800 rounded disabled:opacity-30 hover:bg-zinc-700">Prev</button>
            <span className="px-2 py-1 text-[10px] text-zinc-500">{page + 1} / {Math.max(1, Math.ceil(total / limit))}</span>
            <button disabled={(page + 1) * limit >= total} onClick={() => setPage(p => p + 1)} className="px-2 py-1 text-[10px] text-zinc-400 bg-zinc-800 rounded disabled:opacity-30 hover:bg-zinc-700">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Reusable Activity Block for embedding in Lead/Delivery detail
export function ActivityBlock({ entityType, entityId }) {
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!entityId) return;
    (async () => {
      try {
        const res = await authFetch(`${API}/api/event-log?entity_type=${entityType}&entity_id=${entityId}&limit=20`);
        if (res.ok) { const d = await res.json(); setEvents(d.events || []); }
      } catch (e) { console.error(e); }
      setLoading(false);
    })();
  }, [entityId, entityType, authFetch]);

  if (loading) return <p className="text-[10px] text-zinc-600">Chargement activité...</p>;
  if (events.length === 0) return <p className="text-[10px] text-zinc-600">Aucune activité</p>;

  return (
    <div className="space-y-2" data-testid="activity-block">
      {events.map((e, i) => (
        <div key={e.id || i} className="flex gap-2 text-xs">
          <div className={`w-1 h-1 rounded-full mt-1.5 shrink-0 ${ACTION_COLORS[e.action] || 'text-zinc-500'} bg-current`} />
          <div>
            <span className={`font-medium ${ACTION_COLORS[e.action] || 'text-zinc-400'}`}>{ACTION_LABELS[e.action] || e.action}</span>
            <span className="text-[10px] text-zinc-600 ml-2">{e.created_at?.slice(5, 16).replace('T', ' ')}</span>
            <span className="text-[10px] text-zinc-700 ml-1">{e.user}</span>
            {e.details?.reason && <p className="text-[10px] text-zinc-500 mt-0.5">Raison: {e.details.reason}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
