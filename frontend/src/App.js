import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  BarChart3, Users, CheckCircle, XCircle, RefreshCw, Download, Eye, Search, Copy, 
  Settings, Plus, LogOut, Home, Layers, FileText, TrendingUp, MessageSquare, 
  Activity, ChevronRight, ChevronDown, Edit, Trash2, ExternalLink, Code,
  Building, Globe, Image, Shield, Bell, Filter, Calendar, Award, AlertTriangle
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

// ==================== AUTH CONTEXT ====================
const AuthContext = createContext(null);

const useAuth = () => useContext(AuthContext);

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
  const { user, logout } = useAuth();
  const location = useLocation();
  const [expanded, setExpanded] = useState({ crm: true });

  const isActive = (path) => location.pathname.startsWith(path);

  const menuItems = [
    { path: '/dashboard', icon: Home, label: 'Tableau de bord' },
    { path: '/analytics', icon: TrendingUp, label: 'Analytics' },
    { path: '/leads', icon: Users, label: 'Leads' },
    { path: '/lps', icon: Layers, label: 'Landing Pages' },
    { path: '/forms', icon: FileText, label: 'Formulaires' },
    { path: '/accounts', icon: Building, label: 'Sous-comptes' },
    { path: '/generator', icon: Code, label: 'Générateur Scripts' },
  ];

  const adminItems = [
    { path: '/users', icon: Shield, label: 'Utilisateurs' },
    { path: '/activity', icon: Activity, label: 'Journal activité' },
    { path: '/settings', icon: Settings, label: 'Paramètres' },
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

      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              isActive(item.path) ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        ))}

        {user?.role === 'admin' && (
          <>
            <div className="pt-4 pb-2">
              <p className="text-xs text-slate-500 uppercase tracking-wider px-3">Administration</p>
            </div>
            {adminItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive(item.path) ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
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
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('today');

  useEffect(() => {
    loadData();
  }, [period]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, leadsRes] = await Promise.all([
        authFetch(`${API}/api/analytics/stats?period=${period}`),
        authFetch(`${API}/api/leads?limit=10`)
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
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', form_code: '' });

  useEffect(() => {
    loadLeads();
  }, [filters]);

  const loadLeads = async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.form_code) params.set('form_code', filters.form_code);
    
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
  };

  const retryLead = async (leadId) => {
    try {
      await authFetch(`${API}/api/leads/retry/${leadId}`, { method: 'POST' });
      loadLeads();
    } catch (e) {
      console.error(e);
    }
  };

  const exportCSV = () => {
    const headers = ['Date', 'Nom', 'Téléphone', 'Email', 'Département', 'Formulaire', 'Statut'];
    const rows = leads.map(l => [
      new Date(l.created_at).toLocaleString('fr-FR'),
      l.nom, l.phone, l.email, l.departement, l.form_code || l.form_id, l.api_status
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
        <button onClick={exportCSV} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Download className="w-4 h-4" />
          Export CSV
        </button>
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
          <Table
            columns={[
              { key: 'created_at', label: 'Date', render: v => new Date(v).toLocaleString('fr-FR') },
              { key: 'nom', label: 'Nom' },
              { key: 'phone', label: 'Téléphone' },
              { key: 'email', label: 'Email' },
              { key: 'departement', label: 'Dept' },
              { key: 'form_code', label: 'Form', render: (v, row) => v || row.form_id },
              { key: 'lp_code', label: 'LP' },
              { key: 'api_status', label: 'Statut', render: v => <StatusBadge status={v} /> },
              { 
                key: 'actions', 
                label: '', 
                render: (_, row) => row.api_status === 'failed' && (
                  <button onClick={() => retryLead(row.id)} className="text-blue-600 hover:text-blue-800">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                )
              }
            ]}
            data={leads}
          />
        )}
      </div>
    </div>
  );
};

const SubAccountsPage = () => {
  const { authFetch } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [crms, setCrms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [formData, setFormData] = useState({
    crm_id: '', name: '', domain: '', logo_url: '', logo_secondary_url: '',
    privacy_policy_url: '', terms_url: '', layout: 'center', primary_color: '#3B82F6',
    tracking_pixel_header: '', tracking_cta_code: '', tracking_conversion_type: 'redirect',
    tracking_conversion_code: '', tracking_redirect_url: '', notes: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [accountsRes, crmsRes] = await Promise.all([
        authFetch(`${API}/api/sub-accounts`),
        authFetch(`${API}/api/crms`)
      ]);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).sub_accounts || []);
      if (crmsRes.ok) setCrms((await crmsRes.json()).crms || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const url = editingAccount ? `${API}/api/sub-accounts/${editingAccount.id}` : `${API}/api/sub-accounts`;
    const method = editingAccount ? 'PUT' : 'POST';
    
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(formData) });
      if (res.ok) {
        setShowModal(false);
        setEditingAccount(null);
        setFormData({ crm_id: '', name: '', domain: '', logo_url: '', layout: 'center', primary_color: '#3B82F6', tracking_conversion_type: 'redirect', notes: '' });
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const editAccount = (account) => {
    setEditingAccount(account);
    setFormData(account);
    setShowModal(true);
  };

  const deleteAccount = async (id) => {
    if (!window.confirm('Supprimer ce sous-compte ?')) return;
    try {
      await authFetch(`${API}/api/sub-accounts/${id}`, { method: 'DELETE' });
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Sous-comptes</h1>
        <button onClick={() => { setEditingAccount(null); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Nouveau sous-compte
        </button>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map(account => (
          <div key={account.id} className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-slate-800">{account.name}</h3>
                <p className="text-sm text-slate-500">{account.domain || 'Pas de domaine'}</p>
              </div>
              <div className="flex gap-1">
                <button onClick={() => editAccount(account)} className="p-1 hover:bg-slate-100 rounded">
                  <Edit className="w-4 h-4 text-slate-600" />
                </button>
                <button onClick={() => deleteAccount(account.id)} className="p-1 hover:bg-slate-100 rounded">
                  <Trash2 className="w-4 h-4 text-red-600" />
                </button>
              </div>
            </div>
            <div className="text-xs text-slate-500 space-y-1">
              <p>CRM: {crms.find(c => c.id === account.crm_id)?.name || 'Non défini'}</p>
              <p>Tracking: {account.tracking_conversion_type}</p>
              <p>Layout: {account.layout}</p>
            </div>
          </div>
        ))}
      </div>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingAccount ? 'Modifier le sous-compte' : 'Nouveau sous-compte'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">CRM</label>
              <select value={formData.crm_id} onChange={e => setFormData({ ...formData, crm_id: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required>
                <option value="">Sélectionner</option>
                {crms.map(crm => <option key={crm.id} value={crm.id}>{crm.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nom du compte</label>
              <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Domaine</label>
              <input type="text" value={formData.domain} onChange={e => setFormData({ ...formData, domain: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="exemple.fr" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Layout</label>
              <select value={formData.layout} onChange={e => setFormData({ ...formData, layout: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                <option value="left">Gauche</option>
                <option value="center">Centre</option>
                <option value="right">Droite</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">URL Logo principal</label>
            <input type="url" value={formData.logo_url} onChange={e => setFormData({ ...formData, logo_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Politique de confidentialité (URL)</label>
            <input type="url" value={formData.privacy_policy_url} onChange={e => setFormData({ ...formData, privacy_policy_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Type de tracking conversion</label>
            <select value={formData.tracking_conversion_type} onChange={e => setFormData({ ...formData, tracking_conversion_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
              <option value="code">Code (après téléphone)</option>
              <option value="redirect">Page de redirection</option>
              <option value="both">Les deux</option>
            </select>
          </div>

          {(formData.tracking_conversion_type === 'code' || formData.tracking_conversion_type === 'both') && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Code tracking conversion</label>
              <textarea value={formData.tracking_conversion_code} onChange={e => setFormData({ ...formData, tracking_conversion_code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={3} placeholder="<script>...</script>" />
            </div>
          )}

          {(formData.tracking_conversion_type === 'redirect' || formData.tracking_conversion_type === 'both') && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">URL de redirection</label>
              <input type="url" value={formData.tracking_redirect_url} onChange={e => setFormData({ ...formData, tracking_redirect_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="https://exemple.fr/merci/" />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Pixel Header (à mettre dans &lt;head&gt;)</label>
            <textarea value={formData.tracking_pixel_header} onChange={e => setFormData({ ...formData, tracking_pixel_header: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={3} placeholder="Code Facebook Pixel, Google Ads, etc." />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
            <textarea value={formData.notes} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg">Annuler</button>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">{editingAccount ? 'Modifier' : 'Créer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

const LPsPage = () => {
  const { authFetch } = useAuth();
  const [lps, setLps] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingLP, setEditingLP] = useState(null);
  const [formData, setFormData] = useState({
    sub_account_id: '', code: '', name: '', url: '', source_type: 'native',
    source_name: '', cta_selector: '.cta-btn', screenshot_url: '', diffusion_url: '', notes: '', status: 'active'
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [lpsRes, accountsRes] = await Promise.all([
        authFetch(`${API}/api/lps`),
        authFetch(`${API}/api/sub-accounts`)
      ]);
      if (lpsRes.ok) setLps((await lpsRes.json()).lps || []);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).sub_accounts || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const url = editingLP ? `${API}/api/lps/${editingLP.id}` : `${API}/api/lps`;
    const method = editingLP ? 'PUT' : 'POST';
    
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(formData) });
      if (res.ok) {
        setShowModal(false);
        setEditingLP(null);
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Landing Pages</h1>
        <button onClick={() => { setEditingLP(null); setFormData({ sub_account_id: '', code: '', name: '', url: '', source_type: 'native', source_name: '', cta_selector: '.cta-btn', status: 'active' }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
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
            { key: 'stats', label: 'Clics CTA', render: v => v?.cta_clicks || 0 },
            { key: 'stats', label: 'Leads', render: v => v?.leads || 0 },
            { key: 'status', label: 'Statut', render: v => <StatusBadge status={v} /> },
            { 
              key: 'actions', 
              label: '', 
              render: (_, row) => (
                <div className="flex gap-1">
                  <button onClick={() => { setEditingLP(row); setFormData(row); setShowModal(true); }} className="p-1 hover:bg-slate-100 rounded">
                    <Edit className="w-4 h-4 text-slate-600" />
                  </button>
                </div>
              )
            }
          ]}
          data={lps}
        />
      </div>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingLP ? 'Modifier la LP' : 'Nouvelle Landing Page'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Sous-compte</label>
              <select value={formData.sub_account_id} onChange={e => setFormData({ ...formData, sub_account_id: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required>
                <option value="">Sélectionner</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Code LP</label>
              <input type="text" value={formData.code} onChange={e => setFormData({ ...formData, code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="LP-TAB-V1" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nom</label>
              <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">URL de la LP</label>
              <input type="url" value={formData.url} onChange={e => setFormData({ ...formData, url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
            </div>
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
              <input type="text" value={formData.source_name} onChange={e => setFormData({ ...formData, source_name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Taboola, Outbrain, etc." />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Sélecteur CSS des CTA</label>
            <input type="text" value={formData.cta_selector} onChange={e => setFormData({ ...formData, cta_selector: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder=".cta-btn" />
            <p className="text-xs text-slate-500 mt-1">Sélecteur CSS pour identifier les boutons CTA sur la LP</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes</label>
            <textarea value={formData.notes} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={2} />
          </div>

          <div className="flex justify-end gap-2 pt-4">
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
  const [forms, setForms] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [lps, setLps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingForm, setEditingForm] = useState(null);
  const [formData, setFormData] = useState({
    sub_account_id: '', lp_ids: [], code: '', name: '', product_type: 'panneaux',
    source_type: 'native', source_name: '', api_key: '', tracking_type: 'redirect',
    tracking_code: '', redirect_url: '', notes: '', status: 'active'
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [formsRes, accountsRes, lpsRes] = await Promise.all([
        authFetch(`${API}/api/forms`),
        authFetch(`${API}/api/sub-accounts`),
        authFetch(`${API}/api/lps`)
      ]);
      if (formsRes.ok) setForms((await formsRes.json()).forms || []);
      if (accountsRes.ok) setAccounts((await accountsRes.json()).sub_accounts || []);
      if (lpsRes.ok) setLps((await lpsRes.json()).lps || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const url = editingForm ? `${API}/api/forms/${editingForm.id}` : `${API}/api/forms`;
    const method = editingForm ? 'PUT' : 'POST';
    
    try {
      const res = await authFetch(url, { method, body: JSON.stringify(formData) });
      if (res.ok) {
        setShowModal(false);
        setEditingForm(null);
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Formulaires</h1>
        <button onClick={() => { setEditingForm(null); setFormData({ sub_account_id: '', lp_ids: [], code: '', name: '', product_type: 'panneaux', source_type: 'native', source_name: '', api_key: '', tracking_type: 'redirect', status: 'active' }); setShowModal(true); }} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
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
            { key: 'stats', label: 'Démarrés', render: v => v?.started || 0 },
            { key: 'stats', label: 'Complétés', render: v => v?.completed || 0 },
            { key: 'stats', label: 'Taux', render: v => `${v?.conversion_rate || 0}%` },
            { key: 'status', label: 'Statut', render: v => <StatusBadge status={v} /> },
            { 
              key: 'actions', 
              label: '', 
              render: (_, row) => (
                <button onClick={() => { setEditingForm(row); setFormData(row); setShowModal(true); }} className="p-1 hover:bg-slate-100 rounded">
                  <Edit className="w-4 h-4 text-slate-600" />
                </button>
              )
            }
          ]}
          data={forms}
        />
      </div>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title={editingForm ? 'Modifier le formulaire' : 'Nouveau formulaire'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Sous-compte</label>
              <select value={formData.sub_account_id} onChange={e => setFormData({ ...formData, sub_account_id: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required>
                <option value="">Sélectionner</option>
                {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Code formulaire</label>
              <input type="text" value={formData.code} onChange={e => setFormData({ ...formData, code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="PV-TAB-001" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nom</label>
              <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Type de produit</label>
              <select value={formData.product_type} onChange={e => setFormData({ ...formData, product_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                <option value="panneaux">Panneaux solaires</option>
                <option value="pompes">Pompes à chaleur</option>
                <option value="isolation">Isolation</option>
                <option value="autre">Autre</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Type de source</label>
              <select value={formData.source_type} onChange={e => setFormData({ ...formData, source_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
                <option value="native">Native</option>
                <option value="google">Google Ads</option>
                <option value="facebook">Facebook Ads</option>
                <option value="tiktok">TikTok Ads</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Source</label>
              <input type="text" value={formData.source_name} onChange={e => setFormData({ ...formData, source_name: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Taboola, Outbrain, etc." />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Clé API du CRM</label>
            <input type="text" value={formData.api_key} onChange={e => setFormData({ ...formData, api_key: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="xxxx-xxxx-xxxx-xxxx" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Type de tracking conversion</label>
            <select value={formData.tracking_type} onChange={e => setFormData({ ...formData, tracking_type: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg">
              <option value="code">Code (après téléphone)</option>
              <option value="redirect">Page de redirection</option>
              <option value="both">Les deux</option>
            </select>
          </div>

          {(formData.tracking_type === 'code' || formData.tracking_type === 'both') && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Code tracking</label>
              <textarea value={formData.tracking_code} onChange={e => setFormData({ ...formData, tracking_code: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" rows={3} />
            </div>
          )}

          {(formData.tracking_type === 'redirect' || formData.tracking_type === 'both') && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">URL de redirection</label>
              <input type="url" value={formData.redirect_url} onChange={e => setFormData({ ...formData, redirect_url: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
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
  const [stats, setStats] = useState(null);
  const [winners, setWinners] = useState(null);
  const [period, setPeriod] = useState('week');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [period]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, winnersRes] = await Promise.all([
        authFetch(`${API}/api/analytics/stats?period=${period}`),
        authFetch(`${API}/api/analytics/winners?period=${period}`)
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
  const [lps, setLps] = useState([]);
  const [forms, setForms] = useState([]);
  const [selectedLP, setSelectedLP] = useState('');
  const [selectedForm, setSelectedForm] = useState('');
  const [generatedScript, setGeneratedScript] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [lpsRes, formsRes] = await Promise.all([
        authFetch(`${API}/api/lps`),
        authFetch(`${API}/api/forms`)
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
      if (res.ok) setGeneratedScript(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const generateFormScript = async () => {
    if (!selectedForm) return;
    try {
      const res = await authFetch(`${API}/api/generate-script/form/${selectedForm}`);
      if (res.ok) setGeneratedScript(await res.json());
    } catch (e) {
      console.error(e);
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const res = await authFetch(`${API}/api/users`);
      if (res.ok) setUsers((await res.json()).users || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const updateRole = async (userId, role) => {
    try {
      await authFetch(`${API}/api/users/${userId}/role?role=${role}`, { method: 'PUT' });
      loadUsers();
    } catch (e) {
      console.error(e);
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Supprimer cet utilisateur ?')) return;
    try {
      await authFetch(`${API}/api/users/${userId}`, { method: 'DELETE' });
      loadUsers();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Utilisateurs</h1>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <Table
          columns={[
            { key: 'nom', label: 'Nom' },
            { key: 'email', label: 'Email' },
            { key: 'role', label: 'Rôle', render: (v, row) => (
              <select 
                value={v} 
                onChange={e => updateRole(row.id, e.target.value)}
                disabled={row.id === currentUser?.id}
                className="px-2 py-1 border border-slate-300 rounded text-sm"
              >
                <option value="admin">Admin</option>
                <option value="editor">Éditeur</option>
                <option value="viewer">Lecteur</option>
              </select>
            )},
            { key: 'created_at', label: 'Créé le', render: v => new Date(v).toLocaleDateString('fr-FR') },
            { key: 'actions', label: '', render: (_, row) => row.id !== currentUser?.id && (
              <button onClick={() => deleteUser(row.id)} className="p-1 hover:bg-slate-100 rounded text-red-600">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          ]}
          data={users}
        />
      </div>
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
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="/leads" element={<ProtectedRoute><LeadsPage /></ProtectedRoute>} />
          <Route path="/lps" element={<ProtectedRoute><LPsPage /></ProtectedRoute>} />
          <Route path="/forms" element={<ProtectedRoute><FormsPage /></ProtectedRoute>} />
          <Route path="/accounts" element={<ProtectedRoute><SubAccountsPage /></ProtectedRoute>} />
          <Route path="/generator" element={<ProtectedRoute><ScriptGeneratorPage /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
          <Route path="/activity" element={<ProtectedRoute><ActivityPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
