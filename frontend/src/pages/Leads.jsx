/**
 * Page Leads - Gestion complète des leads
 * - Liste avec filtres
 * - Voir détail
 * - Modifier (single + mass)
 * - Supprimer (single + mass)
 * - Forcer envoi CRM (single + mass)
 * - Export CSV
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { API } from '../hooks/useApi';
import { Card, Loading, Badge, Button, Modal, Input, Select } from '../components/UI';
import { 
  Users, RefreshCw, Download, Eye, RotateCcw, ArrowRightLeft, Calendar,
  Edit, Trash2, Send, CheckSquare, Square, AlertTriangle, X
} from 'lucide-react';

export default function Leads() {
  const { authFetch, user } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const [leads, setLeads] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [transferredFilter, setTransferredFilter] = useState(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  
  // Modals
  const [selectedLead, setSelectedLead] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showForceSendModal, setShowForceSendModal] = useState(false);
  const [showMassEditModal, setShowMassEditModal] = useState(false);
  const [showMassDeleteModal, setShowMassDeleteModal] = useState(false);
  const [showMassForceSendModal, setShowMassForceSendModal] = useState(false);
  
  // Selection pour mass actions
  const [selectedLeadIds, setSelectedLeadIds] = useState([]);
  const [selectAll, setSelectAll] = useState(false);
  
  // Form data
  const [editForm, setEditForm] = useState({});
  const [massEditForm, setMassEditForm] = useState({});
  const [forceSendCRM, setForceSendCRM] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const isAdmin = user?.role === 'admin';

  // Load data
  const loadData = async () => {
    try {
      setLoading(true);
      let url = `${API}/api/leads?crm_id=${selectedCRM}&limit=500`;
      if (transferredFilter !== null) url += `&transferred=${transferredFilter}`;
      if (dateFrom) url += `&date_from=${dateFrom}`;
      if (dateTo) url += `&date_to=${dateTo}`;
      
      const res = await authFetch(url);
      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads || []);
      }
      
      const accountsRes = await authFetch(`${API}/api/accounts?crm_id=${selectedCRM}`);
      if (accountsRes.ok) {
        const data = await accountsRes.json();
        setAccounts(data.accounts || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
      setSelectedLeadIds([]);
      setSelectAll(false);
    }
  };

  useEffect(() => {
    if (selectedCRM) loadData();
  }, [selectedCRM, transferredFilter, dateFrom, dateTo]);

  // ==================== SELECTION ====================
  
  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedLeadIds([]);
    } else {
      setSelectedLeadIds(filteredLeads.map(l => l.id));
    }
    setSelectAll(!selectAll);
  };

  const toggleSelectLead = (leadId) => {
    if (selectedLeadIds.includes(leadId)) {
      setSelectedLeadIds(selectedLeadIds.filter(id => id !== leadId));
    } else {
      setSelectedLeadIds([...selectedLeadIds, leadId]);
    }
  };

  // ==================== SINGLE ACTIONS ====================

  const viewLead = (lead) => {
    setSelectedLead(lead);
    setShowDetailModal(true);
  };

  const openEditModal = (lead) => {
    setSelectedLead(lead);
    setEditForm({
      phone: lead.phone || '',
      nom: lead.nom || '',
      prenom: lead.prenom || '',
      email: lead.email || '',
      departement: lead.departement || '',
      ville: lead.ville || '',
      civilite: lead.civilite || '',
      type_logement: lead.type_logement || '',
      statut_occupant: lead.statut_occupant || '',
      notes_admin: lead.notes_admin || ''
    });
    setShowEditModal(true);
  };

  const saveLead = async () => {
    try {
      setActionLoading(true);
      const res = await authFetch(`${API}/api/leads/${selectedLead.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      });
      
      if (res.ok) {
        setActionMessage({ type: 'success', text: 'Lead modifié avec succès !' });
        setShowEditModal(false);
        loadData();
      } else {
        const err = await res.json();
        setActionMessage({ type: 'error', text: err.detail || 'Erreur lors de la modification' });
      }
    } catch (e) {
      setActionMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const openDeleteModal = (lead) => {
    setSelectedLead(lead);
    setShowDeleteModal(true);
  };

  const deleteLead = async () => {
    try {
      setActionLoading(true);
      const res = await authFetch(`${API}/api/leads/${selectedLead.id}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        setActionMessage({ type: 'success', text: 'Lead supprimé !' });
        setShowDeleteModal(false);
        loadData();
      } else {
        const err = await res.json();
        setActionMessage({ type: 'error', text: err.detail || 'Erreur lors de la suppression' });
      }
    } catch (e) {
      setActionMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const openForceSendModal = (lead) => {
    setSelectedLead(lead);
    setForceSendCRM('');
    setShowForceSendModal(true);
  };

  const forceSendLead = async () => {
    if (!forceSendCRM) return;
    try {
      setActionLoading(true);
      const res = await authFetch(`${API}/api/leads/${selectedLead.id}/force-send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_crm: forceSendCRM })
      });
      
      if (res.ok) {
        const data = await res.json();
        setActionMessage({ type: 'success', text: `Envoyé vers ${forceSendCRM.toUpperCase()} !` });
        setShowForceSendModal(false);
        loadData();
      } else {
        const err = await res.json();
        setActionMessage({ type: 'error', text: err.detail || 'Erreur lors de l\'envoi' });
      }
    } catch (e) {
      setActionMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const retryLead = async (leadId) => {
    try {
      const res = await authFetch(`${API}/api/leads/${leadId}/retry`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setActionMessage({ type: 'success', text: `Lead relancé (${data.status})` });
        } else {
          setActionMessage({ type: 'error', text: data.error || data.status });
        }
        loadData();
      }
    } catch (e) {
      setActionMessage({ type: 'error', text: e.message });
    }
    setTimeout(() => setActionMessage(null), 3000);
  };

  // ==================== MASS ACTIONS ====================

  const openMassEditModal = () => {
    setMassEditForm({
      departement: '',
      ville: '',
      notes_admin: ''
    });
    setShowMassEditModal(true);
  };

  const saveMassEdit = async () => {
    try {
      setActionLoading(true);
      let successCount = 0;
      let errorCount = 0;
      
      // Filtrer les champs vides
      const updateData = Object.fromEntries(
        Object.entries(massEditForm).filter(([k, v]) => v !== '')
      );
      
      if (Object.keys(updateData).length === 0) {
        setActionMessage({ type: 'error', text: 'Aucun champ à modifier' });
        setActionLoading(false);
        return;
      }
      
      for (const leadId of selectedLeadIds) {
        const res = await authFetch(`${API}/api/leads/${leadId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updateData)
        });
        if (res.ok) successCount++;
        else errorCount++;
      }
      
      setActionMessage({ 
        type: successCount > 0 ? 'success' : 'error', 
        text: `${successCount} modifié(s), ${errorCount} erreur(s)` 
      });
      setShowMassEditModal(false);
      loadData();
    } catch (e) {
      setActionMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const openMassDeleteModal = () => {
    setShowMassDeleteModal(true);
  };

  const massDeleteLeads = async () => {
    try {
      setActionLoading(true);
      let successCount = 0;
      
      for (const leadId of selectedLeadIds) {
        const res = await authFetch(`${API}/api/leads/${leadId}`, { method: 'DELETE' });
        if (res.ok) successCount++;
      }
      
      setActionMessage({ type: 'success', text: `${successCount} lead(s) supprimé(s)` });
      setShowMassDeleteModal(false);
      loadData();
    } catch (e) {
      setActionMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  const openMassForceSendModal = () => {
    setForceSendCRM('');
    setShowMassForceSendModal(true);
  };

  const massForceSend = async () => {
    if (!forceSendCRM) return;
    try {
      setActionLoading(true);
      let successCount = 0;
      let errorCount = 0;
      
      for (const leadId of selectedLeadIds) {
        const res = await authFetch(`${API}/api/leads/${leadId}/force-send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_crm: forceSendCRM })
        });
        if (res.ok) successCount++;
        else errorCount++;
      }
      
      setActionMessage({ 
        type: successCount > 0 ? 'success' : 'error', 
        text: `${successCount} envoyé(s) vers ${forceSendCRM.toUpperCase()}, ${errorCount} erreur(s)` 
      });
      setShowMassForceSendModal(false);
      loadData();
    } catch (e) {
      setActionMessage({ type: 'error', text: e.message });
    } finally {
      setActionLoading(false);
      setTimeout(() => setActionMessage(null), 3000);
    }
  };

  // ==================== EXPORT ====================

  const exportCSV = () => {
    const filtered = filteredLeads;
    const headers = [
      'Téléphone', 'Nom', 'Prénom', 'Civilité', 'Email', 
      'Département', 'Ville', 'Adresse',
      'Type Logement', 'Statut Occupant', 'Surface', 'Année Construction', 'Type Chauffage',
      'Facture Électricité', 'Facture Chauffage',
      'Type Projet', 'Délai', 'Budget',
      'Formulaire', 'LP', 'Liaison', 'Source', 'UTM Source', 'UTM Medium', 'UTM Campaign',
      'CRM Origine', 'CRM Cible', 'Transféré', 'Statut', 'Date'
    ];
    const rows = filtered.map(l => [
      l.phone, l.nom, l.prenom, l.civilite, l.email,
      l.departement, l.ville, l.adresse,
      l.type_logement, l.statut_occupant, l.surface_habitable, l.annee_construction, l.type_chauffage,
      l.facture_electricite, l.facture_chauffage,
      l.type_projet, l.delai_projet, l.budget,
      l.form_code, l.lp_code, l.liaison_code, l.source, l.utm_source, l.utm_medium, l.utm_campaign,
      l.origin_crm, l.target_crm, l.is_transferred ? 'Oui' : 'Non', l.api_status,
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

  // ==================== HELPERS ====================

  const filteredLeads = filter === 'all' ? leads : leads.filter(l => l.api_status === filter);

  const statusVariant = (status) => {
    switch (status) {
      case 'success': return 'success';
      case 'duplicate': return 'warning';
      case 'queued': return 'info';
      case 'failed': return 'danger';
      case 'no_crm': return 'secondary';
      case 'no_api_key': return 'warning';
      case 'orphan': return 'danger';
      case 'invalid_phone': return 'danger';
      case 'missing_required': return 'danger';
      case 'pending_no_order': return 'warning';
      case 'pending_manual': return 'info';
      default: return 'default';
    }
  };

  const statusLabel = (status) => {
    switch (status) {
      case 'success': return 'Envoyé';
      case 'duplicate': return 'Doublon';
      case 'queued': return 'En file';
      case 'failed': return 'Échec';
      case 'no_crm': return 'Sans CRM';
      case 'no_api_key': return 'Sans clé';
      case 'orphan': return 'Orphelin';
      case 'invalid_phone': return 'Tél invalide';
      case 'missing_required': return 'Incomplet';
      case 'pending_no_order': return 'En attente';
      case 'pending_manual': return 'Manuel requis';
      default: return status;
    }
  };

  const getAccountName = (accountId) => {
    const acc = accounts.find(a => a.id === accountId);
    return acc?.name || accountId?.substring(0, 8) || '-';
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-purple-100 to-purple-200 rounded-xl">
            <Users className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Leads {currentCRM?.name || ''}</h1>
            <p className="text-slate-500 text-sm">{filteredLeads.length} lead(s)</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
          </Button>
          <Button variant="outline" onClick={exportCSV}>
            <Download className="w-4 h-4 mr-2" /> Export CSV
          </Button>
        </div>
      </div>

      {/* Message */}
      {actionMessage && (
        <div className={`p-3 rounded-lg ${
          actionMessage.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {actionMessage.text}
        </div>
      )}

      {/* Mass Actions Bar */}
      {isAdmin && selectedLeadIds.length > 0 && (
        <Card className="p-4 bg-amber-50 border-amber-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-amber-600" />
              <span className="font-medium text-amber-800">
                {selectedLeadIds.length} lead(s) sélectionné(s)
              </span>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={openMassEditModal}>
                <Edit className="w-4 h-4 mr-1" /> Modifier
              </Button>
              <Button size="sm" variant="outline" onClick={openMassForceSendModal}>
                <Send className="w-4 h-4 mr-1" /> Forcer envoi
              </Button>
              <Button size="sm" variant="danger" onClick={openMassDeleteModal}>
                <Trash2 className="w-4 h-4 mr-1" /> Supprimer
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setSelectedLeadIds([]); setSelectAll(false); }}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Status filter */}
          <div className="flex gap-2 flex-wrap">
            {['all', 'success', 'failed', 'no_api_key', 'missing_required', 'invalid_phone', 'orphan', 'pending_no_order'].map(s => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  filter === s 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {s === 'all' ? 'Tous' : statusLabel(s)}
              </button>
            ))}
          </div>

          {/* Transferred filter */}
          <select
            value={transferredFilter === null ? '' : transferredFilter.toString()}
            onChange={(e) => setTransferredFilter(e.target.value === '' ? null : e.target.value === 'true')}
            className="px-3 py-1 border rounded-lg text-sm"
          >
            <option value="">Tous (transfert)</option>
            <option value="true">Transférés</option>
            <option value="false">Non transférés</option>
          </select>

          {/* Date filters */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-2 py-1 border rounded-lg text-sm"
              placeholder="Du"
            />
            <span className="text-slate-400">→</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-2 py-1 border rounded-lg text-sm"
              placeholder="Au"
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                {isAdmin && (
                  <th className="px-4 py-3 text-left">
                    <button onClick={toggleSelectAll} className="p-1 hover:bg-slate-200 rounded">
                      {selectAll ? <CheckSquare className="w-5 h-5 text-purple-600" /> : <Square className="w-5 h-5 text-slate-400" />}
                    </button>
                  </th>
                )}
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Téléphone</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Contact</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Dept</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Formulaire</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Qualité</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Routage</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Statut</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLeads.map(lead => (
                <tr key={lead.id} className="hover:bg-slate-50">
                  {isAdmin && (
                    <td className="px-4 py-3">
                      <button onClick={() => toggleSelectLead(lead.id)} className="p-1 hover:bg-slate-200 rounded">
                        {selectedLeadIds.includes(lead.id) 
                          ? <CheckSquare className="w-5 h-5 text-purple-600" /> 
                          : <Square className="w-5 h-5 text-slate-400" />
                        }
                      </button>
                    </td>
                  )}
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {new Date(lead.created_at).toLocaleDateString('fr-FR')}
                    <br />
                    <span className="text-xs">{new Date(lead.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm">{lead.phone}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium text-slate-800">{lead.nom} {lead.prenom}</div>
                    {lead.email && <div className="text-xs text-slate-500">{lead.email}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center justify-center w-8 h-8 bg-slate-100 rounded-full text-sm font-medium">
                      {lead.departement || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm font-mono text-purple-600">{lead.form_code}</span>
                  </td>
                  <td className="px-4 py-3">
                    {lead.quality_tier === 1 && (
                      <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">Premium</span>
                    )}
                    {lead.quality_tier === 2 && (
                      <span className="px-2 py-1 text-xs font-medium bg-orange-100 text-orange-700 rounded-full">Standard</span>
                    )}
                    {lead.quality_tier === 3 && (
                      <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-full">Low</span>
                    )}
                    {!lead.quality_tier && (
                      <span className="px-2 py-1 text-xs font-medium bg-slate-100 text-slate-500 rounded-full">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-xs">
                      <span className="px-2 py-0.5 bg-slate-100 rounded">{lead.origin_crm || '?'}</span>
                      <ArrowRightLeft className="w-3 h-3 text-slate-400" />
                      <span className={`px-2 py-0.5 rounded ${lead.target_crm === 'zr7' ? 'bg-blue-100 text-blue-700' : lead.target_crm === 'mdl' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100'}`}>
                        {lead.target_crm || 'none'}
                      </span>
                      {lead.is_transferred && (
                        <span className="px-1 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">T</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={statusVariant(lead.api_status)}>
                      {statusLabel(lead.api_status)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => viewLead(lead)} className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded" title="Voir">
                        <Eye className="w-4 h-4" />
                      </button>
                      {isAdmin && (
                        <>
                          <button onClick={() => openEditModal(lead)} className="p-1.5 text-blue-400 hover:text-blue-600 hover:bg-blue-50 rounded" title="Modifier">
                            <Edit className="w-4 h-4" />
                          </button>
                          <button onClick={() => openForceSendModal(lead)} className="p-1.5 text-green-400 hover:text-green-600 hover:bg-green-50 rounded" title="Forcer envoi">
                            <Send className="w-4 h-4" />
                          </button>
                          <button onClick={() => openDeleteModal(lead)} className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded" title="Supprimer">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                      {['failed', 'queued'].includes(lead.api_status) && (
                        <button onClick={() => retryLead(lead.id)} className="p-1.5 text-amber-400 hover:text-amber-600 hover:bg-amber-50 rounded" title="Relancer">
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {filteredLeads.length === 0 && (
          <div className="text-center py-12 text-slate-500">
            Aucun lead trouvé avec ces filtres.
          </div>
        )}
      </Card>

      {/* ==================== MODALS ==================== */}

      {/* Detail Modal */}
      <Modal isOpen={showDetailModal} onClose={() => setShowDetailModal(false)} title="Détail du lead" size="lg">
        {selectedLead && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-x-6 gap-y-2">
              {['phone', 'nom', 'prenom', 'email', 'departement', 'type_logement', 'statut_occupant', 'surface_habitable', 'annee_construction', 'type_chauffage', 'facture_electricite', 'facture_chauffage'].map((key) => {
                const value = selectedLead[key];
                const displayValue = (value !== null && value !== undefined && value !== '') ? String(value) : '—';
                
                return (
                  <div key={key} className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-sm text-slate-500 font-mono">{key}</span>
                    <span className="text-sm font-medium text-slate-700">{displayValue}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Modal>

      {/* Edit Modal */}
      <Modal isOpen={showEditModal} onClose={() => setShowEditModal(false)} title="Modifier le lead" size="md">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Téléphone" value={editForm.phone} onChange={e => setEditForm({...editForm, phone: e.target.value})} />
            <Input label="Email" value={editForm.email} onChange={e => setEditForm({...editForm, email: e.target.value})} />
            <Input label="Nom" value={editForm.nom} onChange={e => setEditForm({...editForm, nom: e.target.value})} />
            <Input label="Prénom" value={editForm.prenom} onChange={e => setEditForm({...editForm, prenom: e.target.value})} />
            <Input label="Département" value={editForm.departement} onChange={e => setEditForm({...editForm, departement: e.target.value})} />
            <Input label="Ville" value={editForm.ville} onChange={e => setEditForm({...editForm, ville: e.target.value})} />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes admin</label>
            <textarea 
              value={editForm.notes_admin} 
              onChange={e => setEditForm({...editForm, notes_admin: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              rows={3}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowEditModal(false)}>Annuler</Button>
            <Button onClick={saveLead} disabled={actionLoading}>
              {actionLoading ? 'Enregistrement...' : 'Enregistrer'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Modal */}
      <Modal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)} title="Supprimer le lead" size="sm">
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-red-600" />
            <div>
              <p className="font-medium text-red-800">Action irréversible</p>
              <p className="text-sm text-red-600">Le lead {selectedLead?.phone} sera définitivement supprimé.</p>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>Annuler</Button>
            <Button variant="danger" onClick={deleteLead} disabled={actionLoading}>
              {actionLoading ? 'Suppression...' : 'Supprimer'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Force Send Modal */}
      <Modal isOpen={showForceSendModal} onClose={() => setShowForceSendModal(false)} title="Forcer envoi vers CRM" size="sm">
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Choisissez le CRM vers lequel envoyer le lead <strong>{selectedLead?.phone}</strong>
          </p>
          <div className="flex gap-4">
            <button
              onClick={() => setForceSendCRM('zr7')}
              className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                forceSendCRM === 'zr7' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="font-semibold text-blue-700">ZR7 Digital</div>
              <div className="text-xs text-slate-500">zr7</div>
            </button>
            <button
              onClick={() => setForceSendCRM('mdl')}
              className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                forceSendCRM === 'mdl' ? 'border-purple-500 bg-purple-50' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="font-semibold text-purple-700">Maison du Lead</div>
              <div className="text-xs text-slate-500">mdl</div>
            </button>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowForceSendModal(false)}>Annuler</Button>
            <Button onClick={forceSendLead} disabled={!forceSendCRM || actionLoading}>
              {actionLoading ? 'Envoi...' : 'Envoyer'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Mass Edit Modal */}
      <Modal isOpen={showMassEditModal} onClose={() => setShowMassEditModal(false)} title={`Modifier ${selectedLeadIds.length} leads`} size="md">
        <div className="space-y-4">
          <p className="text-sm text-slate-600 bg-amber-50 p-3 rounded">
            Seuls les champs remplis seront modifiés. Laissez vide pour ne pas changer.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Département" value={massEditForm.departement} onChange={e => setMassEditForm({...massEditForm, departement: e.target.value})} placeholder="Laisser vide pour ne pas changer" />
            <Input label="Ville" value={massEditForm.ville} onChange={e => setMassEditForm({...massEditForm, ville: e.target.value})} placeholder="Laisser vide pour ne pas changer" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes admin</label>
            <textarea 
              value={massEditForm.notes_admin} 
              onChange={e => setMassEditForm({...massEditForm, notes_admin: e.target.value})}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              rows={2}
              placeholder="Laisser vide pour ne pas changer"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowMassEditModal(false)}>Annuler</Button>
            <Button onClick={saveMassEdit} disabled={actionLoading}>
              {actionLoading ? 'Modification...' : `Modifier ${selectedLeadIds.length} leads`}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Mass Delete Modal */}
      <Modal isOpen={showMassDeleteModal} onClose={() => setShowMassDeleteModal(false)} title="Supprimer les leads" size="sm">
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-red-600" />
            <div>
              <p className="font-medium text-red-800">Action irréversible</p>
              <p className="text-sm text-red-600">{selectedLeadIds.length} lead(s) seront définitivement supprimés.</p>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowMassDeleteModal(false)}>Annuler</Button>
            <Button variant="danger" onClick={massDeleteLeads} disabled={actionLoading}>
              {actionLoading ? 'Suppression...' : `Supprimer ${selectedLeadIds.length} leads`}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Mass Force Send Modal */}
      <Modal isOpen={showMassForceSendModal} onClose={() => setShowMassForceSendModal(false)} title={`Forcer envoi de ${selectedLeadIds.length} leads`} size="sm">
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Choisissez le CRM vers lequel envoyer les {selectedLeadIds.length} leads sélectionnés.
          </p>
          <div className="flex gap-4">
            <button
              onClick={() => setForceSendCRM('zr7')}
              className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                forceSendCRM === 'zr7' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="font-semibold text-blue-700">ZR7 Digital</div>
            </button>
            <button
              onClick={() => setForceSendCRM('mdl')}
              className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                forceSendCRM === 'mdl' ? 'border-purple-500 bg-purple-50' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="font-semibold text-purple-700">Maison du Lead</div>
            </button>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowMassForceSendModal(false)}>Annuler</Button>
            <Button onClick={massForceSend} disabled={!forceSendCRM || actionLoading}>
              {actionLoading ? 'Envoi...' : `Envoyer ${selectedLeadIds.length} leads`}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
