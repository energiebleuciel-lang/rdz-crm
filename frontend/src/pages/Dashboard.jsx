/**
 * Dashboard - Page d'accueil
 */

import { useState, useEffect } from 'react';
import { useApi, API } from '../hooks/useApi';
import { useAuth } from '../hooks/useAuth';
import { useCRM } from '../hooks/useCRM';
import { Card, StatCard, Loading, Badge } from '../components/UI';
import { 
  Users, FileText, Globe, TrendingUp, CheckCircle, XCircle, 
  Clock, AlertTriangle, RefreshCw, Play
} from 'lucide-react';

export default function Dashboard() {
  const { authFetch } = useAuth();
  const { selectedCRM, currentCRM } = useCRM();
  const [stats, setStats] = useState(null);
  const [queueStats, setQueueStats] = useState(null);
  const [recentLeads, setRecentLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedCRM) {
      loadData();
    }
  }, [selectedCRM]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Stats leads - filtré par CRM
      const statsRes = await authFetch(`${API}/api/leads/stats/global?crm_id=${selectedCRM}`);
      if (statsRes.ok) setStats(await statsRes.json());
      
      // Stats queue - filtré par CRM
      const queueRes = await authFetch(`${API}/api/queue/stats?crm_id=${selectedCRM}`);
      if (queueRes.ok) setQueueStats(await queueRes.json());
      
      // Recent leads - filtré par CRM
      const leadsRes = await authFetch(`${API}/api/leads?limit=10&crm_id=${selectedCRM}`);
      if (leadsRes.ok) {
        const data = await leadsRes.json();
        setRecentLeads(data.leads || []);
      }
    } catch (e) {
      console.error('Dashboard load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const processQueue = async () => {
    try {
      const res = await authFetch(`${API}/api/queue/process`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        alert(`Traitement: ${data.results.success} réussis, ${data.results.failed} échoués`);
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Tableau de bord</h1>
        <p className="text-sm text-slate-500">
          CRM: <span className="font-medium text-slate-700">{currentCRM?.name || 'Non sélectionné'}</span>
        </p>
      </div>

      {/* Stats principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          icon={Users} 
          label="Total Leads" 
          value={stats?.total || 0}
          color="amber"
        />
        <StatCard 
          icon={CheckCircle} 
          label="Envoyés" 
          value={stats?.success || 0}
          color="green"
        />
        <StatCard 
          icon={XCircle} 
          label="Échoués" 
          value={stats?.failed || 0}
          color="red"
        />
        <StatCard 
          icon={TrendingUp} 
          label="Taux d'envoi" 
          value={`${stats?.sent_rate || 0}%`}
          color="blue"
        />
      </div>

      {/* File d'attente */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-800">File d'attente</h2>
            {queueStats?.pending > 0 && (
              <Badge variant="warning">{queueStats.pending} en attente</Badge>
            )}
          </div>
          <div className="flex gap-2">
            <button 
              onClick={loadData}
              className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            {queueStats?.pending > 0 && (
              <button
                onClick={processQueue}
                className="flex items-center gap-2 px-3 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 text-sm"
              >
                <Play className="w-4 h-4" />
                Traiter
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center p-3 bg-slate-50 rounded-lg">
            <Clock className="w-5 h-5 text-amber-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">{queueStats?.pending || 0}</p>
            <p className="text-xs text-slate-500">En attente</p>
          </div>
          <div className="text-center p-3 bg-slate-50 rounded-lg">
            <RefreshCw className="w-5 h-5 text-blue-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">{queueStats?.processing || 0}</p>
            <p className="text-xs text-slate-500">En cours</p>
          </div>
          <div className="text-center p-3 bg-slate-50 rounded-lg">
            <CheckCircle className="w-5 h-5 text-green-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">{queueStats?.success || 0}</p>
            <p className="text-xs text-slate-500">Réussis</p>
          </div>
          <div className="text-center p-3 bg-slate-50 rounded-lg">
            <XCircle className="w-5 h-5 text-red-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">{queueStats?.failed || 0}</p>
            <p className="text-xs text-slate-500">Échoués</p>
          </div>
          <div className="text-center p-3 bg-slate-50 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-orange-500 mx-auto mb-1" />
            <p className="text-2xl font-bold">{queueStats?.exhausted || 0}</p>
            <p className="text-xs text-slate-500">Épuisés</p>
          </div>
        </div>
      </Card>

      {/* Leads récents */}
      <Card>
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold text-slate-800">Leads récents</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Téléphone</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Nom</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Formulaire</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Statut</th>
                <th className="text-left p-4 text-sm font-medium text-slate-600">Date</th>
              </tr>
            </thead>
            <tbody>
              {recentLeads.map(lead => (
                <tr key={lead.id} className="border-t hover:bg-slate-50">
                  <td className="p-4 font-mono text-sm">{lead.phone}</td>
                  <td className="p-4">{lead.nom} {lead.prenom}</td>
                  <td className="p-4">
                    <Badge variant="info">{lead.form_code}</Badge>
                  </td>
                  <td className="p-4">
                    <Badge variant={
                      lead.api_status === 'success' ? 'success' :
                      lead.api_status === 'duplicate' ? 'warning' :
                      lead.api_status === 'queued' ? 'info' : 'danger'
                    }>
                      {lead.api_status}
                    </Badge>
                  </td>
                  <td className="p-4 text-sm text-slate-500">
                    {new Date(lead.created_at).toLocaleDateString('fr-FR')}
                  </td>
                </tr>
              ))}
              {recentLeads.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500">
                    Aucun lead récent
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
