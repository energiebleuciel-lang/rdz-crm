import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import {
  ArrowLeft, Star, Shield, Phone, Mail, CalendarDays, Truck,
  BarChart3, CreditCard, Clock, Send, AlertTriangle, Plus, Save, Tag,
  DollarSign, Gift, Trash2
} from 'lucide-react';

const DAY_SHORT = ['L', 'M', 'Me', 'J', 'V', 'S', 'D'];
const STATUS_COLORS = { VIP: 'text-amber-400 bg-amber-500/10 border-amber-500/30', Normal: 'text-zinc-400 bg-zinc-800 border-zinc-700', Watchlist: 'text-orange-400 bg-orange-500/10 border-orange-500/30', Blocked: 'text-red-400 bg-red-500/10 border-red-500/30' };
const ACCOUNTING_COLORS = { up_to_date: 'text-emerald-400', late: 'text-amber-400', dispute: 'text-red-400' };
const TAG_OPTIONS = ['VIP', 'slow_payer', 'discount_hunter', 'high_volume', 'new_client', 'strategic'];
const ACTION_LABELS = { delivery_rejected: 'Rejet', delivery_failed: 'Echec livraison', crm_update: 'MAJ CRM', note_added: 'Note' };
const ACTION_COLORS = { delivery_rejected: 'text-orange-400', delivery_failed: 'text-red-400', crm_update: 'text-cyan-400', note_added: 'text-zinc-300' };

function Stars({ value, onChange, size = 'w-4 h-4' }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <button key={i} onClick={() => onChange?.(i)} className={`${size} ${i <= value ? 'text-amber-400' : 'text-zinc-700'} transition-colors`} data-testid={`star-${i}`}>
          <Star className={`${size} ${i <= value ? 'fill-amber-400' : ''}`} />
        </button>
      ))}
    </div>
  );
}

