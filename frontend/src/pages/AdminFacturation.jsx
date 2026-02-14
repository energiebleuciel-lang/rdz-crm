import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Link } from 'react-router-dom';
import {
  RefreshCw, Receipt, AlertTriangle, CreditCard,
  FileText, DollarSign, TrendingUp, Package, Check, X, Edit3
} from 'lucide-react';
import { getCurrentWeekKey, shiftWeekKey } from '../lib/weekUtils';
import { WeekNavStandard } from '../components/WeekNav';

const REC_STATUS = {
  not_invoiced: { label: 'Non facturé', cls: 'bg-zinc-700/60 text-zinc-300 border-zinc-600' },
  invoiced: { label: 'Facturé', cls: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  paid: { label: 'Payé', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  overdue: { label: 'Impayé', cls: 'bg-red-500/15 text-red-400 border-red-500/30' },
};
const PREPAID_STATUS = {
  OK: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  LOW: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  BLOCKED: 'bg-red-500/15 text-red-400 border-red-500/30',
};

function StatusPill({ status, map }) {
  const cfg = map[status] || { label: status, cls: 'bg-zinc-800 text-zinc-400 border-zinc-700' };
  return <span className={`text-[10px] px-2 py-0.5 rounded-full border whitespace-nowrap ${cfg.cls}`}>{cfg.label || status}</span>;
}

function KpiCard({ label, value, sub, icon: Icon, color = 'text-white' }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon className="w-3.5 h-3.5 text-zinc-500" />}
        <p className="text-[10px] text-zinc-500">{label}</p>
      </div>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      {sub && <p className="text-[10px] text-zinc-500 mt-0.5">{sub}</p>}
    </div>
  );
}

