import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  BarChart3, Users, CheckCircle, XCircle, RefreshCw, Download, Eye, Search, Copy, 
  Settings, Plus, LogOut, Home, Layers, FileText, TrendingUp, MessageSquare, 
  Activity, ChevronRight, ChevronDown, Edit, Trash2, ExternalLink, Code,
  Building, Globe, Image, Shield, Bell, Filter, Calendar, Award, AlertTriangle,
  HelpCircle, BookOpen, Zap, Target, MousePointer, Send, Database, Lock,
  FolderOpen, Tag, Link2, Clipboard, Key
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
    { path: '/billing', icon: TrendingUp, label: 'Facturation Inter-CRM' },
  ];

  // Section: Gestion
  const gestionItems = [
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
    { path: '/leads', icon: Users, label: 'Leads' },
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
        <StatCard icon={FileText} label="Forms démarrés" value={stats?.forms_started || 0} color="blue" />
        <StatCard icon={CheckCircle} label="Leads reçus" value={stats?.leads_total || 0} color="green" />
        <StatCard icon={Send} label="Envoyés CRM" value={stats?.leads_sent || 0} color="purple" />
        <StatCard icon={XCircle} label="Échecs" value={stats?.leads_failed || 0} color="red" />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-3">Taux de conversion</h3>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600">Formulaire → Lead</span>
                <span className="font-medium">{stats?.form_to_lead_rate || 0}%</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${stats?.form_to_lead_rate || 0}%` }} />
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
    images: [],  // Bibliothèque d'images [{name: "Bannière", url: "..."}, ...]
    privacy_policy_text: '', legal_mentions_text: '',
    layout: 'center', primary_color: '#3B82F6', secondary_color: '#1E40AF', style_officiel: false,
    // GTM Tracking - au niveau du compte
    gtm_pixel_header: '', gtm_conversion_code: '', gtm_cta_code: '',
    // URLs de redirection nommées
    named_redirect_urls: [],  // [{name: "Google", url: "..."}, ...]
    default_redirect_url: '', notes: '',
    form_template: {
      phone_required: true, phone_digits: 10, nom_required: true,
      show_civilite: true, show_prenom: true, show_email: true, show_departement: true,
      show_code_postal: true, show_type_logement: true, show_statut_occupant: true, show_facture: true,
      postal_code_france_metro_only: true, form_style: 'modern'
    }
  };
  const [formData, setFormData] = useState(defaultFormData);
  const [newRedirectUrl, setNewRedirectUrl] = useState({ name: '', url: '' });
  const [newImage, setNewImage] = useState({ name: '', url: '' });

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
    setFormData({ 
      ...defaultFormData, 
      ...account, 
      product_types: account.product_types || ['solaire'],
      named_redirect_urls: account.named_redirect_urls || [],
      images: account.images || []
    });
    setActiveTab('general');
    setShowModal(true);
  };

  const deleteAccount = async (id) => {
    if (!window.confirm('Supprimer ce compte ?')) return;
    try { await authFetch(`${API}/api/accounts/${id}`, { method: 'DELETE' }); loadData(); } catch (e) { console.error(e); }
  };

  const addRedirectUrl = () => {
    if (!newRedirectUrl.name || !newRedirectUrl.url) return;
    setFormData({
      ...formData,
      named_redirect_urls: [...(formData.named_redirect_urls || []), { ...newRedirectUrl }]
    });
    setNewRedirectUrl({ name: '', url: '' });
  };

  const removeRedirectUrl = (index) => {
    setFormData({
      ...formData,
      named_redirect_urls: formData.named_redirect_urls.filter((_, i) => i !== index)
    });
  };

  const addImage = () => {
    if (!newImage.name || !newImage.url) return;
    setFormData({
      ...formData,
      images: [...(formData.images || []), { ...newImage }]
    });
    setNewImage({ name: '', url: '' });
  };

  const removeImage = (index) => {
    setFormData({
      ...formData,
      images: formData.images.filter((_, i) => i !== index)
    });
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
    { id: 'images', label: 'Images', icon: FolderOpen },
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

          {/* Tab: Images Library */}
          {activeTab === 'images' && (
            <div className="space-y-4">
              <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                <h4 className="font-medium text-purple-800 flex items-center gap-2"><FolderOpen className="w-4 h-4" /> Bibliothèque d'images du compte</h4>
                <p className="text-sm text-purple-700 mt-1">Stockez ici toutes les images utilisées pour ce compte (bannières, produits, etc.) pour les retrouver facilement lors de la génération de briefs.</p>
              </div>
              
              {/* Liste des images existantes */}
              {(formData.images || []).length > 0 && (
                <div className="grid grid-cols-2 gap-3">
                  {formData.images.map((img, idx) => (
                    <div key={idx} className="border border-slate-200 rounded-lg overflow-hidden bg-white">
                      <div className="aspect-video bg-slate-100 flex items-center justify-center">
                        <img src={img.url} alt={img.name} className="max-h-full max-w-full object-contain" onError={(e) => e.target.style.display = 'none'} />
                      </div>
                      <div className="p-2 flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-700 truncate">{img.name}</span>
                        <button type="button" onClick={() => removeImage(idx)} className="p-1 text-red-600 hover:bg-red-100 rounded">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {(formData.images || []).length === 0 && (
                <div className="text-center py-8 text-slate-400">
                  <Image className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>Aucune image ajoutée</p>
                </div>
              )}
              
              {/* Ajouter une nouvelle image */}
              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">Ajouter une image</label>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={newImage.name} 
                    onChange={e => setNewImage({ ...newImage, name: e.target.value })}
                    placeholder="Nom (ex: Bannière principale)" 
                    className="w-48 px-2 py-1 text-sm border border-slate-300 rounded" 
                  />
                  <input 
                    type="url" 
                    value={newImage.url} 
                    onChange={e => setNewImage({ ...newImage, url: e.target.value })}
                    placeholder="URL de l'image (https://...)" 
                    className="flex-1 px-2 py-1 text-sm border border-slate-300 rounded" 
                  />
                  <button type="button" onClick={addImage} className="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700">
                    Ajouter
                  </button>
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
              
              {/* URLs de redirection nommées */}
              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">URLs de redirection nommées</label>
                <p className="text-xs text-slate-500 mb-3">Créez plusieurs URLs de redirection (ex: "Google", "Taboola", "Facebook") pour pouvoir choisir laquelle utiliser dans chaque LP/Form</p>
                
                {/* Liste des URLs existantes */}
                {(formData.named_redirect_urls || []).length > 0 && (
                  <div className="space-y-2 mb-3">
                    {formData.named_redirect_urls.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-2 bg-slate-50 p-2 rounded-lg">
                        <span className="font-medium text-slate-700 min-w-20">{item.name}</span>
                        <span className="text-xs text-slate-500 flex-1 truncate">{item.url}</span>
                        <button type="button" onClick={() => removeRedirectUrl(idx)} className="p-1 text-red-600 hover:bg-red-100 rounded">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Ajouter une nouvelle URL */}
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={newRedirectUrl.name} 
                    onChange={e => setNewRedirectUrl({ ...newRedirectUrl, name: e.target.value })}
                    placeholder="Nom (ex: Google)" 
                    className="w-32 px-2 py-1 text-sm border border-slate-300 rounded" 
                  />
                  <input 
                    type="url" 
                    value={newRedirectUrl.url} 
                    onChange={e => setNewRedirectUrl({ ...newRedirectUrl, url: e.target.value })}
                    placeholder="URL (https://...)" 
                    className="flex-1 px-2 py-1 text-sm border border-slate-300 rounded" 
                  />
                  <button type="button" onClick={addRedirectUrl} className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
                    Ajouter
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">URL de redirection par défaut</label>
                <input type="url" value={formData.default_redirect_url || ''} onChange={e => setFormData({ ...formData, default_redirect_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://exemple.fr/merci/" />
                <p className="text-xs text-slate-500 mt-1">Utilisée si aucune URL nommée n'est sélectionnée</p>
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
    source_name: '', notes: '', status: 'active',
    lp_type: 'redirect', redirect_url_name: '', form_url: '', html_code: ''
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
        <button onClick={() => { setEditingLP(null); setFormData({ account_id: '', code: '', name: '', url: '', source_type: 'native', source_name: '', notes: '', status: 'active', lp_type: 'redirect', redirect_url_name: '', form_url: '', html_code: '' }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
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
            <h4 className="font-medium text-slate-800">Source de diffusion</h4>
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

          {/* Section: Code HTML */}
          <div className="bg-purple-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-purple-800 flex items-center gap-2">
              <Code className="w-4 h-4" /> Code HTML de la LP
            </h4>
            <textarea 
              value={formData.html_code || ''} 
              onChange={e => setFormData({ ...formData, html_code: e.target.value })} 
              className="w-full px-3 py-2 border border-purple-300 rounded-lg font-mono text-xs bg-white" 
              rows={8} 
              placeholder="Coller ici le code HTML complet de la LP..."
            />
            <p className="text-xs text-purple-600">Stockez le code HTML de votre LP pour référence</p>
          </div>

          {/* Section: Notes */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
              <textarea value={formData.notes || ''} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} placeholder="Notes personnelles sur cette LP..." />
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
  const [duplicateData, setDuplicateData] = useState({ new_code: '', new_name: '', new_crm_api_key: '' });
  const [error, setError] = useState('');
  const [productFilter, setProductFilter] = useState(''); // Nouveau filtre produit
  const [formData, setFormData] = useState({
    account_id: '', lp_ids: [], code: '', name: '', url: '', product_type: 'panneaux',
    source_type: 'native', source_name: '', tracking_type: 'redirect',
    redirect_url_name: '', notes: '', status: 'active',
    form_type: 'standalone', html_code: '', crm_api_key: '',
    exclude_from_routing: false  // Exclusion du routage inter-CRM
  });

  useEffect(() => {
    loadData();
  }, [selectedCRM, productFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      let crmParam = selectedCRM ? `crm_id=${selectedCRM}` : '';
      let productParam = productFilter ? `product_type=${productFilter}` : '';
      let queryParams = [crmParam, productParam].filter(Boolean).join('&');
      let queryString = queryParams ? `?${queryParams}` : '';
      
      const [formsRes, accountsRes, lpsRes] = await Promise.all([
        authFetch(`${API}/api/forms${queryString}`),
        authFetch(`${API}/api/accounts${selectedCRM ? `?crm_id=${selectedCRM}` : ''}`),
        authFetch(`${API}/api/lps${selectedCRM ? `?crm_id=${selectedCRM}` : ''}`)
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
    if (!showDuplicateModal || !duplicateData.new_code || !duplicateData.new_name || !duplicateData.new_crm_api_key) return;
    try {
      const res = await authFetch(`${API}/api/forms/${showDuplicateModal.id}/duplicate?new_code=${encodeURIComponent(duplicateData.new_code)}&new_name=${encodeURIComponent(duplicateData.new_name)}&new_crm_api_key=${encodeURIComponent(duplicateData.new_crm_api_key)}`, { method: 'POST' });
      if (res.ok) {
        setShowDuplicateModal(null);
        setDuplicateData({ new_code: '', new_name: '', new_crm_api_key: '' });
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

  const productTypes = [
    { value: '', label: 'Tous', icon: '📋' },
    { value: 'panneaux', label: 'PV', icon: '☀️' },
    { value: 'pompes', label: 'PAC', icon: '🔥' },
    { value: 'isolation', label: 'ITE', icon: '🏠' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Formulaires</h1>
        <button onClick={() => { setEditingForm(null); setFormData({ account_id: '', lp_ids: [], code: '', name: '', url: '', product_type: 'panneaux', source_type: 'native', source_name: '', tracking_type: 'redirect', redirect_url_name: '', notes: '', status: 'active', form_type: 'standalone', html_code: '', crm_api_key: '' }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouveau formulaire
        </button>
      </div>

      {/* Filtre par type de produit */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-500">Filtrer par produit :</span>
        <div className="flex gap-1">
          {productTypes.map(pt => (
            <button
              key={pt.value}
              onClick={() => setProductFilter(pt.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                productFilter === pt.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {pt.icon} {pt.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-400 ml-2">({forms.length} formulaires)</span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <Table
          columns={[
            { key: 'code', label: 'Code', render: v => <span className="font-mono text-sm bg-slate-100 px-2 py-1 rounded">{v}</span> },
            { key: 'name', label: 'Nom' },
            { key: 'internal_api_key', label: 'Clé API (pour vos scripts)', render: (v, row) => v ? (
              <div className="flex items-center gap-1">
                <code className="text-xs bg-orange-50 text-orange-700 px-2 py-1 rounded font-mono truncate max-w-[180px]" title={v}>{v}</code>
                <button onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(v); }} className="p-1 hover:bg-orange-100 rounded" title="Copier la clé">
                  <Copy className="w-3 h-3 text-orange-600" />
                </button>
              </div>
            ) : <span className="text-xs text-slate-400">Non générée</span> },
            { key: 'source_name', label: 'Source' },
            { key: 'exclude_from_routing', label: 'Routage', render: (v, row) => 
              v ? <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded" title="Ce formulaire est exclu du routage inter-CRM">🚫 Exclu</span> : 
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded" title="Ce formulaire peut être rerouté vers l'autre CRM">✓ Actif</span>
            },
            { key: 'stats', label: 'Leads', render: v => v?.completed || 0 },
            { key: 'status', label: 'Statut', render: v => <StatusBadge status={v} /> },
            { 
              key: 'actions', 
              label: '', 
              render: (_, row) => (
                <div className="flex gap-1">
                  <button onClick={() => { setEditingForm(row); setFormData(row); setShowModal(true); }} className="p-1 hover:bg-slate-100 rounded" title="Modifier">
                    <Edit className="w-4 h-4 text-slate-600" />
                  </button>
                  <button onClick={() => { setShowDuplicateModal(row); setDuplicateData({ new_code: row.code + '-COPY', new_name: row.name + ' (copie)', new_crm_api_key: '' }); }} className="p-1 hover:bg-slate-100 rounded" title="Dupliquer">
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
            Dupliquer <strong>{showDuplicateModal?.name}</strong>. Une nouvelle clé API interne sera générée automatiquement.
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
            <label className="block text-sm font-medium text-slate-700 mb-1">Clé API CRM destination (ZR7/MDL) *</label>
            <input type="text" value={duplicateData.new_crm_api_key} onChange={e => setDuplicateData({ ...duplicateData, new_crm_api_key: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm" placeholder="uuid-xxx-xxx" required />
            <p className="text-xs text-slate-500 mt-1">La clé API fournie par ZR7 ou MDL pour ce formulaire</p>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={() => setShowDuplicateModal(null)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button onClick={duplicateForm} disabled={!duplicateData.new_crm_api_key} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">Dupliquer</button>
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
                <label className="block text-sm font-medium text-slate-700 mb-1">URL du formulaire</label>
                <input type="url" value={formData.url || ''} onChange={e => setFormData({ ...formData, url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://..." />
              </div>
            </div>

            {/* PRODUIT - CHOIX IMPORTANT */}
            <div className="bg-yellow-100 p-4 rounded-lg border-2 border-yellow-400">
              <label className="block text-sm font-bold text-yellow-800 mb-2">🎯 TYPE DE PRODUIT *</label>
              <div className="flex gap-2">
                {[
                  { value: 'panneaux', label: '☀️ Panneaux Solaires (PV)', color: 'yellow' },
                  { value: 'pompes', label: '🔥 Pompes à Chaleur (PAC)', color: 'red' },
                  { value: 'isolation', label: '🏠 Isolation (ITE)', color: 'blue' }
                ].map(prod => (
                  <button
                    key={prod.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, product_type: prod.value })}
                    className={`flex-1 px-4 py-3 rounded-lg font-medium transition-all ${
                      formData.product_type === prod.value
                        ? prod.color === 'yellow' ? 'bg-yellow-500 text-white ring-2 ring-yellow-600' :
                          prod.color === 'red' ? 'bg-red-500 text-white ring-2 ring-red-600' :
                          'bg-blue-500 text-white ring-2 ring-blue-600'
                        : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    {prod.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-yellow-700 mt-2">
                ⚠️ Chaque formulaire = 1 seul type de produit. Ce choix détermine le routage et la facturation.
              </p>
            </div>
          </div>

          {/* Section: Type et Tracking */}
          <div className="bg-green-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-green-800 flex items-center gap-2">
              <Target className="w-4 h-4" /> Type et Tracking
            </h4>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type de formulaire</label>
                <select value={formData.form_type} onChange={e => setFormData({ ...formData, form_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                  <option value="standalone">Page séparée</option>
                  <option value="integrated">Intégré dans LP</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Type de tracking</label>
                <select value={formData.tracking_type} onChange={e => setFormData({ ...formData, tracking_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                  <option value="redirect">Redirection (page merci)</option>
                  <option value="gtm">GTM / Code JS</option>
                  <option value="none">Aucun</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section: Intégration CRM */}
          <div className="bg-orange-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-orange-800 flex items-center gap-2">
              <Key className="w-4 h-4" /> Intégration CRM (ZR7 / MDL)
            </h4>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Clé API CRM destination</label>
              <input 
                type="text" 
                value={formData.crm_api_key || ''} 
                onChange={e => setFormData({ ...formData, crm_api_key: e.target.value })} 
                className="w-full px-3 py-2 border border-orange-300 rounded-lg font-mono text-sm" 
                placeholder="Ex: c2c4149e-a3ff-4290-a140-c1e90be8441a"
              />
              <p className="text-xs text-orange-600 mt-1">
                La clé API fournie par ZR7 ou MDL pour envoyer les leads vers leur CRM
              </p>
            </div>

            {/* Exclusion du routage inter-CRM */}
            <div className="bg-red-50 p-3 rounded border border-red-200">
              <label className="flex items-center gap-3 cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={formData.exclude_from_routing || false}
                  onChange={e => setFormData({ ...formData, exclude_from_routing: e.target.checked })}
                  className="w-5 h-5 rounded border-red-300 text-red-600 focus:ring-red-500"
                />
                <div>
                  <span className="font-medium text-red-800">Exclure du routage inter-CRM</span>
                  <p className="text-xs text-red-600 mt-0.5">
                    Si coché, les leads de ce formulaire ne seront JAMAIS reroutés vers l'autre CRM.
                    Utile pour les formulaires de redirection (évite doublons cross-CRM).
                  </p>
                </div>
              </label>
            </div>

            {editingForm?.internal_api_key && (
              <div className="bg-white p-3 rounded border border-orange-200">
                <label className="block text-xs font-medium text-slate-500 mb-1">Clé API interne (pour recevoir les leads)</label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs bg-slate-100 px-2 py-1 rounded font-mono text-slate-600">{editingForm.internal_api_key}</code>
                  <button 
                    type="button" 
                    onClick={() => navigator.clipboard.writeText(editingForm.internal_api_key)} 
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    Copier
                  </button>
                </div>
              </div>
            )}
            
            {/* Info validations automatiques */}
            <div className="bg-white p-3 rounded border border-orange-200">
              <p className="text-xs text-slate-600">
                <strong>⚠️ Validations automatiques dans le script :</strong><br/>
                • Téléphone obligatoire<br/>
                • Nom obligatoire (min 2 caractères)<br/>
                • Département France métropolitaine uniquement (01-95)
              </p>
            </div>
          </div>

          {/* Section: Source */}
          <div className="bg-slate-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-slate-800">Source de diffusion</h4>
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
              <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
              <textarea value={formData.notes || ''} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} placeholder="Notes personnelles..." />
            </div>
          </div>

          {/* Section: Code HTML */}
          <div className="bg-purple-50 p-4 rounded-lg space-y-4">
            <h4 className="font-medium text-purple-800 flex items-center gap-2">
              <Code className="w-4 h-4" /> Code HTML du formulaire
            </h4>
            <textarea 
              value={formData.html_code || ''} 
              onChange={e => setFormData({ ...formData, html_code: e.target.value })} 
              className="w-full px-3 py-2 border border-purple-300 rounded-lg font-mono text-xs bg-white" 
              rows={8} 
              placeholder="Coller ici le code HTML complet du formulaire..."
            />
            <p className="text-xs text-purple-600">Stockez le code HTML de votre formulaire pour référence</p>
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
        <StatCard icon={FileText} label="Forms démarrés" value={stats?.forms_started || 0} color="blue" />
        <StatCard icon={CheckCircle} label="Leads" value={stats?.leads_total || 0} color="green" />
        <StatCard icon={Send} label="Envoyés CRM" value={stats?.leads_sent || 0} color="purple" />
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
  const [accounts, setAccounts] = useState([]);
  const [selectedLP, setSelectedLP] = useState('');
  const [selectedForm, setSelectedForm] = useState('');
  const [generatedBrief, setGeneratedBrief] = useState(null);
  const [copied, setCopied] = useState(false);
  
  // LP selection options
  const [lpOptions, setLpOptions] = useState({
    include_logo_main: false,
    include_logo_secondary: false,
    include_logo_small: false,
    include_favicon: false,
    include_gtm_pixel: false,
    include_gtm_conversion: false,
    include_gtm_cta: false,
    include_privacy_policy: false,
    include_legal_mentions: false,
    include_colors: false,
    include_redirect_url: '',
    include_notes: false
  });
  
  // Form selection options
  const [formOptions, setFormOptions] = useState({
    include_logo_main: false,
    include_logo_secondary: false,
    include_gtm_pixel: false,
    include_gtm_conversion: false,
    include_privacy_policy: false,
    include_redirect_url: '',
    include_api_key: false,
    include_notes: false
  });

  useEffect(() => {
    loadData();
  }, [selectedCRM]);

  const loadData = async () => {
    try {
      const crmParam = selectedCRM ? `?crm_id=${selectedCRM}` : '';
      const [lpsRes, formsRes, accountsRes] = await Promise.all([
        authFetch(`${API}/api/lps${crmParam}`),
        authFetch(`${API}/api/forms${crmParam}`),
        authFetch(`${API}/api/accounts${crmParam}`)
      ]);
      if (lpsRes.ok) setLps((await lpsRes.json()).lps || []);
      if (formsRes.ok) setForms((await formsRes.json()).forms || []);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).accounts || []);
    } catch (e) {
      console.error(e);
    }
  };

  // Get redirect URLs for selected LP's account
  const getRedirectUrlsForLP = () => {
    if (!selectedLP) return [];
    const lp = lps.find(l => l.id === selectedLP);
    if (!lp) return [];
    const accountId = lp.account_id || lp.sub_account_id;
    const account = accounts.find(a => a.id === accountId);
    return account?.named_redirect_urls || [];
  };

  // Get redirect URLs for selected Form's account
  const getRedirectUrlsForForm = () => {
    if (!selectedForm) return [];
    const form = forms.find(f => f.id === selectedForm);
    if (!form) return [];
    const accountId = form.account_id || form.sub_account_id;
    const account = accounts.find(a => a.id === accountId);
    return account?.named_redirect_urls || [];
  };

  const generateLPBrief = async () => {
    if (!selectedLP) return;
    try {
      const res = await authFetch(`${API}/api/generate-brief/lp`, {
        method: 'POST',
        body: JSON.stringify({ lp_id: selectedLP, ...lpOptions })
      });
      if (res.ok) {
        setGeneratedBrief(await res.json());
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || 'Erreur lors de la génération');
      }
    } catch (e) {
      console.error(e);
      alert('Erreur de connexion');
    }
  };

  const generateFormBrief = async () => {
    if (!selectedForm) return;
    try {
      const res = await authFetch(`${API}/api/generate-brief/form`, {
        method: 'POST',
        body: JSON.stringify({ form_id: selectedForm, ...formOptions })
      });
      if (res.ok) {
        setGeneratedBrief(await res.json());
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || 'Erreur lors de la génération');
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

  const CheckboxOption = ({ label, checked, onChange }) => (
    <label className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 p-1 rounded">
      <input type="checkbox" checked={checked} onChange={onChange} className="rounded border-slate-300 text-blue-600" />
      <span className="text-sm text-slate-700">{label}</span>
    </label>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Générateur de Briefs</h1>
        <p className="text-sm text-slate-500 mt-1">Sélectionnez les éléments à inclure dans le brief pour Emergent</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* LP Brief Generator */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" />
            Brief LP
          </h3>
          
          <div className="space-y-4">
            <select value={selectedLP} onChange={e => { setSelectedLP(e.target.value); setGeneratedBrief(null); }} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
              <option value="">Sélectionner une LP</option>
              {lps.map(lp => <option key={lp.id} value={lp.id}>{lp.code} - {lp.name}</option>)}
            </select>

            {selectedLP && (
              <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
                <p className="text-xs font-medium text-slate-600 uppercase">Éléments à inclure :</p>
                
                <div className="grid grid-cols-2 gap-1">
                  <CheckboxOption label="Logo principal" checked={lpOptions.include_logo_main} onChange={e => setLpOptions({...lpOptions, include_logo_main: e.target.checked})} />
                  <CheckboxOption label="Logo secondaire" checked={lpOptions.include_logo_secondary} onChange={e => setLpOptions({...lpOptions, include_logo_secondary: e.target.checked})} />
                  <CheckboxOption label="Petit logo" checked={lpOptions.include_logo_small} onChange={e => setLpOptions({...lpOptions, include_logo_small: e.target.checked})} />
                  <CheckboxOption label="Favicon" checked={lpOptions.include_favicon} onChange={e => setLpOptions({...lpOptions, include_favicon: e.target.checked})} />
                  <CheckboxOption label="Pixel GTM (header)" checked={lpOptions.include_gtm_pixel} onChange={e => setLpOptions({...lpOptions, include_gtm_pixel: e.target.checked})} />
                  <CheckboxOption label="Code conversion GTM" checked={lpOptions.include_gtm_conversion} onChange={e => setLpOptions({...lpOptions, include_gtm_conversion: e.target.checked})} />
                  <CheckboxOption label="Code CTA GTM" checked={lpOptions.include_gtm_cta} onChange={e => setLpOptions({...lpOptions, include_gtm_cta: e.target.checked})} />
                  <CheckboxOption label="Politique confidentialité" checked={lpOptions.include_privacy_policy} onChange={e => setLpOptions({...lpOptions, include_privacy_policy: e.target.checked})} />
                  <CheckboxOption label="Mentions légales" checked={lpOptions.include_legal_mentions} onChange={e => setLpOptions({...lpOptions, include_legal_mentions: e.target.checked})} />
                  <CheckboxOption label="Couleurs" checked={lpOptions.include_colors} onChange={e => setLpOptions({...lpOptions, include_colors: e.target.checked})} />
                  <CheckboxOption label="Notes" checked={lpOptions.include_notes} onChange={e => setLpOptions({...lpOptions, include_notes: e.target.checked})} />
                </div>

                {/* Redirect URL selector */}
                <div className="pt-2 border-t border-slate-200">
                  <label className="block text-xs font-medium text-slate-600 mb-1">URL de redirection :</label>
                  <select 
                    value={lpOptions.include_redirect_url} 
                    onChange={e => setLpOptions({...lpOptions, include_redirect_url: e.target.value})}
                    className="w-full px-2 py-1 text-sm border border-slate-300 rounded"
                  >
                    <option value="">Aucune</option>
                    <option value="default">URL par défaut</option>
                    {getRedirectUrlsForLP().map((u, i) => (
                      <option key={i} value={u.name}>{u.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            <button onClick={generateLPBrief} disabled={!selectedLP} className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed">
              Générer le brief LP
            </button>
          </div>
        </div>

        {/* Form Brief Generator */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-green-600" />
            Brief Formulaire
          </h3>
          
          <div className="space-y-4">
            <select value={selectedForm} onChange={e => { setSelectedForm(e.target.value); setGeneratedBrief(null); }} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
              <option value="">Sélectionner un formulaire</option>
              {forms.map(f => <option key={f.id} value={f.id}>{f.code} - {f.name}</option>)}
            </select>

            {selectedForm && (
              <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
                <p className="text-xs font-medium text-slate-600 uppercase">Éléments à inclure :</p>
                
                <div className="grid grid-cols-2 gap-1">
                  <CheckboxOption label="Logo principal" checked={formOptions.include_logo_main} onChange={e => setFormOptions({...formOptions, include_logo_main: e.target.checked})} />
                  <CheckboxOption label="Logo secondaire" checked={formOptions.include_logo_secondary} onChange={e => setFormOptions({...formOptions, include_logo_secondary: e.target.checked})} />
                  <CheckboxOption label="Pixel GTM (header)" checked={formOptions.include_gtm_pixel} onChange={e => setFormOptions({...formOptions, include_gtm_pixel: e.target.checked})} />
                  <CheckboxOption label="Code conversion GTM" checked={formOptions.include_gtm_conversion} onChange={e => setFormOptions({...formOptions, include_gtm_conversion: e.target.checked})} />
                  <CheckboxOption label="Politique confidentialité" checked={formOptions.include_privacy_policy} onChange={e => setFormOptions({...formOptions, include_privacy_policy: e.target.checked})} />
                  <CheckboxOption label="Clé API CRM" checked={formOptions.include_api_key} onChange={e => setFormOptions({...formOptions, include_api_key: e.target.checked})} />
                  <CheckboxOption label="Notes" checked={formOptions.include_notes} onChange={e => setFormOptions({...formOptions, include_notes: e.target.checked})} />
                </div>

                {/* Redirect URL selector */}
                <div className="pt-2 border-t border-slate-200">
                  <label className="block text-xs font-medium text-slate-600 mb-1">URL de redirection :</label>
                  <select 
                    value={formOptions.include_redirect_url} 
                    onChange={e => setFormOptions({...formOptions, include_redirect_url: e.target.value})}
                    className="w-full px-2 py-1 text-sm border border-slate-300 rounded"
                  >
                    <option value="">Aucune</option>
                    <option value="default">URL par défaut</option>
                    {getRedirectUrlsForForm().map((u, i) => (
                      <option key={i} value={u.name}>{u.name}</option>
                    ))}
                  </select>
                </div>

                <div className="pt-2 border-t border-slate-200 text-xs text-slate-500">
                  <strong>Champs toujours inclus :</strong> Téléphone (10 chiffres), Nom, Département
                </div>
              </div>
            )}

            <button onClick={generateFormBrief} disabled={!selectedForm} className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-slate-300 disabled:cursor-not-allowed">
              Générer le brief Formulaire
            </button>
          </div>
        </div>
      </div>

      {generatedBrief && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">Brief généré</h3>
            <button 
              onClick={() => copyToClipboard(generatedBrief.brief)}
              className="flex items-center gap-2 px-3 py-1 bg-blue-600 text-white hover:bg-blue-700 rounded-lg text-sm"
            >
              {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copié !' : 'Copier le brief'}
            </button>
          </div>
          <div className="p-4">
            <pre className="bg-slate-50 text-slate-800 p-4 rounded-lg overflow-x-auto text-sm whitespace-pre-wrap font-mono border border-slate-200">
              {generatedBrief.brief}
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
    { id: 'quickstart', label: 'Démarrage Rapide', icon: Zap },
    { id: 'forms', label: 'Formulaires', icon: FileText },
    { id: 'routing', label: 'Routage Inter-CRM', icon: RefreshCw },
    { id: 'billing', label: 'Facturation', icon: TrendingUp },
    { id: 'api', label: 'API & Intégration', icon: Code },
    { id: 'faq', label: 'FAQ', icon: HelpCircle },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
          <BookOpen className="w-6 h-6 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Guide d'utilisation</h1>
          <p className="text-slate-500">Comprendre le fonctionnement du CRM</p>
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
                Bienvenue dans EnerSolar CRM
              </h2>
              <p className="text-slate-600">
                Ce CRM centralise et redistribue vos leads solaires (PAC, PV, ITE) vers <strong>ZR7 Digital</strong> et <strong>Maison du Lead</strong>.
              </p>
              
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <FileText className="w-8 h-8 mx-auto text-blue-600 mb-2" />
                  <h4 className="font-semibold text-blue-800">1. Formulaires</h4>
                  <p className="text-xs text-blue-600">Chaque formulaire = 1 produit (PAC/PV/ITE)</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <RefreshCw className="w-8 h-8 mx-auto text-green-600 mb-2" />
                  <h4 className="font-semibold text-green-800">2. Routage</h4>
                  <p className="text-xs text-green-600">Redistribution intelligente entre CRMs</p>
                </div>
                <div className="bg-orange-50 rounded-lg p-4 text-center">
                  <TrendingUp className="w-8 h-8 mx-auto text-orange-600 mb-2" />
                  <h4 className="font-semibold text-orange-800">3. Facturation</h4>
                  <p className="text-xs text-orange-600">Suivi des échanges inter-CRM</p>
                </div>
              </div>

              <div className="bg-yellow-50 rounded-lg p-4">
                <h4 className="font-semibold text-yellow-800 mb-2">⚠️ Règle anti-doublon</h4>
                <p className="text-sm text-yellow-700">
                  Un <strong>doublon</strong> = même téléphone + même produit (PAC, PV ou ITE) dans la même journée.<br/>
                  Un client peut s'inscrire PAC et PV le même jour → 2 leads valides.
                </p>
              </div>
            </div>
          )}

          {/* Démarrage Rapide */}
          {activeSection === 'quickstart' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-600" />
                Démarrage Rapide
              </h2>

              <div className="space-y-4">
                <div className="flex gap-4 items-start p-4 bg-slate-50 rounded-lg">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">1</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Créer un Compte</h4>
                    <p className="text-sm text-slate-600">Allez dans <strong>Comptes</strong> → Nouveau compte. Associez-le à MDL ou ZR7.</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start p-4 bg-slate-50 rounded-lg">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">2</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Créer un Formulaire</h4>
                    <p className="text-sm text-slate-600">
                      Allez dans <strong>Formulaires</strong> → Nouveau. Choisissez le produit (PAC/PV/ITE) et entrez la <code className="bg-slate-200 px-1 rounded">crm_api_key</code> du CRM destination.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start p-4 bg-slate-50 rounded-lg">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">3</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Copier la Clé API Interne</h4>
                    <p className="text-sm text-slate-600">
                      Dans la liste des formulaires, copiez la <code className="bg-orange-100 px-1 rounded">internal_api_key</code> (icône copier).
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start p-4 bg-slate-50 rounded-lg">
                  <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">4</div>
                  <div>
                    <h4 className="font-semibold text-slate-800">Intégrer dans votre LP</h4>
                    <p className="text-sm text-slate-600">
                      Utilisez le <strong>Générateur de Scripts</strong> ou envoyez les leads via l'API.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start p-4 bg-green-50 rounded-lg">
                  <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center font-bold shrink-0">✓</div>
                  <div>
                    <h4 className="font-semibold text-green-800">C'est parti !</h4>
                    <p className="text-sm text-green-600">Les leads arrivent → sont stockés → redistribués vers ZR7/MDL automatiquement.</p>
                  </div>
                </div>
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

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">📋 1 Formulaire = 1 Produit</h4>
                <p className="text-sm text-blue-700">
                  Chaque formulaire est lié à un type de produit : <strong>PAC</strong> (pompes à chaleur), <strong>PV</strong> (panneaux solaires) ou <strong>ITE</strong> (isolation).
                </p>
              </div>

              <div className="space-y-3">
                <h4 className="font-semibold text-slate-800">Champs importants :</h4>
                <div className="grid md:grid-cols-2 gap-3">
                  <div className="bg-orange-50 p-3 rounded-lg">
                    <p className="font-medium text-orange-800">crm_api_key</p>
                    <p className="text-xs text-orange-600">Clé API du CRM destination (ZR7/MDL) pour envoyer les leads</p>
                  </div>
                  <div className="bg-green-50 p-3 rounded-lg">
                    <p className="font-medium text-green-800">internal_api_key</p>
                    <p className="text-xs text-green-600">Clé générée automatiquement pour recevoir les leads sur ce formulaire</p>
                  </div>
                </div>
              </div>

              <div className="bg-red-50 rounded-lg p-4">
                <h4 className="font-semibold text-red-800 mb-2">🚫 Exclusion du Routage Inter-CRM</h4>
                <p className="text-sm text-red-700">
                  Cochez cette option pour les formulaires de <strong>redirection</strong>. Un lead exclu ne sera JAMAIS rerouté vers l'autre CRM.<br/>
                  <strong>Pourquoi ?</strong> Si un client s'inscrit PAC sur un CRM et PV via redirection sur l'autre, vous évitez de livrer 2 fois le même client.
                </p>
              </div>
            </div>
          )}

          {/* Routage Inter-CRM */}
          {activeSection === 'routing' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-blue-600" />
                Routage Intelligent Inter-CRM
              </h2>

              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-800 mb-2">🔄 Comment ça marche ?</h4>
                <pre className="text-sm text-slate-600 bg-white p-3 rounded border overflow-x-auto">
{`[Lead arrive sur formulaire MDL, dept 75, produit PAC]
     ↓
[Vérification] MDL a-t-il une commande PAC pour le 75 ?
     → OUI : Envoi vers MDL ✓
     → NON : ZR7 a-t-il une commande PAC pour le 75 ?
           → OUI : Reroutage vers ZR7 ✓
           → NON : Fallback vers MDL (origine) ✓`}
                </pre>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-green-50 rounded-lg p-4">
                  <h4 className="font-semibold text-green-800 mb-2">✓ Routage actif si...</h4>
                  <ul className="text-sm text-green-700 space-y-1">
                    <li>• Des commandes sont configurées (Paramètres)</li>
                    <li>• Le département est renseigné</li>
                    <li>• Le formulaire n'est PAS exclu du routage</li>
                  </ul>
                </div>
                <div className="bg-red-50 rounded-lg p-4">
                  <h4 className="font-semibold text-red-800 mb-2">✗ Routage désactivé si...</h4>
                  <ul className="text-sm text-red-700 space-y-1">
                    <li>• Aucune commande configurée</li>
                    <li>• Formulaire marqué "Exclure du routage"</li>
                    <li>• Département manquant</li>
                  </ul>
                </div>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">⚙️ Configurer les commandes</h4>
                <p className="text-sm text-blue-700">
                  Allez dans <strong>Paramètres</strong> → Cliquez sur <strong>Configurer Commandes</strong> pour un CRM.<br/>
                  Sélectionnez les départements (01-95) pour chaque produit (PAC, PV, ITE) et définissez les prix par lead.
                </p>
              </div>
            </div>
          )}

          {/* Facturation */}
          {activeSection === 'billing' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-600" />
                Facturation Inter-CRM
              </h2>

              <p className="text-slate-600">
                La page <strong>Facturation Inter-CRM</strong> vous montre combien de leads ont été échangés entre MDL et ZR7, et les montants associés.
              </p>

              <div className="space-y-3">
                <h4 className="font-semibold text-slate-800">Termes clés :</h4>
                <div className="space-y-2">
                  <div className="bg-slate-50 p-3 rounded-lg flex items-start gap-3">
                    <span className="text-lg">📤</span>
                    <div>
                      <p className="font-medium text-slate-800">Leads originaires</p>
                      <p className="text-xs text-slate-600">Leads soumis via les formulaires de ce CRM</p>
                    </div>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-lg flex items-start gap-3">
                    <span className="text-lg">📥</span>
                    <div>
                      <p className="font-medium text-slate-800">Leads reçus</p>
                      <p className="text-xs text-slate-600">Leads effectivement envoyés vers ce CRM (après routage)</p>
                    </div>
                  </div>
                  <div className="bg-orange-50 p-3 rounded-lg flex items-start gap-3">
                    <span className="text-lg">↗️</span>
                    <div>
                      <p className="font-medium text-orange-800">Routés vers autres</p>
                      <p className="text-xs text-orange-600">Leads de ce CRM envoyés vers l'autre CRM (car pas de commande)</p>
                    </div>
                  </div>
                  <div className="bg-purple-50 p-3 rounded-lg flex items-start gap-3">
                    <span className="text-lg">↙️</span>
                    <div>
                      <p className="font-medium text-purple-800">Reçus d'autres</p>
                      <p className="text-xs text-purple-600">Leads de l'autre CRM redirigés vers celui-ci (car commande active)</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <h4 className="font-semibold text-green-800 mb-2">💰 Montants</h4>
                <ul className="text-sm text-green-700 space-y-1">
                  <li>• <strong>À facturer</strong> : Ce que ce CRM doit facturer aux autres</li>
                  <li>• <strong>À payer</strong> : Ce que ce CRM doit payer aux autres</li>
                  <li>• <strong>Solde net</strong> : Différence (positif = à recevoir)</li>
                </ul>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">✅ Marquer comme facturé</h4>
                <p className="text-sm text-blue-700">
                  En fin de mois, cliquez sur <strong>"Marquer ce mois comme facturé"</strong> pour enregistrer la facturation dans l'historique.
                </p>
              </div>
            </div>
          )}

          {/* API */}
          {activeSection === 'api' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Code className="w-5 h-5 text-blue-600" />
                API & Intégration
              </h2>

              <div className="bg-orange-50 rounded-lg p-4">
                <h4 className="font-semibold text-orange-800 mb-2">📡 Endpoint pour envoyer un lead</h4>
                <pre className="text-sm bg-white p-3 rounded border overflow-x-auto">
{`POST /api/submit-lead
Content-Type: application/json

{
  "form_code": "VOTRE-CODE-FORM",
  "phone": "0612345678",
  "nom": "Dupont",
  "prenom": "Jean",
  "email": "email@example.com",
  "departement": "75",
  "code_postal": "75001",
  "civilite": "M.",
  "superficie_logement": "120",
  "chauffage_actuel": "Gaz",
  "type_logement": "Maison",
  "statut_occupant": "Propriétaire",
  "facture_electricite": "150"
}`}
                </pre>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-2">🔑 Champs obligatoires</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• <code className="bg-white px-1 rounded">form_code</code> : Code unique du formulaire</li>
                  <li>• <code className="bg-white px-1 rounded">phone</code> : Numéro de téléphone (10 chiffres, commence par 0)</li>
                  <li>• <code className="bg-white px-1 rounded">nom</code> : Nom de famille (min 2 caractères)</li>
                  <li>• <code className="bg-white px-1 rounded">departement</code> : 01-95 uniquement (pas Corse)</li>
                </ul>
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-800 mb-2">📋 Exemple JavaScript</h4>
                <pre className="text-xs bg-white p-3 rounded border overflow-x-auto">
{`fetch('https://votre-domaine.com/api/submit-lead', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    form_code: 'PV-TAB-001',
    phone: document.getElementById('phone').value,
    nom: document.getElementById('nom').value,
    prenom: document.getElementById('prenom').value,
    email: document.getElementById('email').value,
    departement: document.getElementById('dept').value.substring(0, 2),
    code_postal: document.getElementById('dept').value
  })
})
.then(r => r.json())
.then(data => console.log(data));`}
                </pre>
              </div>
            </div>
          )}

          {/* FAQ */}
          {activeSection === 'faq' && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-blue-600" />
                Questions Fréquentes
              </h2>

              <div className="space-y-4">
                <div className="border-b pb-4">
                  <h4 className="font-semibold text-slate-800 mb-2">❓ Comment éviter les doublons cross-CRM ?</h4>
                  <p className="text-sm text-slate-600">
                    Cochez <strong>"Exclure du routage inter-CRM"</strong> sur les formulaires de redirection. 
                    Ainsi, si un client s'inscrit PAC sur MDL et PV via redirection sur ZR7, il ne sera pas rerouté.
                  </p>
                </div>

                <div className="border-b pb-4">
                  <h4 className="font-semibold text-slate-800 mb-2">❓ Un lead peut-il s'inscrire PAC et PV le même jour ?</h4>
                  <p className="text-sm text-slate-600">
                    <strong>Oui !</strong> Le système détecte les doublons par téléphone + produit. 
                    Un client peut donc soumettre PAC et PV le même jour = 2 leads valides.
                  </p>
                </div>

                <div className="border-b pb-4">
                  <h4 className="font-semibold text-slate-800 mb-2">❓ Comment configurer le routage intelligent ?</h4>
                  <p className="text-sm text-slate-600">
                    Allez dans <strong>Paramètres</strong> → Cliquez sur <strong>Configurer Commandes</strong> pour un CRM → 
                    Sélectionnez les départements par produit → Définissez les prix par lead.
                  </p>
                </div>

                <div className="border-b pb-4">
                  <h4 className="font-semibold text-slate-800 mb-2">❓ Les leads échoués sont-ils réessayés ?</h4>
                  <p className="text-sm text-slate-600">
                    <strong>Oui !</strong> Un job automatique s'exécute chaque nuit à 3h pour réessayer les leads échoués des dernières 24h.
                  </p>
                </div>

                <div className="pb-4">
                  <h4 className="font-semibold text-slate-800 mb-2">❓ Comment archiver les anciens leads ?</h4>
                  <p className="text-sm text-slate-600">
                    Dans la page <strong>Facturation Inter-CRM</strong>, cliquez sur <strong>"Archiver (&gt; 3 mois)"</strong>. 
                    Les leads de plus de 3 mois seront déplacés vers l'archive.
                  </p>
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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

// ==================== BILLING PAGE ====================

const BillingPage = () => {
  const { authFetch } = useAuth();
  const [billingData, setBillingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [archiving, setArchiving] = useState(false);
  const [billingHistory, setBillingHistory] = useState([]);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [invoiceData, setInvoiceData] = useState({ from_crm_id: '', to_crm_id: '', amount: 0, lead_count: 0, notes: '' });

  useEffect(() => {
    // Par défaut : mois en cours
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    setDateFrom(firstDay.toISOString().split('T')[0]);
    setDateTo(now.toISOString().split('T')[0]);
  }, []);

  useEffect(() => {
    if (dateFrom && dateTo) {
      loadBillingData();
      loadBillingHistory();
    }
  }, [dateFrom, dateTo]);

  const loadBillingData = async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/billing/dashboard?date_from=${dateFrom}T00:00:00&date_to=${dateTo}T23:59:59`);
      if (res.ok) {
        setBillingData(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const loadBillingHistory = async () => {
    try {
      const year = new Date(dateFrom).getFullYear();
      const res = await authFetch(`${API}/api/billing/history?year=${year}`);
      if (res.ok) {
        const data = await res.json();
        setBillingHistory(data.history || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const markAsInvoiced = async () => {
    if (!invoiceData.from_crm_id || !invoiceData.to_crm_id) return;
    
    const date = new Date(dateFrom);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    
    try {
      const res = await authFetch(`${API}/api/billing/mark-invoiced`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year,
          month,
          from_crm_id: invoiceData.from_crm_id,
          to_crm_id: invoiceData.to_crm_id,
          amount: invoiceData.amount,
          lead_count: invoiceData.lead_count,
          notes: invoiceData.notes
        })
      });
      if (res.ok) {
        setShowInvoiceModal(false);
        setInvoiceData({ from_crm_id: '', to_crm_id: '', amount: 0, lead_count: 0, notes: '' });
        loadBillingHistory();
        alert('Période marquée comme facturée !');
      }
    } catch (e) {
      console.error(e);
      alert('Erreur lors du marquage');
    }
  };

  const deleteBillingRecord = async (id) => {
    if (!window.confirm('Supprimer cet enregistrement de facturation ?')) return;
    try {
      const res = await authFetch(`${API}/api/billing/history/${id}`, { method: 'DELETE' });
      if (res.ok) {
        loadBillingHistory();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const archiveOldLeads = async () => {
    if (!window.confirm('Archiver tous les leads de plus de 3 mois ? Cette action est irréversible.')) return;
    setArchiving(true);
    try {
      const res = await authFetch(`${API}/api/leads/archive?months=3`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        alert(`${data.archived_count} leads archivés avec succès !`);
      }
    } catch (e) {
      console.error(e);
      alert('Erreur lors de l\'archivage');
    }
    setArchiving(false);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount);
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
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Facturation Inter-CRM</h1>
          <p className="text-sm text-slate-500">Suivi des leads routés entre CRMs et montants à facturer</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowInvoiceModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            data-testid="mark-invoiced-btn"
          >
            <CheckCircle className="w-4 h-4" />
            Marquer ce mois comme facturé
          </button>
          <button
            onClick={archiveOldLeads}
            disabled={archiving}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50"
          >
            <Database className="w-4 h-4" />
            {archiving ? 'Archivage...' : 'Archiver (> 3 mois)'}
          </button>
        </div>
      </div>

      {/* Filtres de période */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Date début</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Date fin</label>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <button
            onClick={loadBillingData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <div className="ml-auto text-right">
            <p className="text-xs text-slate-500">Total leads période</p>
            <p className="text-2xl font-bold text-slate-800">{billingData?.total_leads || 0}</p>
          </div>
        </div>
      </div>

      {/* Résumé par CRM */}
      <div className="grid md:grid-cols-2 gap-4">
        {billingData?.crm_stats?.map(crm => (
          <div key={crm.crm_id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className={`p-4 ${crm.crm_slug === 'mdl' ? 'bg-blue-600' : 'bg-green-600'} text-white`}>
              <h3 className="font-bold text-lg">{crm.crm_name}</h3>
              <div className="flex gap-4 mt-2 text-sm opacity-90">
                <span>Originaires : {crm.leads_originated.total}</span>
                <span>Reçus : {crm.leads_received.total}</span>
              </div>
            </div>
            <div className="p-4 space-y-4">
              {/* Stats par produit */}
              <div>
                <p className="text-xs text-slate-500 mb-2">Leads par produit (originaires)</p>
                <div className="flex gap-2">
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs">
                    ☀️ PV: {crm.leads_originated.PV}
                  </span>
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs">
                    🔥 PAC: {crm.leads_originated.PAC}
                  </span>
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                    🏠 ITE: {crm.leads_originated.ITE}
                  </span>
                </div>
              </div>

              {/* Routage */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-orange-50 p-3 rounded-lg">
                  <p className="text-xs text-orange-600 mb-1">Routés vers autres CRMs</p>
                  <p className="text-xl font-bold text-orange-700">{crm.leads_rerouted_out.total}</p>
                </div>
                <div className="bg-purple-50 p-3 rounded-lg">
                  <p className="text-xs text-purple-600 mb-1">Reçus d'autres CRMs</p>
                  <p className="text-xl font-bold text-purple-700">{crm.leads_rerouted_in.total}</p>
                </div>
              </div>

              {/* Prix configurés */}
              <div>
                <p className="text-xs text-slate-500 mb-1">Prix par lead configurés</p>
                <div className="flex gap-2 text-xs">
                  {['PAC', 'PV', 'ITE'].map(pt => (
                    <span key={pt} className="px-2 py-1 bg-slate-100 rounded">
                      {pt}: {crm.lead_prices?.[pt] ? formatCurrency(crm.lead_prices[pt]) : 'Non défini'}
                    </span>
                  ))}
                </div>
              </div>

              {/* Facturation */}
              <div className="border-t pt-3 grid grid-cols-3 gap-2 text-center">
                <div>
                  <p className="text-xs text-slate-500">À facturer</p>
                  <p className="font-bold text-green-600">{formatCurrency(crm.amount_to_invoice)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">À payer</p>
                  <p className="font-bold text-red-600">{formatCurrency(crm.amount_to_pay)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Solde net</p>
                  <p className={`font-bold ${crm.net_balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(crm.net_balance)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Transferts détaillés */}
      {billingData?.transfers?.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200">
          <div className="p-4 border-b border-slate-200">
            <h3 className="font-semibold text-slate-800">Détail des transferts inter-CRM</h3>
            <p className="text-xs text-slate-500">Leads routés d'un CRM vers un autre (quand routage intelligent activé)</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">De</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Vers</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">☀️ PV</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">🔥 PAC</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">🏠 ITE</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Total</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-500">Montant</th>
                </tr>
              </thead>
              <tbody>
                {billingData.transfers.map((transfer, idx) => (
                  <tr key={idx} className="border-b border-slate-100">
                    <td className="py-3 px-4 text-sm font-medium text-slate-700">{transfer.from_crm}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">→ {transfer.to_crm}</td>
                    <td className="py-3 px-4 text-sm text-center text-slate-600">{transfer.by_product.PV}</td>
                    <td className="py-3 px-4 text-sm text-center text-slate-600">{transfer.by_product.PAC}</td>
                    <td className="py-3 px-4 text-sm text-center text-slate-600">{transfer.by_product.ITE}</td>
                    <td className="py-3 px-4 text-sm text-center font-medium text-slate-800">{transfer.count}</td>
                    <td className="py-3 px-4 text-sm text-right font-bold text-green-600">{formatCurrency(transfer.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Historique des facturations */}
      {billingHistory.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200">
          <div className="p-4 border-b border-slate-200">
            <h3 className="font-semibold text-slate-800">Historique des facturations</h3>
            <p className="text-xs text-slate-500">Périodes marquées comme facturées</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Période</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">De</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Vers</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Leads</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-500">Montant</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Notes</th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {billingHistory.map((record) => (
                  <tr key={record.id} className="border-b border-slate-100">
                    <td className="py-3 px-4 text-sm font-medium text-slate-700">
                      {String(record.month).padStart(2, '0')}/{record.year}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{record.from_crm_name}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">→ {record.to_crm_name}</td>
                    <td className="py-3 px-4 text-sm text-center text-slate-600">{record.lead_count}</td>
                    <td className="py-3 px-4 text-sm text-right font-bold text-green-600">{formatCurrency(record.amount)}</td>
                    <td className="py-3 px-4 text-sm text-slate-500 max-w-[200px] truncate">{record.notes || '-'}</td>
                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => deleteBillingRecord(record.id)}
                        className="p-1 text-red-600 hover:bg-red-100 rounded"
                        title="Supprimer"
                        data-testid={`delete-billing-${record.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Aide */}
      <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
        <h4 className="font-medium text-blue-800 mb-2">Comment ça fonctionne ?</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• <strong>Leads originaires</strong> : Leads soumis via les formulaires de ce CRM</li>
          <li>• <strong>Leads reçus</strong> : Leads effectivement envoyés vers ce CRM (après routage)</li>
          <li>• <strong>Routés vers autres</strong> : Leads de ce CRM envoyés vers un autre CRM (car pas de commande)</li>
          <li>• <strong>Reçus d'autres</strong> : Leads d'un autre CRM redirigés vers celui-ci (car commande active)</li>
          <li>• <strong>À facturer</strong> : Montant que ce CRM doit facturer aux autres pour les leads reçus en reroutage</li>
          <li>• <strong>À payer</strong> : Montant que ce CRM doit payer aux autres pour les leads envoyés en reroutage</li>
          <li>• Configurez les prix dans <strong>Paramètres → Configurer Commandes</strong></li>
        </ul>
      </div>

      {/* Modal Marquer comme facturé */}
      <Modal isOpen={showInvoiceModal} onClose={() => setShowInvoiceModal(false)} title="Marquer ce mois comme facturé">
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Enregistrez une facturation inter-CRM pour la période sélectionnée ({dateFrom ? new Date(dateFrom).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' }) : 'Non définie'}).
          </p>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">CRM payeur *</label>
              <select
                value={invoiceData.from_crm_id}
                onChange={e => setInvoiceData({ ...invoiceData, from_crm_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                data-testid="invoice-from-crm"
              >
                <option value="">Sélectionner</option>
                {billingData?.crm_stats?.map(crm => (
                  <option key={crm.crm_id} value={crm.crm_id}>{crm.crm_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">CRM receveur *</label>
              <select
                value={invoiceData.to_crm_id}
                onChange={e => setInvoiceData({ ...invoiceData, to_crm_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                data-testid="invoice-to-crm"
              >
                <option value="">Sélectionner</option>
                {billingData?.crm_stats?.map(crm => (
                  <option key={crm.crm_id} value={crm.crm_id}>{crm.crm_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nombre de leads</label>
              <input
                type="number"
                value={invoiceData.lead_count}
                onChange={e => setInvoiceData({ ...invoiceData, lead_count: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                min="0"
                data-testid="invoice-lead-count"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Montant (€)</label>
              <input
                type="number"
                value={invoiceData.amount}
                onChange={e => setInvoiceData({ ...invoiceData, amount: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                min="0"
                step="0.01"
                data-testid="invoice-amount"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
            <textarea
              value={invoiceData.notes}
              onChange={e => setInvoiceData({ ...invoiceData, notes: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              rows={2}
              placeholder="Notes optionnelles..."
              data-testid="invoice-notes"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setShowInvoiceModal(false)}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Annuler
            </button>
            <button
              onClick={markAsInvoiced}
              disabled={!invoiceData.from_crm_id || !invoiceData.to_crm_id}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              data-testid="confirm-invoice-btn"
            >
              Marquer comme facturé
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

const SettingsPage = () => {
  const { authFetch } = useAuth();
  const [crms, setCrms] = useState([]);
  const [editingCRM, setEditingCRM] = useState(null);
  const [commandesData, setCommandesData] = useState({ PAC: [], PV: [], ITE: [] });
  const [leadPrices, setLeadPrices] = useState({ PAC: 0, PV: 0, ITE: 0 });
  const [routingLimits, setRoutingLimits] = useState({ PAC: 0, PV: 0, ITE: 0 });

  // Liste des départements 01-95
  const DEPARTMENTS = Array.from({ length: 95 }, (_, i) => String(i + 1).padStart(2, '0'));

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

  const openCommandesModal = (crm) => {
    setEditingCRM(crm);
    setCommandesData(crm.commandes || { PAC: [], PV: [], ITE: [] });
    setLeadPrices(crm.lead_prices || { PAC: 0, PV: 0, ITE: 0 });
    setRoutingLimits(crm.routing_limits || { PAC: 0, PV: 0, ITE: 0 });
  };

  const toggleDept = (product, dept) => {
    const current = commandesData[product] || [];
    if (current.includes(dept)) {
      setCommandesData({ ...commandesData, [product]: current.filter(d => d !== dept) });
    } else {
      setCommandesData({ ...commandesData, [product]: [...current, dept] });
    }
  };

  const selectAllDepts = (product) => {
    setCommandesData({ ...commandesData, [product]: [...DEPARTMENTS] });
  };

  const clearAllDepts = (product) => {
    setCommandesData({ ...commandesData, [product]: [] });
  };

  const saveCommandes = async () => {
    if (!editingCRM) return;
    try {
      const res = await authFetch(`${API}/api/crms/${editingCRM.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ commandes: commandesData, lead_prices: leadPrices, routing_limits: routingLimits })
      });
      if (res.ok) {
        setEditingCRM(null);
        loadCRMs();
      }
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
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-slate-800">{crm.name}</h4>
                    <p className="text-sm text-slate-500">{crm.api_url}</p>
                  </div>
                  <button 
                    onClick={() => openCommandesModal(crm)}
                    className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
                  >
                    Configurer Commandes
                  </button>
                </div>
                {crm.commandes && Object.keys(crm.commandes).some(k => crm.commandes[k]?.length > 0) && (
                  <div className="mt-3 pt-3 border-t border-slate-200">
                    <p className="text-xs text-slate-500 mb-2">Commandes actives :</p>
                    <div className="flex gap-4 text-xs">
                      {['PAC', 'PV', 'ITE'].map(product => (
                        <span key={product} className={`px-2 py-1 rounded ${
                          (crm.commandes[product]?.length || 0) > 0 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-slate-100 text-slate-400'
                        }`}>
                          {product}: {crm.commandes[product]?.length || 0} dép.
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Commandes */}
      <Modal isOpen={!!editingCRM} onClose={() => setEditingCRM(null)} title={`Commandes - ${editingCRM?.name}`}>
        <div className="space-y-6">
          <p className="text-sm text-slate-600">
            Sélectionnez les départements où ce CRM a des commandes pour chaque type de produit.
            <strong className="block mt-1 text-orange-600">
              ⚠️ Si aucun département n'est sélectionné, le routage intelligent est DÉSACTIVÉ pour ce produit.
            </strong>
          </p>

          {['PAC', 'PV', 'ITE'].map(product => (
            <div key={product} className="border border-slate-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-slate-800">
                  {product === 'PAC' ? '🔥 Pompe à Chaleur (PAC)' : 
                   product === 'PV' ? '☀️ Panneau Solaire (PV)' : 
                   '🏠 Isolation Extérieure (ITE)'}
                </h4>
                <div className="flex gap-2">
                  <button 
                    type="button" 
                    onClick={() => selectAllDepts(product)}
                    className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Tout
                  </button>
                  <button 
                    type="button" 
                    onClick={() => clearAllDepts(product)}
                    className="text-xs px-2 py-1 bg-slate-500 text-white rounded hover:bg-slate-600"
                  >
                    Aucun
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-500 mb-2">
                {(commandesData[product] || []).length} département(s) sélectionné(s)
              </p>
              <div className="grid grid-cols-10 gap-1 max-h-32 overflow-y-auto bg-slate-50 p-2 rounded">
                {DEPARTMENTS.map(dept => (
                  <label 
                    key={dept} 
                    className={`flex items-center justify-center p-1 rounded cursor-pointer text-xs ${
                      (commandesData[product] || []).includes(dept) 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-white hover:bg-slate-100'
                    }`}
                  >
                    <input 
                      type="checkbox" 
                      checked={(commandesData[product] || []).includes(dept)}
                      onChange={() => toggleDept(product, dept)}
                      className="sr-only"
                    />
                    {dept}
                  </label>
                ))}
              </div>
            </div>
          ))}

          {/* Prix par lead */}
          <div className="border-t pt-4">
            <h4 className="font-medium text-slate-800 mb-3">💰 Prix par lead (pour facturation inter-CRM)</h4>
            <p className="text-xs text-slate-500 mb-3">
              Ces prix seront utilisés pour calculer les montants à facturer quand un lead est routé vers ce CRM depuis un autre.
            </p>
            <div className="grid grid-cols-3 gap-4">
              {['PAC', 'PV', 'ITE'].map(product => (
                <div key={product}>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {product === 'PAC' ? '🔥 PAC' : product === 'PV' ? '☀️ PV' : '🏠 ITE'}
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={leadPrices[product] || 0}
                      onChange={e => setLeadPrices({ ...leadPrices, [product]: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg pr-8"
                      placeholder="0.00"
                    />
                    <span className="absolute right-3 top-2.5 text-slate-400 text-sm">€</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Limites de leads inter-CRM */}
          <div className="border-t pt-4">
            <h4 className="font-medium text-slate-800 mb-3">📊 Limites de leads inter-CRM (par mois)</h4>
            <p className="text-xs text-slate-500 mb-3">
              Nombre maximum de leads que ce CRM peut <strong>recevoir</strong> des autres CRMs par mois. 0 = illimité.
            </p>
            <div className="grid grid-cols-3 gap-4">
              {['PAC', 'PV', 'ITE'].map(product => (
                <div key={product}>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {product === 'PAC' ? '🔥 PAC' : product === 'PV' ? '☀️ PV' : '🏠 ITE'}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={routingLimits[product] || 0}
                    onChange={e => setRoutingLimits({ ...routingLimits, [product]: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    placeholder="0 = illimité"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <button 
              type="button" 
              onClick={() => setEditingCRM(null)}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Annuler
            </button>
            <button 
              onClick={saveCommandes}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Enregistrer
            </button>
          </div>
        </div>
      </Modal>
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

// Route protégée pour les admins uniquement
const AdminRoute = ({ children }) => {
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
  
  // Rediriger vers dashboard si pas admin
  if (user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
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
          <Route path="/billing" element={<AdminRoute><BillingPage /></AdminRoute>} />
          <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="/leads" element={<AdminRoute><LeadsPage /></AdminRoute>} />
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
