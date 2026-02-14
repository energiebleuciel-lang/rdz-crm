import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  LayoutDashboard, Package, Users, ShoppingCart, Settings, LogOut,
  Truck, ChevronLeft, ChevronRight, FileText, Clock, MapPin, Receipt
} from 'lucide-react';
import { useState } from 'react';

const NAV = [
  { path: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/admin/deliveries', icon: Truck, label: 'Deliveries' },
  { path: '/admin/leads', icon: FileText, label: 'Leads' },
  { path: '/admin/clients', icon: Users, label: 'Clients' },
  { path: '/admin/commandes', icon: ShoppingCart, label: 'Commandes' },
  { path: '/admin/departements', icon: MapPin, label: 'Départements' },
  { path: '/admin/facturation', icon: Receipt, label: 'Facturation' },
  { path: '/admin/activity', icon: Clock, label: 'Activity' },
  { path: '/admin/settings', icon: Settings, label: 'Settings' },
];

export default function AdminLayout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-zinc-950">
      <aside className={`${collapsed ? 'w-16' : 'w-56'} bg-zinc-900 border-r border-zinc-800 flex flex-col transition-all duration-200`}>
        <div className={`h-14 flex items-center border-b border-zinc-800 ${collapsed ? 'justify-center px-2' : 'px-4 gap-3'}`}>
          <div className="w-8 h-8 rounded-lg bg-teal-500 flex items-center justify-center shrink-0">
            <Package className="w-4 h-4 text-white" />
          </div>
          {!collapsed && <span className="font-semibold text-sm text-white tracking-wide">RDZ Admin</span>}
        </div>

        <nav className="flex-1 py-3 px-2 space-y-0.5">
          {NAV.map(item => {
            const active = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
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

        <div className="border-t border-zinc-800 p-2">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center p-2 text-zinc-500 hover:text-zinc-300 rounded-md hover:bg-zinc-800 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        <div className={`border-t border-zinc-800 p-3 ${collapsed ? 'flex justify-center' : ''}`}>
          {collapsed ? (
            <button onClick={() => { logout(); navigate('/login'); }} className="p-2 text-zinc-500 hover:text-red-400 rounded-md hover:bg-zinc-800">
              <LogOut className="w-4 h-4" />
            </button>
          ) : (
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-xs text-zinc-300 truncate">{user?.email}</p>
                <p className="text-[10px] text-zinc-600">{user?.role}</p>
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
