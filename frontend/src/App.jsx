/**
 * EnerSolar CRM - Application principale
 * Version 2.0
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { CRMProvider } from './hooks/useCRM';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import LandingPages from './pages/LandingPages';
import Forms from './pages/Forms';
import Leads from './pages/Leads';
import Commandes from './pages/Commandes';
import Departements from './pages/Departements';
import Billing from './pages/Billing';
import Settings from './pages/Settings';
import UsersPage from './pages/UsersPage';
import Media from './pages/Media';
import QualityMappings from './pages/QualityMappings';

// Components
import Layout from './components/Layout';
import { Loading } from './components/UI';

// Route protégée avec CRM Provider
function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <Loading text="Vérification de la session..." />
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return (
    <CRMProvider>
      <Layout>{children}</Layout>
    </CRMProvider>
  );
}

// Routes
function AppRoutes() {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <Loading text="Chargement..." />
      </div>
    );
  }
  
  return (
    <Routes>
      <Route 
        path="/login" 
        element={user ? <Navigate to="/dashboard" replace /> : <Login />} 
      />
      
      <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
      <Route path="/accounts" element={<PrivateRoute><Accounts /></PrivateRoute>} />
      <Route path="/lps" element={<PrivateRoute><LandingPages /></PrivateRoute>} />
      <Route path="/forms" element={<PrivateRoute><Forms /></PrivateRoute>} />
      <Route path="/leads" element={<PrivateRoute><Leads /></PrivateRoute>} />
      <Route path="/departements" element={<PrivateRoute><Departements /></PrivateRoute>} />
      <Route path="/commandes" element={<PrivateRoute><Commandes /></PrivateRoute>} />
      <Route path="/billing" element={<PrivateRoute><Billing /></PrivateRoute>} />
      <Route path="/media" element={<PrivateRoute><Media /></PrivateRoute>} />
      <Route path="/quality-mappings" element={<PrivateRoute><QualityMappings /></PrivateRoute>} />
      <Route path="/users" element={<PrivateRoute><UsersPage /></PrivateRoute>} />
      <Route path="/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
      
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

// App
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
