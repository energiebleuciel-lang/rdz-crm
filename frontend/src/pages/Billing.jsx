/**
 * Page Facturation Inter-CRM
 * - Navigation par semaine (ex: 05/01/2026 → 12/01/2026)
 * - Bouton "Marquer comme facturé"
 * - Calcul des montants dus entre CRMs
 */

import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useCRM } from '../hooks/useCRM';
import { 
  DollarSign, TrendingUp, TrendingDown, Calendar, 
  ArrowRight, RefreshCw, Clock, AlertCircle, CheckCircle,
  FileText, ChevronLeft, ChevronRight, Check
} from 'lucide-react';
import { Card, Badge, Loading, Button } from '../components/UI';

export default function Billing() {
  const api = useApi();
  const { crms } = useCRM();
  const [loading, setLoading] = useState(true);
  const [billing, setBilling] = useState(null);
  const [verificationStatus, setVerificationStatus] = useState(null);
  const [runningVerification, setRunningVerification] = useState(false);
  
  // Navigation par semaine
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [currentWeek, setCurrentWeek] = useState(1);
  const [invoiceStatus, setInvoiceStatus] = useState(null);
  const [savingInvoice, setSavingInvoice] = useState(false);

  // Initialiser à la semaine actuelle
  useEffect(() => {
    loadCurrentWeek();
  }, []);

  useEffect(() => {
    if (currentYear && currentWeek) {
      loadWeekBilling();
    }
  }, [currentYear, currentWeek]);

  const loadCurrentWeek = async () => {
    try {
      const data = await api.get('/api/billing/weeks/current');
      setCurrentYear(data.year);
      setCurrentWeek(data.week);
    } catch (err) {
      console.error('Erreur chargement semaine:', err);
      // Fallback: calculer manuellement
      const now = new Date();
      const startOfYear = new Date(now.getFullYear(), 0, 1);
      const days = Math.floor((now - startOfYear) / (24 * 60 * 60 * 1000));
      setCurrentWeek(Math.ceil((days + startOfYear.getDay() + 1) / 7));
      setCurrentYear(now.getFullYear());
    }
    loadVerificationStatus();
  };

  const loadWeekBilling = async () => {
    setLoading(true);
    try {
      const data = await api.get(`/api/billing/weeks/${currentYear}/${currentWeek}`);
      setBilling(data);
      setInvoiceStatus(data.invoice_status);
    } catch (err) {
      console.error('Erreur chargement facturation:', err);
    }
    setLoading(false);
  };

  const loadVerificationStatus = async () => {
    try {
      const data = await api.get('/api/verification/status');
      setVerificationStatus(data);
    } catch (err) {
      console.error('Erreur chargement status:', err);
    }
  };

  const runVerification = async () => {
    setRunningVerification(true);
    try {
      const result = await api.post('/api/verification/run');
      alert(result.message);
      loadVerificationStatus();
    } catch (err) {
      alert('Erreur: ' + err.message);
    }
    setRunningVerification(false);
  };

  // Navigation semaines
  const prevWeek = () => {
    if (currentWeek > 1) {
      setCurrentWeek(currentWeek - 1);
    } else {
      setCurrentYear(currentYear - 1);
      setCurrentWeek(52);
    }
  };

  const nextWeek = () => {
    if (currentWeek < 52) {
      setCurrentWeek(currentWeek + 1);
    } else {
      setCurrentYear(currentYear + 1);
      setCurrentWeek(1);
    }
  };

  // Marquer comme facturé
  const toggleInvoiced = async () => {
    setSavingInvoice(true);
    try {
      const newStatus = !invoiceStatus?.invoiced;
      await api.post(`/api/billing/weeks/${currentYear}/${currentWeek}/invoice?invoiced=${newStatus}`);
      setInvoiceStatus({ ...invoiceStatus, invoiced: newStatus });
      alert(newStatus ? 'Semaine marquée comme facturée ✓' : 'Statut facturé retiré');
    } catch (err) {
      alert('Erreur: ' + err.message);
    }
    setSavingInvoice(false);
  };

  // Couleur selon le solde
  const getBalanceColor = (net) => {
    if (net > 0) return 'text-green-600';
    if (net < 0) return 'text-red-600';
    return 'text-slate-600';
  };

  const getBalanceBg = (net) => {
    if (net > 0) return 'bg-green-50 border-green-200';
    if (net < 0) return 'bg-red-50 border-red-200';
    return 'bg-slate-50 border-slate-200';
  };

  if (loading && !billing) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading text="Chargement de la facturation..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Facturation Inter-CRM</h1>
          <p className="text-slate-500">Vue par semaine - Calcul des montants dus</p>
        </div>
        
        <Button onClick={loadWeekBilling} variant="secondary">
          <RefreshCw className="w-4 h-4" />
          Actualiser
        </Button>
      </div>

      {/* Navigation par semaine */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <button
            onClick={prevWeek}
            className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
            Semaine précédente
          </button>
          
          <div className="text-center">
            <p className="text-sm text-slate-500">Semaine {currentWeek} / {currentYear}</p>
            <p className="text-xl font-bold text-slate-800">
              {billing?.week_info ? (
                `${billing.week_info.start} → ${billing.week_info.end}`
              ) : (
                `Semaine ${currentWeek}`
              )}
            </p>
          </div>
          
          <button
            onClick={nextWeek}
            className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            Semaine suivante
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
        
        {/* Bouton Facturé */}
        <div className="mt-4 pt-4 border-t flex items-center justify-center gap-4">
          <button
            onClick={toggleInvoiced}
            disabled={savingInvoice}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
              invoiceStatus?.invoiced
                ? 'bg-green-500 text-white hover:bg-green-600'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {savingInvoice ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : invoiceStatus?.invoiced ? (
              <Check className="w-5 h-5" />
            ) : (
              <DollarSign className="w-5 h-5" />
            )}
            {invoiceStatus?.invoiced ? 'Facturé ✓' : 'Marquer comme facturé'}
          </button>
          
          {invoiceStatus?.invoiced && invoiceStatus?.invoiced_at && (
            <span className="text-sm text-green-600">
              Facturé le {new Date(invoiceStatus.invoiced_at).toLocaleDateString('fr-FR')}
            </span>
          )}
        </div>
      </Card>

      {/* Stats de la semaine */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Total Leads</p>
              <p className="text-2xl font-bold text-slate-800">
                {billing?.total_leads_period || 0}
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Leads Cross-CRM</p>
              <p className="text-2xl font-bold text-amber-600">
                {billing?.cross_crm_leads || 0}
              </p>
            </div>
            <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
              <ArrowRight className="w-6 h-6 text-amber-600" />
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">% Cross-CRM</p>
              <p className="text-2xl font-bold text-slate-800">
                {billing?.cross_crm_percentage || 0}%
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </Card>

        <Card className={`p-5 ${invoiceStatus?.invoiced ? 'bg-green-50 border-green-200' : ''}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Statut</p>
              <p className={`text-lg font-bold ${invoiceStatus?.invoiced ? 'text-green-600' : 'text-slate-600'}`}>
                {invoiceStatus?.invoiced ? 'Facturé' : 'Non facturé'}
              </p>
            </div>
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              invoiceStatus?.invoiced ? 'bg-green-100' : 'bg-slate-100'
            }`}>
              {invoiceStatus?.invoiced ? (
                <Check className="w-6 h-6 text-green-600" />
              ) : (
                <Calendar className="w-6 h-6 text-slate-600" />
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Balances par CRM */}
      <Card>
        <div className="p-5 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-amber-500" />
            Balances par CRM
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Solde net = Montant dû - Montant à payer
          </p>
        </div>
        
        <div className="p-5">
          {billing?.balances && Object.keys(billing.balances).length > 0 ? (
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(billing.balances).map(([crmId, balance]) => (
                <div 
                  key={crmId}
                  className={`p-5 rounded-xl border-2 ${getBalanceBg(balance.net)}`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-bold text-lg text-slate-800">{balance.name}</h3>
                      <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded">
                        {balance.slug?.toUpperCase()}
                      </span>
                    </div>
                    <div className={`text-2xl font-bold ${getBalanceColor(balance.net)}`}>
                      {balance.net >= 0 ? '+' : ''}{balance.net.toFixed(2)}€
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="bg-white/50 rounded-lg p-3">
                      <div className="flex items-center gap-2 text-green-600 mb-1">
                        <TrendingUp className="w-4 h-4" />
                        <span>À recevoir</span>
                      </div>
                      <p className="font-bold text-lg">{balance.owed.toFixed(2)}€</p>
                    </div>
                    <div className="bg-white/50 rounded-lg p-3">
                      <div className="flex items-center gap-2 text-red-600 mb-1">
                        <TrendingDown className="w-4 h-4" />
                        <span>À payer</span>
                      </div>
                      <p className="font-bold text-lg">{balance.owes.toFixed(2)}€</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              <ArrowRight className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Aucun lead cross-CRM cette semaine</p>
            </div>
          )}
        </div>
      </Card>

      {/* Transactions détaillées */}
      {billing?.transactions && billing.transactions.length > 0 && (
        <Card>
          <div className="p-5 border-b border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800">Transactions Inter-CRM</h2>
          </div>
          
          <div className="divide-y divide-slate-100">
            {billing.transactions.map((tx, idx) => (
              <div key={idx} className="p-5 flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
                    <ArrowRight className="w-5 h-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-800">
                      {tx.debtor.name} → {tx.creditor.name}
                    </p>
                    <p className="text-sm text-slate-500">
                      {tx.count} lead{tx.count > 1 ? 's' : ''} transféré{tx.count > 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="font-bold text-lg text-slate-800">{tx.amount.toFixed(2)}€</p>
                  <p className="text-xs text-slate-500">
                    {tx.debtor.slug?.toUpperCase()} doit à {tx.creditor.slug?.toUpperCase()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Détails des leads cross-CRM */}
      {billing?.lead_details && billing.lead_details.length > 0 && (
        <Card>
          <div className="p-5 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800">Détail des Leads Cross-CRM</h2>
            <Badge variant="info">{billing.lead_details.length} leads</Badge>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-5 py-3 text-left">Date</th>
                  <th className="px-5 py-3 text-left">Téléphone</th>
                  <th className="px-5 py-3 text-left">Produit</th>
                  <th className="px-5 py-3 text-left">Dépt</th>
                  <th className="px-5 py-3 text-left">Origine</th>
                  <th className="px-5 py-3 text-left">Destination</th>
                  <th className="px-5 py-3 text-right">Prix</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {billing.lead_details.slice(0, 50).map((lead, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="px-5 py-3 text-sm text-slate-600">{lead.date}</td>
                    <td className="px-5 py-3 text-sm font-mono">****{lead.phone}</td>
                    <td className="px-5 py-3">
                      <Badge variant={lead.product_type === 'PV' ? 'success' : lead.product_type === 'PAC' ? 'info' : 'warning'}>
                        {lead.product_type}
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-600">{lead.departement}</td>
                    <td className="px-5 py-3 text-sm text-slate-800">{lead.origin_crm}</td>
                    <td className="px-5 py-3 text-sm text-slate-800">{lead.dest_crm}</td>
                    <td className="px-5 py-3 text-sm text-right font-medium">{lead.prix.toFixed(2)}€</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {billing.lead_details.length > 50 && (
            <div className="p-3 bg-slate-50 text-center text-sm text-slate-500">
              Affichage limité à 50 leads sur {billing.lead_details.length}
            </div>
          )}
        </Card>
      )}

      {/* Section Vérification Nocturne */}
      <Card>
        <div className="p-5 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-500" />
            Vérification Nocturne
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Vérification automatique à 3h du matin - Relance des leads échoués
          </p>
        </div>
        
        <div className="p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                verificationStatus?.enabled ? 'bg-green-100' : 'bg-red-100'
              }`}>
                {verificationStatus?.enabled ? (
                  <CheckCircle className="w-6 h-6 text-green-600" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-600" />
                )}
              </div>
              <div>
                <p className="font-medium text-slate-800">
                  {verificationStatus?.enabled ? 'Activée' : 'Désactivée'}
                </p>
                <p className="text-sm text-slate-500">
                  Planifiée: {verificationStatus?.schedule || 'Non configuré'}
                </p>
                {verificationStatus?.last_run && (
                  <p className="text-xs text-slate-400 mt-1">
                    Dernière exécution: {new Date(verificationStatus.last_run).toLocaleString('fr-FR')}
                  </p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {verificationStatus?.last_result && (
                <div className="text-right text-sm">
                  <p className="text-slate-600">
                    {verificationStatus.last_result.total_leads} leads analysés
                  </p>
                  <p className="text-green-600">
                    {verificationStatus.last_result.retry_success} relancés avec succès
                  </p>
                </div>
              )}
              
              <Button 
                onClick={runVerification} 
                disabled={runningVerification}
                className="bg-blue-500 hover:bg-blue-600"
              >
                {runningVerification ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    En cours...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    Lancer maintenant
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
