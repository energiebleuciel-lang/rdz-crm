import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Link } from 'react-router-dom';
import {
  RefreshCw, Receipt, AlertTriangle, CreditCard,
  FileText, DollarSign, TrendingUp, Package, Check, X, Edit3,
  Plus, ArrowRightLeft, Users
} from 'lucide-react';
import { getCurrentWeekKey, shiftWeekKey, getCurrentMonthKey, shiftMonthKey } from '../lib/weekUtils';
import { WeekNavStandard, MonthNavStandard } from '../components/WeekNav';

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

function UnitsDisplay({ total, lb }) {
  if (!lb) return <span>{total}</span>;
  return <span>{total} <span className="text-zinc-500 text-[10px]">(LB: {lb})</span></span>;
}

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
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
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

function CreateClientModal({ authFetch, onClose, onCreated }) {
  const [form, setForm] = useState({ entity: 'ZR7', name: '', email: '', delivery_emails: '', billing_mode: 'WEEKLY_INVOICE', tva_enabled: true, tva_rate: 20 });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    if (!form.name || !form.email) { setError('Nom et email requis'); return; }
    setSaving(true);
    setError('');
    try {
      const body = {
        entity: form.entity, name: form.name, email: form.email,
        delivery_emails: form.delivery_emails.split(',').map(s => s.trim()).filter(Boolean),
        auto_send_enabled: true, default_prix_lead: 0, remise_percent: 0,
      };
      const r = await authFetch(`${API}/api/clients`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!r.ok) { const d = await r.json(); setError(d.detail || 'Erreur'); setSaving(false); return; }
      const created = await r.json();
      const clientId = created.client?.id;
      if (clientId) {
        await authFetch(`${API}/api/clients/${clientId}/pricing`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ discount_pct_global: 0, tva_rate: form.tva_enabled ? form.tva_rate : 0 }),
        });
      }
      onCreated(created.client);
      onClose();
    } catch (e) { setError(e.message); }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" data-testid="create-client-modal">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-full max-w-md">
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2"><Users className="w-4 h-4 text-teal-400" /> Nouveau Client</h2>
        {error && <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-3 py-1.5 mb-3">{error}</div>}
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Entity</label>
              <select value={form.entity} onChange={e => setForm(f => ({ ...f, entity: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="new-client-entity">
                <option value="ZR7">ZR7</option><option value="MDL">MDL</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Billing mode</label>
              <select value={form.billing_mode} onChange={e => setForm(f => ({ ...f, billing_mode: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="new-client-billing-mode">
                <option value="WEEKLY_INVOICE">Facturation hebdo</option><option value="PREPAID">Prépaiement</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Nom</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="new-client-name" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Email principal</label>
            <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" data-testid="new-client-email" />
          </div>
          <div>
            <label className="text-[10px] text-zinc-500 block mb-1">Emails livraison (virgule)</label>
            <input value={form.delivery_emails} onChange={e => setForm(f => ({ ...f, delivery_emails: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300" placeholder="a@b.com, c@d.com" data-testid="new-client-delivery-emails" />
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-zinc-300">
              <input type="checkbox" checked={form.tva_enabled} onChange={e => setForm(f => ({ ...f, tva_enabled: e.target.checked }))}
                className="rounded bg-zinc-800 border-zinc-700" data-testid="new-client-tva-toggle" /> TVA
            </label>
            {form.tva_enabled && (
              <div className="flex items-center gap-1">
                <input type="number" value={form.tva_rate} onChange={e => setForm(f => ({ ...f, tva_rate: Number(e.target.value) }))}
                  className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300 w-16" data-testid="new-client-tva-rate" />
                <span className="text-[10px] text-zinc-500">%</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 text-xs text-zinc-400">Annuler</button>
          <button onClick={submit} disabled={saving || !form.name || !form.email}
            className="px-3 py-1.5 text-xs bg-teal-500/20 text-teal-400 rounded-md hover:bg-teal-500/30 border border-teal-500/30 disabled:opacity-50" data-testid="create-client-submit">
            Créer
          </button>
        </div>
      </div>
    </div>
  );
}

function InterEditRow({ record, authFetch, onDone }) {
  const [form, setForm] = useState({
    external_invoice_number: record.external_invoice_number || '',
    status: record.status || 'not_invoiced',
    paid_at: record.paid_at || '',
  });
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    const body = {};
    if (form.external_invoice_number) body.external_invoice_number = form.external_invoice_number;
    if (form.status) body.status = form.status;
    if (form.paid_at) body.paid_at = form.paid_at;
    if (form.status === 'invoiced' && !record.issued_at) body.issued_at = new Date().toISOString();
    await authFetch(`${API}/api/billing/interfacturation/${record.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    onDone();
    setSaving(false);
  };
  return (
    <tr className="bg-zinc-800/60 border-b border-zinc-700">
      <td colSpan={10} className="px-3 py-2">
        <div className="flex items-center gap-3 flex-wrap">
          <div>
            <label className="text-[9px] text-zinc-500 block">N facture interne</label>
            <input value={form.external_invoice_number} onChange={e => setForm(f => ({ ...f, external_invoice_number: e.target.value }))}
              className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300 w-28" data-testid="inter-edit-number" />
          </div>
          <div>
            <label className="text-[9px] text-zinc-500 block">Statut</label>
            <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
              className="bg-zinc-900 text-zinc-300 text-xs rounded px-2 py-1 border border-zinc-700" data-testid="inter-edit-status">
              {Object.entries(REC_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[9px] text-zinc-500 block">Payé le</label>
            <input type="date" value={form.paid_at?.slice(0, 10) || ''} onChange={e => setForm(f => ({ ...f, paid_at: e.target.value }))}
              className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-300" />
          </div>
          <button onClick={save} disabled={saving} className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded border border-emerald-500/30"><Check className="w-3.5 h-3.5" /></button>
          <button onClick={onDone} className="p-1.5 text-zinc-400 hover:bg-zinc-700 rounded border border-zinc-700"><X className="w-3.5 h-3.5" /></button>
        </div>
      </td>
    </tr>
  );
}

function MonthView({ authFetch }) {
  const [month, setMonth] = useState(getCurrentMonthKey());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch(`${API}/api/billing/month-summary?month=${month}`);
      if (r.ok) setData(await r.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [month, authFetch]);

  useEffect(() => { load(); }, [load]);
  const handleMonthNav = (dir) => setMonth(m => shiftMonthKey(m, dir));

  const s = data?.summary || {};
  const t = data?.totals || {};

  return (
    <div data-testid="month-view">
      <div className="flex items-center justify-between mb-5">
        <MonthNavStandard month={month} onChange={handleMonthNav} />
        {data && <span className="text-[10px] text-zinc-500">{(data.weeks_in_month || []).length} semaines</span>}
        <button onClick={load} className="p-1.5 bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="month-refresh-btn">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-16 justify-center text-zinc-500 text-xs"><RefreshCw className="w-4 h-4 animate-spin" /> Chargement...</div>
      ) : data ? (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-5">
            <KpiCard label="Units total" value={<UnitsDisplay total={s.units_delivered ?? 0} lb={s.total_lb} />} icon={Package} />
            <KpiCard label="Leads total" value={s.total_leads ?? 0} icon={TrendingUp} />
            <KpiCard label="LB total" value={s.total_lb ?? 0} icon={TrendingUp} color="text-violet-400" />
            <KpiCard label="Units billable" value={<UnitsDisplay total={s.units_billable ?? 0} lb={s.billable_lb} />} icon={DollarSign} color="text-emerald-400" />
            <KpiCard label="Non-billable" value={s.units_non_billable ?? 0} icon={AlertTriangle} color="text-amber-400" />
            <KpiCard label="CA HT net" value={`${(t.net_ht || 0).toFixed(2)} EUR`} icon={CreditCard} color="text-teal-400" />
            <KpiCard label="TVA" value={`${(t.vat || 0).toFixed(2)} EUR`} icon={Receipt} />
            <KpiCard label="CA TTC" value={`${(t.ttc || 0).toFixed(2)} EUR`} icon={Receipt} color="text-white" />
          </div>

          {/* Monthly table */}
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Receipt className="w-4 h-4 text-teal-400" /> Récapitulatif mensuel
            <span className="text-[10px] text-zinc-500 font-normal">({(data.rows || []).length} lignes)</span>
          </h2>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto mb-6">
            <table className="w-full text-xs" data-testid="month-table">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                  <th className="text-left px-3 py-2 font-medium">Client</th>
                  <th className="px-2 py-2 font-medium">Produit</th>
                  <th className="text-right px-2 py-2 font-medium">Units</th>
                  <th className="text-right px-2 py-2 font-medium">Leads</th>
                  <th className="text-right px-2 py-2 font-medium">LB</th>
                  <th className="text-right px-2 py-2 font-medium">Offerts</th>
                  <th className="text-right px-2 py-2 font-medium">Facturés</th>
                  <th className="text-right px-2 py-2 font-medium">HT net</th>
                  <th className="text-right px-2 py-2 font-medium">TVA</th>
                  <th className="text-right px-2 py-2 font-medium">TTC</th>
                  <th className="px-2 py-2 font-medium text-center">Statut</th>
                  <th className="text-right px-2 py-2 font-medium">Sem.</th>
                </tr>
              </thead>
              <tbody>
                {(data.rows || []).filter(r => r.billing_mode !== 'PREPAID').map((r, i) => (
                  <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`month-row-${r.client_id}-${r.product_code}`}>
                    <td className="px-3 py-2">
                      <Link to={`/admin/clients/${r.client_id}`} className="text-teal-400 hover:underline font-medium text-xs">{r.client_name || r.client_id?.slice(0, 8)}</Link>
                    </td>
                    <td className="px-2 py-2 text-center"><span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">{r.product_code}</span></td>
                    <td className="px-2 py-2 text-right text-zinc-300 font-medium"><UnitsDisplay total={r.units_billable} lb={r.units_lb} /></td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.units_leads ?? 0}</td>
                    <td className="px-2 py-2 text-right text-violet-400">{r.units_lb ?? 0}</td>
                    <td className="px-2 py-2 text-right text-violet-400">{r.units_free ?? 0}</td>
                    <td className="px-2 py-2 text-right text-white font-medium">{r.units_invoiced ?? 0}</td>
                    <td className="px-2 py-2 text-right text-teal-400 font-medium">{(r.net_total_ht ?? 0).toFixed(2)}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{(r.vat_amount ?? 0).toFixed(2)}</td>
                    <td className="px-2 py-2 text-right text-white font-medium">{(r.total_ttc ?? 0).toFixed(2)}</td>
                    <td className="px-2 py-2 text-center"><StatusPill status={r.status} map={REC_STATUS} /></td>
                    <td className="px-2 py-2 text-right text-zinc-500">{r.weeks_count}</td>
                  </tr>
                ))}
                {(data.rows || []).filter(r => r.billing_mode !== 'PREPAID').length === 0 && (
                  <tr><td colSpan={12} className="px-3 py-8 text-center text-zinc-500">Aucune facturation ce mois</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Interfacturation mensuelle */}
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4 text-amber-400" /> Interfacturation interne (mois)
            <span className="text-[10px] text-zinc-500 font-normal">({(data.interfacturation || []).length} lignes)</span>
          </h2>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto">
            <table className="w-full text-xs" data-testid="month-inter-table">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                  <th className="text-left px-3 py-2 font-medium">Direction</th>
                  <th className="px-2 py-2 font-medium">Produit</th>
                  <th className="text-right px-2 py-2 font-medium">Units</th>
                  <th className="text-right px-2 py-2 font-medium">Leads</th>
                  <th className="text-right px-2 py-2 font-medium">LB</th>
                  <th className="text-right px-2 py-2 font-medium">Total HT</th>
                  <th className="px-2 py-2 font-medium text-center">Statut</th>
                  <th className="text-right px-2 py-2 font-medium">Sem.</th>
                </tr>
              </thead>
              <tbody>
                {(data.interfacturation || []).map((r, i) => (
                  <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.from_entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{r.from_entity}</span>
                        <ArrowRightLeft className="w-3 h-3 text-zinc-600" />
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.to_entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{r.to_entity}</span>
                      </div>
                    </td>
                    <td className="px-2 py-2 text-center"><span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">{r.product_code}</span></td>
                    <td className="px-2 py-2 text-right text-zinc-300 font-medium"><UnitsDisplay total={r.units_total} lb={r.units_lb} /></td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.units_leads ?? 0}</td>
                    <td className="px-2 py-2 text-right text-violet-400">{r.units_lb ?? 0}</td>
                    <td className="px-2 py-2 text-right text-amber-400 font-medium">{(r.total_ht ?? 0).toFixed(2)} EUR</td>
                    <td className="px-2 py-2 text-center"><StatusPill status={r.status} map={REC_STATUS} /></td>
                    <td className="px-2 py-2 text-right text-zinc-500">{r.weeks_count}</td>
                  </tr>
                ))}
                {(data.interfacturation || []).length === 0 && (
                  <tr><td colSpan={8} className="px-3 py-8 text-center text-zinc-500">Aucun transfert interne ce mois</td></tr>
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

export default function AdminFacturation() {
  const { authFetch } = useAuth();
  const [viewTab, setViewTab] = useState('week');
  const [week, setWeek] = useState(getCurrentWeekKey());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editingInterId, setEditingInterId] = useState(null);
  const [showCreateClient, setShowCreateClient] = useState(false);

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
          {/* Semaine / Mois tabs */}
          <div className="flex rounded-md overflow-hidden border border-zinc-700 ml-2">
            {[{ id: 'week', label: 'Semaine' }, { id: 'month', label: 'Mois' }].map(t => (
              <button key={t.id} onClick={() => setViewTab(t.id)}
                className={`px-3 py-1 text-xs ${viewTab === t.id ? 'bg-teal-500/20 text-teal-400' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'}`}
                data-testid={`tab-${t.id}`}>
                {t.label}
              </button>
            ))}
          </div>
          {viewTab === 'week' && data?.has_records && <span className="text-[10px] bg-emerald-500/15 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/30">Ledger construit</span>}
          {viewTab === 'week' && data && !data.has_records && <span className="text-[10px] bg-zinc-700/60 text-zinc-400 px-2 py-0.5 rounded-full border border-zinc-600">Aperçu</span>}
        </div>
        <div className="flex items-center gap-2">
          {viewTab === 'week' && <WeekNavStandard week={week} onChange={handleWeekNav} />}
          <button onClick={() => setShowCreateClient(true)}
            className="flex items-center gap-1 px-3 py-1.5 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30" data-testid="add-client-btn">
            <Plus className="w-3 h-3" /> Client
          </button>
          {viewTab === 'week' && (
            <button onClick={load} className="p-1.5 bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700" data-testid="refresh-btn">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {showCreateClient && <CreateClientModal authFetch={authFetch} onClose={() => setShowCreateClient(false)} onCreated={() => load()} />}

      {viewTab === 'month' ? (
        <MonthView authFetch={authFetch} />
      ) : loading ? (
        <div className="flex items-center gap-2 py-16 justify-center text-zinc-500 text-xs">
          <RefreshCw className="w-4 h-4 animate-spin" /> Chargement...
        </div>
      ) : data ? (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-5">
            <KpiCard label="Units total" value={<UnitsDisplay total={s.units_delivered ?? 0} lb={s.total_lb} />} icon={Package} />
            <KpiCard label="Leads total" value={s.total_leads ?? 0} icon={TrendingUp} />
            <KpiCard label="LB total" value={s.total_lb ?? 0} icon={TrendingUp} color="text-violet-400" />
            <KpiCard label="Units billable" value={<UnitsDisplay total={s.units_billable ?? 0} lb={s.billable_lb} />} icon={DollarSign} color="text-emerald-400" />
            <KpiCard label="Non-billable" value={s.units_non_billable ?? 0} icon={AlertTriangle} color="text-amber-400" />
            <KpiCard label="CA HT net" value={`${(t.net_ht || 0).toFixed(2)} EUR`} icon={CreditCard} color="text-teal-400" />
            <KpiCard label="CA TTC" value={`${(t.ttc || 0).toFixed(2)} EUR`} icon={Receipt} color="text-white" />
            <KpiCard label="Leads prod." value={s.leads_produced ?? 0} icon={FileText} />
          </div>

          {/* Build Ledger */}
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
                  <th className="text-right px-2 py-2 font-medium">Units</th>
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
                        <Link to={`/admin/clients/${r.client_id}`} className="text-teal-400 hover:underline font-medium text-xs">{r.client_name || r.client_id?.slice(0, 8)}</Link>
                        {r.external_invoice_number && <div className="text-[9px] text-zinc-500 mt-0.5">{r.external_invoice_number}</div>}
                        {r.pricing_missing && <div className="flex items-center gap-1 mt-0.5"><AlertTriangle className="w-2.5 h-2.5 text-red-400" /><span className="text-[9px] text-red-400">Pricing manquant</span></div>}
                      </td>
                      <td className="px-2 py-2 text-center"><span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">{r.product_code}</span></td>
                      <td className="px-2 py-2 text-right text-zinc-300 font-medium"><UnitsDisplay total={r.units_billable} lb={r.units_lb} /></td>
                      <td className="px-2 py-2 text-right text-zinc-400">{r.units_leads ?? '-'}</td>
                      <td className="px-2 py-2 text-right text-violet-400">{r.units_lb ?? 0}</td>
                      <td className="px-2 py-2 text-right text-violet-400">{r.units_free || 0}</td>
                      <td className="px-2 py-2 text-right text-white font-medium">{r.units_invoiced}</td>
                      <td className="px-2 py-2 text-right text-zinc-300">{r.unit_price_ht_snapshot ?? r.unit_price_eur ?? 0} EUR</td>
                      <td className="px-2 py-2 text-right text-zinc-400">{r.discount_pct_snapshot ?? r.discount_pct ?? 0}%</td>
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
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto mb-6">
            <table className="w-full text-xs" data-testid="prepaid-table">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                  <th className="text-left px-3 py-2 font-medium">Client</th>
                  <th className="px-2 py-2 font-medium">Produit</th>
                  <th className="text-right px-2 py-2 font-medium">Units sem.</th>
                  <th className="text-right px-2 py-2 font-medium">Leads</th>
                  <th className="text-right px-2 py-2 font-medium">LB</th>
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
                    <td className="px-2 py-2 text-right text-zinc-300"><UnitsDisplay total={r.units_billable ?? 0} lb={r.units_lb} /></td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.units_leads ?? 0}</td>
                    <td className="px-2 py-2 text-right text-violet-400">{r.units_lb ?? 0}</td>
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
                  <tr><td colSpan={9} className="px-3 py-8 text-center text-zinc-500">Aucun client prépayé</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* INTERFACTURATION SECTION */}
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4 text-amber-400" /> Interfacturation interne
            <span className="text-[10px] text-zinc-500 font-normal">({(data.interfacturation || []).length} lignes)</span>
          </h2>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto">
            <table className="w-full text-xs" data-testid="interfacturation-table">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-[10px]">
                  <th className="text-left px-3 py-2 font-medium">Direction</th>
                  <th className="px-2 py-2 font-medium">Produit</th>
                  <th className="text-right px-2 py-2 font-medium">Units</th>
                  <th className="text-right px-2 py-2 font-medium">Leads</th>
                  <th className="text-right px-2 py-2 font-medium">LB</th>
                  <th className="text-right px-2 py-2 font-medium">Prix int. HT</th>
                  <th className="text-right px-2 py-2 font-medium">Total HT</th>
                  <th className="text-left px-2 py-2 font-medium">N facture</th>
                  <th className="px-2 py-2 font-medium text-center">Statut</th>
                  <th className="px-2 py-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {(data.interfacturation || []).map((r, i) => {
                  const isEditing = editingInterId === r.id;
                  return isEditing ? (
                    <InterEditRow key={r.id} record={r} authFetch={authFetch} onDone={() => { setEditingInterId(null); load(); }} />
                  ) : (
                    <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30" data-testid={`inter-row-${r.from_entity}-${r.to_entity}-${r.product_code}`}>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.from_entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{r.from_entity}</span>
                          <ArrowRightLeft className="w-3 h-3 text-zinc-600" />
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${r.to_entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{r.to_entity}</span>
                        </div>
                      </td>
                      <td className="px-2 py-2 text-center"><span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">{r.product_code}</span></td>
                      <td className="px-2 py-2 text-right text-zinc-300 font-medium"><UnitsDisplay total={r.units_total} lb={r.units_lb} /></td>
                      <td className="px-2 py-2 text-right text-zinc-400">{r.units_leads ?? 0}</td>
                      <td className="px-2 py-2 text-right text-violet-400">{r.units_lb ?? 0}</td>
                      <td className="px-2 py-2 text-right text-zinc-300">{r.unit_price_ht_internal ?? 0} EUR</td>
                      <td className="px-2 py-2 text-right text-amber-400 font-medium">{(r.total_ht ?? 0).toFixed(2)} EUR</td>
                      <td className="px-2 py-2 text-zinc-400 text-[10px]">{r.external_invoice_number || '-'}</td>
                      <td className="px-2 py-2 text-center"><StatusPill status={r.status || 'not_invoiced'} map={REC_STATUS} /></td>
                      <td className="px-2 py-2">
                        <button onClick={() => setEditingInterId(r.id)} className="p-1 text-zinc-400 hover:text-amber-400 hover:bg-amber-500/10 rounded" data-testid={`inter-edit-${r.id}`}>
                          <Edit3 className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {(data.interfacturation || []).length === 0 && (
                  <tr><td colSpan={10} className="px-3 py-8 text-center text-zinc-500">Aucun transfert interne cette semaine</td></tr>
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
