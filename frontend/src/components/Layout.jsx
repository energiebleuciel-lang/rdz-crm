/**
 * Layout principal avec sidebar et sélecteur CRM
 */

import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { 
  Home, Layers, FileText, Users, Settings, LogOut, 
  Building, Globe, Zap, ChevronDown, Database, Package
} from 'lucide-react';
import { useState } from 'react';

const menuItems = [
  { path: '/dashboard', icon: Home, label: 'Tableau de bord' },
  { path: '/accounts', icon: Building, label: 'Comptes' },
  { path: '/lps', icon: Globe, label: 'Landing Pages' },
  { path: '/forms', icon: FileText, label: 'Formulaires' },
  { path: '/leads', icon: Users, label: 'Leads' },
  { path: '/commandes', icon: Package, label: 'Commandes' },
  { path: '/settings', icon: Settings, label: 'Paramètres' },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const { crms, selectedCRM, selectCRM, currentCRM } = useCRM();
  const location = useLocation();
  const navigate = useNavigate();
  const [showCRMDropdown, setShowCRMDropdown] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Couleur du CRM
  const getCRMColor = (slug) => {
    switch(slug?.toLowerCase()) {
      case 'mdl': return 'from-blue-500 to-blue-600';
      case 'zr7': return 'from-green-500 to-green-600';
      default: return 'from-slate-500 to-slate-600';
    }
  };

  return (
    <div className="flex h-screen bg-slate-100">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg">EnerSolar</h1>
              <p className="text-xs text-slate-400">CRM v2.0</p>
            </div>
          </div>
        </div>

        {/* Sélecteur CRM */}
        <div className="p-4 border-b border-slate-700">
          <label className="text-xs text-slate-400 uppercase tracking-wider mb-2 block">
            CRM Actif
          </label>
          <div className="relative">
            <button
              onClick={() => setShowCRMDropdown(!showCRMDropdown)}
              className={`w-full flex items-center justify-between gap-2 px-4 py-3 rounded-lg bg-gradient-to-r ${getCRMColor(currentCRM?.slug)} text-white font-medium shadow-lg transition-all hover:shadow-xl`}
            >
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4" />
                <span>{currentCRM?.name || 'Sélectionner'}</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${showCRMDropdown ? 'rotate-180' : ''}`} />
            </button>
            
            {showCRMDropdown && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-slate-800 rounded-lg shadow-xl border border-slate-700 overflow-hidden z-50">
                {crms.map(crm => (
                  <button
                    key={crm.id}
                    onClick={() => {
                      selectCRM(crm.id);
                      setShowCRMDropdown(false);
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-700 transition-colors ${
                      selectedCRM === crm.id ? 'bg-slate-700 text-amber-400' : 'text-slate-200'
                    }`}
                  >
                    <div className={`w-3 h-3 rounded-full bg-gradient-to-r ${getCRMColor(crm.slug)}`} />
                    <div>
                      <p className="font-medium">{crm.name}</p>
                      <p className="text-xs text-slate-400">{crm.slug?.toUpperCase()}</p>
                    </div>
                    {selectedCRM === crm.id && (
                      <span className="ml-auto text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded">
                        Actif
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Menu */}
        <nav className="flex-1 p-4 space-y-1">
          {menuItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                location.pathname === item.path
                  ? 'bg-amber-500/20 text-amber-400'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* User */}
        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">{user?.nom || user?.email}</p>
              <p className="text-xs text-slate-400">{user?.role}</p>
            </div>
            <button 
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
              title="Déconnexion"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
