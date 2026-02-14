import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  LayoutDashboard, Package, Users, ShoppingCart, Settings, LogOut,
  Truck, ChevronLeft, ChevronRight, FileText, Clock, MapPin, Receipt,
  Shield, UserCog, FileCheck
} from 'lucide-react';
import { useState, useEffect } from 'react';

const NAV_ITEMS = [
  { path: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard', permission: 'dashboard.view' },
  { path: '/admin/deliveries', icon: Truck, label: 'Deliveries', permission: 'deliveries.view' },
  { path: '/admin/leads', icon: FileText, label: 'Leads', permission: 'leads.view' },
  { path: '/admin/clients', icon: Users, label: 'Clients', permission: 'clients.view' },
  { path: '/admin/commandes', icon: ShoppingCart, label: 'Commandes', permission: 'commandes.view' },
  { path: '/admin/departements', icon: MapPin, label: 'Départements', permission: 'departements.view' },
  { path: '/admin/facturation', icon: Receipt, label: 'Facturation', permission: 'billing.view' },
  { path: '/admin/invoices', icon: FileCheck, label: 'Factures', permission: 'billing.view' },
  { path: '/admin/activity', icon: Clock, label: 'Activity', permission: 'activity.view' },
  { path: '/admin/users', icon: UserCog, label: 'Utilisateurs', permission: 'users.manage' },
  { path: '/admin/settings', icon: Settings, label: 'Settings', permission: 'settings.access' },
];

const SCOPE_OPTIONS = [
  { value: 'ZR7', label: 'ZR7', color: 'emerald' },
  { value: 'MDL', label: 'MDL', color: 'blue' },
  { value: 'BOTH', label: 'BOTH', color: 'amber' },
];

export default function AdminLayout({ children }) {
  const { user, logout, hasPermission, entityScope, setEntityScope, isSuperAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const visibleNav = NAV_ITEMS.filter(item => hasPermission(item.permission));

  const scopeColor = entityScope === 'ZR7' ? 'emerald' : entityScope === 'MDL' ? 'blue' : 'amber';

  return (
    <div className="flex h-screen bg-zinc-950">
      <aside className={`${collapsed ? 'w-16' : 'w-56'} bg-zinc-900 border-r border-zinc-800 flex flex-col transition-all duration-200`}
             data-testid="admin-sidebar">
        {/* Header */}
        <div className={`h-14 flex items-center border-b border-zinc-800 ${collapsed ? 'justify-center px-2' : 'px-4 gap-3'}`}>
          <div className="w-8 h-8 rounded-lg bg-teal-500 flex items-center justify-center shrink-0">
            <Package className="w-4 h-4 text-white" />
          </div>
          {!collapsed && <span className="font-semibold text-sm text-white tracking-wide">RDZ Admin</span>}
        </div>

        {/* Entity Scope Switcher (super_admin only) */}
        {isSuperAdmin && !collapsed && (
          <div className="px-3 py-2 border-b border-zinc-800" data-testid="entity-scope-switcher">
            <p className="text-[9px] uppercase tracking-wider text-zinc-600 mb-1.5 font-medium">Scope Entité</p>
            <div className="flex gap-1">
              {SCOPE_OPTIONS.map(opt => {
                const isActive = entityScope === opt.value;
                const colorMap = {
                  emerald: isActive ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' : '',
                  blue: isActive ? 'bg-blue-500/20 text-blue-400 border-blue-500/40' : '',
                  amber: isActive ? 'bg-amber-500/20 text-amber-400 border-amber-500/40' : '',
                };
                return (
                  <button
                    key={opt.value}
                    onClick={() => setEntityScope(opt.value)}
                    data-testid={`scope-${opt.value.toLowerCase()}`}
                    className={`flex-1 px-1.5 py-1 text-[10px] font-medium rounded border transition-colors ${
                      isActive
                        ? colorMap[opt.color]
                        : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/50 hover:border-zinc-600'
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Entity badge (non-super_admin) */}
        {!isSuperAdmin && !collapsed && user?.entity && (
          <div className="px-3 py-2 border-b border-zinc-800">
            <p className="text-[9px] uppercase tracking-wider text-zinc-600 mb-1">Entité</p>
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${
              user.entity === 'ZR7' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-blue-500/15 text-blue-400'
            }`} data-testid="user-entity-badge">
              {user.entity}
            </span>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
          {visibleNav.map(item => {
            const active = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  active
                    ? 'bg-teal-500/15 text-teal-400'
                    : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
                } ${collapsed ? 'justify-center' : ''}`}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="w-4 h-4 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <div className="border-t border-zinc-800 p-2">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center p-2 text-zinc-500 hover:text-zinc-300 rounded-md hover:bg-zinc-800 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* User info */}
        <div className={`border-t border-zinc-800 p-3 ${collapsed ? 'flex justify-center' : ''}`}>
          {collapsed ? (
            <button onClick={() => { logout(); navigate('/login'); }} className="p-2 text-zinc-500 hover:text-red-400 rounded-md hover:bg-zinc-800">
              <LogOut className="w-4 h-4" />
            </button>
          ) : (
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-xs text-zinc-300 truncate">{user?.email}</p>
                <div className="flex items-center gap-1.5">
                  <p className="text-[10px] text-zinc-600">{user?.role}</p>
                  {isSuperAdmin && (
                    <Shield className="w-2.5 h-2.5 text-amber-500" />
                  )}
                </div>
              </div>
              <button onClick={() => { logout(); navigate('/login'); }} className="p-1.5 text-zinc-500 hover:text-red-400 rounded-md hover:bg-zinc-800" data-testid="logout-btn">
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-zinc-950">
        <div className="p-6 max-w-[1400px]">
          {children}
        </div>
      </main>
    </div>
  );
}
