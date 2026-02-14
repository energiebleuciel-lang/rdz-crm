import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Receipt, Plus, Send, Check, AlertTriangle, Clock, X } from 'lucide-react';

const STATUS_STYLES = {
  draft: 'bg-zinc-700/30 text-zinc-400 border-zinc-600/30',
  sent: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  paid: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  overdue: 'bg-red-500/15 text-red-400 border-red-500/30',
};

export default function AdminInvoices() {
  const { authFetch, hasPermission, isWriteBlocked } = useAuth();
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
  }, [authFetch, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const loadClients = async () => {
    try {
      const [z, m] = await Promise.all([
        authFetch(`${API}/api/clients?entity=ZR7`),
        authFetch(`${API}/api/clients?entity=MDL`),
      ]);
      let all = [];
      if (z.ok) { const d = await z.json(); all = all.concat(d.clients || []); }
      if (m.ok) { const d = await m.json(); all = all.concat(d.clients || []); }
      setClients(all);
    } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      const client = clients.find(c => c.id === form.client_id);
      const body = {
        client_id: form.client_id,
        amount_ht: Number(form.amount_ht),
        description: form.description,
        entity: client?.entity,
      };
      const res = await authFetch(`${API}/api/invoices`, {
        method: 'POST', body: JSON.stringify(body)
      });
      if (res.ok) { setShowCreate(false); load(); }
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const sendInvoice = async (id) => {
    await authFetch(`${API}/api/invoices/${id}/send`, { method: 'POST' });
    load();
  };

  const markPaid = async (id) => {
    await authFetch(`${API}/api/invoices/${id}/mark-paid`, { method: 'POST' });
    load();
  };

  const canManage = hasPermission('billing.manage') && !isWriteBlocked;
  const fmt = (n) => new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n || 0);

  return (
    <div data-testid="admin-invoices">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-white flex items-center gap-2">
          <Receipt className="w-5 h-5 text-teal-400" /> Factures
        </h1>
        <div className="flex gap-2 items-center">
          {['list', 'overdue'].map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1 text-xs rounded-md border transition-colors ${tab === t ? 'bg-teal-500/15 text-teal-400 border-teal-500/30' : 'text-zinc-500 border-zinc-800 hover:border-zinc-700'}`}
              data-testid={`tab-${t}`}>
              {t === 'list' ? 'Toutes' : 'Impayées'}
              {t === 'overdue' && overdue?.client_count > 0 && (
                <span className="ml-1.5 px-1 py-0.5 text-[9px] bg-red-500/20 text-red-400 rounded">{overdue.client_count}</span>
              )}
            </button>
          ))}
          {canManage && (
            <button onClick={() => { setShowCreate(true); loadClients(); }}
              className="flex items-center gap-1 px-3 py-1 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30"
              data-testid="create-invoice-btn">
              <Plus className="w-3 h-3" /> Nouvelle facture
            </button>
          )}
        </div>
      </div>

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
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500">
                      <th className="text-left px-3 py-2.5 font-medium">Client</th>
                      <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                      <th className="text-left px-3 py-2.5 font-medium">Factures</th>
                      <th className="text-right px-3 py-2.5 font-medium">Total HT</th>
                      <th className="text-right px-3 py-2.5 font-medium">Total TTC</th>
                      <th className="text-right px-3 py-2.5 font-medium">Retard</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overdue.clients?.map(c => (
                      <tr key={c.client_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                        <td className="px-3 py-2 text-zinc-300">{c.client_name}</td>
                        <td className="px-3 py-2"><span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${c.entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>{c.entity}</span></td>
                        <td className="px-3 py-2 text-zinc-400">{c.invoice_count}</td>
                        <td className="px-3 py-2 text-right text-zinc-400">{fmt(c.total_ht)}</td>
                        <td className="px-3 py-2 text-right text-red-400 font-medium">{fmt(c.total_ttc)}</td>
                        <td className="px-3 py-2 text-right">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${c.days_overdue > 30 ? 'bg-red-500/15 text-red-400' : 'bg-amber-500/15 text-amber-400'}`}>
                            {c.days_overdue}j
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
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
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500">
                <th className="text-left px-3 py-2.5 font-medium">N.</th>
                <th className="text-left px-3 py-2.5 font-medium">Client</th>
                <th className="text-left px-3 py-2.5 font-medium">Entity</th>
                <th className="text-right px-3 py-2.5 font-medium">HT</th>
                <th className="text-right px-3 py-2.5 font-medium">TVA</th>
                <th className="text-right px-3 py-2.5 font-medium">TTC</th>
                <th className="text-left px-3 py-2.5 font-medium">Status</th>
                <th className="text-left px-3 py-2.5 font-medium">Émise</th>
                <th className="text-left px-3 py-2.5 font-medium">Échéance</th>
                {canManage && <th className="text-right px-3 py-2.5 font-medium">Actions</th>}
              </tr>
            </thead>
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
                  <td className="px-3 py-2">
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${STATUS_STYLES[inv.status] || STATUS_STYLES.draft}`}>{inv.status}</span>
                  </td>
                  <td className="px-3 py-2 text-zinc-500">{inv.issued_at?.slice(0, 10)}</td>
                  <td className="px-3 py-2 text-zinc-500">{inv.due_at?.slice(0, 10)}</td>
                  {canManage && (
                    <td className="px-3 py-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {inv.status === 'draft' && (
                          <button onClick={() => sendInvoice(inv.id)} className="p-1 text-blue-400 hover:bg-zinc-800 rounded" title="Envoyer">
                            <Send className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {(inv.status === 'sent' || inv.status === 'overdue') && (
                          <button onClick={() => markPaid(inv.id)} className="p-1 text-emerald-400 hover:bg-zinc-800 rounded" title="Marquer payé">
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        )}
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
              {form.client_id && form.amount_ht && (
                <div className="bg-zinc-800/50 rounded-md px-3 py-2 text-xs">
                  {(() => {
                    const cl = clients.find(c => c.id === form.client_id);
                    const vat = cl?.vat_rate ?? 20;
                    const ht = Number(form.amount_ht) || 0;
                    const ttc = ht * (1 + vat / 100);
                    return (
                      <div className="flex justify-between">
                        <span className="text-zinc-500">TTC estimé ({vat}% TVA)</span>
                        <span className="text-zinc-200 font-medium">{fmt(ttc)} EUR</span>
                      </div>
                    );
                  })()}
                </div>
              )}
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
