import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Link } from 'react-router-dom';
import {
  RefreshCw, Receipt, AlertTriangle, Check, Lock, Send, CreditCard,
  FileText, DollarSign, TrendingUp, Package
} from 'lucide-react';
import { getCurrentWeekKey, shiftWeekKey } from '../lib/weekUtils';
import { WeekNavStandard } from '../components/WeekNav';

const INV_STATUS = {
  draft: { label: 'Draft', cls: 'bg-zinc-700/60 text-zinc-300 border-zinc-600' },
  frozen: { label: 'Frozen', cls: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  sent: { label: 'Sent', cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  paid: { label: 'Paid', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
};
const PREPAID_STATUS = {
  OK: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  LOW: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  BLOCKED: 'bg-red-500/15 text-red-400 border-red-500/30',
};

function Pill({ status, map }) {
  const cfg = map[status] || { label: status, cls: 'bg-zinc-800 text-zinc-400 border-zinc-700' };
  return <span className={`text-[10px] px-2 py-0.5 rounded-full border ${cfg.cls}`}>{cfg.label || status}</span>;
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

export default function AdminFacturation() {
  const { authFetch } = useAuth();
  const [week, setWeek] = useState(getCurrentWeekKey());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');

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

  const doAction = async (url, label) => {
    setActionLoading(label);
    try {
      const r = await authFetch(`${API}${url}`, { method: 'POST' });
      if (!r.ok) { const d = await r.json(); alert(d.detail || 'Erreur'); }
      else { load(); }
    } catch (e) { alert(e.message); }
    setActionLoading('');
  };

  const buildLedger = () => doAction(`/api/billing/week/${week}/build-ledger`, 'ledger');
  const generateInvoices = () => doAction(`/api/billing/week/${week}/generate-invoices`, 'invoices');
  const freezeInvoice = (id) => doAction(`/api/invoices/${id}/freeze`, `freeze-${id}`);
  const markSent = (id) => doAction(`/api/invoices/${id}/mark-sent`, `sent-${id}`);
  const markPaid = (id) => doAction(`/api/invoices/${id}/mark-paid`, `paid-${id}`);

  const s = data?.summary || {};
  const t = data?.totals_invoice || {};

  return (
    <div data-testid="admin-facturation">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <Receipt className="w-5 h-5 text-teal-400" />
          <h1 className="text-lg font-semibold text-white">Facturation</h1>
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
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-5">
            <KpiCard label="Leads produits" value={s.leads_produced ?? 0} icon={Package} />
            <KpiCard label="Units livrées" value={s.units_delivered ?? 0} icon={TrendingUp} />
            <KpiCard label="Units billable" value={s.units_billable ?? 0} icon={DollarSign} color="text-emerald-400" />
            <KpiCard label="Non-billable" value={s.units_non_billable ?? 0} icon={AlertTriangle} color="text-amber-400" />
            <KpiCard label="CA HT net" value={`${(t.net || 0).toFixed(2)} EUR`} icon={CreditCard} color="text-teal-400" />
            <KpiCard label="Units offertes" value={t.units_free ?? 0} icon={FileText} color="text-violet-400" />
          </div>

          {/* Actions */}
          <div className="flex gap-2 mb-5">
            <button onClick={buildLedger} disabled={!!actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-md hover:bg-zinc-700 border border-zinc-700 disabled:opacity-50" data-testid="build-ledger-btn">
              {actionLoading === 'ledger' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
              Build Ledger
            </button>
            <button onClick={generateInvoices} disabled={!!actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-teal-500/15 text-teal-400 rounded-md hover:bg-teal-500/25 border border-teal-500/30 disabled:opacity-50" data-testid="generate-invoices-btn">
              {actionLoading === 'invoices' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Receipt className="w-3 h-3" />}
              Générer Factures
            </button>
          </div>

          {/* WEEKLY INVOICE SECTION */}
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
                  <th className="text-right px-2 py-2 font-medium">HT brut</th>
                  <th className="text-right px-2 py-2 font-medium">HT net</th>
                  <th className="text-right px-2 py-2 font-medium">TVA</th>
                  <th className="text-right px-2 py-2 font-medium">TTC</th>
                  <th className="px-2 py-2 font-medium text-center">Statut</th>
                  <th className="px-2 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(data.weekly_invoice || []).map((r, i) => (
                  <tr key={i} className={`border-b border-zinc-800/50 hover:bg-zinc-800/30 ${r.pricing_missing ? 'bg-red-500/5' : ''}`}
                    data-testid={`invoice-row-${r.client_id}-${r.product_code}`}>
                    <td className="px-3 py-2">
                      <Link to={`/admin/clients/${r.client_id}`} className="text-teal-400 hover:underline font-medium">
                        {r.client_name || r.client_id?.slice(0, 8)}
                      </Link>
                      {r.pricing_missing && (
                        <div className="flex items-center gap-1 mt-0.5">
                          <AlertTriangle className="w-3 h-3 text-red-400" />
                          <span className="text-[9px] text-red-400">Pricing manquant</span>
                        </div>
                      )}
                    </td>
                    <td className="px-2 py-2 text-center"><span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">{r.product_code}</span></td>
                    <td className="px-2 py-2 text-right text-zinc-300 font-medium">{r.units_billable}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.units_leads}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.units_lb}</td>
                    <td className="px-2 py-2 text-right text-violet-400">{r.units_free_applied || 0}</td>
                    <td className="px-2 py-2 text-right text-white font-medium">{r.units_invoiced}</td>
                    <td className="px-2 py-2 text-right text-zinc-300">{r.unit_price_eur} EUR</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.discount_pct}%</td>
                    <td className="px-2 py-2 text-right text-zinc-300">{r.gross_total?.toFixed(2)}</td>
                    <td className="px-2 py-2 text-right text-teal-400 font-medium">{r.net_total?.toFixed(2)}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.tva_amount?.toFixed(2)}</td>
                    <td className="px-2 py-2 text-right text-white font-medium">{r.ttc?.toFixed(2)}</td>
                    <td className="px-2 py-2 text-center">
                      {r.invoice_status ? <Pill status={r.invoice_status} map={INV_STATUS} /> : <span className="text-[10px] text-zinc-600">-</span>}
                    </td>
                    <td className="px-2 py-2">
                      <div className="flex gap-1">
                        {r.invoice_id && r.invoice_status === 'draft' && (
                          <button onClick={() => freezeInvoice(r.invoice_id)} title="Freeze" disabled={!!actionLoading}
                            className="p-1 text-blue-400 hover:bg-blue-500/10 rounded" data-testid={`freeze-${r.invoice_id}`}>
                            <Lock className="w-3 h-3" />
                          </button>
                        )}
                        {r.invoice_id && r.invoice_status === 'frozen' && (
                          <button onClick={() => markSent(r.invoice_id)} title="Mark Sent" disabled={!!actionLoading}
                            className="p-1 text-amber-400 hover:bg-amber-500/10 rounded" data-testid={`send-${r.invoice_id}`}>
                            <Send className="w-3 h-3" />
                          </button>
                        )}
                        {r.invoice_id && (r.invoice_status === 'sent' || r.invoice_status === 'frozen') && (
                          <button onClick={() => markPaid(r.invoice_id)} title="Mark Paid" disabled={!!actionLoading}
                            className="p-1 text-emerald-400 hover:bg-emerald-500/10 rounded" data-testid={`paid-${r.invoice_id}`}>
                            <Check className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {(data.weekly_invoice || []).length === 0 && (
                  <tr><td colSpan={15} className="px-3 py-8 text-center text-zinc-500">Aucune facturation cette semaine</td></tr>
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
                  <th className="text-right px-2 py-2 font-medium">Livrées sem.</th>
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
                    <td className="px-2 py-2 text-right text-zinc-300">{r.units_billable}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.prepaid_purchased ?? 0}</td>
                    <td className="px-2 py-2 text-right text-zinc-400">{r.prepaid_delivered ?? 0}</td>
                    <td className={`px-2 py-2 text-right font-medium ${(r.prepaid_remaining ?? 0) <= 0 ? 'text-red-400' : (r.prepaid_remaining ?? 0) <= 10 ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {r.prepaid_remaining ?? 0}
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${PREPAID_STATUS[r.prepaid_status] || PREPAID_STATUS.OK}`}>
                        {r.prepaid_status || 'OK'}
                      </span>
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
