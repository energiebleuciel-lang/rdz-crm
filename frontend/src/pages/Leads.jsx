/**
 * Page Leads - Filtrée par CRM sélectionné
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { API } from '../hooks/useApi';
import { Card, Loading, Badge, Button, Modal, Input } from '../components/UI';
import { Users, RefreshCw, Download, Eye, RotateCcw, ArrowRightLeft, Calendar } from 'lucide-react';

export default function Leads() {
  const { authFetch } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const [leads, setLeads] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [transferredFilter, setTransferredFilter] = useState(null); // null = tous, true = transférés, false = non transférés
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedLead, setSelectedLead] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  useEffect(() => {
    // Ce useEffect est maintenant géré par celui avec les filtres
  }, [selectedCRM]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Construire l'URL avec les filtres
      let url = `${API}/api/leads?crm_id=${selectedCRM}&limit=500`;
      if (transferredFilter !== null) {
        url += `&transferred=${transferredFilter}`;
      }
      if (dateFrom) {
        url += `&date_from=${dateFrom}`;
      }
      if (dateTo) {
        url += `&date_to=${dateTo}`;
      }
      
      const res = await authFetch(url);
      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads || []);
      }
      
      // Charger les comptes pour référence
      const accountsRes = await authFetch(`${API}/api/accounts?crm_id=${selectedCRM}`);
      if (accountsRes.ok) {
        const data = await accountsRes.json();
        setAccounts(data.accounts || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  // Recharger quand les filtres changent
  useEffect(() => {
    if (selectedCRM) {
      loadData();
    }
  }, [selectedCRM, transferredFilter, dateFrom, dateTo]);

  const viewLead = (lead) => {
    setSelectedLead(lead);
    setShowDetailModal(true);
  };

  const retryLead = async (leadId) => {
    try {
      const res = await authFetch(`${API}/api/leads/${leadId}/retry`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          alert(`✅ Lead relancé avec succès (${data.status})`);
        } else {
          alert(`❌ Échec: ${data.error || data.status}`);
        }
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const exportCSV = () => {
    const filtered = filteredLeads;
    const headers = [
      'Téléphone', 'Nom', 'Prénom', 'Civilité', 'Email', 
      'Code Postal', 'Département', 'Ville', 'Adresse',
      'Type Logement', 'Statut Occupant', 'Surface', 'Année Construction', 'Type Chauffage',
      'Facture Électricité', 'Facture Chauffage',
      'Type Projet', 'Délai', 'Budget',
      'Formulaire', 'LP', 'Liaison', 'Source', 'UTM Source', 'UTM Medium', 'UTM Campaign',
      'CRM', 'Statut', 'Date'
    ];
    const rows = filtered.map(l => [
      l.phone,
      l.nom,
      l.prenom,
      l.civilite,
      l.email,
      l.code_postal,
      l.departement,
      l.ville,
      l.adresse,
      l.type_logement,
      l.statut_occupant,
      l.surface_habitable,
      l.annee_construction,
      l.type_chauffage,
      l.facture_electricite,
      l.facture_chauffage,
      l.type_projet,
      l.delai_projet,
      l.budget,
      l.form_code,
      l.lp_code,
      l.liaison_code,
      l.source,
      l.utm_source,
      l.utm_medium,
      l.utm_campaign,
      l.target_crm_slug,
      l.api_status,
      new Date(l.created_at).toLocaleDateString('fr-FR')
    ]);
    
    const csv = [headers, ...rows].map(r => r.map(c => `"${c || ''}"`).join(';')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `leads_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  const filteredLeads = filter === 'all' 
    ? leads 
    : leads.filter(l => l.api_status === filter);

  const statusVariant = (status) => {
    switch (status) {
      case 'success': return 'success';
      case 'duplicate': return 'warning';
      case 'queued': return 'info';
      case 'failed': return 'danger';
      case 'no_crm': return 'secondary';
      default: return 'default';
    }
  };
  
  const statusLabel = (status) => {
    switch (status) {
      case 'success': return 'Envoyé';
      case 'duplicate': return 'Doublon';
      case 'queued': return 'En queue';
      case 'failed': return 'Échoué';
      case 'no_crm': return 'Sans CRM';
      case 'pending': return 'En attente';
      default: return status;
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Leads</h1>
          <p className="text-sm text-slate-500">
            CRM: <span className="font-medium text-slate-700">{currentCRM?.name}</span>
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Filtres */}
          <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
            {[
              { value: 'all', label: 'Tous' },
              { value: 'success', label: 'Envoyés' },
              { value: 'failed', label: 'Échoués' },
              { value: 'no_crm', label: 'Sans CRM' },
              { value: 'queued', label: 'En queue' }
            ].map(f => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  filter === f.value 
                    ? 'bg-white text-slate-800 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-800'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          
          <Button variant="secondary" onClick={loadData}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          
          <Button variant="secondary" onClick={exportCSV}>
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
        </div>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Téléphone</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Nom</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Email</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">CP / Dept</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Form</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">LP</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Source</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">CRM</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Statut</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Date</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredLeads.map(lead => (
                <tr key={lead.id} className="border-t hover:bg-slate-50">
                  <td className="p-4 font-mono text-sm">{lead.phone}</td>
                  <td className="p-4">
                    <span className="text-slate-500 text-xs">{lead.civilite}</span>{' '}
                    {lead.nom} {lead.prenom}
                  </td>
                  <td className="p-4 text-sm text-slate-600 truncate max-w-[150px]">{lead.email}</td>
                  <td className="p-4">
                    <span className="font-mono text-sm">{lead.code_postal}</span>
                    <span className="text-slate-400 text-xs ml-1">({lead.departement})</span>
                  </td>
                  <td className="p-4">
                    <Badge variant="info">{lead.form_code}</Badge>
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {lead.lp_code || '-'}
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {lead.source || lead.utm_source || '-'}
                  </td>
                  <td className="p-4 text-sm">
                    {lead.target_crm_slug?.toUpperCase() || '-'}
                  </td>
                  <td className="p-4">
                    <div className="flex flex-col">
                      <Badge variant={statusVariant(lead.api_status)}>
                        {statusLabel(lead.api_status)}
                      </Badge>
                      {['failed', 'no_crm'].includes(lead.api_status) && lead.api_response && (
                        <span className="text-xs text-red-500 mt-1 max-w-[150px] truncate" title={lead.api_response}>
                          {(() => {
                            try {
                              const resp = typeof lead.api_response === 'string' 
                                ? JSON.parse(lead.api_response.replace(/'/g, '"'))
                                : lead.api_response;
                              return resp?.error || resp?.message || lead.api_response;
                            } catch {
                              return lead.api_response?.substring?.(0, 50) || 'Erreur';
                            }
                          })()}
                        </span>
                      )}
                      {lead.api_status === 'no_crm' && !lead.api_response && (
                        <span className="text-xs text-slate-500 mt-1">Pas de commande active</span>
                      )}
                    </div>
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {new Date(lead.created_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => viewLead(lead)}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                        title="Voir détails"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      {['failed', 'no_crm', 'queued'].includes(lead.api_status) && (
                        <button
                          onClick={() => retryLead(lead.id)}
                          className="flex items-center gap-1 px-2 py-1 text-sm text-amber-600 hover:bg-amber-50 rounded font-medium"
                          title="Relancer l'envoi"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Relancer
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {filteredLeads.length === 0 && (
                <tr>
                  <td colSpan={11} className="p-8 text-center text-slate-500">
                    Aucun lead trouvé
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <p className="text-sm text-slate-500 text-center">
        {filteredLeads.length} lead(s) affiché(s) sur {leads.length} total
      </p>

      {/* Modal Détail Lead */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        title={`Lead ${selectedLead?.phone || ''}`}
        size="lg"
      >
        {selectedLead && (
          <div className="space-y-6">
            {/* Identité */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                Identité
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Civilité:</span> <span className="font-medium">{selectedLead.civilite || '-'}</span></div>
                <div><span className="text-slate-500">Nom:</span> <span className="font-medium">{selectedLead.nom || '-'}</span></div>
                <div><span className="text-slate-500">Prénom:</span> <span className="font-medium">{selectedLead.prenom || '-'}</span></div>
                <div><span className="text-slate-500">Email:</span> <span className="font-medium">{selectedLead.email || '-'}</span></div>
                <div><span className="text-slate-500">Téléphone:</span> <span className="font-medium font-mono">{selectedLead.phone}</span></div>
              </div>
            </div>

            {/* Localisation */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                Localisation
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Code postal:</span> <span className="font-medium font-mono">{selectedLead.code_postal || '-'}</span></div>
                <div><span className="text-slate-500">Département:</span> <span className="font-medium">{selectedLead.departement || '-'}</span></div>
                <div><span className="text-slate-500">Ville:</span> <span className="font-medium">{selectedLead.ville || '-'}</span></div>
                <div className="col-span-2"><span className="text-slate-500">Adresse:</span> <span className="font-medium">{selectedLead.adresse || '-'}</span></div>
              </div>
            </div>

            {/* Logement */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                Logement
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Type:</span> <span className="font-medium">{selectedLead.type_logement || '-'}</span></div>
                <div><span className="text-slate-500">Statut:</span> <span className="font-medium">{selectedLead.statut_occupant || '-'}</span></div>
                <div><span className="text-slate-500">Surface:</span> <span className="font-medium">{selectedLead.surface_habitable ? `${selectedLead.surface_habitable} m²` : '-'}</span></div>
                <div><span className="text-slate-500">Année construction:</span> <span className="font-medium">{selectedLead.annee_construction || '-'}</span></div>
                <div><span className="text-slate-500">Chauffage:</span> <span className="font-medium">{selectedLead.type_chauffage || '-'}</span></div>
              </div>
            </div>

            {/* Énergie */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                Énergie
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Facture électricité:</span> <span className="font-medium">{selectedLead.facture_electricite || '-'}</span></div>
                <div><span className="text-slate-500">Facture chauffage:</span> <span className="font-medium">{selectedLead.facture_chauffage || '-'}</span></div>
              </div>
            </div>

            {/* Projet */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                Projet
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Type projet:</span> <span className="font-medium">{selectedLead.type_projet || '-'}</span></div>
                <div><span className="text-slate-500">Délai:</span> <span className="font-medium">{selectedLead.delai_projet || '-'}</span></div>
                <div><span className="text-slate-500">Budget:</span> <span className="font-medium">{selectedLead.budget || '-'}</span></div>
              </div>
            </div>

            {/* Tracking */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                Tracking
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Formulaire:</span> <Badge variant="info">{selectedLead.form_code}</Badge></div>
                <div><span className="text-slate-500">LP:</span> <span className="font-medium font-mono">{selectedLead.lp_code || '-'}</span></div>
                <div><span className="text-slate-500">Code liaison:</span> <span className="font-medium font-mono text-xs">{selectedLead.liaison_code || '-'}</span></div>
                <div><span className="text-slate-500">Source:</span> <span className="font-medium">{selectedLead.source || '-'}</span></div>
                <div><span className="text-slate-500">UTM Source:</span> <span className="font-medium">{selectedLead.utm_source || '-'}</span></div>
                <div><span className="text-slate-500">UTM Medium:</span> <span className="font-medium">{selectedLead.utm_medium || '-'}</span></div>
                <div><span className="text-slate-500">UTM Campaign:</span> <span className="font-medium">{selectedLead.utm_campaign || '-'}</span></div>
              </div>
            </div>

            {/* CRM */}
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                CRM
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">CRM cible:</span> <span className="font-medium">{selectedLead.target_crm_slug?.toUpperCase() || '-'}</span></div>
                <div><span className="text-slate-500">Statut:</span> <Badge variant={statusVariant(selectedLead.api_status)}>{selectedLead.api_status}</Badge></div>
                <div><span className="text-slate-500">Raison routing:</span> <span className="font-medium">{selectedLead.routing_reason || '-'}</span></div>
                <div><span className="text-slate-500">Envoyé:</span> <span className="font-medium">{selectedLead.sent_to_crm ? 'Oui' : 'Non'}</span></div>
              </div>
              {selectedLead.api_response && (
                <div className="mt-2 p-2 bg-slate-50 rounded text-xs font-mono">
                  {selectedLead.api_response}
                </div>
              )}
            </div>

            {/* Metadata */}
            <div className="pt-3 border-t text-xs text-slate-500">
              <p>ID: {selectedLead.id}</p>
              <p>Créé le: {new Date(selectedLead.created_at).toLocaleString('fr-FR')}</p>
              <p>IP: {selectedLead.ip}</p>
              <p>RGPD: {selectedLead.rgpd_consent ? '✓' : '✗'} | Newsletter: {selectedLead.newsletter ? '✓' : '✗'}</p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
