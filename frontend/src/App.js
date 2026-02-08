import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  BarChart3, Users, CheckCircle, XCircle, RefreshCw, Download, Eye, Search, Copy, 
  Settings, Plus, LogOut, Home, Layers, FileText, TrendingUp, MessageSquare, 
  Activity, ChevronRight, ChevronDown, Edit, Trash2, ExternalLink, Code,
  Building, Globe, Image, Shield, Bell, Filter, Calendar, Award, AlertTriangle,
  HelpCircle, BookOpen, Zap, Target, MousePointer, Send, Database, Lock,
  FolderOpen, Tag, Link2, Clipboard
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

// ==================== AUTH CONTEXT ====================
const AuthContext = createContext(null);

const useAuth = () => useContext(AuthContext);

// ==================== CRM CONTEXT ====================
const CRMContext = createContext(null);

const useCRM = () => useContext(CRMContext);

const CRMProvider = ({ children }) => {
  const [selectedCRM, setSelectedCRM] = useState(localStorage.getItem('selectedCRM') || '');
  const [crms, setCrms] = useState([]);

  const selectCRM = (crmId) => {
    setSelectedCRM(crmId);
    localStorage.setItem('selectedCRM', crmId);
  };

  return (
    <CRMContext.Provider value={{ selectedCRM, selectCRM, crms, setCrms }}>
      {children}
    </CRMContext.Provider>
  );
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const res = await fetch(`${API}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        logout();
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const login = async (email, password) => {
    const res = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem('token', data.token);
      setToken(data.token);
      setUser(data.user);
      return { success: true };
    }
    return { success: false, error: data.detail || 'Erreur de connexion' };
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const authFetch = async (url, options = {}) => {
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading, authFetch }}>
      {children}
    </AuthContext.Provider>
  );
};

// ==================== COMPONENTS ====================

const Sidebar = () => {
  const { user, logout, authFetch } = useAuth();
  const { selectedCRM, selectCRM, crms, setCrms } = useCRM();
  const location = useLocation();

  useEffect(() => {
    loadCRMs();
  }, []);

  const loadCRMs = async () => {
    try {
      const res = await authFetch(`${API}/api/crms`);
      if (res.ok) {
        const data = await res.json();
        setCrms(data.crms || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const isActive = (path) => location.pathname.startsWith(path);

  // Menu réorganisé logiquement
  const menuItems = [
    { path: '/dashboard', icon: Home, label: 'Tableau de bord' },
    { path: '/compare', icon: BarChart3, label: 'Comparatif' },
  ];

  // Section: Gestion
  const gestionItems = [
    { path: '/leads', icon: Users, label: 'Leads' },
    { path: '/accounts', icon: Building, label: 'Comptes' },
    { path: '/lps', icon: Layers, label: 'Landing Pages' },
    { path: '/forms', icon: FileText, label: 'Formulaires' },
  ];

  // Section: Outils
  const outilsItems = [
    { path: '/generator', icon: Code, label: 'Générateur Scripts' },
    { path: '/assets', icon: FolderOpen, label: 'Bibliothèque Assets' },
    { path: '/analytics', icon: TrendingUp, label: 'Analytics détaillé' },
  ];

  // Section: Configuration
  const configItems = [
    { path: '/diffusion', icon: Send, label: 'Sources Diffusion' },
    { path: '/products', icon: Tag, label: 'Types Produits' },
  ];

  // Section: Administration
  const adminItems = [
    { path: '/users', icon: Shield, label: 'Utilisateurs' },
    { path: '/activity', icon: Activity, label: 'Journal activité' },
    { path: '/settings', icon: Settings, label: 'Paramètres' },
    { path: '/guide', icon: HelpCircle, label: 'Guide d\'utilisation' },
  ];

  return (
    <div className="w-64 bg-slate-900 text-white min-h-screen flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          CRM Dashboard
        </h1>
        <p className="text-xs text-slate-400 mt-1">Gestion des leads</p>
      </div>

      {/* CRM Selector */}
      <div className="p-4 border-b border-slate-700">
        <label className="block text-xs text-slate-400 mb-2">Sélectionner le CRM</label>
        <select
          value={selectedCRM}
          onChange={e => selectCRM(e.target.value)}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Tous les CRMs</option>
          {crms.map(crm => (
            <option key={crm.id} value={crm.id}>{crm.name}</option>
          ))}
        </select>
        {selectedCRM && (
          <div className="mt-2 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${crms.find(c => c.id === selectedCRM)?.slug === 'mdl' ? 'bg-blue-500' : 'bg-green-500'}`} />
            <span className="text-xs text-slate-300">
              {crms.find(c => c.id === selectedCRM)?.name}
            </span>
          </div>
        )}
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {/* Dashboards */}
        {menuItems.map(item => (
          <Link key={item.path} to={item.path} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive(item.path) ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        ))}

        {/* Gestion */}
        <div className="pt-4 pb-2">
          <p className="text-xs text-slate-500 uppercase tracking-wider px-3">Gestion</p>
        </div>
        {gestionItems.map(item => (
          <Link key={item.path} to={item.path} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive(item.path) ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        ))}

        {/* Outils */}
        <div className="pt-4 pb-2">
          <p className="text-xs text-slate-500 uppercase tracking-wider px-3">Outils</p>
        </div>
        {outilsItems.map(item => (
          <Link key={item.path} to={item.path} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive(item.path) ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        ))}

        {/* Configuration */}
        <div className="pt-4 pb-2">
          <p className="text-xs text-slate-500 uppercase tracking-wider px-3">Configuration</p>
        </div>
        {configItems.map(item => (
          <Link key={item.path} to={item.path} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive(item.path) ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        ))}

        {/* Administration (admin only) */}
        {user?.role === 'admin' && (
          <>
            <div className="pt-4 pb-2">
              <p className="text-xs text-slate-500 uppercase tracking-wider px-3">Administration</p>
            </div>
            {adminItems.map(item => (
              <Link key={item.path} to={item.path} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive(item.path) ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            ))}
          </>
        )}
      </nav>

      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
            {user?.nom?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.nom}</p>
            <p className="text-xs text-slate-400 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Déconnexion
        </button>
      </div>
    </div>
  );
};

const StatCard = ({ icon: Icon, label, value, color = 'blue', trend, onClick }) => {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    orange: 'bg-orange-100 text-orange-600',
    purple: 'bg-purple-100 text-purple-600'
  };

  return (
    <div 
      className={`bg-white rounded-xl p-4 shadow-sm border border-slate-200 ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        {trend && (
          <span className={`text-xs font-medium ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-slate-800">{value}</p>
      <p className="text-sm text-slate-500">{label}</p>
    </div>
  );
};

