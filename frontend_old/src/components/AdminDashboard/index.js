import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Users, 
  CheckCircle, 
  XCircle, 
  RefreshCw, 
  Download,
  Eye,
  ChevronRight,
  Search,
  Copy,
  AlertTriangle,
  HelpCircle,
  Code,
  BookOpen,
  Settings,
  Plus,
  ExternalLink,
  Info,
  Check,
  X
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
  const [activeTab, setActiveTab] = useState('dashboard'); // dashboard, guide, integration
  const [showCodeModal, setShowCodeModal] = useState(null);
  const [copiedCode, setCopiedCode] = useState(false);

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

  // Copier le code
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
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
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
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
                <p className="text-xs text-muted-foreground">Gestion centralisée des formulaires et leads</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={loadData}>
                <RefreshCw className="w-4 h-4 mr-1" />
                Actualiser
              </Button>
            </div>
          </div>
          
          {/* Navigation Tabs */}
          <div className="flex gap-1 mt-4 border-b border-border -mb-4">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'dashboard' 
                  ? 'border-primary text-primary' 
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <BarChart3 className="w-4 h-4 inline mr-2" />
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('guide')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'guide' 
                  ? 'border-primary text-primary' 
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <BookOpen className="w-4 h-4 inline mr-2" />
              Guide d'utilisation
            </button>
            <button
              onClick={() => setActiveTab('integration')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'integration' 
                  ? 'border-primary text-primary' 
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Code className="w-4 h-4 inline mr-2" />
              Intégration
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        
        {/* TAB: Dashboard */}
        {activeTab === 'dashboard' && (
          <>
            {/* Bandeau explicatif */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <div className="flex gap-3">
                <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-800">
                    <strong>Comment lire ce dashboard :</strong> Chaque lead qui arrive via un formulaire est enregistré ici. 
                    Les statistiques sont groupées par formulaire (identifié par son <code className="bg-blue-100 px-1 rounded">form_id</code>).
                  </p>
                </div>
              </div>
            </div>

            {/* Stats globales avec explications */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <StatCard 
                icon={Users} 
                label="Total Leads" 
                value={stats?.total || 0} 
                color="primary"
                tooltip="Nombre total de leads reçus depuis tous les formulaires"
              />
              <StatCard 
                icon={CheckCircle} 
                label="Envoyés" 
                value={stats?.success || 0} 
                color="green"
                tooltip="Leads envoyés avec succès à l'API externe (maison-du-lead.com ou autre)"
              />
              <StatCard 
                icon={XCircle} 
                label="Échecs" 
                value={stats?.failed || 0} 
                color="red"
                action={stats?.failed > 0 ? () => handleRetryFailed() : null}
                actionLabel="Retry tous"
                actionLoading={retrying}
                tooltip="Leads qui n'ont pas pu être envoyés à l'API (erreur réseau, API down, etc.). Cliquez sur Retry pour réessayer."
              />
              <StatCard 
                icon={Copy} 
                label="Doublons" 
                value={stats?.duplicate || 0} 
                color="orange"
                tooltip="Leads déjà existants dans l'API externe (même numéro de téléphone)"
              />
            </div>

            {/* Liste des formulaires */}
            <div className="bg-card rounded-xl border border-border p-4 mb-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-foreground">
                    Formulaires ({forms.length})
                  </h2>
                  <Tooltip text="Chaque formulaire a un identifiant unique (form_id). Les leads sont automatiquement groupés par formulaire." />
                </div>
                <Button variant="outline" size="sm" onClick={() => setActiveTab('integration')}>
                  <Plus className="w-4 h-4 mr-1" />
                  Ajouter un formulaire
                </Button>
              </div>
              
              {forms.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground bg-secondary/30 rounded-lg">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="font-medium">Aucun formulaire détecté</p>
                  <p className="text-sm mt-1">Les formulaires apparaissent automatiquement dès qu'un lead est reçu.</p>
                  <Button variant="outline" size="sm" className="mt-3" onClick={() => setActiveTab('integration')}>
                    Voir comment intégrer un formulaire
                  </Button>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {forms.map(form => (
                    <FormCard 
                      key={form.form_id} 
                      form={form} 
                      onSelect={() => {
                        setSelectedForm(form.form_id);
                      }}
                      onRetry={() => handleRetryFailed(form.form_id)}
                      onShowCode={() => setShowCodeModal(form)}
                      retrying={retrying}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Filtres et liste des leads */}
            <div className="bg-card rounded-xl border border-border p-4">
              <div className="flex items-center gap-2 mb-4">
                <h2 className="text-lg font-semibold text-foreground">Détail des leads</h2>
                <Tooltip text="Liste de tous les leads reçus. Utilisez les filtres pour affiner la recherche." />
                <div className="ml-auto">
                  <Button variant="outline" size="sm" onClick={handleExportCSV}>
                    <Download className="w-4 h-4 mr-1" />
                    Export CSV
                  </Button>
                </div>
              </div>

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
                    <option value="success">✅ Succès</option>
                    <option value="failed">❌ Échec</option>
                    <option value="duplicate">🔄 Doublon</option>
                    <option value="pending">⏳ En attente</option>
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
              
              {filteredLeads.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Aucun lead trouvé avec ces critères</p>
                </div>
              )}
            </div>
          </>
        )}

        {/* TAB: Guide */}
        {activeTab === 'guide' && (
          <GuideSection />
        )}

        {/* TAB: Intégration */}
        {activeTab === 'integration' && (
          <IntegrationSection backendUrl={BACKEND_URL} onCopy={copyToClipboard} copied={copiedCode} />
        )}

      </main>

      {/* Modal Code */}
      {showCodeModal && (
        <CodeModal 
          form={showCodeModal} 
          backendUrl={BACKEND_URL}
          onClose={() => setShowCodeModal(null)}
          onCopy={copyToClipboard}
          copied={copiedCode}
        />
      )}
    </div>
  );
};

// Composant Tooltip
const Tooltip = ({ text }) => {
  const [show, setShow] = useState(false);
  
  return (
    <div className="relative inline-block">
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="text-muted-foreground hover:text-foreground"
      >
        <HelpCircle className="w-4 h-4" />
      </button>
      {show && (
        <div className="absolute z-50 w-64 p-2 bg-foreground text-background text-xs rounded-lg shadow-lg -top-2 left-6">
          {text}
        </div>
      )}
    </div>
  );
};

// Composant StatCard
const StatCard = ({ icon: Icon, label, value, color, action, actionLabel, actionLoading, tooltip }) => {
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
        {tooltip && <Tooltip text={tooltip} />}
      </div>
      <p className="text-2xl font-bold text-foreground">{value}</p>
      <p className="text-sm text-muted-foreground">{label}</p>
      {action && (
        <Button 
          variant="outline" 
          size="sm" 
          onClick={action}
          disabled={actionLoading}
          className="mt-2 w-full text-xs"
        >
          {actionLoading ? <RefreshCw className="w-3 h-3 animate-spin mr-1" /> : null}
          {actionLabel}
        </Button>
      )}
    </div>
  );
};

// Composant FormCard
const FormCard = ({ form, onSelect, onRetry, onShowCode, retrying }) => {
  const successRate = form.total > 0 
    ? Math.round(((form.success + form.duplicate) / form.total) * 100) 
    : 0;

  return (
    <div className="bg-secondary/30 rounded-lg p-4 hover:bg-secondary/50 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-foreground">{form.form_name}</h3>
          <code className="text-xs text-muted-foreground bg-muted px-1 rounded">{form.form_id}</code>
        </div>
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={onShowCode} title="Voir le code d'intégration">
            <Code className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={onSelect} title="Voir les leads">
            <Eye className="w-4 h-4" />
          </Button>
        </div>
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
    success: { label: 'Envoyé', className: 'bg-green-100 text-green-700', icon: Check },
    failed: { label: 'Échec', className: 'bg-red-100 text-red-700', icon: X },
    duplicate: { label: 'Doublon', className: 'bg-orange-100 text-orange-700', icon: Copy },
    pending: { label: 'En attente', className: 'bg-gray-100 text-gray-700', icon: RefreshCw },
  };

  const { label, className, icon: Icon } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${className}`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
};

// Section Guide
const GuideSection = () => (
  <div className="space-y-6">
    <div className="bg-card rounded-xl border border-border p-6">
      <h2 className="text-xl font-bold text-foreground mb-4 flex items-center gap-2">
        <BookOpen className="w-6 h-6 text-primary" />
        Comment fonctionne ce système ?
      </h2>
      
      <div className="space-y-6">
        {/* Schéma explicatif */}
        <div className="bg-secondary/30 rounded-lg p-4">
          <h3 className="font-semibold text-foreground mb-3">🔄 Flux d'un lead</h3>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-center">
            <div className="bg-card p-4 rounded-lg border border-border flex-1">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <p className="font-medium">1. Visiteur</p>
              <p className="text-xs text-muted-foreground">Remplit le formulaire</p>
            </div>
            <ChevronRight className="w-6 h-6 text-muted-foreground hidden md:block" />
            <div className="bg-card p-4 rounded-lg border border-border flex-1">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <BarChart3 className="w-6 h-6 text-green-600" />
              </div>
              <p className="font-medium">2. Backend Central</p>
              <p className="text-xs text-muted-foreground">Sauvegarde en base de données</p>
            </div>
            <ChevronRight className="w-6 h-6 text-muted-foreground hidden md:block" />
            <div className="bg-card p-4 rounded-lg border border-border flex-1">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <ExternalLink className="w-6 h-6 text-purple-600" />
              </div>
              <p className="font-medium">3. API Externe</p>
              <p className="text-xs text-muted-foreground">Envoi vers maison-du-lead.com (ou autre)</p>
            </div>
            <ChevronRight className="w-6 h-6 text-muted-foreground hidden md:block" />
            <div className="bg-card p-4 rounded-lg border border-border flex-1">
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <Eye className="w-6 h-6 text-orange-600" />
              </div>
              <p className="font-medium">4. Dashboard</p>
              <p className="text-xs text-muted-foreground">Vous voyez le lead ici</p>
            </div>
          </div>
        </div>

        {/* Explications des statuts */}
        <div>
          <h3 className="font-semibold text-foreground mb-3">📊 Comprendre les statuts</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium text-green-800">Succès (Envoyé)</p>
                <p className="text-sm text-green-700">Le lead a été envoyé et accepté par l'API externe. Tout est OK !</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
              <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
              <div>
                <p className="font-medium text-red-800">Échec</p>
                <p className="text-sm text-red-700">L'envoi a échoué (API down, erreur réseau...). Le lead est sauvegardé, vous pouvez cliquer "Retry" pour réessayer.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg">
              <Copy className="w-5 h-5 text-orange-600 mt-0.5" />
              <div>
                <p className="font-medium text-orange-800">Doublon</p>
                <p className="text-sm text-orange-700">Ce numéro de téléphone existe déjà dans l'API externe. Le lead n'est pas perdu, il est juste déjà connu.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <RefreshCw className="w-5 h-5 text-gray-600 mt-0.5" />
              <div>
                <p className="font-medium text-gray-800">En attente</p>
                <p className="text-sm text-gray-700">Le lead est enregistré mais l'envoi n'a pas encore été tenté.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Points importants */}
        <div>
          <h3 className="font-semibold text-foreground mb-3">⚠️ Points importants</h3>
          <ul className="space-y-2">
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
              <span className="text-sm"><strong>Les leads ne sont JAMAIS perdus</strong> - Ils sont sauvegardés en base de données avant tout envoi.</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
              <span className="text-sm"><strong>Retry automatique</strong> - Vous pouvez réessayer l'envoi des leads en échec à tout moment.</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
              <span className="text-sm"><strong>Multi-formulaires</strong> - Chaque formulaire a un identifiant unique, les stats sont séparées.</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
              <span className="text-sm"><strong>Multi-API</strong> - Chaque formulaire peut envoyer vers une API différente.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
);

// Section Intégration
const IntegrationSection = ({ backendUrl, onCopy, copied }) => {
  const envCode = `REACT_APP_BACKEND_URL=${backendUrl}`;
  const apiCode = `// Fichier: api.js de votre formulaire

export const FORM_CONFIG = {
  form_id: "mon-nouveau-formulaire",    // ⬅️ Identifiant UNIQUE
  form_name: "Mon Nouveau Formulaire"   // ⬅️ Nom affiché dans le dashboard
};

// Le reste du code reste identique...`;

  const curlCode = `# Tester l'envoi d'un lead manuellement
curl -X POST "${backendUrl}/api/submit-lead" \\
  -H "Content-Type: application/json" \\
  -d '{
    "phone": "0612345678",
    "nom": "Test Lead",
    "email": "test@example.com",
    "departement": "75",
    "form_id": "mon-nouveau-formulaire",
    "form_name": "Mon Nouveau Formulaire"
  }'`;

  return (
    <div className="space-y-6">
      <div className="bg-card rounded-xl border border-border p-6">
        <h2 className="text-xl font-bold text-foreground mb-4 flex items-center gap-2">
          <Code className="w-6 h-6 text-primary" />
          Comment intégrer un nouveau formulaire ?
        </h2>

        {/* Étapes */}
        <div className="space-y-6">
          
          {/* Étape 1 */}
          <div className="border-l-4 border-primary pl-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <span className="w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm">1</span>
              Configurer l'URL du backend
            </h3>
            <p className="text-sm text-muted-foreground mt-1 mb-3">
              Dans le fichier <code className="bg-muted px-1 rounded">.env</code> de votre formulaire, ajoutez :
            </p>
            <div className="bg-gray-900 rounded-lg p-4 relative">
              <code className="text-green-400 text-sm">{envCode}</code>
              <Button 
                variant="ghost" 
                size="sm" 
                className="absolute top-2 right-2 text-white hover:bg-white/10"
                onClick={() => onCopy(envCode)}
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              ℹ️ Cette URL est la même pour TOUS vos formulaires. C'est le backend central.
            </p>
          </div>

          {/* Étape 2 */}
          <div className="border-l-4 border-primary pl-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <span className="w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm">2</span>
              Définir l'identifiant du formulaire
            </h3>
            <p className="text-sm text-muted-foreground mt-1 mb-3">
              Dans le fichier <code className="bg-muted px-1 rounded">api.js</code> de votre formulaire, modifiez :
            </p>
            <div className="bg-gray-900 rounded-lg p-4 relative overflow-x-auto">
              <pre className="text-green-400 text-sm whitespace-pre">{apiCode}</pre>
              <Button 
                variant="ghost" 
                size="sm" 
                className="absolute top-2 right-2 text-white hover:bg-white/10"
                onClick={() => onCopy(apiCode)}
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-800">
                <strong>⚠️ Important :</strong> Le <code className="bg-amber-100 px-1 rounded">form_id</code> doit être UNIQUE pour chaque formulaire. 
                Exemples : <code>pv-outbrain-2026</code>, <code>pac-taboola-mars</code>, <code>isolation-facebook</code>
              </p>
            </div>
          </div>

          {/* Étape 3 */}
          <div className="border-l-4 border-primary pl-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <span className="w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm">3</span>
              Déployer le formulaire
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Déployez votre formulaire sur n'importe quel hébergement :
            </p>
            <ul className="mt-2 space-y-1 text-sm">
              <li className="flex items-center gap-2">
                <Check className="w-4 h-4 text-green-600" />
                Sous-domaine Hostinger (ex: formulaire-pv.monsite.com)
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-4 h-4 text-green-600" />
                Vercel / Netlify (gratuit)
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-4 h-4 text-green-600" />
                En iframe sur un site WordPress
              </li>
            </ul>
          </div>

          {/* Étape 4 */}
          <div className="border-l-4 border-green-500 pl-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <span className="w-6 h-6 bg-green-500 text-white rounded-full flex items-center justify-center text-sm">4</span>
              C'est tout ! Le formulaire apparaît automatiquement
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Dès qu'un lead est soumis, le formulaire apparaît dans le dashboard avec ses statistiques.
            </p>
          </div>

          {/* Test manuel */}
          <div className="border-l-4 border-gray-300 pl-4">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Tester manuellement (optionnel)
            </h3>
            <p className="text-sm text-muted-foreground mt-1 mb-3">
              Vous pouvez tester l'envoi d'un lead avec cette commande :
            </p>
            <div className="bg-gray-900 rounded-lg p-4 relative overflow-x-auto">
              <pre className="text-green-400 text-sm whitespace-pre">{curlCode}</pre>
              <Button 
                variant="ghost" 
                size="sm" 
                className="absolute top-2 right-2 text-white hover:bg-white/10"
                onClick={() => onCopy(curlCode)}
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

// Modal Code pour un formulaire existant
const CodeModal = ({ form, backendUrl, onClose, onCopy, copied }) => {
  const code = `// Configuration pour le formulaire "${form.form_name}"

// Fichier .env
REACT_APP_BACKEND_URL=${backendUrl}

// Fichier api.js
export const FORM_CONFIG = {
  form_id: "${form.form_id}",
  form_name: "${form.form_name}"
};`;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-card rounded-xl border border-border p-6 max-w-2xl w-full" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground">
            Code d'intégration - {form.form_name}
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-4 relative">
          <pre className="text-green-400 text-sm whitespace-pre overflow-x-auto">{code}</pre>
          <Button 
            variant="ghost" 
            size="sm" 
            className="absolute top-2 right-2 text-white hover:bg-white/10"
            onClick={() => onCopy(code)}
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </Button>
        </div>

        <p className="text-sm text-muted-foreground mt-4">
          Ce formulaire envoie les leads vers : <code className="bg-muted px-1 rounded">{backendUrl}/api/submit-lead</code>
        </p>
      </div>
    </div>
  );
};

export default AdminDashboard;
