/**
 * FormsGrid Component - Grille de cartes de formulaires style Landbot
 * Gère l'affichage en grille, le filtrage, et les actions
 * Composant indépendant avec gestion d'erreurs isolée
 */

import React, { useState, useMemo } from 'react';
import { Plus, Grid, List, Search, Filter, Key, Edit, Copy, Trash2 } from 'lucide-react';
import FormCard from './FormCard';

// Configuration des filtres produit
const PRODUCT_FILTERS = [
  { value: '', label: 'Tous', icon: '📋' },
  { value: 'panneaux', label: 'PV', icon: '☀️' },
  { value: 'pompes', label: 'PAC', icon: '🔥' },
  { value: 'isolation', label: 'ITE', icon: '🏠' },
];

const FormsGrid = ({
  forms = [],
  accounts = [],
  onNewForm,
  onEditForm,
  onDuplicateForm,
  onDeleteForm,
  onCopyFormId,
  onViewBrief,
  isLoading = false,
}) => {
  // États locaux - isolés du reste de l'app
  const [viewMode, setViewMode] = useState('grid'); // 'grid' ou 'list'
  const [productFilter, setProductFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('active'); // 'active', 'archived', 'all'

  // Création d'un map des comptes pour lookup rapide
  const accountsMap = useMemo(() => {
    const map = {};
    accounts.forEach(acc => {
      if (acc?.id) map[acc.id] = acc;
    });
    return map;
  }, [accounts]);

  // Filtrage des formulaires - isolé et sécurisé
  const filteredForms = useMemo(() => {
    try {
      return forms.filter(form => {
        if (!form) return false;
        
        // Filtre par produit
        if (productFilter && form.product_type !== productFilter) {
          return false;
        }
        
        // Filtre par statut
        if (statusFilter === 'active' && form.status === 'archived') {
          return false;
        }
        if (statusFilter === 'archived' && form.status !== 'archived') {
          return false;
        }
        
        // Filtre par recherche
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          const matchName = (form.name || '').toLowerCase().includes(query);
          const matchCode = (form.code || '').toLowerCase().includes(query);
          const matchSource = (form.source_name || '').toLowerCase().includes(query);
          if (!matchName && !matchCode && !matchSource) {
            return false;
          }
        }
        
        return true;
      });
    } catch (error) {
      console.error('Erreur filtrage formulaires:', error);
      return forms; // Fallback: retourner tous les formulaires
    }
  }, [forms, productFilter, statusFilter, searchQuery]);

  // Stats globales
  const globalStats = useMemo(() => {
    try {
      const active = forms.filter(f => f?.status !== 'archived').length;
      const archived = forms.filter(f => f?.status === 'archived').length;
      const totalLeads = forms.reduce((sum, f) => sum + (f?.stats?.completed || 0), 0);
      return { active, archived, totalLeads };
    } catch {
      return { active: 0, archived: 0, totalLeads: 0 };
    }
  }, [forms]);

  // Handlers sécurisés
  const handleEdit = (form) => {
    try {
      onEditForm?.(form);
    } catch (error) {
      console.error('Erreur édition formulaire:', error);
    }
  };

  const handleDuplicate = (form) => {
    try {
      onDuplicateForm?.(form);
    } catch (error) {
      console.error('Erreur duplication formulaire:', error);
    }
  };

  const handleDelete = (form) => {
    try {
      onDeleteForm?.(form);
    } catch (error) {
      console.error('Erreur suppression formulaire:', error);
    }
  };

  const handleCopyKey = (form) => {
    try {
      // Copier le form_id (code) au lieu de l'API key pour le nouveau système
      if (form?.id) {
        navigator.clipboard.writeText(form.id);
        // Toast notification serait idéal ici
        alert(`✅ form_id copié !\n\n${form.id}\n\nUtilisez ce form_id dans vos requêtes API.`);
      }
      onCopyFormId?.(form);
    } catch (error) {
      console.error('Erreur copie form_id:', error);
    }
  };

  const handleViewBrief = (form) => {
    try {
      onViewBrief?.(form);
    } catch (error) {
      console.error('Erreur affichage brief:', error);
    }
  };

  return (
    <div className="space-y-6" data-testid="forms-grid-container">
      {/* Header avec titre et bouton nouveau */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Formulaires</h1>
          <p className="text-sm text-slate-500 mt-1">
            {globalStats.active} actifs · {globalStats.archived} archivés · {globalStats.totalLeads} leads total
          </p>
        </div>
        <button 
          onClick={onNewForm}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
          data-testid="new-form-button"
        >
          <Plus className="w-5 h-5" />
          Nouveau formulaire
        </button>
      </div>

      {/* Barre de filtres et recherche */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Recherche */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Rechercher par nom, code ou source..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
              data-testid="forms-search-input"
            />
          </div>

          {/* Filtres produit */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <div className="flex gap-1">
              {PRODUCT_FILTERS.map(pf => (
                <button
                  key={pf.value}
                  onClick={() => setProductFilter(pf.value)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    productFilter === pf.value
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                  data-testid={`filter-${pf.value || 'all'}`}
                >
                  {pf.icon} {pf.label}
                </button>
              ))}
            </div>
          </div>

          {/* Filtre statut */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            data-testid="status-filter"
          >
            <option value="active">Actifs uniquement</option>
            <option value="archived">Archivés</option>
            <option value="all">Tous</option>
          </select>

          {/* Toggle vue grille/liste */}
          <div className="flex border border-slate-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
              title="Vue grille"
              data-testid="view-grid"
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
              title="Vue liste"
              data-testid="view-list"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Compteur résultats */}
        <div className="mt-3 text-sm text-slate-500">
          {filteredForms.length} formulaire{filteredForms.length > 1 ? 's' : ''} 
          {productFilter && ` · Produit: ${PRODUCT_FILTERS.find(p => p.value === productFilter)?.label}`}
          {searchQuery && ` · Recherche: "${searchQuery}"`}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-slate-500">Chargement...</span>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && filteredForms.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <div className="text-6xl mb-4">📋</div>
          <h3 className="text-lg font-medium text-slate-700 mb-2">Aucun formulaire trouvé</h3>
          <p className="text-slate-500 mb-6">
            {searchQuery || productFilter 
              ? 'Essayez de modifier vos filtres de recherche'
              : 'Créez votre premier formulaire pour commencer'}
          </p>
          {!searchQuery && !productFilter && (
            <button 
              onClick={onNewForm}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4 inline mr-2" />
              Créer un formulaire
            </button>
          )}
        </div>
      )}

      {/* Grille de cartes */}
      {!isLoading && filteredForms.length > 0 && viewMode === 'grid' && (
        <div 
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
          data-testid="forms-grid"
        >
          {filteredForms.map(form => (
            <FormCard
              key={form.id}
              form={form}
              account={accountsMap[form.account_id] || accountsMap[form.sub_account_id]}
              onEdit={handleEdit}
              onDuplicate={handleDuplicate}
              onDelete={handleDelete}
              onCopyKey={handleCopyKey}
            />
          ))}
        </div>
      )}

      {/* Vue liste (fallback vers ancien style si besoin) */}
      {!isLoading && filteredForms.length > 0 && viewMode === 'list' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full" data-testid="forms-table">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Code</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Nom</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Produit</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-slate-600">Démarrés</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-slate-600">Terminés</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-slate-600">% Conv.</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredForms.map(form => {
                const productConfig = {
                  'panneaux': { label: 'PV', class: 'bg-amber-100 text-amber-700' },
                  'pompes': { label: 'PAC', class: 'bg-blue-100 text-blue-700' },
                  'isolation': { label: 'ITE', class: 'bg-emerald-100 text-emerald-700' },
                }[form.product_type] || { label: '?', class: 'bg-slate-100 text-slate-700' };
                
                const stats = form.stats || {};
                const rate = stats.conversion_rate || 0;
                const rateClass = rate >= 50 ? 'bg-emerald-100 text-emerald-700' : rate >= 25 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700';
                
                return (
                  <tr key={form.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4">
                      <code className="text-sm bg-slate-100 px-2 py-0.5 rounded">{form.code}</code>
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">{form.name}</td>
                    <td className="py-3 px-4">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${productConfig.class}`}>
                        {productConfig.label}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center text-blue-600 font-medium">{stats.started || 0}</td>
                    <td className="py-3 px-4 text-center text-emerald-600 font-medium">{stats.completed || 0}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${rateClass}`}>{rate}%</span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-1">
                        <button onClick={() => handleCopyKey(form)} className="p-1.5 hover:bg-amber-50 rounded" title="Copier form_id">
                          <Key className="w-4 h-4 text-amber-600" />
                        </button>
                        <button onClick={() => handleEdit(form)} className="p-1.5 hover:bg-slate-100 rounded" title="Modifier">
                          <Edit className="w-4 h-4 text-slate-600" />
                        </button>
                        <button onClick={() => handleDuplicate(form)} className="p-1.5 hover:bg-blue-50 rounded" title="Dupliquer">
                          <Copy className="w-4 h-4 text-blue-600" />
                        </button>
                        <button onClick={() => handleDelete(form)} className="p-1.5 hover:bg-red-50 rounded" title="Archiver">
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default FormsGrid;