const Table = ({ columns, data, onRowClick }) => (
  <div className="overflow-x-auto">
    <table className="w-full">
      <thead>
        <tr className="border-b border-slate-200">
          {columns.map(col => (
            <th key={col.key} className="text-left py-3 px-4 text-sm font-medium text-slate-500">
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr 
            key={row.id || i} 
            className={`border-b border-slate-100 ${onRowClick ? 'cursor-pointer hover:bg-slate-50' : ''}`}
            onClick={() => onRowClick && onRowClick(row)}
          >
            {columns.map(col => (
              <td key={col.key} className="py-3 px-4 text-sm text-slate-700">
                {col.render ? col.render(row[col.key], row) : row[col.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const StatusBadge = ({ status }) => {
  const config = {
    success: { label: 'Succès', className: 'bg-green-100 text-green-700' },
    failed: { label: 'Échec', className: 'bg-red-100 text-red-700' },
    duplicate: { label: 'Doublon', className: 'bg-orange-100 text-orange-700' },
    pending: { label: 'En attente', className: 'bg-slate-100 text-slate-700' },
    active: { label: 'Actif', className: 'bg-green-100 text-green-700' },
    paused: { label: 'Pause', className: 'bg-yellow-100 text-yellow-700' },
    archived: { label: 'Archivé', className: 'bg-slate-100 text-slate-700' }
  };
  const { label, className } = config[status] || config.pending;
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${className}`}>{label}</span>;
};

const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
};

// ==================== PAGES ====================

const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const result = await login(email, password);
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  const initAdmin = async () => {
    try {
      await fetch(`${API}/api/auth/init-admin`, { method: 'POST' });
      await fetch(`${API}/api/crms/init`, { 
        method: 'POST',
        headers: { 'Authorization': 'Bearer temp' }
      });
      setEmail('energiebleuciel@gmail.com');
      setPassword('92Ruemarxdormoy');
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-lg p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">CRM Dashboard</h1>
          <p className="text-slate-500">Connectez-vous pour continuer</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>

        <button
          onClick={initAdmin}
          className="w-full mt-4 text-sm text-slate-500 hover:text-slate-700"
        >
          Initialiser le compte admin
        </button>
      </div>
    </div>
  );
};

const DashboardPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('today');

  useEffect(() => {
    loadData();
  }, [period, selectedCRM]);

  const loadData = async () => {
    setLoading(true);
    try {
      const crmParam = selectedCRM ? `&crm_id=${selectedCRM}` : '';
      const [statsRes, leadsRes] = await Promise.all([
        authFetch(`${API}/api/analytics/stats?period=${period}${crmParam}`),
        authFetch(`${API}/api/leads?limit=10${crmParam}`)
      ]);
      
      if (statsRes.ok) setStats(await statsRes.json());
      if (leadsRes.ok) {
        const data = await leadsRes.json();
        setLeads(data.leads || []);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Tableau de bord</h1>
        <div className="flex items-center gap-2">
          <select
            value={period}
            onChange={e => setPeriod(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="today">Aujourd'hui</option>
            <option value="week">Cette semaine</option>
            <option value="month">Ce mois</option>
          </select>
          <button onClick={loadData} className="p-2 hover:bg-slate-100 rounded-lg">
            <RefreshCw className="w-5 h-5 text-slate-600" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Clics CTA" value={stats?.cta_clicks || 0} color="purple" />
        <StatCard icon={FileText} label="Forms démarrés" value={stats?.forms_started || 0} color="blue" />
        <StatCard icon={CheckCircle} label="Leads reçus" value={stats?.leads_total || 0} color="green" />
        <StatCard icon={XCircle} label="Échecs" value={stats?.leads_failed || 0} color="red" />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-3">Taux de conversion</h3>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600">CTA → Formulaire</span>
                <span className="font-medium">{stats?.cta_to_form_rate || 0}%</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${stats?.cta_to_form_rate || 0}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600">Formulaire → Lead</span>
                <span className="font-medium">{stats?.form_to_lead_rate || 0}%</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-green-500 rounded-full" style={{ width: `${stats?.form_to_lead_rate || 0}%` }} />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-3">Statut des leads</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Succès</span>
              <span className="text-sm font-medium text-green-600">{stats?.leads_success || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Échecs</span>
              <span className="text-sm font-medium text-red-600">{stats?.leads_failed || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Doublons</span>
              <span className="text-sm font-medium text-orange-600">{stats?.leads_duplicate || 0}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <div className="p-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-800">Derniers leads</h3>
        </div>
        <Table
          columns={[
            { key: 'created_at', label: 'Date', render: v => new Date(v).toLocaleString('fr-FR') },
            { key: 'nom', label: 'Nom' },
            { key: 'phone', label: 'Téléphone' },
            { key: 'form_code', label: 'Formulaire' },
            { key: 'api_status', label: 'Statut', render: v => <StatusBadge status={v} /> }
          ]}
          data={leads}
        />
      </div>
    </div>
  );
};

const LeadsPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', form_code: '' });
  const [selectedLeads, setSelectedLeads] = useState([]);

  useEffect(() => {
    loadLeads();
  }, [filters, selectedCRM]);

  const loadLeads = async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.form_code) params.set('form_code', filters.form_code);
    if (selectedCRM) params.set('crm_id', selectedCRM);
    
    try {
      const res = await authFetch(`${API}/api/leads?${params.toString()}&limit=200`);
      if (res.ok) {
        const data = await res.json();
        setLeads(data.leads || []);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
    setSelectedLeads([]);
  };

  const retryLead = async (leadId) => {
    try {
      await authFetch(`${API}/api/leads/retry/${leadId}`, { method: 'POST' });
      loadLeads();
    } catch (e) {
      console.error(e);
    }
  };

  const deleteLead = async (leadId) => {
    if (!window.confirm('Supprimer ce lead ?')) return;
    try {
      await authFetch(`${API}/api/leads/${leadId}`, { method: 'DELETE' });
      loadLeads();
    } catch (e) {
      console.error(e);
    }
  };

  const deleteSelectedLeads = async () => {
    if (selectedLeads.length === 0) return;
    if (!window.confirm(`Supprimer ${selectedLeads.length} lead(s) sélectionné(s) ?`)) return;
    try {
      await authFetch(`${API}/api/leads/bulk-delete`, { 
        method: 'POST',
        body: JSON.stringify({ lead_ids: selectedLeads })
      });
      loadLeads();
    } catch (e) {
      console.error(e);
    }
  };

  const toggleSelectLead = (leadId) => {
    setSelectedLeads(prev => 
      prev.includes(leadId) 
        ? prev.filter(id => id !== leadId)
        : [...prev, leadId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedLeads.length === leads.length) {
      setSelectedLeads([]);
    } else {
      setSelectedLeads(leads.map(l => l.id));
    }
  };

  const exportCSV = () => {
    const headers = ['Date', 'Nom', 'Téléphone', 'Email', 'Département', 'Code Postal', 'Formulaire', 'Statut'];
    const rows = leads.map(l => [
      new Date(l.created_at).toLocaleString('fr-FR'),
      l.nom, l.phone, l.email, l.departement, l.code_postal || '', l.form_code || l.form_id, l.api_status
    ]);
    const csv = [headers, ...rows].map(r => r.join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `leads_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Leads</h1>
        <div className="flex items-center gap-2">
          {selectedLeads.length > 0 && (
            <button 
              onClick={deleteSelectedLeads} 
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              <Trash2 className="w-4 h-4" />
              Supprimer ({selectedLeads.length})
            </button>
          )}
          <button onClick={exportCSV} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="flex gap-4">
        <select
          value={filters.status}
          onChange={e => setFilters({ ...filters, status: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg"
        >
          <option value="">Tous les statuts</option>
          <option value="success">Succès</option>
          <option value="failed">Échec</option>
          <option value="duplicate">Doublon</option>
          <option value="pending">En attente</option>
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        {loading ? (
          <div className="p-8 text-center">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4">
                    <input 
                      type="checkbox" 
                      checked={selectedLeads.length === leads.length && leads.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Date</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Nom</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Téléphone</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Email</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">CP</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Form</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Statut</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.map(lead => (
                  <tr key={lead.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4">
                      <input 
                        type="checkbox"
                        checked={selectedLeads.includes(lead.id)}
                        onChange={() => toggleSelectLead(lead.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{new Date(lead.created_at).toLocaleString('fr-FR')}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{lead.nom}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{lead.phone}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{lead.email}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{lead.code_postal || lead.departement}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{lead.form_code || lead.form_id}</td>
                    <td className="py-3 px-4"><StatusBadge status={lead.api_status} /></td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1">
                        {lead.api_status === 'failed' && (
                          <button onClick={() => retryLead(lead.id)} className="p-1 text-blue-600 hover:text-blue-800" title="Réessayer">
                            <RefreshCw className="w-4 h-4" />
                          </button>
                        )}
                        <button onClick={() => deleteLead(lead.id)} className="p-1 text-red-600 hover:text-red-800" title="Supprimer">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const AccountsPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [accounts, setAccounts] = useState([]);
  const [crms, setCrms] = useState([]);
  const [productTypes, setProductTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [showLegalModal, setShowLegalModal] = useState(null);
  const [activeTab, setActiveTab] = useState('general');
  
  const defaultFormData = {
    crm_id: '', name: '', domain: '', product_types: ['solaire'],
    logo_main_url: '', logo_secondary_url: '', logo_small_url: '', favicon_url: '',
    privacy_policy_text: '', legal_mentions_text: '',
    layout: 'center', primary_color: '#3B82F6', secondary_color: '#1E40AF', style_officiel: false,
    // GTM Tracking - au niveau du compte
    gtm_pixel_header: '', gtm_conversion_code: '', gtm_cta_code: '',
    default_redirect_url: '', notes: '',
    form_template: {
      phone_required: true, phone_digits: 10, nom_required: true,
      show_civilite: true, show_prenom: true, show_email: true, show_departement: true,
      show_code_postal: true, show_type_logement: true, show_statut_occupant: true, show_facture: true,
      postal_code_france_metro_only: true, form_style: 'modern'
    }
  };
  const [formData, setFormData] = useState(defaultFormData);

  useEffect(() => { loadData(); }, [selectedCRM]);

  const loadData = async () => {
    setLoading(true);
    try {
      const crmParam = selectedCRM ? `?crm_id=${selectedCRM}` : '';
      const [accountsRes, crmsRes, productsRes] = await Promise.all([
        authFetch(`${API}/api/accounts${crmParam}`),
        authFetch(`${API}/api/crms`),
        authFetch(`${API}/api/product-types`)
      ]);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).accounts || []);
      if (crmsRes.ok) setCrms((await crmsRes.json()).crms || []);
      if (productsRes.ok) setProductTypes((await productsRes.json()).product_types || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const url = editingAccount ? `${API}/api/accounts/${editingAccount.id}` : `${API}/api/accounts`;
    const method = editingAccount ? 'PUT' : 'POST';
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(formData) });
      if (res.ok) { setShowModal(false); setEditingAccount(null); setFormData(defaultFormData); loadData(); }
    } catch (e) { console.error(e); }
  };

  const editAccount = (account) => {
    setEditingAccount(account);
    setFormData({ ...defaultFormData, ...account, product_types: account.product_types || ['solaire'] });
    setActiveTab('general');
    setShowModal(true);
  };

  const deleteAccount = async (id) => {
    if (!window.confirm('Supprimer ce compte ?')) return;
    try { await authFetch(`${API}/api/accounts/${id}`, { method: 'DELETE' }); loadData(); } catch (e) { console.error(e); }
  };

  const toggleProductType = (slug) => {
    const types = formData.product_types || [];
    if (types.includes(slug)) {
      setFormData({ ...formData, product_types: types.filter(t => t !== slug) });
    } else {
      setFormData({ ...formData, product_types: [...types, slug] });
    }
  };

  const tabs = [
    { id: 'general', label: 'Général', icon: Building },
    { id: 'logos', label: 'Logos', icon: Image },
    { id: 'tracking', label: 'Tracking GTM', icon: Target },
    { id: 'legal', label: 'Légal', icon: Shield },
    { id: 'form', label: 'Formulaire', icon: FileText },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Comptes</h1>
          <p className="text-sm text-slate-500">Configurez vos comptes avec tracking GTM, logos et paramètres</p>
        </div>
        <button onClick={() => { setEditingAccount(null); setFormData({ ...defaultFormData, crm_id: selectedCRM || '' }); setActiveTab('general'); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouveau compte
        </button>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
        </div>
      ) : accounts.length === 0 ? (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <Building className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Aucun compte trouvé</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map(account => (
            <div key={account.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow">
              <div className={`p-4 ${account.style_officiel ? 'bg-gradient-to-r from-blue-900 to-blue-700' : 'bg-gradient-to-r from-slate-100 to-slate-50'}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {account.logo_main_url && <img src={account.logo_main_url} alt="" className="h-10 max-w-[80px] object-contain bg-white rounded p-1" />}
                    <div>
                      <h3 className={`font-bold text-lg ${account.style_officiel ? 'text-white' : 'text-slate-800'}`}>{account.name}</h3>
                      <p className={`text-xs ${account.style_officiel ? 'text-blue-200' : 'text-slate-500'}`}>{account.domain || 'Pas de domaine'}</p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => editAccount(account)} className="p-1.5 hover:bg-white/20 rounded" title="Modifier"><Edit className={`w-4 h-4 ${account.style_officiel ? 'text-white' : 'text-slate-600'}`} /></button>
                    <button onClick={() => deleteAccount(account.id)} className="p-1.5 hover:bg-white/20 rounded" title="Supprimer"><Trash2 className="w-4 h-4 text-red-400" /></button>
                  </div>
                </div>
              </div>
              <div className="p-4 space-y-3">
                <div className="flex flex-wrap gap-1">
                  {(account.product_types || []).map(pt => {
                    const product = productTypes.find(p => p.slug === pt);
                    return <span key={pt} className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">{product?.name || pt}</span>;
                  })}
                </div>
                <div className="text-xs text-slate-500 space-y-1">
                  <p className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${crms.find(c => c.id === account.crm_id)?.slug === 'mdl' ? 'bg-blue-500' : 'bg-green-500'}`} />
                    {crms.find(c => c.id === account.crm_id)?.name || 'CRM non défini'}
                  </p>
                  <div className="flex items-center gap-2">
                    <Target className="w-3 h-3" />
                    GTM: {account.gtm_pixel_header ? '✓ Pixel' : '✗'} | {account.gtm_conversion_code ? '✓ Conv.' : '✗'}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Legal Modal */}
      <Modal isOpen={!!showLegalModal} onClose={() => setShowLegalModal(null)} title={`Textes légaux - ${showLegalModal?.name || ''}`}>
        <div className="space-y-4">
          {showLegalModal?.privacy_policy_text && (
            <div><h4 className="font-medium mb-2">Politique de confidentialité</h4><div className="bg-slate-50 p-4 rounded-lg text-sm max-h-60 overflow-auto whitespace-pre-wrap">{showLegalModal.privacy_policy_text}</div></div>
          )}
          {showLegalModal?.legal_mentions_text && (
            <div><h4 className="font-medium mb-2">Mentions légales</h4><div className="bg-slate-50 p-4 rounded-lg text-sm max-h-60 overflow-auto whitespace-pre-wrap">{showLegalModal.legal_mentions_text}</div></div>
          )}
        </div>
      </Modal>

      {/* Edit/Create Modal with Tabs */}
      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingAccount ? `Modifier: ${editingAccount.name}` : 'Nouveau compte'}>
        <div className="flex border-b border-slate-200 mb-4 overflow-x-auto">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${activeTab === tab.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
              <tab.icon className="w-4 h-4" />{tab.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
          {/* Tab: Général */}
          {activeTab === 'general' && (
            <div className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">CRM *</label>
                  <select value={formData.crm_id} onChange={e => setFormData({ ...formData, crm_id: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required>
                    <option value="">Sélectionner</option>
                    {crms.map(crm => <option key={crm.id} value={crm.id}>{crm.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Nom du compte *</label>
                  <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Domaine</label>
                  <input type="text" value={formData.domain || ''} onChange={e => setFormData({ ...formData, domain: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="exemple.fr" />
                </div>
                <div>
                  <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-1">
                    <input type="checkbox" checked={formData.style_officiel} onChange={e => setFormData({ ...formData, style_officiel: e.target.checked })} className="rounded" />
                    Style officiel / gouvernemental
                  </label>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Types de produits</label>
                <div className="flex flex-wrap gap-2">
                  {productTypes.map(pt => (
                    <button key={pt.slug} type="button" onClick={() => toggleProductType(pt.slug)} className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${(formData.product_types || []).includes(pt.slug) ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                      {pt.name}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Couleur principale</label>
                  <input type="color" value={formData.primary_color} onChange={e => setFormData({ ...formData, primary_color: e.target.value })} className="w-full h-10 rounded-lg cursor-pointer" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Couleur secondaire</label>
                  <input type="color" value={formData.secondary_color} onChange={e => setFormData({ ...formData, secondary_color: e.target.value })} className="w-full h-10 rounded-lg cursor-pointer" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Notes internes</label>
                <textarea value={formData.notes || ''} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} />
              </div>
            </div>
          )}

          {/* Tab: Logos */}
          {activeTab === 'logos' && (
            <div className="space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-blue-700">Ces logos seront utilisés dans les LP et formulaires générés pour ce compte.</p>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Logo principal (gauche)</label>
                  <input type="url" value={formData.logo_main_url || ''} onChange={e => setFormData({ ...formData, logo_main_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://..." />
                  {formData.logo_main_url && <img src={formData.logo_main_url} alt="Preview" className="mt-2 h-12 object-contain bg-slate-100 rounded p-2" onError={e => e.target.style.display='none'} />}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Logo secondaire (droite)</label>
                  <input type="url" value={formData.logo_secondary_url || ''} onChange={e => setFormData({ ...formData, logo_secondary_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://..." />
                  {formData.logo_secondary_url && <img src={formData.logo_secondary_url} alt="Preview" className="mt-2 h-12 object-contain bg-slate-100 rounded p-2" onError={e => e.target.style.display='none'} />}
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Petit logo / Badge</label>
                  <input type="url" value={formData.logo_small_url || ''} onChange={e => setFormData({ ...formData, logo_small_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://..." />
                  {formData.logo_small_url && <img src={formData.logo_small_url} alt="Preview" className="mt-2 h-8 object-contain bg-slate-100 rounded p-1" onError={e => e.target.style.display='none'} />}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Favicon</label>
                  <input type="url" value={formData.favicon_url || ''} onChange={e => setFormData({ ...formData, favicon_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://..." />
                </div>
              </div>
            </div>
          )}

          {/* Tab: Tracking GTM */}
          {activeTab === 'tracking' && (
            <div className="space-y-4">
              <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                <h4 className="font-medium text-yellow-800 flex items-center gap-2"><Target className="w-4 h-4" /> Configuration GTM du compte</h4>
                <p className="text-sm text-yellow-700 mt-1">Ces codes seront automatiquement injectés dans les LP et formulaires de ce compte.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Pixel Header (dans &lt;head&gt;)</label>
                <textarea value={formData.gtm_pixel_header || ''} onChange={e => setFormData({ ...formData, gtm_pixel_header: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-xs" rows={4} placeholder="<!-- Facebook Pixel, Google Ads, GTM Container, etc. -->" />
                <p className="text-xs text-slate-500 mt-1">Ce code sera injecté dans le &lt;head&gt; de toutes les pages</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Code de conversion (après validation téléphone)</label>
                <textarea value={formData.gtm_conversion_code || ''} onChange={e => setFormData({ ...formData, gtm_conversion_code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-xs" rows={4} placeholder="fbq('track', 'Lead');\ndataLayer.push({event: 'conversion'});" />
                <p className="text-xs text-slate-500 mt-1">Exécuté après validation du téléphone (10 chiffres requis)</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Code CTA Click</label>
                <textarea value={formData.gtm_cta_code || ''} onChange={e => setFormData({ ...formData, gtm_cta_code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-xs" rows={3} placeholder="dataLayer.push({event: 'cta_click'});" />
                <p className="text-xs text-slate-500 mt-1">Exécuté au clic sur les boutons CTA</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">URL de redirection par défaut</label>
                <input type="url" value={formData.default_redirect_url || ''} onChange={e => setFormData({ ...formData, default_redirect_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://exemple.fr/merci/" />
                <p className="text-xs text-slate-500 mt-1">Page de remerciement après soumission (si tracking redirection)</p>
              </div>
            </div>
          )}

          {/* Tab: Légal */}
          {activeTab === 'legal' && (
            <div className="space-y-4">
              <div className="bg-slate-50 p-4 rounded-lg">
                <p className="text-sm text-slate-600">Ces textes s'afficheront dans une popup sur les formulaires de ce compte.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Politique de confidentialité</label>
                <textarea value={formData.privacy_policy_text || ''} onChange={e => setFormData({ ...formData, privacy_policy_text: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={6} placeholder="Texte de votre politique de confidentialité..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Mentions légales</label>
                <textarea value={formData.legal_mentions_text || ''} onChange={e => setFormData({ ...formData, legal_mentions_text: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={6} placeholder="Texte de vos mentions légales..." />
              </div>
            </div>
          )}

          {/* Tab: Formulaire */}
          {activeTab === 'form' && (
            <div className="space-y-4">
              <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                <h4 className="font-medium text-green-800">Configuration par défaut des formulaires</h4>
                <p className="text-sm text-green-700 mt-1">Ces paramètres seront appliqués aux nouveaux formulaires de ce compte.</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h5 className="font-medium text-slate-700">Champs obligatoires</h5>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.phone_required !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, phone_required: e.target.checked } })} className="rounded" disabled />
                    Téléphone (10 chiffres) ✓
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.nom_required !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, nom_required: e.target.checked } })} className="rounded" disabled />
                    Nom ✓
                  </label>
                </div>
                <div className="space-y-3">
                  <h5 className="font-medium text-slate-700">Champs optionnels</h5>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_civilite !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_civilite: e.target.checked } })} className="rounded" />
                    Civilité
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_prenom !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_prenom: e.target.checked } })} className="rounded" />
                    Prénom
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_email !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_email: e.target.checked } })} className="rounded" />
                    Email
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_departement !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_departement: e.target.checked } })} className="rounded" />
                    Département
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_code_postal !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_code_postal: e.target.checked } })} className="rounded" />
                    Code postal
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_type_logement !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_type_logement: e.target.checked } })} className="rounded" />
                    Type de logement
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_statut_occupant !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_statut_occupant: e.target.checked } })} className="rounded" />
                    Statut occupant
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={formData.form_template?.show_facture !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, show_facture: e.target.checked } })} className="rounded" />
                    Facture électricité
                  </label>
                </div>
              </div>
              <div className="border-t border-slate-200 pt-4">
                <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <input type="checkbox" checked={formData.form_template?.postal_code_france_metro_only !== false} onChange={e => setFormData({ ...formData, form_template: { ...formData.form_template, postal_code_france_metro_only: e.target.checked } })} className="rounded" />
                  Codes postaux France métropolitaine uniquement (01-95)
                </label>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 sticky bottom-0 bg-white py-4">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{editingAccount ? 'Modifier' : 'Créer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

// Keep alias for backwards compatibility
const SubAccountsPage = AccountsPage;

const LPsPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [lps, setLps] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showDuplicateModal, setShowDuplicateModal] = useState(null);
  const [editingLP, setEditingLP] = useState(null);
  const [duplicateData, setDuplicateData] = useState({ new_code: '', new_name: '' });
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    account_id: '', code: '', name: '', url: '', source_type: 'native',
    source_name: '', cta_selector: '.cta-btn', screenshot_url: '', diffusion_url: '', notes: '', status: 'active',
    lp_type: 'redirect', form_url: '', generation_notes: ''
  });

  useEffect(() => {
    loadData();
  }, [selectedCRM]);

  const loadData = async () => {
    setLoading(true);
    try {
      const crmParam = selectedCRM ? `?crm_id=${selectedCRM}` : '';
      const [lpsRes, accountsRes] = await Promise.all([
        authFetch(`${API}/api/lps${crmParam}`),
        authFetch(`${API}/api/accounts${crmParam}`)
      ]);
      if (lpsRes.ok) setLps((await lpsRes.json()).lps || []);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).accounts || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const url = editingLP ? `${API}/api/lps/${editingLP.id}` : `${API}/api/lps`;
    const method = editingLP ? 'PUT' : 'POST';
    
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(formData) });
      if (res.ok) {
        setShowModal(false);
        setEditingLP(null);
        loadData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Erreur lors de la création');
      }
    } catch (e) {
      console.error(e);
      setError('Erreur de connexion');
    }
  };

  const duplicateLP = async () => {
    if (!showDuplicateModal || !duplicateData.new_code || !duplicateData.new_name) return;
    try {
      const res = await authFetch(`${API}/api/lps/${showDuplicateModal.id}/duplicate?new_code=${encodeURIComponent(duplicateData.new_code)}&new_name=${encodeURIComponent(duplicateData.new_name)}`, { method: 'POST' });
      if (res.ok) {
        setShowDuplicateModal(null);
        setDuplicateData({ new_code: '', new_name: '' });
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteLP = async (id) => {
    if (!window.confirm('Supprimer cette LP ?')) return;
    try {
      await authFetch(`${API}/api/lps/${id}`, { method: 'DELETE' });
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Landing Pages</h1>
        <button onClick={() => { setEditingLP(null); setFormData({ account_id: '', code: '', name: '', url: '', source_type: 'native', source_name: '', cta_selector: '.cta-btn', status: 'active', lp_type: 'redirect', form_url: '', generation_notes: '' }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouvelle LP
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <Table
          columns={[
            { key: 'code', label: 'Code', render: v => <span className="font-mono text-sm bg-slate-100 px-2 py-1 rounded">{v}</span> },
            { key: 'name', label: 'Nom' },
            { key: 'source_name', label: 'Source' },
            { key: 'lp_type', label: 'Type', render: v => v === 'integrated' ? 
              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">Intégré</span> : 
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Redirection</span>
            },
            { key: 'stats', label: 'Clics CTA', render: v => v?.cta_clicks || 0 },
            { key: 'stats', label: 'Leads', render: v => v?.leads || 0 },
            { key: 'status', label: 'Statut', render: v => <StatusBadge status={v} /> },
            { 
              key: 'actions', 
              label: '', 
              render: (_, row) => (
                <div className="flex gap-1">
                  <button onClick={() => { setEditingLP(row); setFormData(row); setShowModal(true); }} className="p-1 hover:bg-slate-100 rounded" title="Modifier">
                    <Edit className="w-4 h-4 text-slate-600" />
                  </button>
                  <button onClick={() => { setShowDuplicateModal(row); setDuplicateData({ new_code: row.code + '-COPY', new_name: row.name + ' (copie)' }); }} className="p-1 hover:bg-slate-100 rounded" title="Dupliquer">
                    <Copy className="w-4 h-4 text-blue-600" />
                  </button>
                  <button onClick={() => deleteLP(row.id)} className="p-1 hover:bg-slate-100 rounded" title="Supprimer">
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              )
            }
          ]}
          data={lps}
        />
      </div>

      {/* Modal Duplicate LP */}
      <Modal isOpen={!!showDuplicateModal} onClose={() => setShowDuplicateModal(null)} title="Dupliquer la Landing Page">
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Dupliquer <strong>{showDuplicateModal?.name}</strong> avec un nouveau code et nom.
            La configuration sera identique.
          </p>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nouveau code *</label>
            <input type="text" value={duplicateData.new_code} onChange={e => setDuplicateData({ ...duplicateData, new_code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nouveau nom *</label>
            <input type="text" value={duplicateData.new_name} onChange={e => setDuplicateData({ ...duplicateData, new_name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={() => setShowDuplicateModal(null)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button onClick={duplicateLP} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Dupliquer</button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingLP ? 'Modifier la LP' : 'Nouvelle Landing Page'}>
        <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>
          )}
          {/* Section: Informations générales */}
          <div className="bg-slate-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-slate-800 flex items-center gap-2">
              <Layers className="w-4 h-4" /> Informations générales
            </h4>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Compte *</label>
                <select value={formData.account_id} onChange={e => setFormData({ ...formData, account_id: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required>
                  <option value="">Sélectionner</option>
                  {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Code LP *</label>
                <input type="text" value={formData.code} onChange={e => setFormData({ ...formData, code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="LP-TAB-V1" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nom *</label>
                <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">URL de la LP</label>
                <input type="url" value={formData.url || ''} onChange={e => setFormData({ ...formData, url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
              </div>
            </div>
          </div>

          {/* Section: Type de LP */}
          <div className="bg-blue-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-blue-800 flex items-center gap-2">
              <Link2 className="w-4 h-4" /> Type de LP
            </h4>
            <div className="grid md:grid-cols-2 gap-4">
              <label className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${formData.lp_type === 'redirect' ? 'border-blue-500 bg-blue-100' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
                <input type="radio" name="lp_type" value="redirect" checked={formData.lp_type === 'redirect'} onChange={e => setFormData({ ...formData, lp_type: e.target.value })} className="sr-only" />
                <div className="font-medium text-slate-800">LP → Formulaire externe</div>
                <p className="text-xs text-slate-500 mt-1">La LP redirige vers un formulaire sur une autre page</p>
              </label>
              <label className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${formData.lp_type === 'integrated' ? 'border-purple-500 bg-purple-100' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
                <input type="radio" name="lp_type" value="integrated" checked={formData.lp_type === 'integrated'} onChange={e => setFormData({ ...formData, lp_type: e.target.value })} className="sr-only" />
                <div className="font-medium text-slate-800">Formulaire intégré</div>
                <p className="text-xs text-slate-500 mt-1">Le formulaire est directement dans la LP</p>
              </label>
            </div>
            
            {formData.lp_type === 'redirect' && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">URL du formulaire</label>
                <input type="url" value={formData.form_url || ''} onChange={e => setFormData({ ...formData, form_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://..." />
              </div>
            )}
          </div>

          {/* Section: Source */}
          <div className="bg-slate-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-slate-800">Source de trafic</h4>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type de source</label>
                <select value={formData.source_type} onChange={e => setFormData({ ...formData, source_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                  <option value="native">Native (Taboola, Outbrain)</option>
                  <option value="google">Google Ads</option>
                  <option value="facebook">Facebook Ads</option>
                  <option value="tiktok">TikTok Ads</option>
                  <option value="other">Autre</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nom de la source</label>
                <input type="text" value={formData.source_name || ''} onChange={e => setFormData({ ...formData, source_name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Taboola, Outbrain, etc." />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Sélecteur CSS des CTA</label>
              <input type="text" value={formData.cta_selector || '.cta-btn'} onChange={e => setFormData({ ...formData, cta_selector: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder=".cta-btn" />
              <p className="text-xs text-slate-500 mt-1">Sélecteur CSS pour identifier les boutons CTA sur la LP</p>
            </div>
          </div>

          {/* Section: Notes & Instructions */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Notes internes</label>
              <textarea value={formData.notes || ''} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Commentaires pour génération scripts</label>
              <textarea value={formData.generation_notes || ''} onChange={e => setFormData({ ...formData, generation_notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} placeholder="Instructions supplémentaires pour le générateur de scripts..." />
              <p className="text-xs text-slate-500 mt-1">Ces commentaires seront pris en compte lors de la génération des instructions</p>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 sticky bottom-0 bg-white py-4">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{editingLP ? 'Modifier' : 'Créer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

const FormsPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [forms, setForms] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [lps, setLps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showDuplicateModal, setShowDuplicateModal] = useState(null);
  const [editingForm, setEditingForm] = useState(null);
  const [duplicateData, setDuplicateData] = useState({ new_code: '', new_name: '', new_api_key: '' });
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    account_id: '', lp_ids: [], code: '', name: '', product_type: 'panneaux',
    source_type: 'native', source_name: '', api_key: '', tracking_type: 'redirect',
    tracking_code: '', redirect_url: '', notes: '', status: 'active',
    form_type: 'standalone', generation_notes: ''
  });

  useEffect(() => {
    loadData();
  }, [selectedCRM]);

  const loadData = async () => {
    setLoading(true);
    try {
      const crmParam = selectedCRM ? `?crm_id=${selectedCRM}` : '';
      const [formsRes, accountsRes, lpsRes] = await Promise.all([
        authFetch(`${API}/api/forms${crmParam}`),
        authFetch(`${API}/api/accounts${crmParam}`),
        authFetch(`${API}/api/lps${crmParam}`)
      ]);
      if (formsRes.ok) setForms((await formsRes.json()).forms || []);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).accounts || []);
      if (lpsRes.ok) setLps((await lpsRes.json()).lps || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const url = editingForm ? `${API}/api/forms/${editingForm.id}` : `${API}/api/forms`;
    const method = editingForm ? 'PUT' : 'POST';
    
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(formData) });
      if (res.ok) {
        setShowModal(false);
        setEditingForm(null);
        loadData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Erreur lors de la création');
      }
    } catch (e) {
      console.error(e);
      setError('Erreur de connexion');
    }
  };

  const duplicateForm = async () => {
    if (!showDuplicateModal || !duplicateData.new_code || !duplicateData.new_name || !duplicateData.new_api_key) return;
    try {
      const res = await authFetch(`${API}/api/forms/${showDuplicateModal.id}/duplicate?new_code=${encodeURIComponent(duplicateData.new_code)}&new_name=${encodeURIComponent(duplicateData.new_name)}&new_api_key=${encodeURIComponent(duplicateData.new_api_key)}`, { method: 'POST' });
      if (res.ok) {
        setShowDuplicateModal(null);
        setDuplicateData({ new_code: '', new_name: '', new_api_key: '' });
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteForm = async (id) => {
    if (!window.confirm('Supprimer ce formulaire ?')) return;
    try {
      await authFetch(`${API}/api/forms/${id}`, { method: 'DELETE' });
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Formulaires</h1>
        <button onClick={() => { setEditingForm(null); setFormData({ account_id: '', lp_ids: [], code: '', name: '', product_type: 'panneaux', source_type: 'native', source_name: '', api_key: '', tracking_type: 'redirect', status: 'active', form_type: 'standalone', generation_notes: '' }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouveau formulaire
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <Table
          columns={[
            { key: 'code', label: 'Code', render: v => <span className="font-mono text-sm bg-slate-100 px-2 py-1 rounded">{v}</span> },
            { key: 'name', label: 'Nom' },
            { key: 'source_name', label: 'Source' },
            { key: 'tracking_type', label: 'Tracking', render: v => v === 'gtm' ? 
              <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">GTM</span> : 
              v === 'none' ? <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">Aucun</span> :
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Redirect</span>
            },
            { key: 'stats', label: 'Démarrés', render: v => v?.started || 0 },
            { key: 'stats', label: 'Complétés', render: v => v?.completed || 0 },
            { key: 'status', label: 'Statut', render: v => <StatusBadge status={v} /> },
            { 
              key: 'actions', 
              label: '', 
              render: (_, row) => (
                <div className="flex gap-1">
                  <button onClick={() => { setEditingForm(row); setFormData(row); setShowModal(true); }} className="p-1 hover:bg-slate-100 rounded" title="Modifier">
                    <Edit className="w-4 h-4 text-slate-600" />
                  </button>
                  <button onClick={() => { setShowDuplicateModal(row); setDuplicateData({ new_code: row.code + '-COPY', new_name: row.name + ' (copie)', new_api_key: '' }); }} className="p-1 hover:bg-slate-100 rounded" title="Dupliquer">
                    <Copy className="w-4 h-4 text-blue-600" />
                  </button>
                  <button onClick={() => deleteForm(row.id)} className="p-1 hover:bg-slate-100 rounded" title="Supprimer">
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              )
            }
          ]}
          data={forms}
        />
      </div>

      {/* Modal Duplicate Form */}
      <Modal isOpen={!!showDuplicateModal} onClose={() => setShowDuplicateModal(null)} title="Dupliquer le formulaire">
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Dupliquer <strong>{showDuplicateModal?.name}</strong>. Seule la <strong>clé API</strong> sera différente.
          </p>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nouveau code *</label>
            <input type="text" value={duplicateData.new_code} onChange={e => setDuplicateData({ ...duplicateData, new_code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nouveau nom *</label>
            <input type="text" value={duplicateData.new_name} onChange={e => setDuplicateData({ ...duplicateData, new_name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nouvelle clé API CRM *</label>
            <input type="text" value={duplicateData.new_api_key} onChange={e => setDuplicateData({ ...duplicateData, new_api_key: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm" placeholder="uuid-xxx-xxx" required />
            <p className="text-xs text-slate-500 mt-1">La clé API fournie par le CRM pour cette campagne</p>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={() => setShowDuplicateModal(null)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button onClick={duplicateForm} disabled={!duplicateData.new_api_key} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">Dupliquer</button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingForm ? 'Modifier le formulaire' : 'Nouveau formulaire'}>
        <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>
          )}
          {/* Section: Informations générales */}
          <div className="bg-slate-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-slate-800 flex items-center gap-2">
              <FileText className="w-4 h-4" /> Informations générales
            </h4>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Compte *</label>
                <select value={formData.account_id} onChange={e => setFormData({ ...formData, account_id: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required>
                  <option value="">Sélectionner</option>
                  {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Code formulaire *</label>
                <input type="text" value={formData.code} onChange={e => setFormData({ ...formData, code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="PV-TAB-001" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nom *</label>
                <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Clé API CRM *</label>
                <input type="text" value={formData.api_key} onChange={e => setFormData({ ...formData, api_key: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm" placeholder="uuid-xxx-xxx" required />
              </div>
            </div>
          </div>

          {/* Section: Tracking */}
          <div className="bg-green-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-green-800 flex items-center gap-2">
              <Target className="w-4 h-4" /> Tracking de conversion
            </h4>
            <p className="text-xs text-green-700">Pour les formulaires de <strong>redirection</strong>, pas besoin de tracking GTM (la redirection suffit).</p>
            
            <div className="grid md:grid-cols-3 gap-3">
              <label className={`p-3 border-2 rounded-lg cursor-pointer transition-colors ${formData.tracking_type === 'redirect' ? 'border-green-500 bg-green-100' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
                <input type="radio" name="tracking_type" value="redirect" checked={formData.tracking_type === 'redirect'} onChange={e => setFormData({ ...formData, tracking_type: e.target.value })} className="sr-only" />
                <div className="font-medium text-slate-800 text-sm">Redirection</div>
                <p className="text-xs text-slate-500 mt-1">Page de merci</p>
              </label>
              <label className={`p-3 border-2 rounded-lg cursor-pointer transition-colors ${formData.tracking_type === 'gtm' ? 'border-yellow-500 bg-yellow-100' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
                <input type="radio" name="tracking_type" value="gtm" checked={formData.tracking_type === 'gtm'} onChange={e => setFormData({ ...formData, tracking_type: e.target.value })} className="sr-only" />
                <div className="font-medium text-slate-800 text-sm">GTM / Code JS</div>
                <p className="text-xs text-slate-500 mt-1">Event tracking</p>
              </label>
              <label className={`p-3 border-2 rounded-lg cursor-pointer transition-colors ${formData.tracking_type === 'none' ? 'border-slate-500 bg-slate-100' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
                <input type="radio" name="tracking_type" value="none" checked={formData.tracking_type === 'none'} onChange={e => setFormData({ ...formData, tracking_type: e.target.value })} className="sr-only" />
                <div className="font-medium text-slate-800 text-sm">Aucun</div>
                <p className="text-xs text-slate-500 mt-1">Pas de tracking</p>
              </label>
            </div>

            {formData.tracking_type === 'redirect' && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">URL de redirection (page merci)</label>
                <input type="url" value={formData.redirect_url || ''} onChange={e => setFormData({ ...formData, redirect_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://..." />
              </div>
            )}

            {formData.tracking_type === 'gtm' && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Code tracking (GTM / JS)</label>
                <textarea value={formData.tracking_code || ''} onChange={e => setFormData({ ...formData, tracking_code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-xs" rows={3} placeholder="dataLayer.push({event: 'conversion'});" />
              </div>
            )}
          </div>

          {/* Section: Source */}
          <div className="bg-slate-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-slate-800">Source de trafic</h4>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type de source</label>
                <select value={formData.source_type} onChange={e => setFormData({ ...formData, source_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                  <option value="native">Native (Taboola, Outbrain)</option>
                  <option value="google">Google Ads</option>
                  <option value="facebook">Facebook Ads</option>
                  <option value="tiktok">TikTok Ads</option>
                  <option value="other">Autre</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nom de la source</label>
                <input type="text" value={formData.source_name || ''} onChange={e => setFormData({ ...formData, source_name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Taboola, Outbrain, etc." />
              </div>
            </div>
          </div>

          {/* Section: Notes */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Notes internes</label>
              <textarea value={formData.notes || ''} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Commentaires pour génération</label>
              <textarea value={formData.generation_notes || ''} onChange={e => setFormData({ ...formData, generation_notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} placeholder="Instructions supplémentaires..." />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200 sticky bottom-0 bg-white py-4">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{editingForm ? 'Modifier' : 'Créer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

const AnalyticsPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [stats, setStats] = useState(null);
  const [winners, setWinners] = useState(null);
  const [period, setPeriod] = useState('week');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [period, selectedCRM]);

  const loadData = async () => {
    setLoading(true);
    try {
      const crmParam = selectedCRM ? `&crm_id=${selectedCRM}` : '';
      const [statsRes, winnersRes] = await Promise.all([
        authFetch(`${API}/api/analytics/stats?period=${period}${crmParam}`),
        authFetch(`${API}/api/analytics/winners?period=${period}${crmParam}`)
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (winnersRes.ok) setWinners(await winnersRes.json());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><RefreshCw className="w-8 h-8 animate-spin text-blue-600" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Analytics</h1>
        <select value={period} onChange={e => setPeriod(e.target.value)} className="px-3 py-2 border border-slate-300 rounded-lg">
          <option value="today">Aujourd'hui</option>
          <option value="week">Cette semaine</option>
          <option value="month">Ce mois</option>
        </select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Clics CTA" value={stats?.cta_clicks || 0} color="purple" />
        <StatCard icon={FileText} label="Forms démarrés" value={stats?.forms_started || 0} color="blue" />
        <StatCard icon={CheckCircle} label="Leads" value={stats?.leads_total || 0} color="green" />
        <StatCard icon={Award} label="Taux conversion" value={`${stats?.form_to_lead_rate || 0}%`} color="orange" />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-green-600" />
            🏆 LPs Gagnantes
          </h3>
          <div className="space-y-3">
            {winners?.lp_winners?.length > 0 ? winners.lp_winners.map((lp, i) => (
              <div key={lp.code} className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-green-600">#{i + 1}</span>
                  <span className="font-medium">{lp.code}</span>
                </div>
                <div className="text-right">
                  <p className="font-bold text-green-600">{lp.leads} leads</p>
                  <p className="text-xs text-slate-500">{lp.success_rate}% succès</p>
                </div>
              </div>
            )) : <p className="text-slate-500">Pas de données</p>}
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            🔻 LPs à améliorer
          </h3>
          <div className="space-y-3">
            {winners?.lp_losers?.length > 0 ? winners.lp_losers.map((lp, i) => (
              <div key={lp.code} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-red-600">#{i + 1}</span>
                  <span className="font-medium">{lp.code}</span>
                </div>
                <div className="text-right">
                  <p className="font-bold text-red-600">{lp.leads} leads</p>
                  <p className="text-xs text-slate-500">{lp.success_rate}% succès</p>
                </div>
              </div>
            )) : <p className="text-slate-500">Pas de données</p>}
          </div>
        </div>
      </div>
    </div>
  );
};

const ScriptGeneratorPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [lps, setLps] = useState([]);
  const [forms, setForms] = useState([]);
  const [selectedLP, setSelectedLP] = useState('');
  const [selectedForm, setSelectedForm] = useState('');
  const [generatedScript, setGeneratedScript] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadData();
  }, [selectedCRM]);

  const loadData = async () => {
    try {
      const crmParam = selectedCRM ? `?crm_id=${selectedCRM}` : '';
      const [lpsRes, formsRes] = await Promise.all([
        authFetch(`${API}/api/lps${crmParam}`),
        authFetch(`${API}/api/forms${crmParam}`)
      ]);
      if (lpsRes.ok) setLps((await lpsRes.json()).lps || []);
      if (formsRes.ok) setForms((await formsRes.json()).forms || []);
    } catch (e) {
      console.error(e);
    }
  };

  const generateLPScript = async () => {
    if (!selectedLP) return;
    try {
      const res = await authFetch(`${API}/api/generate-script/lp/${selectedLP}`);
      if (res.ok) {
        setGeneratedScript(await res.json());
      } else {
        console.error('Error generating LP script:', res.status);
        const data = await res.json().catch(() => ({}));
        alert(data.detail || 'Erreur lors de la génération du script');
      }
    } catch (e) {
      console.error(e);
      alert('Erreur de connexion');
    }
  };

  const generateFormScript = async () => {
    if (!selectedForm) return;
    try {
      const res = await authFetch(`${API}/api/generate-script/form/${selectedForm}`);
      if (res.ok) {
        setGeneratedScript(await res.json());
      } else {
        console.error('Error generating Form script:', res.status);
        const data = await res.json().catch(() => ({}));
        alert(data.detail || 'Erreur lors de la génération du script');
      }
    } catch (e) {
      console.error(e);
      alert('Erreur de connexion');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Générateur de Scripts</h1>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" />
            Script LP (Tracking CTA)
          </h3>
          <div className="space-y-4">
            <select value={selectedLP} onChange={e => setSelectedLP(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
              <option value="">Sélectionner une LP</option>
              {lps.map(lp => <option key={lp.id} value={lp.id}>{lp.code} - {lp.name}</option>)}
            </select>
            <button onClick={generateLPScript} className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Générer le script
            </button>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-green-600" />
            Script Formulaire
          </h3>
          <div className="space-y-4">
            <select value={selectedForm} onChange={e => setSelectedForm(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
              <option value="">Sélectionner un formulaire</option>
              {forms.map(f => <option key={f.id} value={f.id}>{f.code} - {f.name}</option>)}
            </select>
            <button onClick={generateFormScript} className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
              Générer le script
            </button>
          </div>
        </div>
      </div>

      {generatedScript && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">Script généré</h3>
            <button 
              onClick={() => copyToClipboard(generatedScript.instructions || generatedScript.script)}
              className="flex items-center gap-2 px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm"
            >
              {copied ? <CheckCircle className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copié !' : 'Copier'}
            </button>
          </div>
          <div className="p-4">
            <pre className="bg-slate-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm whitespace-pre-wrap">
              {generatedScript.instructions || generatedScript.script}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

const UsersPage = () => {
  const { authFetch, user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(null);
  const [newUser, setNewUser] = useState({ email: '', password: '', nom: '', role: 'viewer', allowed_accounts: [] });
  const [editData, setEditData] = useState({ role: '', allowed_accounts: [] });
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [usersRes, accountsRes] = await Promise.all([
        authFetch(`${API}/api/users`),
        authFetch(`${API}/api/accounts`)
      ]);
      if (usersRes.ok) setUsers((await usersRes.json()).users || []);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).accounts || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const createUser = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await authFetch(`${API}/api/auth/register`, {
        method: 'POST',
        body: JSON.stringify(newUser)
      });
      if (res.ok) {
        setShowModal(false);
        setNewUser({ email: '', password: '', nom: '', role: 'viewer', allowed_accounts: [] });
        loadData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Erreur lors de la création');
      }
    } catch (e) {
      setError('Erreur de connexion');
    }
  };

  const openEditModal = (user) => {
    setEditData({
      role: user.role,
      allowed_accounts: user.allowed_accounts || []
    });
    setShowEditModal(user);
  };

  const updateUser = async () => {
    if (!showEditModal) return;
    try {
      const res = await authFetch(`${API}/api/users/${showEditModal.id}`, {
        method: 'PUT',
        body: JSON.stringify(editData)
      });
      if (res.ok) {
        setShowEditModal(null);
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Supprimer cet utilisateur ?')) return;
    try {
      await authFetch(`${API}/api/users/${userId}`, { method: 'DELETE' });
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const toggleAccount = (accountId, isEdit = false) => {
    if (isEdit) {
      const current = editData.allowed_accounts || [];
      if (current.includes(accountId)) {
        setEditData({ ...editData, allowed_accounts: current.filter(id => id !== accountId) });
      } else {
        setEditData({ ...editData, allowed_accounts: [...current, accountId] });
      }
    } else {
      const current = newUser.allowed_accounts || [];
      if (current.includes(accountId)) {
        setNewUser({ ...newUser, allowed_accounts: current.filter(id => id !== accountId) });
      } else {
        setNewUser({ ...newUser, allowed_accounts: [...current, accountId] });
      }
    }
  };

  const getAccountNames = (accountIds) => {
    if (!accountIds || accountIds.length === 0) return 'Tous les comptes';
    return accountIds.map(id => accounts.find(a => a.id === id)?.name || id).join(', ');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Utilisateurs</h1>
          <p className="text-sm text-slate-500">Gérez les accès et les comptes autorisés par utilisateur</p>
        </div>
        <button 
          onClick={() => setShowModal(true)} 
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          Nouvel utilisateur
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        {loading ? (
          <div className="p-8 text-center"><RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Nom</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Email</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Rôle</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Comptes autorisés</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Créé le</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4 text-sm font-medium text-slate-800">{user.nom}</td>
                    <td className="py-3 px-4 text-sm text-slate-600">{user.email}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        user.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                        user.role === 'editor' ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {user.role === 'admin' ? 'Admin' : user.role === 'editor' ? 'Éditeur' : 'Lecteur'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-xs text-slate-600 max-w-xs truncate" title={getAccountNames(user.allowed_accounts)}>
                        {(!user.allowed_accounts || user.allowed_accounts.length === 0) ? (
                          <span className="text-green-600 font-medium">✓ Tous les comptes</span>
                        ) : (
                          <span>{user.allowed_accounts.length} compte(s): {getAccountNames(user.allowed_accounts)}</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-500">{new Date(user.created_at).toLocaleDateString('fr-FR')}</td>
                    <td className="py-3 px-4">
                      {user.id !== currentUser?.id && (
                        <div className="flex items-center gap-1">
                          <button onClick={() => openEditModal(user)} className="p-1.5 hover:bg-slate-100 rounded" title="Modifier">
                            <Edit className="w-4 h-4 text-slate-600" />
                          </button>
                          <button onClick={() => deleteUser(user.id)} className="p-1.5 hover:bg-slate-100 rounded" title="Supprimer">
                            <Trash2 className="w-4 h-4 text-red-600" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Modifier utilisateur */}
      <Modal isOpen={!!showEditModal} onClose={() => setShowEditModal(null)} title={`Modifier: ${showEditModal?.nom || ''}`}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Rôle</label>
            <select
              value={editData.role}
              onChange={e => setEditData({ ...editData, role: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            >
              <option value="viewer">Lecteur (voir seulement)</option>
              <option value="editor">Éditeur (créer, modifier)</option>
              <option value="admin">Admin (tout accès)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Comptes autorisés</label>
            <p className="text-xs text-slate-500 mb-3">
              Sélectionnez les comptes auxquels cet utilisateur a accès. Si aucun n'est sélectionné, l'utilisateur a accès à tous les comptes.
            </p>
            <div className="space-y-2 max-h-60 overflow-y-auto border border-slate-200 rounded-lg p-3">
              {accounts.map(account => (
                <label key={account.id} className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(editData.allowed_accounts || []).includes(account.id)}
                    onChange={() => toggleAccount(account.id, true)}
                    className="rounded border-slate-300 text-blue-600"
                  />
                  <span className="text-sm text-slate-700">{account.name}</span>
                </label>
              ))}
            </div>
            {editData.allowed_accounts?.length === 0 && (
              <p className="text-xs text-green-600 mt-2">✓ Accès à tous les comptes</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200">
            <button type="button" onClick={() => setShowEditModal(null)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">
              Annuler
            </button>
            <button onClick={updateUser} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Enregistrer
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal: Nouvel utilisateur */}
      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="Nouvel utilisateur">
        <form onSubmit={createUser} className="space-y-4">
          {error && (
            <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>
          )}
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nom</label>
              <input
                type="text"
                value={newUser.nom}
                onChange={e => setNewUser({ ...newUser, nom: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                type="email"
                value={newUser.email}
                onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                required
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Mot de passe</label>
              <input
                type="password"
                value={newUser.password}
                onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                required
                minLength={6}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Rôle</label>
              <select
                value={newUser.role}
                onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              >
                <option value="viewer">Lecteur</option>
                <option value="editor">Éditeur</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Comptes autorisés</label>
            <p className="text-xs text-slate-500 mb-3">
              Sélectionnez les comptes auxquels cet utilisateur aura accès. Laissez vide pour accès à tous.
            </p>
            <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto border border-slate-200 rounded-lg p-3">
              {accounts.map(account => (
                <label key={account.id} className="flex items-center gap-2 p-1.5 hover:bg-slate-50 rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(newUser.allowed_accounts || []).includes(account.id)}
                    onChange={() => toggleAccount(account.id, false)}
                    className="rounded border-slate-300 text-blue-600"
                  />
                  <span className="text-sm text-slate-700">{account.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">
              Annuler
            </button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Créer l'utilisateur
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

const ActivityPage = () => {
  const { authFetch } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    try {
      const res = await authFetch(`${API}/api/activity-logs?limit=100`);
      if (res.ok) setLogs((await res.json()).logs || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const actionIcons = {
    login: '🔓',
    logout: '🔴',
    create: '➕',
    update: '✏️',
    delete: '🗑️',
    comment: '💬',
    update_role: '👤'
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Journal d'activité</h1>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <div className="divide-y divide-slate-100">
          {logs.map(log => (
            <div key={log.id} className="p-4 flex items-start gap-4">
              <span className="text-xl">{actionIcons[log.action] || '📝'}</span>
              <div className="flex-1">
                <p className="text-sm text-slate-800">
                  <span className="font-medium">{log.user_email}</span>
                  {' '}{log.action}{' '}
                  {log.entity_type && <span className="text-slate-500">{log.entity_type}</span>}
                </p>
                {log.details && <p className="text-xs text-slate-500 mt-1">{log.details}</p>}
              </div>
              <span className="text-xs text-slate-400">
                {new Date(log.created_at).toLocaleString('fr-FR')}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const GuidePage = () => {
  const [activeSection, setActiveSection] = useState('intro');

  const sections = [
    { id: 'intro', label: 'Introduction', icon: BookOpen },
    { id: 'crm-selector', label: 'Sélecteur CRM', icon: Building },
    { id: 'accounts', label: 'Comptes', icon: Database },
    { id: 'lps', label: 'Landing Pages', icon: Layers },
    { id: 'forms', label: 'Formulaires', icon: FileText },
    { id: 'tracking', label: 'Tracking', icon: Target },
    { id: 'leads', label: 'Gestion Leads', icon: Users },
    { id: 'analytics', label: 'Analytics', icon: TrendingUp },
    { id: 'generator', label: 'Générateur Scripts', icon: Code },
    { id: 'users', label: 'Utilisateurs', icon: Shield },
    { id: 'workflow', label: 'Workflow Complet', icon: Zap },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
          <BookOpen className="w-6 h-6 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Guide d'utilisation</h1>
          <p className="text-slate-500">Tout savoir sur le fonctionnement du CRM</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Navigation */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 sticky top-6">
            <h3 className="font-semibold text-slate-800 mb-3">Sections</h3>
            <nav className="space-y-1">
              {sections.map(section => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
                    activeSection === section.id 
                      ? 'bg-blue-50 text-blue-700 font-medium' 
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <section.icon className="w-4 h-4" />
                  {section.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Introduction */}
          {activeSection === 'intro' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-600" />
                Bienvenue dans le CRM
              </h2>
              <p className="text-slate-600">
                Ce CRM vous permet de gérer vos leads provenant de différentes sources (Taboola, Outbrain, Facebook, Google, TikTok) 
                et de les envoyer vers vos CRMs de destination (Maison du Lead, ZR7 Digital).
              </p>
              
              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">🎯 Fonctionnalités principales</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• <strong>Multi-CRM</strong> : Gérer MDL et ZR7 séparément</li>
                  <li>• <strong>Comptes</strong> : Un compte par site/domaine (MDL, SPOOT, ZR7, AZ...)</li>
                  <li>• <strong>Tracking complet</strong> : Pixels, CTA, conversions</li>
                  <li>• <strong>Analytics</strong> : Statistiques et gagnants/perdants</li>
                  <li>• <strong>Générateur de scripts</strong> : Code prêt à copier</li>
                  <li>• <strong>Gestion utilisateurs</strong> : Rôles et comptes autorisés par personne</li>
                </ul>
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-800 mb-2">📊 Structure des données</h4>
                <pre className="text-sm text-slate-600 bg-white p-3 rounded border border-slate-200">
{`CRM (MDL ou ZR7)
  └── Compte (MDL, SPOOT, ZR7, AZ, etc.)
        ├── Landing Pages (LP)
        │     └── Tracking CTA (clics)
        └── Formulaires
              └── Leads (données)`}
                </pre>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-2">📦 Comptes par défaut</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <strong className="text-green-800">Maison du Lead:</strong>
                    <p className="text-green-700">MDL, SPOOT, OBJECTIF ACADEMIE, AUDIT GREEN</p>
                  </div>
                  <div>
                    <strong className="text-green-800">ZR7 Digital:</strong>
                    <p className="text-green-700">ZR7, AZ</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* CRM Selector */}
          {activeSection === 'crm-selector' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Building className="w-5 h-5 text-blue-600" />
                Sélecteur CRM
              </h2>
              
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 className="font-semibold text-yellow-800 mb-2">⚠️ Important</h4>
                <p className="text-sm text-yellow-700">
                  Le sélecteur CRM en haut à gauche de l'écran filtre TOUTES les données affichées.
                </p>
              </div>

              <div className="space-y-3">
                <div className="p-4 bg-slate-50 rounded-lg">
                  <h4 className="font-medium text-slate-800">🔹 Tous les CRMs</h4>
                  <p className="text-sm text-slate-600 mt-1">Affiche les données de MDL ET ZR7 combinées</p>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-800">🔹 Maison du Lead (MDL)</h4>
                  <p className="text-sm text-blue-700 mt-1">Affiche UNIQUEMENT les leads envoyés vers MDL</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-800">🔹 ZR7 Digital</h4>
                  <p className="text-sm text-green-700 mt-1">Affiche UNIQUEMENT les leads envoyés vers ZR7</p>
                </div>
              </div>

              <div className="bg-slate-100 rounded-lg p-4">
                <h4 className="font-semibold text-slate-800 mb-2">💡 Conseil</h4>
                <p className="text-sm text-slate-600">
                  Votre sélection est mémorisée. Quand vous revenez sur le dashboard, 
                  le même CRM sera automatiquement sélectionné.
                </p>
              </div>
            </div>
          )}

          {/* Comptes */}
          {activeSection === 'accounts' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Database className="w-5 h-5 text-blue-600" />
                Comptes
              </h2>
              
              <p className="text-slate-600">
                Un compte représente <strong>un site/domaine spécifique</strong>. 
                Chaque compte a ses propres configurations (logos, GTM, légal).
              </p>

              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-3">📋 Configuration d'un compte</h4>
                <div className="grid md:grid-cols-2 gap-3 text-sm">
                  <div className="bg-white p-3 rounded border border-green-200">
                    <strong className="text-green-800">Général</strong>
                    <p className="text-green-700">CRM, Nom, Domaine, Types produits, Couleurs</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-green-200">
                    <strong className="text-green-800">Logos</strong>
                    <p className="text-green-700">Principal, Secondaire, Petit logo, Favicon</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-green-200">
                    <strong className="text-green-800">Tracking GTM</strong>
                    <p className="text-green-700">Pixel header, Code conversion, CTA click</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-green-200">
                    <strong className="text-green-800">Légal</strong>
                    <p className="text-green-700">Politique confidentialité, Mentions légales</p>
                  </div>
                </div>
              </div>

              <div className="bg-orange-50 rounded-lg p-4">
                <h4 className="font-semibold text-orange-800 mb-2">🎯 Tracking GTM au niveau du compte</h4>
                <ul className="text-sm text-orange-700 space-y-2">
                  <li><strong>Pixel Header</strong> : Code Facebook/Google dans &lt;head&gt;</li>
                  <li><strong>Code conversion</strong> : Script déclenché après validation téléphone (10 chiffres)</li>
                  <li><strong>Code CTA</strong> : Script au clic sur les boutons CTA</li>
                  <li><strong>URL redirection</strong> : Page merci par défaut</li>
                </ul>
              </div>
            </div>
          )}

          {/* Landing Pages */}
          {activeSection === 'lps' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-600" />
                Landing Pages (LP)
              </h2>
              
              <p className="text-slate-600">
                Une LP est la page sur laquelle arrivent vos visiteurs depuis les pubs (Taboola, Outbrain, etc.).
              </p>

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-3">📋 Créer une LP</h4>
                <div className="space-y-2 text-sm text-blue-700">
                  <p><strong>Compte</strong> : Sélectionner le compte associé (MDL, SPOOT, ZR7...)</p>
                  <p><strong>Code LP</strong> : Identifiant unique (ex: LP-TAB-V1)</p>
                  <p><strong>Type</strong> : Redirect (vers form externe) ou Intégré (form dans LP)</p>
                  <p><strong>Source</strong> : Taboola, Outbrain, Google Ads, etc.</p>
                  <p><strong>Sélecteur CTA</strong> : Classe CSS des boutons (ex: .cta-btn)</p>
                </div>
              </div>

              <div className="bg-purple-50 rounded-lg p-4">
                <h4 className="font-semibold text-purple-800 mb-2">🖱️ Tracking CTA (au niveau LP)</h4>
                <p className="text-sm text-purple-700 mb-3">
                  Le tracking CTA est généré au niveau de chaque LP pour compter les clics sur vos boutons.
                </p>
                <div className="bg-white p-3 rounded border border-purple-200">
                  <p className="text-xs text-purple-600 mb-1">Pour obtenir le script :</p>
                  <code className="text-xs text-purple-800">
                    Générateur Scripts → Sélectionnez la LP → Copiez le code
                  </code>
                </div>
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-800 mb-2">📊 Stats trackées par LP</h4>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>• <strong>Clics CTA</strong> : Nombre de clics sur les boutons</li>
                  <li>• <strong>Forms démarrés</strong> : Visiteurs arrivés sur le formulaire</li>
                  <li>• <strong>Leads</strong> : Formulaires soumis avec succès</li>
                </ul>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-2">📋 Dupliquer une LP</h4>
                <p className="text-sm text-green-700">
                  Cliquez sur l'icône de duplication pour créer une copie avec un nouveau code.
                  Utile pour tester différentes versions (A/B testing).
                </p>
              </div>
            </div>
          )}

          {/* Formulaires */}
          {activeSection === 'forms' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                Formulaires
              </h2>
              
              <p className="text-slate-600">
                Le formulaire capture les informations du prospect (nom, téléphone, email, etc.) 
                et les envoie vers votre CRM.
              </p>

              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-3">📋 Créer un formulaire</h4>
                <div className="space-y-2 text-sm text-green-700">
                  <p><strong>Compte</strong> : Sélectionner le compte associé</p>
                  <p><strong>Code Form</strong> : Identifiant unique (ex: PV-TAB-001)</p>
                  <p><strong>Type produit</strong> : Panneaux / Pompes / Isolation</p>
                  <p><strong>Source</strong> : Taboola, Outbrain, etc.</p>
                  <p><strong>Clé API CRM</strong> : Token d'authentification (fourni par le CRM)</p>
                </div>
              </div>

              <div className="bg-orange-50 rounded-lg p-4">
                <h4 className="font-semibold text-orange-800 mb-2">🎯 Tracking conversion</h4>
                <div className="space-y-3 text-sm">
                  <div className="bg-white p-3 rounded border border-orange-200">
                    <strong className="text-orange-800">Redirection</strong>
                    <p className="text-orange-700">Redirige vers une page /merci/ avec pixel (pas besoin de GTM)</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-orange-200">
                    <strong className="text-orange-800">GTM / Code JS</strong>
                    <p className="text-orange-700">Script déclenché après validation du téléphone (10 chiffres)</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-orange-200">
                    <strong className="text-orange-800">Aucun</strong>
                    <p className="text-orange-700">Pas de tracking conversion</p>
                  </div>
                </div>
              </div>

              <div className="bg-yellow-50 rounded-lg p-4">
                <h4 className="font-semibold text-yellow-800 mb-2">⚠️ Validation obligatoire</h4>
                <ul className="text-sm text-yellow-700 space-y-1">
                  <li>• <strong>Téléphone</strong> : 10 chiffres obligatoires</li>
                  <li>• <strong>Nom</strong> : Minimum 2 caractères</li>
                  <li>• <strong>Code postal</strong> : France métropolitaine (01-95)</li>
                </ul>
              </div>
            </div>
          )}

          {/* Tracking */}
          {activeSection === 'tracking' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Target className="w-5 h-5 text-blue-600" />
                Types de Tracking
              </h2>

              <div className="space-y-4">
                <div className="p-4 border border-blue-200 rounded-lg bg-blue-50">
                  <h4 className="font-semibold text-blue-800 flex items-center gap-2">
                    <MousePointer className="w-4 h-4" />
                    1. Pixel Header (configuré au niveau COMPTE)
                  </h4>
                  <p className="text-sm text-blue-700 mt-2">
                    Code Facebook Pixel, Google Ads, etc. dans le &lt;head&gt;. Configurez-le dans les paramètres du compte.
                  </p>
                </div>

                <div className="p-4 border border-purple-200 rounded-lg bg-purple-50">
                  <h4 className="font-semibold text-purple-800 flex items-center gap-2">
                    <MousePointer className="w-4 h-4" />
                    2. Tracking CTA (généré au niveau LP)
                  </h4>
                  <p className="text-sm text-purple-700 mt-2">
                    Script sur les boutons CTA pour compter les clics. Généré via le Générateur de Scripts.
                  </p>
                </div>

                <div className="p-4 border border-green-200 rounded-lg bg-green-50">
                  <h4 className="font-semibold text-green-800 flex items-center gap-2">
                    <Send className="w-4 h-4" />
                    3. Tracking Conversion (configuré au niveau COMPTE et FORM)
                  </h4>
                  <p className="text-sm text-green-700 mt-2">
                    Se déclenche après validation du téléphone (10 chiffres). Le code est dans le compte, le type dans le form.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Leads */}
          {activeSection === 'leads' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-600" />
                Gestion des Leads
              </h2>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 bg-green-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                    <strong className="text-green-800">Succès</strong>
                  </div>
                  <p className="text-sm text-green-700">Lead envoyé et accepté par le CRM</p>
                </div>
                <div className="p-4 bg-red-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <XCircle className="w-5 h-5 text-red-600" />
                    <strong className="text-red-800">Échec</strong>
                  </div>
                  <p className="text-sm text-red-700">Erreur lors de l'envoi (retry possible)</p>
                </div>
                <div className="p-4 bg-orange-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-orange-600" />
                    <strong className="text-orange-800">Doublon</strong>
                  </div>
                  <p className="text-sm text-orange-700">Le téléphone existe déjà dans le CRM</p>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <RefreshCw className="w-5 h-5 text-slate-600" />
                    <strong className="text-slate-800">En attente</strong>
                  </div>
                  <p className="text-sm text-slate-600">Envoi en cours ou non encore traité</p>
                </div>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">📋 Actions disponibles</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• <strong>Retry</strong> : Réessayer l'envoi d'un lead en échec</li>
                  <li>• <strong>Supprimer</strong> : Supprimer un lead (test) individuellement</li>
                  <li>• <strong>Supprimer en masse</strong> : Cocher plusieurs leads et supprimer</li>
                  <li>• <strong>Export CSV</strong> : Télécharger la liste des leads</li>
                </ul>
              </div>
            </div>
          )}

          {/* Analytics */}
          {activeSection === 'analytics' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                Analytics
              </h2>

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">📊 Dashboard comparatif</h4>
                <p className="text-sm text-blue-700">
                  Comparez les performances par source de diffusion (Native, Google, Facebook, TikTok) et par CRM.
                  Filtrez par période pour voir l'évolution.
                </p>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-2">🏆 Métriques clés</h4>
                <ul className="text-sm text-green-700 space-y-1">
                  <li>• <strong>Clics CTA</strong> : Visiteurs ayant cliqué sur un bouton</li>
                  <li>• <strong>Forms démarrés</strong> : Visiteurs ayant ouvert le formulaire</li>
                  <li>• <strong>Leads</strong> : Formulaires soumis avec succès</li>
                  <li>• <strong>Taux conversion</strong> : % Forms démarrés → Leads</li>
                </ul>
              </div>
            </div>
          )}

          {/* Generator */}
          {activeSection === 'generator' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Code className="w-5 h-5 text-blue-600" />
                Générateur de Scripts
              </h2>

              <div className="bg-purple-50 rounded-lg p-4">
                <h4 className="font-semibold text-purple-800 mb-2">🔧 Scripts disponibles</h4>
                <ul className="text-sm text-purple-700 space-y-2">
                  <li>
                    <strong>Script LP (Tracking CTA)</strong>
                    <p className="text-purple-600">Code à insérer pour tracker les clics sur les boutons CTA</p>
                  </li>
                  <li>
                    <strong>Script Form (Démarrage)</strong>
                    <p className="text-purple-600">Code pour tracker quand un visiteur ouvre le formulaire</p>
                  </li>
                </ul>
              </div>

              <div className="bg-yellow-50 rounded-lg p-4">
                <h4 className="font-semibold text-yellow-800 mb-2">⚠️ Important</h4>
                <p className="text-sm text-yellow-700">
                  Les codes GTM (Pixel, Conversion) sont configurés au niveau du <strong>Compte</strong>.
                  Le Générateur ne génère que le code de tracking CTA et Form Start.
                </p>
              </div>
            </div>
          )}

          {/* Users */}
          {activeSection === 'users' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-600" />
                Gestion des Utilisateurs
              </h2>

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">👥 Rôles disponibles</h4>
                <div className="space-y-2 text-sm">
                  <div className="bg-white p-3 rounded border border-blue-200">
                    <strong className="text-purple-800">Admin</strong>
                    <p className="text-blue-700">Accès complet : gestion utilisateurs, suppression, configuration</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-blue-200">
                    <strong className="text-blue-800">Éditeur</strong>
                    <p className="text-blue-700">Créer et modifier LP, Forms, Comptes. Pas de suppression ni gestion utilisateurs</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-blue-200">
                    <strong className="text-slate-800">Lecteur</strong>
                    <p className="text-blue-700">Consultation uniquement. Aucune modification possible</p>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-2">🔐 Comptes autorisés</h4>
                <p className="text-sm text-green-700 mb-3">
                  Vous pouvez restreindre l'accès d'un utilisateur à certains comptes seulement.
                </p>
                <div className="space-y-2 text-sm">
                  <div className="bg-white p-3 rounded border border-green-200">
                    <strong className="text-green-800">Aucun compte sélectionné</strong>
                    <p className="text-green-700">→ L'utilisateur a accès à TOUS les comptes</p>
                  </div>
                  <div className="bg-white p-3 rounded border border-green-200">
                    <strong className="text-green-800">Comptes spécifiques sélectionnés</strong>
                    <p className="text-green-700">→ L'utilisateur ne voit QUE les comptes cochés (ex: AUDIT GREEN, OBJECTIF ACADEMIE)</p>
                  </div>
                </div>
              </div>

              <div className="bg-orange-50 rounded-lg p-4">
                <h4 className="font-semibold text-orange-800 mb-2">📝 Exemple d'utilisation</h4>
                <p className="text-sm text-orange-700">
                  Un commercial externe ne travaille que sur le compte "AUDIT GREEN" → 
                  Créez-lui un compte Lecteur avec uniquement "AUDIT GREEN" dans les comptes autorisés.
                  Il ne verra que les LP, Forms et Leads de ce compte.
                </p>
              </div>
            </div>
          )}

          {/* Workflow */}
          {activeSection === 'workflow' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Zap className="w-5 h-5 text-blue-600" />
                Workflow Complet
              </h2>

              <div className="space-y-4">
                <div className="flex gap-4 items-start">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">1</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Configurer le Compte</h4>
                    <p className="text-sm text-slate-600">Ajouter les logos, les codes GTM (pixel header, conversion), les textes légaux</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">2</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Créer la Landing Page</h4>
                    <p className="text-sm text-slate-600">Définir le code LP, la source (Taboola...), le type (redirect/intégré)</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">3</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Générer le script CTA</h4>
                    <p className="text-sm text-slate-600">Aller dans Générateur Scripts → Copier le code de tracking CTA → Coller sur la LP</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">4</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Créer le Formulaire</h4>
                    <p className="text-sm text-slate-600">Définir le code Form, la clé API CRM, le type de tracking (redirect/GTM)</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">5</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Lancer la campagne</h4>
                    <p className="text-sm text-slate-600">Publier la LP et le formulaire avec les scripts de tracking intégrés</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">6</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Suivre les performances</h4>
                    <p className="text-sm text-slate-600">Dashboard → Comparatif → Analyser clics CTA, forms démarrés, leads, taux conversion</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== DASHBOARD COMPARATIF ====================
const CompareDashboard = () => {
  const { authFetch } = useAuth();
  const [stats, setStats] = useState(null);
  const [crms, setCrms] = useState([]);
  const [diffusionSources, setDiffusionSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    crm_ids: 'all',
    diffusion_category: 'all',
    period: 'week'
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadStats();
  }, [filters]);

  const loadInitialData = async () => {
    try {
      const [crmsRes, sourcesRes] = await Promise.all([
        authFetch(`${API}/api/crms`),
        authFetch(`${API}/api/diffusion-sources`)
      ]);
      if (crmsRes.ok) setCrms((await crmsRes.json()).crms || []);
      if (sourcesRes.ok) setDiffusionSources((await sourcesRes.json()).sources || []);
    } catch (e) {
      console.error(e);
    }
  };

  const loadStats = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.crm_ids) params.set('crm_ids', filters.crm_ids);
      if (filters.diffusion_category) params.set('diffusion_category', filters.diffusion_category);
      params.set('period', filters.period);
      
      const res = await authFetch(`${API}/api/analytics/compare?${params.toString()}`);
      if (res.ok) setStats(await res.json());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const diffusionCategories = [
    { value: 'all', label: 'Toutes les sources' },
    { value: 'native', label: 'Native (Taboola, Outbrain, MGID...)' },
    { value: 'google', label: 'Google Ads' },
    { value: 'facebook', label: 'Facebook/Meta Ads' },
    { value: 'tiktok', label: 'TikTok Ads' },
  ];

  const sourceTypeLabels = {
    native: 'Native',
    google: 'Google',
    facebook: 'Facebook',
    tiktok: 'TikTok',
    other: 'Autre'
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Dashboard Comparatif</h1>
          <p className="text-sm text-slate-500">Comparez les performances par source de diffusion et CRM en temps réel</p>
        </div>
      </div>

      {/* Filtres */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-slate-700 mb-1">CRM</label>
            <select 
              value={filters.crm_ids} 
              onChange={e => setFilters({ ...filters, crm_ids: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            >
              <option value="all">Tous les CRMs</option>
              {crms.map(crm => <option key={crm.id} value={crm.id}>{crm.name}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-slate-700 mb-1">Type de diffusion</label>
            <select 
              value={filters.diffusion_category} 
              onChange={e => setFilters({ ...filters, diffusion_category: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            >
              {diffusionCategories.map(cat => <option key={cat.value} value={cat.value}>{cat.label}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium text-slate-700 mb-1">Période</label>
            <select 
              value={filters.period} 
              onChange={e => setFilters({ ...filters, period: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            >
              <option value="today">Aujourd'hui</option>
              <option value="week">7 derniers jours</option>
              <option value="month">30 derniers jours</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
        </div>
      ) : stats ? (
        <>
          {/* Stats Totaux */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Clics CTA</p>
              <p className="text-2xl font-bold text-slate-800">{stats.totals?.cta_clicks || 0}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Forms Démarrés</p>
              <p className="text-2xl font-bold text-blue-600">{stats.totals?.forms_started || 0}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Leads Total</p>
              <p className="text-2xl font-bold text-green-600">{stats.totals?.leads_total || 0}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Leads Succès</p>
              <p className="text-2xl font-bold text-emerald-600">{stats.totals?.leads_success || 0}</p>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Taux Conversion</p>
              <p className="text-2xl font-bold text-purple-600">{stats.totals?.conversion_rate || 0}%</p>
              <p className="text-xs text-slate-400">démarrés → finis</p>
            </div>
          </div>

          {/* Comparaison par Source */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-800">Performance par type de diffusion</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Source</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Formulaires</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Démarrés</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Leads</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Succès</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Taux Conv.</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Taux Succès</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(stats.by_source || {}).map(([key, data]) => (
                    <tr key={key} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${
                            key === 'native' ? 'bg-orange-500' :
                            key === 'google' ? 'bg-red-500' :
                            key === 'facebook' ? 'bg-blue-500' :
                            key === 'tiktok' ? 'bg-black' : 'bg-slate-400'
                          }`} />
                          <span className="font-medium">{sourceTypeLabels[key] || key}</span>
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-sm">{data.forms_count}</td>
                      <td className="py-3 px-4 text-center text-sm">{data.forms_started}</td>
                      <td className="py-3 px-4 text-center font-medium text-green-600">{data.leads_total}</td>
                      <td className="py-3 px-4 text-center text-sm text-emerald-600">{data.leads_success}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          data.conversion_rate >= 50 ? 'bg-green-100 text-green-700' :
                          data.conversion_rate >= 25 ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {data.conversion_rate}%
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-sm">{data.success_rate}%</td>
                    </tr>
                  ))}
                  {Object.keys(stats.by_source || {}).length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500">Aucune donnée pour cette période</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Comparaison par CRM */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-800">Performance par CRM</h3>
            </div>
            <div className="grid md:grid-cols-2 gap-4 p-4">
              {Object.entries(stats.by_crm || {}).map(([key, data]) => (
                <div key={key} className={`p-4 rounded-lg border-2 ${
                  key === 'mdl' ? 'border-blue-200 bg-blue-50' : 'border-green-200 bg-green-50'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-semibold text-lg">{data.name}</h4>
                    <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                      key === 'mdl' ? 'bg-blue-600 text-white' : 'bg-green-600 text-white'
                    }`}>{data.leads_total} leads</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <p className="text-slate-500">Formulaires</p>
                      <p className="font-bold">{data.forms_count}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Démarrés</p>
                      <p className="font-bold">{data.forms_started}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Taux Conv.</p>
                      <p className="font-bold text-purple-600">{data.conversion_rate}%</p>
                    </div>
                  </div>
                </div>
              ))}
              {Object.keys(stats.by_crm || {}).length === 0 && (
                <div className="col-span-2 py-8 text-center text-slate-500">Aucune donnée pour cette période</div>
              )}
            </div>
          </div>
        </>
      ) : (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <p className="text-slate-500">Impossible de charger les données</p>
        </div>
      )}
    </div>
  );
};

// ==================== DIFFUSION SOURCES PAGE ====================
const DiffusionSourcesPage = () => {
  const { authFetch } = useAuth();
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ name: '', category: 'native', is_active: true });

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/diffusion-sources`);
      if (res.ok) setSources((await res.json()).sources || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await authFetch(`${API}/api/diffusion-sources`, { method: 'POST', body: JSON.stringify(formData) });
      if (res.ok) {
        setShowModal(false);
        setFormData({ name: '', category: 'native', is_active: true });
        loadSources();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteSource = async (id) => {
    if (!window.confirm('Supprimer cette source ?')) return;
    try {
      await authFetch(`${API}/api/diffusion-sources/${id}`, { method: 'DELETE' });
      loadSources();
    } catch (e) {
      console.error(e);
    }
  };

  const categories = {
    native: { label: 'Native', color: 'bg-orange-100 text-orange-700' },
    google: { label: 'Google', color: 'bg-red-100 text-red-700' },
    facebook: { label: 'Facebook/Meta', color: 'bg-blue-100 text-blue-700' },
    tiktok: { label: 'TikTok', color: 'bg-black text-white' },
    other: { label: 'Autre', color: 'bg-slate-100 text-slate-700' }
  };

  const groupedSources = sources.reduce((acc, source) => {
    const cat = source.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(source);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Sources de Diffusion</h1>
          <p className="text-sm text-slate-500">Gérez les plateformes de diffusion (Taboola, Google Ads, etc.)</p>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouvelle source
        </button>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(categories).map(([catKey, catInfo]) => {
            const catSources = groupedSources[catKey] || [];
            if (catSources.length === 0) return null;
            return (
              <div key={catKey} className="bg-white rounded-xl shadow-sm border border-slate-200">
                <div className="p-4 border-b border-slate-200 flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${catInfo.color}`}>{catInfo.label}</span>
                  <span className="text-sm text-slate-500">({catSources.length} sources)</span>
                </div>
                <div className="p-4 flex flex-wrap gap-2">
                  {catSources.map(source => (
                    <div key={source.id} className="flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-lg">
                      <span className="font-medium">{source.name}</span>
                      <button onClick={() => deleteSource(source.id)} className="p-1 hover:bg-slate-200 rounded">
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="Nouvelle source de diffusion">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nom de la source</label>
            <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Ex: Mediago, Yahoo Gemini..." required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Catégorie</label>
            <select value={formData.category} onChange={e => setFormData({ ...formData, category: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
              <option value="native">Native (Taboola, Outbrain...)</option>
              <option value="google">Google (Ads, YouTube...)</option>
              <option value="facebook">Facebook/Meta</option>
              <option value="tiktok">TikTok</option>
              <option value="other">Autre</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Créer</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

// ==================== PRODUCT TYPES PAGE ====================
const ProductTypesPage = () => {
  const { authFetch } = useAuth();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({
    name: '', slug: '', aide_montant: '', aides_liste: [], description: '', is_active: true
  });
  const [newAide, setNewAide] = useState('');

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/product-types`);
      if (res.ok) setProducts((await res.json()).product_types || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const url = editingProduct ? `${API}/api/product-types/${editingProduct.id}` : `${API}/api/product-types`;
    const method = editingProduct ? 'PUT' : 'POST';
    
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(formData) });
      if (res.ok) {
        setShowModal(false);
        setEditingProduct(null);
        setFormData({ name: '', slug: '', aide_montant: '', aides_liste: [], description: '', is_active: true });
        loadProducts();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const addAide = () => {
    if (newAide.trim() && !formData.aides_liste.includes(newAide.trim())) {
      setFormData({ ...formData, aides_liste: [...formData.aides_liste, newAide.trim()] });
      setNewAide('');
    }
  };

  const removeAide = (aide) => {
    setFormData({ ...formData, aides_liste: formData.aides_liste.filter(a => a !== aide) });
  };

  const editProduct = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      slug: product.slug,
      aide_montant: product.aide_montant,
      aides_liste: product.aides_liste || [],
      description: product.description || '',
      is_active: product.is_active !== false
    });
    setShowModal(true);
  };

  const deleteProduct = async (id) => {
    if (!window.confirm('Supprimer ce type de produit ?')) return;
    try {
      await authFetch(`${API}/api/product-types/${id}`, { method: 'DELETE' });
      loadProducts();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Types de Produits</h1>
          <p className="text-sm text-slate-500">Gérez les produits et leurs instructions (aides, montants)</p>
        </div>
        <button onClick={() => { setEditingProduct(null); setFormData({ name: '', slug: '', aide_montant: '', aides_liste: [], description: '', is_active: true }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouveau produit
        </button>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map(product => (
            <div key={product.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-4 bg-gradient-to-r from-blue-50 to-green-50">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-lg text-slate-800">{product.name}</h3>
                    <span className="text-xs bg-slate-200 px-2 py-0.5 rounded">{product.slug}</span>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => editProduct(product)} className="p-1.5 hover:bg-white/50 rounded" title="Modifier">
                      <Edit className="w-4 h-4 text-slate-600" />
                    </button>
                    <button onClick={() => deleteProduct(product.id)} className="p-1.5 hover:bg-white/50 rounded" title="Supprimer">
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                </div>
              </div>
              <div className="p-4">
                <div className="mb-3">
                  <p className="text-sm text-slate-500">Montant des aides</p>
                  <p className="text-2xl font-bold text-green-600">{product.aide_montant}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500 mb-2">Aides disponibles</p>
                  <div className="flex flex-wrap gap-1">
                    {(product.aides_liste || []).map(aide => (
                      <span key={aide} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">{aide}</span>
                    ))}
                  </div>
                </div>
                {product.description && (
                  <p className="mt-3 text-sm text-slate-500 border-t border-slate-100 pt-3">{product.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingProduct ? 'Modifier le produit' : 'Nouveau type de produit'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nom du produit</label>
              <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Panneaux solaires" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Slug (code)</label>
              <input type="text" value={formData.slug} onChange={e => setFormData({ ...formData, slug: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="solaire" required />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Montant des aides</label>
            <input type="text" value={formData.aide_montant} onChange={e => setFormData({ ...formData, aide_montant: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="10 000€" required />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Aides disponibles</label>
            <div className="flex gap-2 mb-2">
              <input type="text" value={newAide} onChange={e => setNewAide(e.target.value)} onKeyPress={e => e.key === 'Enter' && (e.preventDefault(), addAide())} className="flex-1 px-3 py-2 border border-slate-300 rounded-lg" placeholder="MaPrimeRenov, CEE..." />
              <button type="button" onClick={addAide} className="px-3 py-2 bg-slate-200 rounded-lg hover:bg-slate-300">
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {formData.aides_liste.map(aide => (
                <span key={aide} className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded-full">
                  {aide}
                  <button type="button" onClick={() => removeAide(aide)} className="hover:text-red-600">×</button>
                </span>
              ))}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} />
          </div>
          
          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{editingProduct ? 'Modifier' : 'Créer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

// ==================== ASSETS PAGE ====================
const AssetsPage = () => {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [assets, setAssets] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAsset, setEditingAsset] = useState(null);
  const [filter, setFilter] = useState('all'); // all, global, account
  const [formData, setFormData] = useState({
    label: '', url: '', asset_type: 'image', account_id: '', crm_id: ''
  });

  useEffect(() => {
    loadData();
  }, [selectedCRM]);

  const loadData = async () => {
    setLoading(true);
    try {
      const crmParam = selectedCRM ? `?crm_id=${selectedCRM}` : '';
      const [assetsRes, accountsRes] = await Promise.all([
        authFetch(`${API}/api/assets${crmParam}`),
        authFetch(`${API}/api/accounts${crmParam}`)
      ]);
      if (assetsRes.ok) setAssets((await assetsRes.json()).assets || []);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).accounts || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const url = editingAsset ? `${API}/api/assets/${editingAsset.id}` : `${API}/api/assets`;
    const method = editingAsset ? 'PUT' : 'POST';
    
    // Clean up data - set null for global assets
    const submitData = {
      ...formData,
      sub_account_id: formData.account_id || null,
      crm_id: formData.crm_id || selectedCRM || null
    };
    
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(submitData) });
      if (res.ok) {
        setShowModal(false);
        setEditingAsset(null);
        setFormData({ label: '', url: '', asset_type: 'image', account_id: '', crm_id: '' });
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const editAsset = (asset) => {
    setEditingAsset(asset);
    setFormData({
      label: asset.label,
      url: asset.url,
      asset_type: asset.asset_type,
      account_id: asset.sub_account_id || '',
      crm_id: asset.crm_id || ''
    });
    setShowModal(true);
  };

  const deleteAsset = async (id) => {
    if (!window.confirm('Supprimer cet asset ?')) return;
    try {
      await authFetch(`${API}/api/assets/${id}`, { method: 'DELETE' });
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  const copyUrl = (url) => {
    navigator.clipboard.writeText(url);
  };

  const filteredAssets = assets.filter(a => {
    if (filter === 'global') return !a.sub_account_id;
    if (filter === 'account') return !!a.sub_account_id;
    return true;
  });

  const assetTypes = {
    image: { label: 'Image', color: 'bg-blue-100 text-blue-700' },
    logo: { label: 'Logo', color: 'bg-purple-100 text-purple-700' },
    favicon: { label: 'Favicon', color: 'bg-green-100 text-green-700' },
    background: { label: 'Fond', color: 'bg-orange-100 text-orange-700' }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Bibliothèque d'Assets</h1>
          <p className="text-sm text-slate-500">Stockez vos URLs d'images et logos pour les réutiliser facilement</p>
        </div>
        <button onClick={() => { setEditingAsset(null); setFormData({ label: '', url: '', asset_type: 'image', account_id: '', crm_id: '' }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouvel Asset
        </button>
      </div>

      <div className="flex gap-2">
        <button 
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-sm ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
        >
          Tous
        </button>
        <button 
          onClick={() => setFilter('global')}
          className={`px-3 py-1.5 rounded-lg text-sm ${filter === 'global' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
        >
          Globaux
        </button>
        <button 
          onClick={() => setFilter('account')}
          className={`px-3 py-1.5 rounded-lg text-sm ${filter === 'account' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
        >
          Par sous-compte
        </button>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
        </div>
      ) : filteredAssets.length === 0 ? (
        <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
          <FolderOpen className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Aucun asset trouvé</p>
          <p className="text-sm text-slate-400 mt-1">Ajoutez des URLs d'images pour les réutiliser dans vos LP et formulaires</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredAssets.map(asset => (
            <div key={asset.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow">
              {/* Preview */}
              <div className="h-32 bg-slate-100 flex items-center justify-center overflow-hidden">
                <img 
                  src={asset.url} 
                  alt={asset.label}
                  className="max-h-full max-w-full object-contain"
                  onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                />
                <div className="hidden items-center justify-center text-slate-400 flex-col" style={{display: 'none'}}>
                  <Image className="w-8 h-8" />
                  <span className="text-xs mt-1">Erreur chargement</span>
                </div>
              </div>
              
              {/* Info */}
              <div className="p-3">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-slate-800 truncate" title={asset.label}>{asset.label}</h4>
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mt-1 ${assetTypes[asset.asset_type]?.color || 'bg-slate-100 text-slate-700'}`}>
                      {assetTypes[asset.asset_type]?.label || asset.asset_type}
                    </span>
                  </div>
                </div>
                
                <div className="text-xs text-slate-500 mb-2 flex items-center gap-1">
                  {asset.sub_account_id ? (
                    <>
                      <Building className="w-3 h-3" />
                      {accounts.find(a => a.id === asset.sub_account_id)?.name || 'Compte'}
                    </>
                  ) : (
                    <>
                      <Globe className="w-3 h-3" />
                      Global
                    </>
                  )}
                </div>
                
                <div className="flex items-center gap-1 pt-2 border-t border-slate-100">
                  <button 
                    onClick={() => copyUrl(asset.url)} 
                    className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs text-blue-600 hover:bg-blue-50 rounded"
                    title="Copier l'URL"
                  >
                    <Copy className="w-3 h-3" />
                    Copier URL
                  </button>
                  <button onClick={() => editAsset(asset)} className="p-1.5 hover:bg-slate-100 rounded" title="Modifier">
                    <Edit className="w-4 h-4 text-slate-600" />
                  </button>
                  <button onClick={() => deleteAsset(asset.id)} className="p-1.5 hover:bg-slate-100 rounded" title="Supprimer">
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingAsset ? 'Modifier l\'asset' : 'Nouvel asset'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Label (nom pour vous) *</label>
            <input 
              type="text" 
              value={formData.label} 
              onChange={e => setFormData({ ...formData, label: e.target.value })} 
              className="w-full px-3 py-2 border border-slate-300 rounded-lg" 
              placeholder="Ex: Logo principal bleu"
              required 
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">URL de l'image *</label>
            <input 
              type="url" 
              value={formData.url} 
              onChange={e => setFormData({ ...formData, url: e.target.value })} 
              className="w-full px-3 py-2 border border-slate-300 rounded-lg" 
              placeholder="https://..."
              required 
            />
            {formData.url && (
              <div className="mt-2 p-2 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-500 mb-1">Aperçu:</p>
                <img src={formData.url} alt="Preview" className="max-h-20 object-contain" onError={e => e.target.style.display='none'} />
              </div>
            )}
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
              <select value={formData.asset_type} onChange={e => setFormData({ ...formData, asset_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                <option value="image">Image</option>
                <option value="logo">Logo</option>
                <option value="favicon">Favicon</option>
                <option value="background">Image de fond</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Associer à un compte</label>
              <select value={formData.account_id} onChange={e => setFormData({ ...formData, account_id: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                <option value="">Global (tous les comptes)</option>
                {accounts.map(acc => <option key={acc.id} value={acc.id}>{acc.name}</option>)}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{editingAsset ? 'Modifier' : 'Créer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

const SettingsPage = () => {
  const { authFetch } = useAuth();
  const [crms, setCrms] = useState([]);

  useEffect(() => {
    loadCRMs();
  }, []);

  const loadCRMs = async () => {
    try {
      const res = await authFetch(`${API}/api/crms`);
      if (res.ok) setCrms((await res.json()).crms || []);
    } catch (e) {
      console.error(e);
    }
  };

  const initCRMs = async () => {
    try {
      await authFetch(`${API}/api/crms/init`, { method: 'POST' });
      loadCRMs();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Paramètres</h1>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="font-semibold text-slate-800 mb-4">CRMs configurés</h3>
        
        {crms.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-slate-500 mb-4">Aucun CRM configuré</p>
            <button onClick={initCRMs} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Initialiser les CRMs par défaut
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {crms.map(crm => (
              <div key={crm.id} className="p-4 bg-slate-50 rounded-lg">
                <h4 className="font-medium text-slate-800">{crm.name}</h4>
                <p className="text-sm text-slate-500">{crm.api_url}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ==================== MAIN APP ====================

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <CRMProvider>
        <BrowserRouter>
          <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/compare" element={<ProtectedRoute><CompareDashboard /></ProtectedRoute>} />
          <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="/leads" element={<ProtectedRoute><LeadsPage /></ProtectedRoute>} />
          <Route path="/lps" element={<ProtectedRoute><LPsPage /></ProtectedRoute>} />
          <Route path="/forms" element={<ProtectedRoute><FormsPage /></ProtectedRoute>} />
          <Route path="/accounts" element={<ProtectedRoute><SubAccountsPage /></ProtectedRoute>} />
          <Route path="/assets" element={<ProtectedRoute><AssetsPage /></ProtectedRoute>} />
          <Route path="/generator" element={<ProtectedRoute><ScriptGeneratorPage /></ProtectedRoute>} />
          <Route path="/guide" element={<ProtectedRoute><GuidePage /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
          <Route path="/activity" element={<ProtectedRoute><ActivityPage /></ProtectedRoute>} />
          <Route path="/diffusion" element={<ProtectedRoute><DiffusionSourcesPage /></ProtectedRoute>} />
          <Route path="/products" element={<ProtectedRoute><ProductTypesPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        </BrowserRouter>
      </CRMProvider>
    </AuthProvider>
  );
}

export default App;