/* Inline edit row for external tracking */
function EditRow({ record, authFetch, onDone }) {
  const [form, setForm] = useState({
    external_invoice_number: record.external_invoice_number || '',
    external_invoice_ttc: record.external_invoice_ttc || '',
    status: record.status || 'not_invoiced',
    due_date: record.due_date || '',
    paid_at: record.paid_at || '',
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    const body = {};
    if (form.external_invoice_number) body.external_invoice_number = form.external_invoice_number;
    if (form.external_invoice_ttc) body.external_invoice_ttc = Number(form.external_invoice_ttc);
    if (form.status) body.status = form.status;
    if (form.due_date) body.due_date = form.due_date;
    if (form.paid_at) body.paid_at = form.paid_at;
    if (form.status === 'invoiced' && !record.issued_at) body.issued_at = new Date().toISOString();
    try {
      await authFetch(`${API}/api/billing/records/${record.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      onDone();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  return (
    <tr className="bg-zinc-800/60 border-b border-zinc-700">
      <td colSpan={14} className="px-3 py-2">
        <div className="flex items-center gap-3 flex-wrap">
          <div>
            <label className="text-[9px] text-zinc-500 block">N facture ext.</label>
            <input value={form.external_invoice_number} onChange={e => setForm(f => ({ ...f, external_invoice_number: e.target.value }))}
              className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300 w-28" data-testid="edit-ext-number" />
          </div>
          <div>
            <label className="text-[9px] text-zinc-500 block">TTC ext. (EUR)</label>
            <input type="number" value={form.external_invoice_ttc} onChange={e => setForm(f => ({ ...f, external_invoice_ttc: e.target.value }))}
              className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300 w-20" data-testid="edit-ext-ttc" />
          </div>
          <div>
            <label className="text-[9px] text-zinc-500 block">Statut</label>
            <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
              className="bg-zinc-900 text-zinc-300 text-xs rounded px-2 py-1 border border-zinc-700" data-testid="edit-status">
              {Object.entries(REC_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[9px] text-zinc-500 block">Échéance</label>
            <input type="date" value={form.due_date?.slice(0, 10) || ''} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
              className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300" data-testid="edit-due-date" />
          </div>
          <div>
            <label className="text-[9px] text-zinc-500 block">Payé le</label>
            <input type="date" value={form.paid_at?.slice(0, 10) || ''} onChange={e => setForm(f => ({ ...f, paid_at: e.target.value }))}
              className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300" data-testid="edit-paid-at" />
          </div>
          <button onClick={save} disabled={saving} className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded border border-emerald-500/30" data-testid="save-record-btn">
            <Check className="w-3.5 h-3.5" />
          </button>
          <button onClick={onDone} className="p-1.5 text-zinc-400 hover:bg-zinc-700 rounded border border-zinc-700">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function AdminFacturation() {
  const { authFetch } = useAuth();
  const [week, setWeek] = useState(getCurrentWeekKey());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [editingId, setEditingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch(`${API}/api/billing/week?week_key=${week}`);
      if (r.ok) setData(await r.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [week, authFetch]);

  useEffect(() => { load(); }, [load]);

  const handleWeekNav = (dir) => setWeek(w => shiftWeekKey(w, dir));

  const buildLedger = async () => {
    setActionLoading('ledger');
    try {
      const r = await authFetch(`${API}/api/billing/week/${week}/build-ledger`, { method: 'POST' });
      if (!r.ok) { const d = await r.json(); alert(d.detail || 'Erreur'); }
      else { load(); }
    } catch (e) { alert(e.message); }
    setActionLoading('');
  };

  const s = data?.summary || {};
  const t = data?.totals || {};

  return (
    <div data-testid="admin-facturation">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <Receipt className="w-5 h-5 text-teal-400" />
          <h1 className="text-lg font-semibold text-white">Facturation</h1>
          {data?.has_records && <span className="text-[10px] bg-emerald-500/15 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/30">Ledger construit</span>}
          {data && !data.has_records && <span className="text-[10px] bg-zinc-700/60 text-zinc-400 px-2 py-0.5 rounded-full border border-zinc-600">Aperçu</span>}
        </div>
        <div className="flex items-center gap-2">
          <WeekNavStandard week={week} onChange={handleWeekNav} />
          <button onClick={load} className="p-1.5 bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="refresh-btn">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-16 justify-center text-zinc-500 text-xs">
          <RefreshCw className="w-4 h-4 animate-spin" /> Chargement...
        </div>
      ) : data ? (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-5">
            <KpiCard label="Leads produits" value={s.leads_produced ?? 0} icon={Package} />
            <KpiCard label="Units livrées" value={s.units_delivered ?? 0} icon={TrendingUp} />
            <KpiCard label="Units billable" value={s.units_billable ?? 0} icon={DollarSign} color="text-emerald-400" />
            <KpiCard label="Non-billable" value={s.units_non_billable ?? 0} icon={AlertTriangle} color="text-amber-400" />
            <KpiCard label="CA HT net" value={`${(t.net_ht || 0).toFixed(2)} EUR`} icon={CreditCard} color="text-teal-400" />
            <KpiCard label="CA TTC" value={`${(t.ttc || 0).toFixed(2)} EUR`} icon={Receipt} color="text-white" />
          </div>

          {/* Build Ledger action */}
          <div className="flex gap-2 mb-5">
            <button onClick={buildLedger} disabled={!!actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-teal-500/15 text-teal-400 rounded-md hover:bg-teal-500/25 border border-teal-500/30 disabled:opacity-50" data-testid="build-ledger-btn">
              {actionLoading === 'ledger' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
              {data.has_records ? 'Reconstruire Ledger' : 'Construire Ledger'}
            </button>
          </div>

          {/* WEEKLY INVOICE TABLE */}
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Receipt className="w-4 h-4 text-teal-400" /> Facturation hebdomadaire
            <span className="text-[10px] text-zinc-500 font-normal">({(data.weekly_invoice || []).length} lignes)</span>
          </h2>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto mb-6">
            <table className="w-full text-xs" data-testid="weekly-invoice-table">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                  <th className="text-left px-3 py-2 font-medium">Client</th>
                  <th className="px-2 py-2 font-medium">Produit</th>
                  <th className="text-right px-2 py-2 font-medium">Billable</th>
                  <th className="text-right px-2 py-2 font-medium">Leads</th>
                  <th className="text-right px-2 py-2 font-medium">LB</th>
                  <th className="text-right px-2 py-2 font-medium">Offerts</th>
                  <th className="text-right px-2 py-2 font-medium">Facturés</th>
                  <th className="text-right px-2 py-2 font-medium">Prix HT</th>
                  <th className="text-right px-2 py-2 font-medium">Remise</th>
                  <th className="text-right px-2 py-2 font-medium">HT net</th>
                  <th className="text-right px-2 py-2 font-medium">TVA</th>
                  <th className="text-right px-2 py-2 font-medium">TTC</th>
                  <th className="px-2 py-2 font-medium text-center">Statut</th>
                  <th className="px-2 py-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {(data.weekly_invoice || []).map((r, i) => {
                  const isEditing = editingId === r.id;
                  return isEditing ? (
                    <EditRow key={r.id} record={r} authFetch={authFetch} onDone={() => { setEditingId(null); load(); }} />
                  ) : (
                    <tr key={i} className={`border-b border-zinc-800/50 hover:bg-zinc-800/30 ${r.pricing_missing ? 'bg-red-500/5' : ''}`}
                      data-testid={`billing-row-${r.client_id}-${r.product_code}`}>
                      <td className="px-3 py-2">
                        <Link to={`/admin/clients/${r.client_id}`} className="text-teal-400 hover:underline font-medium text-xs">
                          {r.client_name || r.client_id?.slice(0, 8)}
                        </Link>
                        {r.external_invoice_number && (
                          <div className="text-[9px] text-zinc-500 mt-0.5">{r.external_invoice_number}</div>
                        )}
                        {r.pricing_missing && (
                          <div className="flex items-center gap-1 mt-0.5">
                            <AlertTriangle className="w-2.5 h-2.5 text-red-400" />
                            <span className="text-[9px] text-red-400">Pricing manquant</span>
                          </div>
                        )}
                      </td>
                      <td className="px-2 py-2 text-center"><span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">{r.product_code}</span></td>
                      <td className="px-2 py-2 text-right text-zinc-300 font-medium">{r.units_billable}</td>
                      <td className="px-2 py-2 text-right text-zinc-400">{r.units_leads ?? '-'}</td>
                      <td className="px-2 py-2 text-right text-zinc-400">{r.units_lb ?? '-'}</td>
                      <td className="px-2 py-2 text-right text-violet-400">{r.units_free || 0}</td>
                      <td className="px-2 py-2 text-right text-white font-medium">{r.units_invoiced}</td>
                      <td className="px-2 py-2 text-right text-zinc-300">{(r.unit_price_ht_snapshot ?? r.unit_price_eur ?? 0)} EUR</td>
                      <td className="px-2 py-2 text-right text-zinc-400">{(r.discount_pct_snapshot ?? r.discount_pct ?? 0)}%</td>
                      <td className="px-2 py-2 text-right text-teal-400 font-medium">{(r.net_total_ht ?? 0).toFixed(2)}</td>
                      <td className="px-2 py-2 text-right text-zinc-400">{(r.vat_amount ?? 0).toFixed(2)}</td>
                      <td className="px-2 py-2 text-right text-white font-medium">{(r.total_ttc_expected ?? 0).toFixed(2)}</td>
                      <td className="px-2 py-2 text-center"><StatusPill status={r.status || 'not_invoiced'} map={REC_STATUS} /></td>
                      <td className="px-2 py-2">
                        {r.id && !r.is_preview && (
                          <button onClick={() => setEditingId(r.id)} title="Suivi externe"
                            className="p-1 text-zinc-400 hover:text-teal-400 hover:bg-teal-500/10 rounded" data-testid={`edit-${r.id}`}>
                            <Edit3 className="w-3 h-3" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {(data.weekly_invoice || []).length === 0 && (
                  <tr><td colSpan={14} className="px-3 py-8 text-center text-zinc-500">Aucune facturation cette semaine</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* PREPAID SECTION */}
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-violet-400" /> Prépaiement
            <span className="text-[10px] text-zinc-500 font-normal">({(data.prepaid || []).length} lignes)</span>
          </h2>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto">
            <table className="w-full text-xs" data-testid="prepaid-table">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                  <th className="text-left px-3 py-2 font-medium">Client</th>
                  <th className="px-2 py-2 font-medium">Produit</th>
                  <th className="text-right px-2 py-2 font-medium">Billable sem.</th>
                  <th className="text-right px-2 py-2 font-medium">Achetées total</th>
                  <th className="text-right px-2 py-2 font-medium">Livrées total</th>
                  <th className="text-right px-2 py-2 font-medium">Restantes</th>
                  <th className="px-2 py-2 font-medium text-center">Statut</th>
                </tr>
              </thead>
              <tbody>
                {(data.prepaid || []).map((r, i) => (
                  <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`prepaid-row-${r.client_id}-${r.product_code}`}>
                    <td className="px-3 py-2">
                      <Link to={`/admin/clients/${r.client_id}`} className="text-teal-400 hover:underline font-medium">{r.client_name || r.client_id?.slice(0, 8)}</Link>
                    </td>
                    <td className="px-2 py-2 text-center"><span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">{r.product_code}</span></td>
                    <td className="px-2 py-2 text-right text-zinc-300">{r.units_billable ?? 0}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.prepaid_purchased ?? 0}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.prepaid_delivered ?? 0}</td>
                    <td className={`px-2 py-2 text-right font-medium ${(r.prepaid_remaining ?? 0) <= 0 ? 'text-red-400' : (r.prepaid_remaining ?? 0) <= 10 ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {r.prepaid_remaining ?? 0}
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${PREPAID_STATUS[r.prepaid_status] || PREPAID_STATUS.OK}`}>{r.prepaid_status || 'OK'}</span>
                    </td>
                  </tr>
                ))}
                {(data.prepaid || []).length === 0 && (
                  <tr><td colSpan={7} className="px-3 py-8 text-center text-zinc-500">Aucun client prépayé</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="text-zinc-500 text-sm py-12 text-center">Aucune donnée</div>
      )}
    </div>
  );
}
