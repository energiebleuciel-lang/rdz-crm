import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';

import Login from './pages/Login';
import AdminLayout from './components/AdminLayout';
import AdminDashboard from './pages/AdminDashboard';
import AdminDeliveries from './pages/AdminDeliveries';
import AdminDeliveryDetail from './pages/AdminDeliveryDetail';
import AdminClients from './pages/AdminClients';
import AdminClientDetail from './pages/AdminClientDetail';
import AdminCommandes from './pages/AdminCommandes';
import AdminCommandeDetail from './pages/AdminCommandeDetail';
import AdminSettings from './pages/AdminSettings';
import AdminLeads from './pages/AdminLeads';
import AdminLeadDetail from './pages/AdminLeadDetail';
import AdminActivity from './pages/AdminActivity';
import AdminDepartements from './pages/AdminDepartements';
import AdminFacturation from './pages/AdminFacturation';
import AdminUsers from './pages/AdminUsers';
import AdminInvoices from './pages/AdminInvoices';
import AdminMonitoring from './pages/AdminMonitoring';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return <AdminLayout>{children}</AdminLayout>;
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        <div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/admin/dashboard" replace /> : <Login />} />
      <Route path="/admin/dashboard" element={<PrivateRoute><AdminDashboard /></PrivateRoute>} />
      <Route path="/admin/deliveries" element={<PrivateRoute><AdminDeliveries /></PrivateRoute>} />
      <Route path="/admin/deliveries/:id" element={<PrivateRoute><AdminDeliveryDetail /></PrivateRoute>} />
      <Route path="/admin/clients" element={<PrivateRoute><AdminClients /></PrivateRoute>} />
      <Route path="/admin/clients/:id" element={<PrivateRoute><AdminClientDetail /></PrivateRoute>} />
      <Route path="/admin/commandes" element={<PrivateRoute><AdminCommandes /></PrivateRoute>} />
      <Route path="/admin/commandes/:id" element={<PrivateRoute><AdminCommandeDetail /></PrivateRoute>} />
      <Route path="/admin/leads" element={<PrivateRoute><AdminLeads /></PrivateRoute>} />
      <Route path="/admin/leads/:id" element={<PrivateRoute><AdminLeadDetail /></PrivateRoute>} />
      <Route path="/admin/activity" element={<PrivateRoute><AdminActivity /></PrivateRoute>} />
      <Route path="/admin/departements" element={<PrivateRoute><AdminDepartements /></PrivateRoute>} />
      <Route path="/admin/facturation" element={<PrivateRoute><AdminFacturation /></PrivateRoute>} />
      <Route path="/admin/invoices" element={<PrivateRoute><AdminInvoices /></PrivateRoute>} />
      <Route path="/admin/users" element={<PrivateRoute><AdminUsers /></PrivateRoute>} />
      <Route path="/admin/settings" element={<PrivateRoute><AdminSettings /></PrivateRoute>} />
      <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
