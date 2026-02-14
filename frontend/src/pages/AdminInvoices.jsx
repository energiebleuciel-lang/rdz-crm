import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Receipt, Plus, Send, Check, AlertTriangle, ArrowRight, Settings2, RefreshCw, Eye, X } from 'lucide-react';

const STATUS_STYLES = {
  draft: 'bg-zinc-700/30 text-zinc-400 border-zinc-600/30',
  sent: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  paid: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  overdue: 'bg-red-500/15 text-red-400 border-red-500/30',
};

const fmt = (n) => new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n || 0);

// ══════════════════ INTERCOMPANY TAB ══════════════════
function IntercompanyTab({ authFetch, hasPermission, isWriteBlocked }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [weekFilter, setWeekFilter] = useState('');
  const [dirFilter, setDirFilter] = useState('');
  const [detail, setDetail] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [pricing, setPricing] = useState([]);
  const [showPricing, setShowPricing] = useState(false);
  const [editPrice, setEditPrice] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (weekFilter) params.set('week_key', weekFilter);
      if (dirFilter) params.set('direction', dirFilter);
      const res = await authFetch(`${API}/api/intercompany/invoices?${params}`);
      if (res.ok) { const d = await res.json(); setInvoices(d.invoices || []); }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [authFetch, weekFilter, dirFilter]);

  useEffect(() => { load(); }, [load]);

  const loadPricing = async () => {
    const res = await authFetch(`${API}/api/intercompany/pricing`);
    if (res.ok) { const d = await res.json(); setPricing(d.pricing || []); }
  };

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await authFetch(`${API}/api/intercompany/generate-invoices`, { method: 'POST' });
      if (res.ok) { const d = await res.json(); alert(`${d.invoices_created} facture(s) générée(s)`); load(); }
    } catch (e) { console.error(e); }
    setGenerating(false);
  };

  const openDetail = async (inv) => {
    const res = await authFetch(`${API}/api/intercompany/invoices/${inv.id}`);
    if (res.ok) { const d = await res.json(); setDetail(d); }
  };

  const savePricing = async (p) => {
    await authFetch(`${API}/api/intercompany/pricing`, {
      method: 'PUT', body: JSON.stringify(p)
    });
    loadPricing();
    setEditPrice(null);
  };

  const canManage = hasPermission('intercompany.manage') && !isWriteBlocked;
  const canBilling = hasPermission('billing.manage') && !isWriteBlocked;

  // Get unique weeks for filter
  const weeks = [...new Set(invoices.map(i => i.week_key).filter(Boolean))].sort().reverse();

  return (
    <div data-testid="intercompany-tab">
      {/* Toolbar */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <select value={weekFilter} onChange={e => setWeekFilter(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1 text-xs text-zinc-300" data-testid="ic-week-filter">
          <option value="">Toutes semaines</option>
          {weeks.map(w => <option key={w} value={w}>{w}</option>)}
        </select>
        <select value={dirFilter} onChange={e => setDirFilter(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1 text-xs text-zinc-300" data-testid="ic-dir-filter">
          <option value="">Toutes directions</option>
          <option value="ZR7->MDL">ZR7 → MDL</option>
          <option value="MDL->ZR7">MDL → ZR7</option>
        </select>
        <div className="flex-1" />
        <button onClick={() => { setShowPricing(!showPricing); if (!showPricing) loadPricing(); }}
          className="flex items-center gap-1 px-2.5 py-1 text-xs text-zinc-400 hover:text-teal-400 border border-zinc-800 rounded-md hover:border-zinc-700"
          data-testid="ic-pricing-btn">
          <Settings2 className="w-3 h-3" /> Prix
        </button>
        {canBilling && (
          <button onClick={generate} disabled={generating}
            className="flex items-center gap-1 px-3 py-1 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30 disabled:opacity-50"
            data-testid="ic-generate-btn">
            <RefreshCw className={`w-3 h-3 ${generating ? 'animate-spin' : ''}`} /> Générer factures
          </button>
        )}
      </div>

      {/* Pricing panel */}
      {showPricing && (
        <div className="mb-4 bg-zinc-900 border border-zinc-800 rounded-lg p-3" data-testid="ic-pricing-panel">
          <h3 className="text-xs font-medium text-zinc-400 mb-2">Prix intercompany (EUR HT / unité)</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {pricing.map(p => {
              const isEditing = editPrice?.id === p.id;
              return (
                <div key={p.id} className="flex items-center justify-between bg-zinc-800/50 rounded px-2.5 py-1.5 border border-zinc-700/50">
                  <span className="text-[10px] text-zinc-500">{p.from_entity}→{p.to_entity} <span className="text-zinc-400">{p.product}</span></span>
                  {isEditing ? (
                    <div className="flex items-center gap-1">
                      <input type="number" step="0.5" defaultValue={p.unit_price_ht}
                        onKeyDown={e => { if (e.key === 'Enter') savePricing({ ...p, unit_price_ht: Number(e.target.value) }); }}
                        className="w-16 bg-zinc-700 border border-zinc-600 rounded px-1.5 py-0.5 text-xs text-zinc-200 text-right" autoFocus />
                      <button onClick={() => setEditPrice(null)} className="text-zinc-500"><X className="w-3 h-3" /></button>
                    </div>
                  ) : (
                    <button onClick={() => canManage && setEditPrice(p)} className={`text-xs font-medium ${canManage ? 'text-teal-400 hover:text-teal-300' : 'text-zinc-400'}`}>
                      {p.unit_price_ht} €
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Invoice table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-xs" data-testid="ic-invoices-table">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-500">
              <th className="text-left px-3 py-2.5 font-medium">N°</th>
              <th className="text-left px-3 py-2.5 font-medium">Semaine</th>
              <th className="text-left px-3 py-2.5 font-medium">Direction</th>
              <th className="text-right px-3 py-2.5 font-medium">Transfers</th>
              <th className="text-right px-3 py-2.5 font-medium">Total HT</th>
              <th className="text-left px-3 py-2.5 font-medium">Status</th>
              <th className="text-right px-3 py-2.5 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
            ) : invoices.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-8 text-zinc-600">Aucune facture intercompany</td></tr>
            ) : invoices.map(inv => (
              <tr key={inv.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`ic-inv-${inv.id}`}>
                <td className="px-3 py-2 text-zinc-300 font-mono text-[10px]">{inv.invoice_number}</td>
                <td className="px-3 py-2 text-zinc-400">{inv.week_key}</td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-1.5 text-zinc-300">
                    <span className={`text-[10px] font-bold px-1 py-0.5 rounded ${inv.from_entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{inv.from_entity}</span>
                    <ArrowRight className="w-3 h-3 text-zinc-600" />
                    <span className={`text-[10px] font-bold px-1 py-0.5 rounded ${inv.to_entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{inv.to_entity}</span>
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-zinc-400">{inv.transfer_ids?.length || 0}</td>
                <td className="px-3 py-2 text-right text-zinc-200 font-medium">{fmt(inv.amount_ht)}</td>
                <td className="px-3 py-2">
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${STATUS_STYLES[inv.status] || STATUS_STYLES.draft}`}>{inv.status}</span>
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => openDetail(inv)} className="p-1 text-zinc-500 hover:text-teal-400 rounded" data-testid={`ic-detail-${inv.id}`}>
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="ic-detail-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-3xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">{detail.invoice?.invoice_number}</h2>
              <button onClick={() => setDetail(null)} className="text-zinc-500 hover:text-zinc-300"><X className="w-4 h-4" /></button>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-4 text-xs">
              <div className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500">Direction</span>
                <p className="text-zinc-200 mt-0.5">{detail.invoice?.from_entity} → {detail.invoice?.to_entity}</p>
              </div>
              <div className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500">Total HT</span>
                <p className="text-zinc-200 mt-0.5 font-medium">{fmt(detail.invoice?.amount_ht)} EUR</p>
              </div>
              <div className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500">Semaine</span>
                <p className="text-zinc-200 mt-0.5">{detail.invoice?.week_key}</p>
              </div>
            </div>
            {/* Line items */}
            {detail.invoice?.line_items?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Lignes</h3>
                <div className="space-y-1">
                  {detail.invoice.line_items.map((li, i) => (
                    <div key={i} className="flex items-center justify-between bg-zinc-800/30 rounded px-2.5 py-1.5 text-xs">
                      <span className="text-zinc-300">{li.product}</span>
                      <span className="text-zinc-400">{li.qty} x {li.unit_price_ht} € = <span className="text-zinc-200 font-medium">{fmt(li.total_ht)} €</span></span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {/* Transfer details */}
            <h3 className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Transferts ({detail.transfers?.length})</h3>
            <div className="bg-zinc-800/30 rounded-lg overflow-hidden">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="border-b border-zinc-700 text-zinc-500">
                    <th className="text-left px-2 py-1.5">Delivery ID</th>
                    <th className="text-left px-2 py-1.5">Lead ID</th>
                    <th className="text-left px-2 py-1.5">Produit</th>
                    <th className="text-right px-2 py-1.5">Prix HT</th>
                    <th className="text-left px-2 py-1.5">Mode</th>
                    <th className="text-left px-2 py-1.5">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {(detail.transfers || []).map(t => (
                    <tr key={t.id} className="border-b border-zinc-800/50">
                      <td className="px-2 py-1.5 text-zinc-400 font-mono">{t.delivery_id?.slice(0, 12)}...</td>
                      <td className="px-2 py-1.5 text-zinc-400 font-mono">{t.lead_id?.slice(0, 12)}...</td>
                      <td className="px-2 py-1.5 text-zinc-300">{t.product}</td>
                      <td className="px-2 py-1.5 text-right text-zinc-300">{t.unit_price_ht} €</td>
                      <td className="px-2 py-1.5">
                        <span className={`text-[9px] px-1 py-0.5 rounded ${t.routing_mode === 'fallback_no_orders' ? 'bg-amber-500/15 text-amber-400' : 'bg-zinc-700/50 text-zinc-400'}`}>
                          {t.routing_mode || 'normal'}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 text-zinc-500">{t.created_at?.slice(0, 16).replace('T', ' ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════ MAIN PAGE ══════════════════
export default function AdminInvoices() {
  const { authFetch, hasPermission, isWriteBlocked, entityScope } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [overdue, setOverdue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('list');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [clients, setClients] = useState([]);
  const [form, setForm] = useState({ client_id: '', amount_ht: '', description: '' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = statusFilter ? `?status=${statusFilter}` : '';
      const [invRes, odRes] = await Promise.all([
        authFetch(`${API}/api/invoices${params}`),
        authFetch(`${API}/api/invoices/overdue-dashboard`),
      ]);
      if (invRes.ok) { const d = await invRes.json(); setInvoices(d.invoices || []); }
      if (odRes.ok) { const d = await odRes.json(); setOverdue(d); }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [authFetch, statusFilter, entityScope]);

  useEffect(() => { load(); }, [load]);

  const loadClients = async () => {
    try {
      const ents = entityScope === 'BOTH' ? ['ZR7', 'MDL'] : [entityScope || 'ZR7'];
      const results = await Promise.all(ents.map(e => authFetch(`${API}/api/clients?entity=${e}`)));
      let all = [];
      for (const r of results) { if (r.ok) { const d = await r.json(); all = all.concat(d.clients || []); } }
      setClients(all);
    } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      const client = clients.find(c => c.id === form.client_id);
      const res = await authFetch(`${API}/api/invoices`, {
        method: 'POST', body: JSON.stringify({ client_id: form.client_id, amount_ht: Number(form.amount_ht), description: form.description, entity: client?.entity })
      });
      if (res.ok) { setShowCreate(false); load(); }
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const sendInvoice = async (id) => { await authFetch(`${API}/api/invoices/${id}/send`, { method: 'POST' }); load(); };
  const markPaid = async (id) => { await authFetch(`${API}/api/invoices/${id}/mark-paid`, { method: 'POST' }); load(); };

  const canManage = hasPermission('billing.manage') && !isWriteBlocked;
  const hasIntercompany = hasPermission('intercompany.view');

  const TABS = [
    { key: 'list', label: 'Clients' },
    { key: 'overdue', label: 'Impayées', badge: overdue?.client_count > 0 ? overdue.client_count : null },
    ...(hasIntercompany ? [{ key: 'intercompany', label: 'Intercompany' }] : []),
  ];

  return (
    <div data-testid="admin-invoices">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white flex items-center gap-2">
          <Receipt className="w-5 h-5 text-teal-400" /> Factures
        </h1>
        <div className="flex gap-2 items-center">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-3 py-1 text-xs rounded-md border transition-colors ${tab === t.key ? 'bg-teal-500/15 text-teal-400 border-teal-500/30' : 'text-zinc-500 border-zinc-800 hover:border-zinc-700'}`}
              data-testid={`tab-${t.key}`}>
              {t.label}
              {t.badge && <span className="ml-1.5 px-1 py-0.5 text-[9px] bg-red-500/20 text-red-400 rounded">{t.badge}</span>}
            </button>
          ))}
          {tab === 'list' && canManage && (
            <button onClick={() => { setShowCreate(true); loadClients(); }}
              className="flex items-center gap-1 px-3 py-1 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30"
              data-testid="create-invoice-btn">
              <Plus className="w-3 h-3" /> Nouvelle facture
            </button>
          )}
        </div>
      </div>

      {/* Intercompany Tab */}
      {tab === 'intercompany' && (
        <IntercompanyTab authFetch={authFetch} hasPermission={hasPermission} isWriteBlocked={isWriteBlocked} />
      )}

      {/* Overdue banner */}
      {overdue && overdue.total_overdue_ttc > 0 && tab === 'list' && (
        <div className="mb-4 px-4 py-2.5 bg-red-500/5 border border-red-500/20 rounded-lg flex items-center gap-3" data-testid="overdue-banner">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span className="text-xs text-red-300">
            <strong>{overdue.client_count}</strong> client{overdue.client_count > 1 ? 's' : ''} avec factures impayées — Total: <strong>{fmt(overdue.total_overdue_ttc)} EUR TTC</strong>
          </span>
        </div>
      )}

      {/* Overdue Tab */}
      {tab === 'overdue' && (
        <div className="space-y-3" data-testid="overdue-dashboard">
          {!overdue || overdue.client_count === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8 text-center text-zinc-600 text-xs">Aucune facture impayée</div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">Clients en retard</p>
                  <p className="text-2xl font-semibold text-red-400 mt-1">{overdue.client_count}</p>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">Total impayé TTC</p>
                  <p className="text-2xl font-semibold text-red-400 mt-1">{fmt(overdue.total_overdue_ttc)} EUR</p>
                </div>
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">Factures impayées</p>
                  <p className="text-2xl font-semibold text-amber-400 mt-1">{overdue.clients?.reduce((a, c) => a + c.invoice_count, 0) || 0}</p>
                </div>
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
                <table className="w-full text-xs" data-testid="overdue-table">
                  <thead><tr className="border-b border-zinc-800 text-zinc-500">
                    <th className="text-left px-3 py-2.5 font-medium">Client</th>
                    <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                    <th className="text-left px-3 py-2.5 font-medium">Factures</th>
                    <th className="text-right px-3 py-2.5 font-medium">Total HT</th>
                    <th className="text-right px-3 py-2.5 font-medium">Total TTC</th>
                    <th className="text-right px-3 py-2.5 font-medium">Retard</th>
                  </tr></thead>
                  <tbody>{overdue.clients?.map(c => (
                    <tr key={c.client_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                      <td className="px-3 py-2 text-zinc-300">{c.client_name}</td>
                      <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{c.entity}</span></td>
                      <td className="px-3 py-2 text-zinc-400">{c.invoice_count}</td>
                      <td className="px-3 py-2 text-right text-zinc-400">{fmt(c.total_ht)}</td>
                      <td className="px-3 py-2 text-right text-red-400 font-medium">{fmt(c.total_ttc)}</td>
                      <td className="px-3 py-2 text-right"><span className={`text-[10px] px-1.5 py-0.5 rounded ${c.days_overdue > 30 ? 'bg-red-500/15 text-red-400' : 'bg-amber-500/15 text-amber-400'}`}>{c.days_overdue}j</span></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* Invoice list Tab */}
      {tab === 'list' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <div className="flex gap-1 px-3 py-2 border-b border-zinc-800">
            {['', 'draft', 'sent', 'paid', 'overdue'].map(s => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={`px-2 py-0.5 text-[10px] rounded-full border transition-colors ${statusFilter === s ? 'bg-teal-500/20 text-teal-400 border-teal-500/40' : 'text-zinc-500 border-zinc-800 hover:border-zinc-700'}`}>
                {s || 'Toutes'}
              </button>
            ))}
          </div>
          <table className="w-full text-xs" data-testid="invoices-table">
            <thead><tr className="border-b border-zinc-800 text-zinc-500">
              <th className="text-left px-3 py-2.5 font-medium">N°</th>
              <th className="text-left px-3 py-2.5 font-medium">Client</th>
              <th className="text-left px-3 py-2.5 font-medium">Entity</th>
              <th className="text-right px-3 py-2.5 font-medium">HT</th>
              <th className="text-right px-3 py-2.5 font-medium">TVA</th>
              <th className="text-right px-3 py-2.5 font-medium">TTC</th>
              <th className="text-left px-3 py-2.5 font-medium">Status</th>
              <th className="text-left px-3 py-2.5 font-medium">Émise</th>
              <th className="text-left px-3 py-2.5 font-medium">Échéance</th>
              {canManage && <th className="text-right px-3 py-2.5 font-medium">Actions</th>}
            </tr></thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Chargement...</td></tr>
              ) : invoices.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-8 text-zinc-600">Aucune facture</td></tr>
              ) : invoices.map(inv => (
                <tr key={inv.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`invoice-row-${inv.id}`}>
                  <td className="px-3 py-2 text-zinc-300 font-mono text-[10px]">{inv.invoice_number}</td>
                  <td className="px-3 py-2 text-zinc-300">{inv.client_name}</td>
                  <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${inv.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{inv.entity}</span></td>
                  <td className="px-3 py-2 text-right text-zinc-300">{fmt(inv.amount_ht)}</td>
                  <td className="px-3 py-2 text-right text-zinc-500">{inv.vat_rate}%</td>
                  <td className="px-3 py-2 text-right text-zinc-200 font-medium">{fmt(inv.amount_ttc)}</td>
                  <td className="px-3 py-2"><span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${STATUS_STYLES[inv.status] || STATUS_STYLES.draft}`}>{inv.status}</span></td>
                  <td className="px-3 py-2 text-zinc-500">{inv.issued_at?.slice(0, 10)}</td>
                  <td className="px-3 py-2 text-zinc-500">{inv.due_at?.slice(0, 10)}</td>
                  {canManage && (
                    <td className="px-3 py-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {inv.status === 'draft' && <button onClick={() => sendInvoice(inv.id)} className="p-1 text-blue-400 hover:bg-zinc-800 rounded" title="Envoyer"><Send className="w-3.5 h-3.5" /></button>}
                        {(inv.status === 'sent' || inv.status === 'overdue') && <button onClick={() => markPaid(inv.id)} className="p-1 text-emerald-400 hover:bg-zinc-800 rounded" title="Marquer payé"><Check className="w-3.5 h-3.5" /></button>}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="create-invoice-modal">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-sm font-semibold text-white mb-4">Nouvelle Facture</h2>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Client</label>
                <select value={form.client_id} onChange={e => setForm(f => ({...f, client_id: e.target.value}))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="invoice-client">
                  <option value="">Choisir...</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.name} ({c.entity}) — TVA {c.vat_rate ?? 20}%</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Montant HT (EUR)</label>
                <input type="number" step="0.01" value={form.amount_ht} onChange={e => setForm(f => ({...f, amount_ht: e.target.value}))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="invoice-amount" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Description</label>
                <input value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="invoice-description" />
              </div>
              {form.client_id && form.amount_ht && (() => {
                const cl = clients.find(c => c.id === form.client_id);
                const vat = cl?.vat_rate ?? 20;
                const ttc = Number(form.amount_ht) * (1 + vat / 100);
                return (
                  <div className="bg-zinc-800/50 rounded-md px-3 py-2 text-xs flex justify-between">
                    <span className="text-zinc-500">TTC estimé ({vat}% TVA)</span>
                    <span className="text-zinc-200 font-medium">{fmt(ttc)} EUR</span>
                  </div>
                );
              })()}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-xs text-zinc-400">Annuler</button>
              <button onClick={handleCreate} disabled={saving || !form.client_id || !form.amount_ht}
                className="px-3 py-1.5 text-xs bg-teal-500/20 text-teal-400 rounded-md hover:bg-teal-500/30 border border-teal-500/30 disabled:opacity-50"
                data-testid="submit-invoice-btn">Créer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
