import React, { useState, useEffect } from 'react';
import { RefreshCw, AlertTriangle, CheckCircle, Clock, XCircle, Loader2, Play } from 'lucide-react';

const QueueStatus = ({ token, apiUrl }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiUrl}/api/queue/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
        setError(null);
      } else {
        setError('Erreur lors de la récupération des stats');
      }
    } catch (err) {
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const processQueue = async () => {
    try {
      setProcessing(true);
      const response = await fetch(`${apiUrl}/api/queue/process`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        alert(`Traitement terminé: ${data.results.success} réussis, ${data.results.failed} échoués`);
        fetchStats();
      } else {
        alert('Erreur lors du traitement');
      }
    } catch (err) {
      alert('Erreur de connexion');
    } finally {
      setProcessing(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Refresh toutes les 30 secondes
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [token, apiUrl]);

  if (loading && !stats) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">Chargement...</span>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm border border-red-100">
        <div className="flex items-center text-red-600">
          <XCircle className="w-5 h-5 mr-2" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  const hasIssues = stats?.pending > 0 || stats?.exhausted > 0;
  const crmHealthIssues = stats?.crm_health && 
    Object.values(stats.crm_health).some(crm => !crm.healthy);

  return (
    <div className={`bg-white rounded-xl p-6 shadow-sm border ${hasIssues ? 'border-yellow-200' : 'border-gray-100'}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <h3 className="text-lg font-semibold text-gray-900">File d'attente des leads</h3>
          {hasIssues && (
            <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
              Attention
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchStats}
            disabled={loading}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="Rafraîchir"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {stats?.pending > 0 && (
            <button
              onClick={processQueue}
              disabled={processing}
              className="flex items-center gap-1 px-3 py-1 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Traiter maintenant
            </button>
          )}
        </div>
      </div>

      {/* Stats principales */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-center mb-1">
            <Clock className="w-4 h-4 text-yellow-600 mr-1" />
            <span className="text-2xl font-bold text-gray-900">{stats?.pending || 0}</span>
          </div>
          <p className="text-xs text-gray-600">En attente</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-center mb-1">
            <Loader2 className="w-4 h-4 text-blue-600 mr-1" />
            <span className="text-2xl font-bold text-gray-900">{stats?.processing || 0}</span>
          </div>
          <p className="text-xs text-gray-600">En cours</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-center mb-1">
            <CheckCircle className="w-4 h-4 text-green-600 mr-1" />
            <span className="text-2xl font-bold text-gray-900">{stats?.success || 0}</span>
          </div>
          <p className="text-xs text-gray-600">Réussis</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-center mb-1">
            <XCircle className="w-4 h-4 text-red-600 mr-1" />
            <span className="text-2xl font-bold text-gray-900">{stats?.failed || 0}</span>
          </div>
          <p className="text-xs text-gray-600">Échoués</p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-center mb-1">
            <AlertTriangle className="w-4 h-4 text-orange-600 mr-1" />
            <span className="text-2xl font-bold text-gray-900">{stats?.exhausted || 0}</span>
          </div>
          <p className="text-xs text-gray-600">Épuisés</p>
        </div>
      </div>

      {/* État de santé des CRM */}
      {stats?.crm_health && (
        <div className="border-t border-gray-100 pt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">État des CRM externes</h4>
          <div className="flex gap-4">
            {Object.entries(stats.crm_health).map(([slug, health]) => (
              <div 
                key={slug}
                className={`flex items-center px-3 py-2 rounded-lg ${
                  health.healthy ? 'bg-green-50' : 'bg-red-50'
                }`}
              >
                {health.healthy ? (
                  <CheckCircle className="w-4 h-4 text-green-600 mr-2" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-600 mr-2" />
                )}
                <span className={`font-medium ${health.healthy ? 'text-green-800' : 'text-red-800'}`}>
                  {slug.toUpperCase()}
                </span>
                {!health.healthy && (
                  <span className="ml-2 text-xs text-red-600">
                    ({health.consecutive_failures} échecs)
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats dernières 24h */}
      {stats?.last_24h && (
        <div className="border-t border-gray-100 pt-4 mt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Dernières 24 heures</h4>
          <div className="flex gap-6 text-sm">
            <span className="text-gray-600">
              <span className="font-medium text-gray-900">{stats.last_24h.added}</span> ajoutés
            </span>
            <span className="text-gray-600">
              <span className="font-medium text-gray-900">{stats.last_24h.completed}</span> traités
            </span>
            {stats.pending_retries > 0 && (
              <span className="text-yellow-600">
                <span className="font-medium">{stats.pending_retries}</span> prêts à retenter
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default QueueStatus;
