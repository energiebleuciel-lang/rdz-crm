import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { ArrowLeft, Download, Send, RefreshCw, XCircle, AlertTriangle, Phone, Mail, CalendarDays } from 'lucide-react';

const STATUS_BADGE = {
  pending_csv: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  ready_to_send: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  sending: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  sent: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
};
const DAY_SHORT = ['L', 'M', 'Me', 'J', 'V', 'S', 'D'];

export default function AdminDeliveryDetail() {
  const { id } = useParams();
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [delivery, setDelivery] = useState(null);
  const [lead, setLead] = useState(null);
  const [client, setClient] = useState(null);
  const [calendar, setCalendar] = useState({});
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectModal, setRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectError, setRejectError] = useState('');

  useEffect(() => { load(); }, [id]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/deliveries/${id}`);
      if (res.ok) {
        const d = await res.json();
        setDelivery(d);
        const [lRes, cRes, calRes] = await Promise.all([
          d.lead_id ? authFetch(`${API}/api/leads/${d.lead_id}`).catch(() => null) : null,
          d.client_id ? authFetch(`${API}/api/clients/${d.client_id}`).catch(() => null) : null,
          authFetch(`${API}/api/settings/delivery-calendar`).catch(() => null)
        ]);
        if (lRes?.ok) setLead(await lRes.json());
        if (cRes?.ok) { const cd = await cRes.json(); setClient(cd.client || cd); }
        if (calRes?.ok) setCalendar(await calRes.json());
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleSend = async (force = false) => {
    setActionLoading(true);
    try {
      await authFetch(`${API}/api/deliveries/${id}/send`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force })
      });
      load();
    } catch (e) { console.error(e); }
    setActionLoading(false);
  };

  const handleDownload = async () => {
    const res = await authFetch(`${API}/api/deliveries/${id}/download`);
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = delivery?.csv_filename || `delivery_${id}.csv`; a.click(); URL.revokeObjectURL(url);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) { setRejectError('Motif obligatoire'); return; }
    setActionLoading(true);
    setRejectError('');
    try {
      const res = await authFetch(`${API}/api/deliveries/${id}/reject-leads`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: rejectReason })
      });
      if (res.ok) { setRejectModal(false); setRejectReason(''); load(); }
      else { const err = await res.json(); setRejectError(err.detail || 'Erreur'); }
    } catch (e) { setRejectError(e.message); }
    setActionLoading(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!delivery) return <div className="text-zinc-500 text-center py-8">Delivery non trouvee</div>;

  const d = delivery;
  const isRejected = d.outcome === 'rejected';
  const isRemoved = d.outcome === 'removed';
  const entityDays = calendar[d.entity]?.enabled_days || [];

  return (
    <div data-testid="delivery-detail">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 mb-4" data-testid="back-btn">
        <ArrowLeft className="w-3.5 h-3.5" /> Retour
      </button>

      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-lg font-semibold text-white">Delivery</h1>
        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGE[d.status]}`}>{d.status}</span>
        {isRejected && <span className="text-[10px] px-2 py-0.5 rounded-full border bg-orange-500/10 text-orange-400 border-orange-500/30 font-medium">rejected</span>}
        {isRemoved && <span className="text-[10px] px-2 py-0.5 rounded-full border bg-red-500/10 text-red-300 border-red-500/30 font-medium">removed</span>}
        {d.billable && <span className="text-[10px] px-2 py-0.5 rounded-full border bg-emerald-500/10 text-emerald-400 border-emerald-500/30">billable</span>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Delivery info */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Delivery</h2>
          <dl className="space-y-2 text-xs">
            {[
              ['ID', d.id],
              ['Entity', d.entity],
              ['Produit', d.produit],
              ['Created', d.created_at?.slice(0, 19).replace('T', ' ')],
              ['Sent To', d.sent_to?.join(', ') || '-'],
              ['Last Sent', d.last_sent_at?.slice(0, 19).replace('T', ' ') || '-'],
              ['Attempts', d.send_attempts || 0],
              ['Sent By', d.sent_by || '-'],
              ['Error', d.last_error || '-'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <dt className="text-zinc-500 shrink-0">{k}</dt>
                <dd className={`text-right truncate max-w-[180px] ${k === 'Error' && v !== '-' ? 'text-red-400' : 'text-zinc-300'}`}>{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Client info */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Client</h2>
          {client ? (
            <div className="space-y-3">
              <p className="text-sm text-white font-medium">{client.name}</p>
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Phone className="w-3 h-3" /><span className="font-mono">{client.phone || '-'}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Mail className="w-3 h-3" /><span>{client.email}</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-zinc-500">Auto-send:</span>
                {(client.auto_send_enabled ?? true) ? <span className="text-emerald-400">ON</span> : <span className="text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded text-[10px]">OFF</span>}
              </div>
              <div className="flex items-center gap-2">
                <CalendarDays className="w-3 h-3 text-zinc-500" />
                <div className="flex gap-0.5">
                  {DAY_SHORT.map((name, i) => (
                    <span key={i} className={`w-4 h-4 text-[8px] flex items-center justify-center rounded ${entityDays.includes(i) ? 'bg-teal-500/20 text-teal-400' : 'bg-zinc-800 text-zinc-700'}`}>{name}</span>
                  ))}
                </div>
              </div>
              <button onClick={() => navigate(`/admin/deliveries?client_id=${client.id}`)} className="text-[10px] text-teal-400 hover:text-teal-300 mt-1">
                Voir toutes les deliveries de ce client
              </button>
            </div>
          ) : <p className="text-xs text-zinc-600">Client: {d.client_name}</p>}
        </div>

        {/* Actions + Rejection */}
        <div className="space-y-4">
          {isRejected && (
            <div className="bg-orange-500/5 border border-orange-500/20 rounded-lg p-4" data-testid="rejection-info">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-orange-400" />
                <h2 className="text-xs font-medium text-orange-400 uppercase tracking-wider">Rejected</h2>
              </div>
              <dl className="space-y-1.5 text-xs">
                <div className="flex justify-between"><dt className="text-zinc-500">Reason</dt><dd className="text-orange-300">{d.rejection_reason || '-'}</dd></div>
                <div className="flex justify-between"><dt className="text-zinc-500">By</dt><dd className="text-zinc-400">{d.rejected_by || '-'}</dd></div>
                <div className="flex justify-between"><dt className="text-zinc-500">At</dt><dd className="text-zinc-400">{d.rejected_at?.slice(0, 19).replace('T', ' ') || '-'}</dd></div>
              </dl>
            </div>
          )}

          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Actions</h2>
            <div className="flex flex-wrap gap-2">
              {d.has_csv && (
                <button onClick={handleDownload} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-cyan-400 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="download-csv-btn">
                  <Download className="w-3 h-3" /> CSV
                </button>
              )}
              {d.status === 'ready_to_send' && (
                <button onClick={() => handleSend(false)} disabled={actionLoading} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-emerald-500/10 text-emerald-400 rounded-md hover:bg-emerald-500/20 border border-emerald-500/30 disabled:opacity-50" data-testid="send-now-btn">
                  <Send className="w-3 h-3" /> Send Now
                </button>
              )}
              {d.status === 'sent' && (
                <button onClick={() => handleSend(true)} disabled={actionLoading} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-amber-500/10 text-amber-400 rounded-md hover:bg-amber-500/20 border border-amber-500/30 disabled:opacity-50" data-testid="resend-btn">
                  <RefreshCw className="w-3 h-3" /> Resend
                </button>
              )}
              {d.status === 'sent' && !isRejected && (
                <button onClick={() => setRejectModal(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-red-500/10 text-red-400 rounded-md hover:bg-red-500/20 border border-red-500/30" data-testid="reject-btn">
                  <XCircle className="w-3 h-3" /> Reject
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Lead info */}
      {lead && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="lead-info">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Lead</h2>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            {[
              ['Phone', lead.phone],
              ['Nom', lead.nom],
              ['Prenom', lead.prenom],
              ['Dept', lead.departement],
              ['Email', lead.email],
              ['Status', lead.status],
              ['Entity', lead.entity],
              ['Produit', lead.produit],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-zinc-500 text-[10px]">{k}</dt>
                <dd className={`${k === 'Status' ? (v === 'livre' ? 'text-emerald-400' : v === 'new' ? 'text-cyan-400' : 'text-zinc-300') : 'text-zinc-300'}`}>{v || '-'}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Reject Modal */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="reject-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-sm font-semibold text-white mb-4">Confirmer le rejet</h2>
            <p className="text-xs text-zinc-400 mb-3">Le lead sera remis en circulation (status=new). La delivery reste intacte.</p>
            <label className="text-[10px] text-zinc-500 block mb-1">Motif du rejet *</label>
            <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-xs text-zinc-300 mb-2 resize-none" rows={3}
              placeholder="Ex: Lead non qualifie, mauvais produit..." data-testid="reject-reason-input" />
            {rejectError && <p className="text-[10px] text-red-400 mb-2">{rejectError}</p>}
            <div className="flex justify-end gap-2">
              <button onClick={() => { setRejectModal(false); setRejectReason(''); setRejectError(''); }} className="px-3 py-1.5 text-xs text-zinc-400" data-testid="reject-cancel-btn">Annuler</button>
              <button onClick={handleReject} disabled={actionLoading} className="px-3 py-1.5 text-xs bg-red-500/20 text-red-400 rounded-md hover:bg-red-500/30 border border-red-500/30 disabled:opacity-50" data-testid="reject-confirm-btn">Confirmer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
