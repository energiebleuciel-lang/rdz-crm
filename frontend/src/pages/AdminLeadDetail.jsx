import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { ArrowLeft, Truck, Eye, Download, XCircle, Trash2, Clock } from 'lucide-react';
import { ActivityBlock } from './AdminActivity';

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
const DEL_STATUS_BADGE = {
  pending_csv: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  ready_to_send: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  sent: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
};
const REMOVE_REASONS = ['refus_client', 'doublon', 'hors_zone', 'mauvaise_commande', 'test', 'autre'];

export default function AdminLeadDetail() {
  const { id } = useParams();
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(true);
  const [removeModal, setRemoveModal] = useState(null); // delivery_id or null
  const [removeReason, setRemoveReason] = useState('autre');
  const [removeDetail, setRemoveDetail] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => { load(); }, [id]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/leads/${id}`);
      if (res.ok) setLead(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleRemove = async () => {
    if (!removeModal) return;
    setActionLoading(true);
    try {
      const res = await authFetch(`${API}/api/deliveries/${removeModal}/remove-lead`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: removeReason, reason_detail: removeDetail })
      });
      if (res.ok) { setRemoveModal(null); setRemoveDetail(''); load(); }
    } catch (e) { console.error(e); }
    setActionLoading(false);
  };

  const handleReject = async (deliveryId) => {
    const reason = prompt('Motif du rejet client:');
    if (!reason) return;
    setActionLoading(true);
    try {
      await authFetch(`${API}/api/deliveries/${deliveryId}/reject-leads`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });
      load();
    } catch (e) { console.error(e); }
    setActionLoading(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!lead) return <div className="text-zinc-500 text-center py-8">Lead non trouvé</div>;

  const l = lead;
  const deliveries = l.deliveries || [];

  return (
    <div data-testid="lead-detail">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 mb-4" data-testid="back-btn">
        <ArrowLeft className="w-3.5 h-3.5" /> Retour
      </button>

      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-lg font-semibold text-white">Lead</h1>
        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGE[l.status] || 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>{l.status}</span>
        {l.entity && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${l.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{l.entity}</span>}
        {l.is_lb && <span className="text-[10px] px-2 py-0.5 rounded-full border bg-zinc-800 text-zinc-500 border-zinc-700">LB</span>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Lead payload */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Données lead</h2>
          <dl className="space-y-2 text-xs">
            {[
              ['ID', l.id],
              ['Phone', l.phone],
              ['Nom', `${l.nom || ''} ${l.prenom || ''}`],
              ['Email', l.email],
              ['Département', l.departement],
              ['Entity', l.entity],
              ['Produit', l.produit],
              ['Source', l.source || l.lp_code || '-'],
              ['Form', l.form_code || '-'],
              ['Créé', l.created_at?.slice(0, 19).replace('T', ' ')],
              ['Provider', l.provider_slug || '-'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <dt className="text-zinc-500 shrink-0">{k}</dt>
                <dd className="text-zinc-300 text-right max-w-[220px] truncate font-mono text-[10px]">{v || '-'}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Routing info */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Routing</h2>
          <dl className="space-y-2 text-xs">
            {[
              ['Status', l.status],
              ['Client assigné', l.delivered_to_client_name || l.delivery_client_name || '-'],
              ['Client ID', l.delivered_to_client_id || l.delivery_client_id || '-'],
              ['Commande', l.delivery_commande_id || '-'],
              ['Delivery ID', l.delivery_id || '-'],
              ['Routé le', l.routed_at?.slice(0, 19).replace('T', ' ') || '-'],
              ['Livré le', l.delivered_at?.slice(0, 19).replace('T', ' ') || '-'],
              ['Entity locked', l.entity_locked ? 'Oui' : 'Non'],
              ['LB', l.is_lb ? `Oui (${l.lb_reason || '-'})` : 'Non'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <dt className="text-zinc-500 shrink-0">{k}</dt>
                <dd className="text-zinc-300 text-right max-w-[220px] truncate">{String(v)}</dd>
              </div>
            ))}
          </dl>
          {(l.delivered_to_client_id || l.delivery_client_id) && (
            <button onClick={() => navigate(`/admin/clients/${l.delivered_to_client_id || l.delivery_client_id}`)}
              className="mt-3 text-[10px] text-teal-400 hover:text-teal-300" data-testid="view-client-btn">Voir fiche client</button>
          )}
        </div>
      </div>

      {/* Delivery history */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="delivery-history">
        <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Truck className="w-3.5 h-3.5" /> Historique livraisons ({deliveries.length})</h2>
        {deliveries.length === 0 ? <p className="text-[10px] text-zinc-600">Aucune delivery</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs" data-testid="delivery-history-table">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500">
                  <th className="text-left px-3 py-2 font-medium">Date</th>
                  <th className="text-left px-3 py-2 font-medium">Client</th>
                  <th className="text-left px-3 py-2 font-medium">Produit</th>
                  <th className="text-left px-3 py-2 font-medium">Status</th>
                  <th className="text-left px-3 py-2 font-medium">Outcome</th>
                  <th className="text-left px-3 py-2 font-medium">Sent To</th>
                  <th className="text-left px-3 py-2 font-medium">Billable</th>
                  <th className="text-right px-3 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {deliveries.map(d => (
                  <tr key={d.id} className="border-b border-zinc-800/50">
                    <td className="px-3 py-2 text-zinc-400 text-[10px]">{d.created_at?.slice(5, 16).replace('T', ' ')}</td>
                    <td className="px-3 py-2 text-zinc-300">{d.client_name}</td>
                    <td className="px-3 py-2 text-zinc-400">{d.produit}</td>
                    <td className="px-3 py-2"><span className={`text-[10px] px-2 py-0.5 rounded-full border ${DEL_STATUS_BADGE[d.status] || ''}`}>{d.status}</span></td>
                    <td className="px-3 py-2">
                      {d.outcome === 'rejected' && <span className="text-[10px] px-2 py-0.5 rounded-full border bg-orange-500/10 text-orange-400 border-orange-500/30">rejected</span>}
                      {d.outcome === 'removed' && <span className="text-[10px] px-2 py-0.5 rounded-full border bg-red-500/10 text-red-300 border-red-500/30">removed</span>}
                      {d.outcome === 'accepted' && <span className="text-[10px] text-zinc-600">accepted</span>}
                    </td>
                    <td className="px-3 py-2 text-zinc-500 text-[10px] max-w-[120px] truncate">{d.sent_to?.join(', ') || '-'}</td>
                    <td className="px-3 py-2">{d.billable ? <span className="text-[10px] text-emerald-400">Oui</span> : <span className="text-[10px] text-zinc-600">Non</span>}</td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => navigate(`/admin/deliveries/${d.id}`)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" title="Voir delivery"><Eye className="w-3 h-3" /></button>
                        {d.status === 'sent' && d.outcome === 'accepted' && (
                          <>
                            <button onClick={() => handleReject(d.id)} className="p-1 text-zinc-500 hover:text-orange-400 rounded" title="Rejeter" disabled={actionLoading} data-testid={`reject-btn-${d.id}`}><XCircle className="w-3 h-3" /></button>
                            <button onClick={() => setRemoveModal(d.id)} className="p-1 text-zinc-500 hover:text-red-400 rounded" title="Retirer" data-testid={`remove-btn-${d.id}`}><Trash2 className="w-3 h-3" /></button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Custom fields */}
      {l.custom_fields && Object.keys(l.custom_fields).length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mt-4">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Champs secondaires</h2>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            {Object.entries(l.custom_fields).map(([k, v]) => (
              <div key={k}><dt className="text-zinc-500 text-[10px]">{k}</dt><dd className="text-zinc-300">{v || '-'}</dd></div>
            ))}
          </dl>
        </div>
      )}

      {/* Activity log for this lead */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mt-4" data-testid="lead-activity-section">
        <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Clock className="w-3.5 h-3.5" /> Activité</h2>
        <ActivityBlock entityType="delivery" entityId={l.delivery_id || deliveries[0]?.id} />
      </div>

      {/* Remove modal */}
      {removeModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="remove-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-sm font-semibold text-white mb-4">Retirer le lead de la livraison</h2>
            <p className="text-xs text-zinc-400 mb-3">Le lead redeviendra status=new (re-routable). La delivery et le CSV restent intacts. Action loguée.</p>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Raison *</label>
                <select value={removeReason} onChange={e => setRemoveReason(e.target.value)} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="remove-reason-select">
                  {REMOVE_REASONS.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Détail (optionnel)</label>
                <textarea value={removeDetail} onChange={e => setRemoveDetail(e.target.value)} className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-xs text-zinc-300 resize-none" rows={2} data-testid="remove-detail-input" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => { setRemoveModal(null); setRemoveDetail(''); }} className="px-3 py-1.5 text-xs text-zinc-400" data-testid="remove-cancel-btn">Annuler</button>
              <button onClick={handleRemove} disabled={actionLoading} className="px-3 py-1.5 text-xs bg-red-500/20 text-red-400 rounded-md hover:bg-red-500/30 border border-red-500/30 disabled:opacity-50" data-testid="remove-confirm-btn">Retirer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
