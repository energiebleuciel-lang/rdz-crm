/**
 * Page Leads
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Loading, Badge, Button } from '../components/UI';
import { Users, RefreshCw, Download, Filter } from 'lucide-react';

export default function Leads() {
  const { authFetch } = useAuth();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await authFetch(`${API}/api/leads?limit=200`);
      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const retryLead = async (leadId) => {
    try {
      const res = await authFetch(`${API}/api/leads/${leadId}/retry`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Retry: ${data.status}`);
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const exportCSV = () => {
    const filtered = filteredLeads;
    const headers = ['Téléphone', 'Nom', 'Prénom', 'Email', 'Code Postal', 'Formulaire', 'LP', 'Statut', 'Date'];
    const rows = filtered.map(l => [
      l.phone,
      l.nom,
      l.prenom,
      l.email,
      l.code_postal,
      l.form_code,
      l.lp_code,
      l.api_status,
      new Date(l.created_at).toLocaleDateString('fr-FR')
    ]);
    
    const csv = [headers, ...rows].map(r => r.join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
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
      default: return 'default';
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Leads</h1>
        
        <div className="flex items-center gap-3">
          {/* Filtres */}
          <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
            {[
              { value: 'all', label: 'Tous' },
              { value: 'success', label: 'Envoyés' },
              { value: 'failed', label: 'Échoués' },
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
                <th className="text-left p-4 text-sm font-medium text-slate-600">CP</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Form</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">LP</th>
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
                  <td className="p-4">{lead.nom} {lead.prenom}</td>
                  <td className="p-4 text-sm text-slate-600">{lead.email}</td>
                  <td className="p-4">{lead.code_postal}</td>
                  <td className="p-4">
                    <Badge variant="info">{lead.form_code}</Badge>
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {lead.lp_code || '-'}
                  </td>
                  <td className="p-4 text-sm">
                    {lead.target_crm_slug?.toUpperCase() || '-'}
                  </td>
                  <td className="p-4">
                    <Badge variant={statusVariant(lead.api_status)}>
                      {lead.api_status}
                    </Badge>
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {new Date(lead.created_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="p-4">
                    {lead.api_status === 'failed' && (
                      <button
                        onClick={() => retryLead(lead.id)}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        Retry
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {filteredLeads.length === 0 && (
                <tr>
                  <td colSpan={10} className="p-8 text-center text-slate-500">
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
    </div>
  );
}