export default function AdminClientDetail() {
  const { id } = useParams();
  const { authFetch } = useAuth();
  const navigate = useNavigate();
  const [client, setClient] = useState(null);
  const [summary, setSummary] = useState(null);
  const [activity, setActivity] = useState([]);
  const [calendar, setCalendar] = useState({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('summary');
  const [groupBy, setGroupBy] = useState('day');
  const [saving, setSaving] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, calRes] = await Promise.all([
        authFetch(`${API}/api/clients/${id}`),
        authFetch(`${API}/api/settings/delivery-calendar`)
      ]);
      if (cRes.ok) { const d = await cRes.json(); setClient(d.client || d); }
      if (calRes.ok) setCalendar(await calRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [id, authFetch]);

  const loadSummary = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/clients/${id}/summary?group_by=${groupBy}`);
      if (res.ok) setSummary(await res.json());
    } catch (e) { console.error(e); }
  }, [id, groupBy, authFetch]);

  const loadActivity = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/clients/${id}/activity`);
      if (res.ok) { const d = await res.json(); setActivity(d.activities || []); }
    } catch (e) { console.error(e); }
  }, [id, authFetch]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (tab === 'performance') loadSummary(); }, [tab, loadSummary]);
  useEffect(() => { if (tab === 'activity') loadActivity(); }, [tab, loadActivity]);

  const saveCRM = async (field, value) => {
    setSaving(true);
    try {
      await authFetch(`${API}/api/clients/${id}/crm`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value })
      });
      setClient(prev => ({ ...prev, [field]: value }));
      setMsg('Saved'); setTimeout(() => setMsg(''), 1500);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const addNote = async () => {
    if (!noteText.trim()) return;
    try {
      await authFetch(`${API}/api/clients/${id}/notes`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: noteText })
      });
      setNoteText('');
      load();
      if (tab === 'activity') loadActivity();
    } catch (e) { console.error(e); }
  };

  const toggleTag = (tag) => {
    const current = client?.tags || [];
    const next = current.includes(tag) ? current.filter(t => t !== tag) : [...current, tag];
    saveCRM('tags', next);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!client) return <div className="text-zinc-500 text-center py-8">Client non trouvé</div>;

  const c = client;
  const entityDays = calendar[c.entity]?.enabled_days || [];
  const TABS = [
    { key: 'summary', label: 'Résumé', icon: Shield },
    { key: 'performance', label: 'Performance', icon: BarChart3 },
    { key: 'pricing', label: 'Pricing', icon: DollarSign },
    { key: 'offers', label: 'Offres', icon: Gift },
    { key: 'crm', label: 'CRM & Paiement', icon: CreditCard },
    { key: 'activity', label: 'Activité', icon: Clock },
  ];

  return (
    <div data-testid="client-detail">
      <button onClick={() => navigate('/admin/clients')} className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 mb-4" data-testid="back-btn">
        <ArrowLeft className="w-3.5 h-3.5" /> Clients
      </button>

      {msg && <div className="mb-3 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded text-xs text-emerald-400 inline-block">{msg}</div>}

      {/* TOP SUMMARY - always visible */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4" data-testid="client-health-summary">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold text-white">{c.name}</h1>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>{c.entity}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${STATUS_COLORS[c.client_status] || STATUS_COLORS.Normal}`} data-testid="client-status-badge">
                {c.client_status || 'Normal'}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs text-zinc-400">
              {c.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{c.phone}</span>}
              <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{c.email}</span>
            </div>
          </div>
          <div className="flex gap-2">
            {(c.tags || []).map(tag => (
              <span key={tag} className="text-[9px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">{tag}</span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Global</p>
            <Stars value={c.global_rating || 0} onChange={v => saveCRM('global_rating', v)} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Paiement</p>
            <Stars value={c.payment_rating || 0} onChange={v => saveCRM('payment_rating', v)} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Satisfaction leads</p>
            <Stars value={c.lead_satisfaction_rating || 0} onChange={v => saveCRM('lead_satisfaction_rating', v)} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Pression discount</p>
            <Stars value={c.discount_pressure_rating || 0} onChange={v => saveCRM('discount_pressure_rating', v)} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Auto-send</p>
            <span className={`text-xs font-medium ${(c.auto_send_enabled ?? true) ? 'text-emerald-400' : 'text-amber-400'}`}>{(c.auto_send_enabled ?? true) ? 'ON' : 'OFF'}</span>
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Prochain envoi</p>
            <span className="text-xs text-zinc-300">{summary?.next_delivery_day || '-'}</span>
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Jours</p>
            <div className="flex gap-0.5">
              {DAY_SHORT.map((d, i) => (
                <span key={i} className={`w-4 h-4 text-[7px] flex items-center justify-center rounded ${entityDays.includes(i) ? 'bg-teal-500/20 text-teal-400' : 'bg-zinc-800 text-zinc-700'}`}>{d}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* TABS */}
      <div className="flex gap-1 mb-4">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors ${
              tab === t.key ? 'bg-teal-500/15 text-teal-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
            }`} data-testid={`tab-${t.key}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENT */}
      {tab === 'summary' && <SummaryTab client={c} navigate={navigate} />}
      {tab === 'performance' && <PerformanceTab summary={summary} groupBy={groupBy} setGroupBy={setGroupBy} loadSummary={loadSummary} />}
      {tab === 'pricing' && <PricingTab clientId={id} authFetch={authFetch} />}
      {tab === 'offers' && <OffersTab clientId={id} authFetch={authFetch} />}
      {tab === 'crm' && <CRMTab client={c} saveCRM={saveCRM} saving={saving} toggleTag={toggleTag} noteText={noteText} setNoteText={setNoteText} addNote={addNote} />}
      {tab === 'activity' && <ActivityTab activities={activity} />}
    </div>
  );
}

function SummaryTab({ client, navigate }) {
  const c = client;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="tab-content-summary">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Infos client</h3>
        <dl className="space-y-2 text-xs">
          {[['Contact', c.contact_name], ['Email', c.email], ['Tel', c.phone], ['Delivery Emails', (c.delivery_emails||[]).join(', ')], ['API', c.api_endpoint || '-'], ['Prix/lead', `${c.default_prix_lead || 0} EUR`], ['Remise', `${c.remise_percent || 0}%`], ['Créé', c.created_at?.slice(0, 10)]].map(([k, v]) => (
            <div key={k} className="flex justify-between"><dt className="text-zinc-500">{k}</dt><dd className="text-zinc-300 text-right max-w-[200px] truncate">{v || '-'}</dd></div>
          ))}
        </dl>
      </div>
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Deliveries rapide</h3>
        <dl className="space-y-2 text-xs">
          <div className="flex justify-between"><dt className="text-zinc-500">Total reçus</dt><dd className="text-zinc-300">{c.total_leads_received}</dd></div>
          <div className="flex justify-between"><dt className="text-zinc-500">Cette semaine</dt><dd className="text-zinc-300">{c.total_leads_this_week}</dd></div>
          <div className="flex justify-between"><dt className="text-zinc-500">Livrable</dt><dd className={c.has_valid_channel ? 'text-emerald-400' : 'text-red-400'}>{c.has_valid_channel ? 'Oui' : 'Non'}</dd></div>
          {c.deliverable_reason && <div className="text-[10px] text-red-400/70">{c.deliverable_reason}</div>}
        </dl>
        <button onClick={() => navigate(`/admin/deliveries?client_id=${c.id}`)}
          className="mt-3 text-[10px] text-teal-400 hover:text-teal-300 flex items-center gap-1" data-testid="view-deliveries-btn">
          <Truck className="w-3 h-3" /> Voir toutes les deliveries
        </button>
      </div>
    </div>
  );
}

function PerformanceTab({ summary, groupBy, setGroupBy, loadSummary }) {
  if (!summary) return <div className="text-zinc-600 text-xs py-4">Chargement...</div>;
  const t = summary.totals || {};
  return (
    <div data-testid="tab-content-performance">
      {/* Period selector */}
      <div className="flex gap-2 mb-4">
        {['day', 'week', 'month'].map(g => (
          <button key={g} onClick={() => setGroupBy(g)}
            className={`px-2.5 py-1 text-[10px] rounded-full border ${groupBy === g ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'bg-zinc-900 text-zinc-400 border-zinc-800'}`}
            data-testid={`group-by-${g}`}>{g}</button>
        ))}
      </div>

      {/* Totals */}
      <div className="grid grid-cols-5 gap-2.5 mb-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2.5 text-center">
          <p className="text-lg font-semibold text-white">{t.sent}</p><p className="text-[10px] text-zinc-500">Sent</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2.5 text-center">
          <p className="text-lg font-semibold text-emerald-400">{t.billable}</p><p className="text-[10px] text-zinc-500">Billable</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2.5 text-center">
          <p className="text-lg font-semibold text-orange-400">{t.rejected}</p><p className="text-[10px] text-zinc-500">Rejected</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2.5 text-center">
          <p className="text-lg font-semibold text-red-400">{t.failed}</p><p className="text-[10px] text-zinc-500">Failed</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2.5 text-center">
          <p className="text-lg font-semibold text-zinc-300">{t.reject_rate}%</p><p className="text-[10px] text-zinc-500">Reject Rate</p>
        </div>
      </div>

      {/* Period table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-xs" data-testid="performance-table">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-500">
              <th className="text-left px-3 py-2 font-medium">Période</th>
              <th className="text-right px-3 py-2 font-medium">Sent</th>
              <th className="text-right px-3 py-2 font-medium">Billable</th>
              <th className="text-right px-3 py-2 font-medium">Rejected</th>
              <th className="text-right px-3 py-2 font-medium">Failed</th>
              <th className="text-right px-3 py-2 font-medium">Rate</th>
              <th className="text-left px-3 py-2 font-medium">Produits</th>
            </tr>
          </thead>
          <tbody>
            {(summary.periods || []).length === 0 ? (
              <tr><td colSpan={7} className="text-center py-6 text-zinc-600">Aucune donnée</td></tr>
            ) : (summary.periods || []).map((p, i) => (
              <tr key={i} className="border-b border-zinc-800/50">
                <td className="px-3 py-2 text-zinc-300 font-mono">{p.period}</td>
                <td className="px-3 py-2 text-right text-zinc-300">{p.sent}</td>
                <td className="px-3 py-2 text-right text-emerald-400">{p.billable}</td>
                <td className="px-3 py-2 text-right text-orange-400">{p.rejected || 0}</td>
                <td className="px-3 py-2 text-right text-red-400">{p.failed}</td>
                <td className="px-3 py-2 text-right text-zinc-400">{p.reject_rate}%</td>
                <td className="px-3 py-2">
                  <div className="flex gap-1.5">
                    {Object.entries(p.by_produit || {}).map(([prod, cnt]) => (
                      <span key={prod} className="text-[9px] bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400">{prod}:{cnt}</span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-2 flex justify-between text-[10px] text-zinc-600">
        <span>{summary.from} → {summary.to}</span>
        <span>Auto-send: {summary.auto_send_enabled ? 'ON' : 'OFF'} | Next: {summary.next_delivery_day || '-'}</span>
      </div>
    </div>
  );
}

function CRMTab({ client, saveCRM, saving, toggleTag, noteText, setNoteText, addNote }) {
  const c = client;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="tab-content-crm">
      {/* Payment & Status */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Paiement & Statut</h3>
        <div className="space-y-3">
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Client Status</label>
            <div className="flex gap-1.5">
              {['Normal', 'VIP', 'Watchlist', 'Blocked'].map(s => (
                <button key={s} onClick={() => saveCRM('client_status', s)}
                  className={`text-[10px] px-2 py-1 rounded-full border ${(c.client_status || 'Normal') === s ? STATUS_COLORS[s] : 'bg-zinc-800 text-zinc-600 border-zinc-700'}`}
                  data-testid={`status-btn-${s.toLowerCase()}`}>{s}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Accounting Status</label>
            <div className="flex gap-1.5">
              {['up_to_date', 'late', 'dispute'].map(s => (
                <button key={s} onClick={() => saveCRM('accounting_status', s)}
                  className={`text-[10px] px-2 py-1 rounded-full border ${(c.accounting_status || 'up_to_date') === s ? `${ACCOUNTING_COLORS[s]} bg-zinc-800 border-current` : 'bg-zinc-800 text-zinc-600 border-zinc-700'}`}
                  data-testid={`accounting-btn-${s}`}>{s.replace('_', ' ')}</button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Payment Terms</label>
              <select value={c.payment_terms || ''} onChange={e => saveCRM('payment_terms', e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300" data-testid="payment-terms">
                <option value="">-</option>
                <option value="prepaid">Prépayé</option>
                <option value="net_15">Net 15</option>
                <option value="net_30">Net 30</option>
                <option value="net_60">Net 60</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Payment Method</label>
              <select value={c.payment_method || ''} onChange={e => saveCRM('payment_method', e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300" data-testid="payment-method">
                <option value="">-</option>
                <option value="bank_transfer">Virement</option>
                <option value="credit_card">CB</option>
                <option value="check">Chèque</option>
                <option value="direct_debit">Prélèvement</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Dernier paiement (date)</label>
              <input type="date" value={c.last_payment_date || ''} onChange={e => saveCRM('last_payment_date', e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300" data-testid="last-payment-date" />
            </div>
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Montant (EUR)</label>
              <input type="number" value={c.last_payment_amount || ''} onChange={e => saveCRM('last_payment_amount', Number(e.target.value))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300" data-testid="last-payment-amount" />
            </div>
          </div>
        </div>
      </div>

      {/* Tags + Notes */}
      <div className="space-y-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2"><Tag className="w-3.5 h-3.5" /> Tags</h3>
          <div className="flex flex-wrap gap-1.5">
            {TAG_OPTIONS.map(tag => (
              <button key={tag} onClick={() => toggleTag(tag)}
                className={`text-[10px] px-2.5 py-1 rounded-full border transition-colors ${
                  (c.tags || []).includes(tag) ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'bg-zinc-800 text-zinc-600 border-zinc-700 hover:border-zinc-600'
                }`} data-testid={`tag-${tag}`}>{tag}</button>
            ))}
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Notes internes</h3>
          <div className="flex gap-2 mb-3">
            <input value={noteText} onChange={e => setNoteText(e.target.value)} placeholder="Ajouter une note..."
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-xs text-zinc-300" data-testid="note-input"
              onKeyDown={e => e.key === 'Enter' && addNote()} />
            <button onClick={addNote} className="px-3 py-1.5 text-xs bg-teal-500/10 text-teal-400 rounded hover:bg-teal-500/20 border border-teal-500/30" data-testid="add-note-btn">
              <Plus className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {(c.internal_notes || []).slice().reverse().map((n, i) => (
              <div key={i} className="text-xs border-l-2 border-zinc-700 pl-2.5 py-1">
                <p className="text-zinc-300">{n.text}</p>
                <p className="text-[10px] text-zinc-600 mt-0.5">{n.author} - {n.created_at?.slice(0, 16).replace('T', ' ')}</p>
              </div>
            ))}
            {(c.internal_notes || []).length === 0 && <p className="text-[10px] text-zinc-600">Aucune note</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function ActivityTab({ activities }) {
  return (
    <div data-testid="tab-content-activity">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Timeline</h3>
        {activities.length === 0 ? <p className="text-[10px] text-zinc-600">Aucune activité</p> : (
          <div className="space-y-3">
            {activities.map((a, i) => (
              <div key={i} className="flex gap-3 text-xs">
                <div className="w-1.5 shrink-0 relative">
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 ${ACTION_COLORS[a.action] || 'text-zinc-500'} bg-current`} />
                  {i < activities.length - 1 && <div className="absolute top-3 left-[2.5px] bottom-0 w-px bg-zinc-800 -mb-3 h-[calc(100%+0.75rem)]" />}
                </div>
                <div className="flex-1 pb-3">
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${ACTION_COLORS[a.action] || 'text-zinc-400'}`}>{ACTION_LABELS[a.action] || a.action}</span>
                    <span className="text-[10px] text-zinc-600">{a.created_at?.slice(0, 16).replace('T', ' ')}</span>
                    <span className="text-[10px] text-zinc-700">{a.user}</span>
                  </div>
                  {a.details && (
                    <div className="mt-0.5 text-zinc-500">
                      {a.details.reason && <span>Raison: {a.details.reason}</span>}
                      {a.details.error && <span className="text-red-400/70">{a.details.error}</span>}
                      {a.details.text && <span>"{a.details.text}"</span>}
                      {a.details.produit && <span className="ml-2 text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded">{a.details.produit}</span>}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const PRODUCTS = ['PV', 'PAC', 'ITE'];
const BILLING_MODES = ['WEEKLY_INVOICE', 'PREPAID'];
const CREDIT_REASONS = ['fin_de_semaine', 'geste_commercial', 'retard', 'qualite', 'bug', 'autre'];

function PricingTab({ clientId, authFetch }) {
  const [data, setData] = useState(null);
  const [prepay, setPrepay] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [globalDisc, setGlobalDisc] = useState(0);
  const [tvaRate, setTvaRate] = useState(20);
  const [addProd, setAddProd] = useState({ product_code: '', unit_price_eur: 0, discount_pct: 0, billing_mode: 'WEEKLY_INVOICE' });
  const [prepayUnits, setPrepayUnits] = useState({ product_code: '', units_to_add: 0, note: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pRes, bRes] = await Promise.all([
        authFetch(`${API}/api/clients/${clientId}/pricing`),
        authFetch(`${API}/api/clients/${clientId}/prepayment`),
      ]);
      if (pRes.ok) {
        const d = await pRes.json();
        setData(d);
        setGlobalDisc(d.global?.discount_pct_global || 0);
        setTvaRate(d.global?.tva_rate ?? 20);
      }
      if (bRes.ok) { const d = await bRes.json(); setPrepay(d.balances || []); }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [clientId, authFetch]);

  useEffect(() => { load(); }, [load]);

  const saveGlobal = async () => {
    setSaving(true);
    await authFetch(`${API}/api/clients/${clientId}/pricing`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ discount_pct_global: globalDisc, tva_rate: tvaRate }),
    });
    setSaving(false); load();
  };

  const saveProduct = async () => {
    if (!addProd.product_code) return;
    setSaving(true);
    await authFetch(`${API}/api/clients/${clientId}/pricing/product`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(addProd),
    });
    setAddProd({ product_code: '', unit_price_eur: 0, discount_pct: 0, billing_mode: 'WEEKLY_INVOICE' });
    setSaving(false); load();
  };

  const deleteProduct = async (pc) => {
    if (!window.confirm(`Supprimer le pricing ${pc} ?`)) return;
    await authFetch(`${API}/api/clients/${clientId}/pricing/product/${pc}`, { method: 'DELETE' });
    load();
  };

  const addPrepayUnits = async () => {
    if (!prepayUnits.product_code || prepayUnits.units_to_add <= 0) return;
    await authFetch(`${API}/api/clients/${clientId}/prepayment/add-units`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prepayUnits),
    });
    setPrepayUnits({ product_code: '', units_to_add: 0, note: '' });
    load();
  };

  if (loading) return <div className="text-zinc-600 text-xs py-4">Chargement...</div>;

  return (
    <div className="space-y-4" data-testid="tab-content-pricing">
      {/* Global pricing */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Pricing global</h3>
        <div className="flex gap-4 items-end">
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Remise globale (%)</label>
            <input type="number" value={globalDisc} onChange={e => setGlobalDisc(Number(e.target.value))} min={0} max={100} step={0.5}
              className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-24" data-testid="global-discount" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">TVA (%)</label>
            <input type="number" value={tvaRate} onChange={e => setTvaRate(Number(e.target.value))} min={0} max={30} step={0.1}
              className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-24" data-testid="tva-rate" />
          </div>
          <button onClick={saveGlobal} disabled={saving}
            className="px-3 py-1.5 text-xs bg-teal-500/15 text-teal-400 rounded hover:bg-teal-500/25 border border-teal-500/30" data-testid="save-global-btn">
            <Save className="w-3 h-3 inline mr-1" />Sauvegarder
          </button>
        </div>
      </div>

      {/* Per-product pricing table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Pricing par produit</h3>
        <div className="space-y-2 mb-4">
          {(data?.products || []).map(p => (
            <div key={p.product_code} className="flex items-center gap-3 bg-zinc-800/50 rounded-lg px-3 py-2 border border-zinc-700/50">
              <span className="text-xs font-medium text-white w-12">{p.product_code}</span>
              <span className="text-xs text-zinc-300">{p.unit_price_eur} EUR</span>
              <span className="text-xs text-zinc-500">-{p.discount_pct}%</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded border ${p.billing_mode === 'PREPAID' ? 'bg-violet-500/10 text-violet-400 border-violet-500/30' : 'bg-zinc-700/60 text-zinc-300 border-zinc-600'}`}>
                {p.billing_mode}
              </span>
              <div className="flex-1" />
              <button onClick={() => deleteProduct(p.product_code)} className="p-1 text-zinc-500 hover:text-red-400" data-testid={`delete-pricing-${p.product_code}`}>
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
          {(data?.products || []).length === 0 && <p className="text-[10px] text-zinc-600">Aucun pricing produit configuré</p>}
        </div>

        {/* Add product form */}
        <div className="flex gap-2 items-end flex-wrap border-t border-zinc-800 pt-3">
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Produit</label>
            <select value={addProd.product_code} onChange={e => setAddProd(p => ({ ...p, product_code: e.target.value }))}
              className="bg-zinc-800 text-zinc-300 text-xs rounded px-2 py-1.5 border border-zinc-700" data-testid="add-product-select">
              <option value="">-</option>
              {PRODUCTS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Prix HT (EUR)</label>
            <input type="number" value={addProd.unit_price_eur} onChange={e => setAddProd(p => ({ ...p, unit_price_eur: Number(e.target.value) }))}
              className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-20" data-testid="add-price" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Remise %</label>
            <input type="number" value={addProd.discount_pct} onChange={e => setAddProd(p => ({ ...p, discount_pct: Number(e.target.value) }))}
              className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-16" data-testid="add-discount" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Mode</label>
            <select value={addProd.billing_mode} onChange={e => setAddProd(p => ({ ...p, billing_mode: e.target.value }))}
              className="bg-zinc-800 text-zinc-300 text-xs rounded px-2 py-1.5 border border-zinc-700" data-testid="add-billing-mode">
              {BILLING_MODES.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <button onClick={saveProduct} disabled={!addProd.product_code || saving}
            className="px-3 py-1.5 text-xs bg-teal-500/15 text-teal-400 rounded hover:bg-teal-500/25 border border-teal-500/30 disabled:opacity-50" data-testid="add-product-btn">
            <Plus className="w-3 h-3 inline mr-1" />Ajouter
          </button>
        </div>
      </div>

      {/* Prepayment balances */}
      {prepay.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Balances prépaiement</h3>
          <div className="space-y-2 mb-3">
            {prepay.map(b => (
              <div key={b.product_code} className="flex items-center gap-4 text-xs bg-zinc-800/50 rounded-lg px-3 py-2 border border-zinc-700/50">
                <span className="font-medium text-white w-12">{b.product_code}</span>
                <span className="text-zinc-500">Achetées: <span className="text-zinc-300">{b.units_purchased_total}</span></span>
                <span className="text-zinc-500">Livrées: <span className="text-zinc-300">{b.units_delivered_total}</span></span>
                <span className={`font-medium ${b.units_remaining <= 0 ? 'text-red-400' : b.units_remaining <= 10 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  Restantes: {b.units_remaining}
                </span>
              </div>
            ))}
          </div>
          <div className="flex gap-2 items-end border-t border-zinc-800 pt-3">
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Produit</label>
              <select value={prepayUnits.product_code} onChange={e => setPrepayUnits(p => ({ ...p, product_code: e.target.value }))}
                className="bg-zinc-800 text-zinc-300 text-xs rounded px-2 py-1.5 border border-zinc-700" data-testid="prepay-product">
                <option value="">-</option>
                {prepay.map(b => <option key={b.product_code} value={b.product_code}>{b.product_code}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Unités à ajouter</label>
              <input type="number" value={prepayUnits.units_to_add} onChange={e => setPrepayUnits(p => ({ ...p, units_to_add: Number(e.target.value) }))}
                className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-20" data-testid="prepay-units" />
            </div>
            <button onClick={addPrepayUnits} disabled={!prepayUnits.product_code || prepayUnits.units_to_add <= 0}
              className="px-3 py-1.5 text-xs bg-violet-500/15 text-violet-400 rounded hover:bg-violet-500/25 border border-violet-500/30 disabled:opacity-50" data-testid="add-prepay-btn">
              <Plus className="w-3 h-3 inline mr-1" />Ajouter
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function OffersTab({ clientId, authFetch }) {
  const [credits, setCredits] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ order_id: '', product_code: '', week_key: '', quantity_units_free: 0, reason: '', note: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, o1, o2] = await Promise.all([
        authFetch(`${API}/api/clients/${clientId}/credits`),
        authFetch(`${API}/api/commandes?entity=ZR7&active_only=false&client_id=${clientId}`),
        authFetch(`${API}/api/commandes?entity=MDL&active_only=false&client_id=${clientId}`),
      ]);
      if (cRes.ok) { const d = await cRes.json(); setCredits(d.credits || []); }
      const cmds1 = o1.ok ? (await o1.json()).commandes || [] : [];
      const cmds2 = o2.ok ? (await o2.json()).commandes || [] : [];
      setOrders([...cmds1, ...cmds2]);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [clientId, authFetch]);

  useEffect(() => { load(); }, [load]);

  const addCredit = async () => {
    if (!form.week_key || !form.reason || !form.order_id || !form.product_code || form.quantity_units_free <= 0) return;
    const r = await authFetch(`${API}/api/clients/${clientId}/credits`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (r.ok) {
      setForm({ order_id: '', product_code: '', week_key: '', quantity_units_free: 0, reason: '', note: '' });
      load();
    } else { const d = await r.json(); alert(d.detail || 'Erreur'); }
  };

  const deleteCredit = async (creditId) => {
    if (!window.confirm('Supprimer cette offre ?')) return;
    const r = await authFetch(`${API}/api/clients/${clientId}/credits/${creditId}`, { method: 'DELETE' });
    if (r.ok) load();
    else { const d = await r.json(); alert(d.detail || 'Erreur'); }
  };

  if (loading) return <div className="text-zinc-600 text-xs py-4">Chargement...</div>;

  return (
    <div className="space-y-4" data-testid="tab-content-offers">
      {/* Add offer */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Ajouter une offre</h3>
        <div className="flex gap-2 items-end flex-wrap">
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Commande</label>
            <select value={form.order_id} onChange={e => {
              const cmd = orders.find(o => o.id === e.target.value);
              setForm(f => ({ ...f, order_id: e.target.value, product_code: cmd?.produit || f.product_code }));
            }}
              className="bg-zinc-800 text-zinc-300 text-xs rounded px-2 py-1.5 border border-zinc-700 min-w-[180px]" data-testid="offer-order">
              <option value="">Sélectionner</option>
              {orders.map(o => <option key={o.id} value={o.id}>{o.produit} - {o.client_name || o.id.slice(0, 8)} (q:{o.quota_semaine})</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Produit</label>
            <input value={form.product_code} readOnly className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-500 w-16" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Semaine</label>
            <input value={form.week_key} onChange={e => setForm(f => ({ ...f, week_key: e.target.value }))} placeholder="2026-W07"
              className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-28" data-testid="offer-week" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Units offertes</label>
            <input type="number" value={form.quantity_units_free} onChange={e => setForm(f => ({ ...f, quantity_units_free: Number(e.target.value) }))}
              className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-20" data-testid="offer-qty" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Raison</label>
            <select value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
              className="bg-zinc-800 text-zinc-300 text-xs rounded px-2 py-1.5 border border-zinc-700" data-testid="offer-reason">
              <option value="">-</option>
              {CREDIT_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Note</label>
            <input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} placeholder="Commentaire"
              className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 w-36" data-testid="offer-note" />
          </div>
          <button onClick={addCredit} disabled={!form.week_key || !form.reason || !form.order_id || form.quantity_units_free <= 0}
            className="px-3 py-1.5 text-xs bg-teal-500/15 text-teal-400 rounded hover:bg-teal-500/25 border border-teal-500/30 disabled:opacity-50" data-testid="add-offer-btn">
            <Plus className="w-3 h-3 inline mr-1" />Ajouter
          </button>
        </div>
      </div>

      {/* History */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3">Historique offres ({credits.length})</h3>
        <div className="space-y-2">
          {credits.map(c => (
            <div key={c.id} className="flex items-center gap-3 bg-zinc-800/50 rounded-lg px-3 py-2 border border-zinc-700/50">
              <span className="text-xs text-zinc-300 font-mono w-20">{c.week_key}</span>
              <span className="text-xs text-zinc-400">{c.product_code}</span>
              <span className="text-[10px] text-zinc-500">{c.order_id?.slice(0, 8)}</span>
              <span className="text-xs font-medium text-violet-400">{c.quantity_units_free} units</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-300">{c.reason}</span>
              {c.note && <span className="text-[10px] text-zinc-500 truncate max-w-[150px]">{c.note}</span>}
              <div className="flex-1" />
              <span className="text-[10px] text-zinc-600">{c.created_by} - {c.created_at?.slice(0, 10)}</span>
              <button onClick={() => deleteCredit(c.id)} className="p-1 text-zinc-500 hover:text-red-400" data-testid={`delete-credit-${c.id}`}>
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
          {credits.length === 0 && <p className="text-[10px] text-zinc-600">Aucune offre</p>}
        </div>
      </div>
    </div>
  );
}

