import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Users, 
  CheckCircle, 
  XCircle, 
  Clock, 
  RefreshCw, 
  Download,
  Eye,
  ChevronRight,
  Filter,
  Search,
  Copy,
  AlertTriangle,
  TrendingUp,
  Calendar
} from 'lucide-react';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [forms, setForms] = useState([]);
  const [selectedForm, setSelectedForm] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [view, setView] = useState('dashboard'); // dashboard, leads, form-detail

  // Charger les données
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, leadsRes, formsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/admin/stats`),
        fetch(`${BACKEND_URL}/api/leads`),
        fetch(`${BACKEND_URL}/api/admin/forms`)
      ]);
      
      const statsData = await statsRes.json();
      const leadsData = await leadsRes.json();
      const formsData = await formsRes.json();
      
      setStats(statsData);
      setLeads(leadsData.leads || []);
      setForms(formsData.forms || []);
    } catch (error) {
      console.error('Error loading data:', error);
    }
    setLoading(false);
  };

  // Retry failed leads
  const handleRetryFailed = async (formId = null) => {
    setRetrying(true);
    try {
      const url = formId 
        ? `${BACKEND_URL}/api/leads/retry-failed?form_id=${formId}`
        : `${BACKEND_URL}/api/leads/retry-failed`;
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      alert(`Résultat: ${data.success} succès, ${data.failed} échecs sur ${data.retried} tentatives`);
      loadData();
    } catch (error) {
      alert('Erreur lors du retry');
    }
    setRetrying(false);
  };

  // Export CSV
  const handleExportCSV = () => {
    const filteredLeads = getFilteredLeads();
    const headers = ['Date', 'Formulaire', 'Nom', 'Téléphone', 'Email', 'Département', 'Statut API'];
    const rows = filteredLeads.map(lead => [
      new Date(lead.created_at).toLocaleString('fr-FR'),
      lead.form_name || lead.form_id || 'N/A',
      lead.nom,
      lead.phone,
      lead.email,
      lead.departement,
      lead.api_status
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `leads_export_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // Filtrer les leads
  const getFilteredLeads = () => {
    return leads.filter(lead => {
      const matchForm = selectedForm === 'all' || lead.form_id === selectedForm;
      const matchStatus = selectedStatus === 'all' || lead.api_status === selectedStatus;
      const matchSearch = !searchTerm || 
        lead.nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.phone?.includes(searchTerm) ||
        lead.email?.toLowerCase().includes(searchTerm.toLowerCase());
      return matchForm && matchStatus && matchSearch;
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="spinner w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Chargement du dashboard...</p>
        </div>
      </div>
    );
  }

  const filteredLeads = getFilteredLeads();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">Dashboard Admin</h1>
                <p className="text-xs text-muted-foreground">Gestion des formulaires et leads</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={loadData}>
                <RefreshCw className="w-4 h-4 mr-1" />
                Actualiser
              </Button>
              <Button variant="outline" size="sm" onClick={handleExportCSV}>
                <Download className="w-4 h-4 mr-1" />
                Export CSV
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats globales */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard 
            icon={Users} 
            label="Total Leads" 
            value={stats?.total || 0} 
            color="primary"
          />
          <StatCard 
            icon={CheckCircle} 
            label="Envoyés" 
            value={stats?.success || 0} 
            color="green"
          />
          <StatCard 
            icon={XCircle} 
            label="Échecs" 
            value={stats?.failed || 0} 
            color="red"
            action={stats?.failed > 0 ? () => handleRetryFailed() : null}
            actionLabel="Retry"
            actionLoading={retrying}
          />
          <StatCard 
            icon={Copy} 
            label="Doublons" 
            value={stats?.duplicate || 0} 
            color="orange"
          />
        </div>

        {/* Liste des formulaires */}
        <div className="bg-card rounded-xl border border-border p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary" />
              Formulaires ({forms.length})
            </h2>
          </div>
          
          {forms.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Aucun formulaire configuré</p>
              <p className="text-sm">Les formulaires apparaîtront ici automatiquement</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {forms.map(form => (
                <FormCard 
                  key={form.form_id} 
                  form={form} 
                  onSelect={() => {
                    setSelectedForm(form.form_id);
                    setView('leads');
                  }}
                  onRetry={() => handleRetryFailed(form.form_id)}
                  retrying={retrying}
                />
              ))}
            </div>
          )}
        </div>

        {/* Filtres et liste des leads */}
        <div className="bg-card rounded-xl border border-border p-4">
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Rechercher par nom, téléphone, email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-secondary/50 border border-border rounded-lg text-sm"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <select
                value={selectedForm}
                onChange={(e) => setSelectedForm(e.target.value)}
                className="px-3 py-2 bg-secondary/50 border border-border rounded-lg text-sm"
              >
                <option value="all">Tous les formulaires</option>
                {forms.map(form => (
                  <option key={form.form_id} value={form.form_id}>{form.form_name}</option>
                ))}
              </select>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="px-3 py-2 bg-secondary/50 border border-border rounded-lg text-sm"
              >
                <option value="all">Tous les statuts</option>
                <option value="success">Succès</option>
                <option value="failed">Échec</option>
                <option value="duplicate">Doublon</option>
                <option value="pending">En attente</option>
              </select>
            </div>
          </div>

          <div className="text-sm text-muted-foreground mb-3">
            {filteredLeads.length} lead(s) trouvé(s)
          </div>

          {/* Table des leads */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Date</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Formulaire</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Nom</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Téléphone</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Dept</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Statut</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.slice(0, 50).map((lead, idx) => (
                  <tr key={lead.id || idx} className="border-b border-border/50 hover:bg-secondary/30">
                    <td className="py-3 px-2 text-muted-foreground">
                      {new Date(lead.created_at).toLocaleDateString('fr-FR')}
                      <br />
                      <span className="text-xs">{new Date(lead.created_at).toLocaleTimeString('fr-FR')}</span>
                    </td>
                    <td className="py-3 px-2">
                      <span className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full">
                        {lead.form_name || lead.form_id || 'N/A'}
                      </span>
                    </td>
                    <td className="py-3 px-2 font-medium text-foreground">{lead.nom}</td>
                    <td className="py-3 px-2 text-foreground">{lead.phone}</td>
                    <td className="py-3 px-2 text-foreground">{lead.departement}</td>
                    <td className="py-3 px-2">
                      <StatusBadge status={lead.api_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {filteredLeads.length > 50 && (
            <p className="text-center text-sm text-muted-foreground mt-4">
              Affichage des 50 premiers résultats. Utilisez l'export CSV pour tout télécharger.
            </p>
          )}
        </div>
      </main>
    </div>
  );
};

// Composant StatCard
const StatCard = ({ icon: Icon, label, value, color, action, actionLabel, actionLoading }) => {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    orange: 'bg-orange-100 text-orange-600',
  };

  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <div className="flex items-center justify-between mb-2">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        {action && (
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={action}
            disabled={actionLoading}
            className="text-xs"
          >
            {actionLoading ? <RefreshCw className="w-3 h-3 animate-spin" /> : actionLabel}
          </Button>
        )}
      </div>
      <p className="text-2xl font-bold text-foreground">{value}</p>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
};

// Composant FormCard
const FormCard = ({ form, onSelect, onRetry, retrying }) => {
  const successRate = form.total > 0 
    ? Math.round(((form.success + form.duplicate) / form.total) * 100) 
    : 0;

  return (
    <div className="bg-secondary/30 rounded-lg p-4 hover:bg-secondary/50 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-foreground">{form.form_name}</h3>
          <p className="text-xs text-muted-foreground">{form.form_id}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={onSelect}>
          <Eye className="w-4 h-4" />
        </Button>
      </div>
      
      <div className="grid grid-cols-4 gap-2 text-center mb-3">
        <div>
          <p className="text-lg font-bold text-foreground">{form.total}</p>
          <p className="text-xs text-muted-foreground">Total</p>
        </div>
        <div>
          <p className="text-lg font-bold text-green-600">{form.success}</p>
          <p className="text-xs text-muted-foreground">Envoyés</p>
        </div>
        <div>
          <p className="text-lg font-bold text-red-600">{form.failed}</p>
          <p className="text-xs text-muted-foreground">Échecs</p>
        </div>
        <div>
          <p className="text-lg font-bold text-orange-600">{form.duplicate}</p>
          <p className="text-xs text-muted-foreground">Doublons</p>
        </div>
      </div>

      <div className="mb-2">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-muted-foreground">Taux de succès</span>
          <span className="font-medium text-foreground">{successRate}%</span>
        </div>
        <Progress value={successRate} className="h-1.5" />
      </div>

      {form.failed > 0 && (
        <Button 
          variant="outline" 
          size="sm" 
          className="w-full mt-2"
          onClick={onRetry}
          disabled={retrying}
        >
          {retrying ? (
            <RefreshCw className="w-3 h-3 animate-spin mr-1" />
          ) : (
            <RefreshCw className="w-3 h-3 mr-1" />
          )}
          Retry {form.failed} échec(s)
        </Button>
      )}
    </div>
  );
};

// Composant StatusBadge
const StatusBadge = ({ status }) => {
  const config = {
    success: { label: 'Envoyé', className: 'bg-green-100 text-green-700' },
    failed: { label: 'Échec', className: 'bg-red-100 text-red-700' },
    duplicate: { label: 'Doublon', className: 'bg-orange-100 text-orange-700' },
    pending: { label: 'En attente', className: 'bg-gray-100 text-gray-700' },
  };

  const { label, className } = config[status] || config.pending;

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${className}`}>
      {label}
    </span>
  );
};

export default AdminDashboard;
