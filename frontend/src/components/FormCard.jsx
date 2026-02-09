/**
 * FormCard Component - Carte individuelle pour afficher un formulaire
 * Style Landbot avec stats visuelles
 * Composant indépendant et isolé
 */

import React from 'react';
import { Edit, Copy, Trash2, Key, Code } from 'lucide-react';

// Mapping des types de produits
const PRODUCT_CONFIG = {
  'panneaux': { label: 'PV', color: 'bg-amber-500', lightColor: 'bg-amber-100 text-amber-700', icon: '☀️' },
  'pompes': { label: 'PAC', color: 'bg-blue-500', lightColor: 'bg-blue-100 text-blue-700', icon: '🔥' },
  'isolation': { label: 'ITE', color: 'bg-emerald-500', lightColor: 'bg-emerald-100 text-emerald-700', icon: '🏠' },
  'PV': { label: 'PV', color: 'bg-amber-500', lightColor: 'bg-amber-100 text-amber-700', icon: '☀️' },
  'PAC': { label: 'PAC', color: 'bg-blue-500', lightColor: 'bg-blue-100 text-blue-700', icon: '🔥' },
  'ITE': { label: 'ITE', color: 'bg-emerald-500', lightColor: 'bg-emerald-100 text-emerald-700', icon: '🏠' },
};

const FormCard = ({ 
  form, 
  account,
  onEdit, 
  onDuplicate, 
  onDelete, 
  onCopyKey,
  onViewBrief
}) => {
  // Protection contre les erreurs - valeurs par défaut
  const stats = form?.stats || { started: 0, completed: 0, conversion_rate: 0 };
  const productConfig = PRODUCT_CONFIG[form?.product_type] || { label: '?', color: 'bg-slate-500', lightColor: 'bg-slate-100 text-slate-700', icon: '📋' };
  
  // Calcul du taux de conversion avec couleur
  const conversionRate = stats.conversion_rate || 0;
  const getConversionColor = (rate) => {
    if (rate >= 50) return 'text-emerald-600';
    if (rate >= 25) return 'text-amber-600';
    return 'text-red-500';
  };

  // Format de la date
  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' });
    } catch {
      return 'N/A';
    }
  };

  return (
    <div 
      className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden group"
      data-testid={`form-card-${form?.id}`}
    >
      {/* Header avec badge produit */}
      <div className={`${productConfig.color} h-2`} />
      
      <div className="p-5">
        {/* Ligne supérieure: Logo compte + Actions */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            {/* Logo du compte ou placeholder */}
            {account?.logo_main_url ? (
              <img 
                src={account.logo_main_url} 
                alt={account.name} 
                className="w-10 h-10 rounded-lg object-contain bg-slate-50 p-1"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            ) : (
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400 text-sm font-bold">
                {(account?.name || 'N/A').substring(0, 2).toUpperCase()}
              </div>
            )}
            <div>
              <span className={`text-xs font-bold px-2 py-0.5 rounded ${productConfig.lightColor}`}>
                {productConfig.icon} {productConfig.label}
              </span>
              <p className="text-xs text-slate-400 mt-1">{account?.name || 'Compte inconnu'}</p>
            </div>
          </div>
          
          {/* Actions - visibles au hover */}
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button 
              onClick={() => onCopyKey?.(form)}
              className="p-1.5 hover:bg-amber-50 rounded-lg transition-colors" 
              title="Copier form_id"
              data-testid={`copy-key-${form?.id}`}
            >
              <Key className="w-4 h-4 text-amber-600" />
            </button>
            <button 
              onClick={() => onEdit?.(form)}
              className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors" 
              title="Modifier"
              data-testid={`edit-form-${form?.id}`}
            >
              <Edit className="w-4 h-4 text-slate-600" />
            </button>
            <button 
              onClick={() => onDuplicate?.(form)}
              className="p-1.5 hover:bg-blue-50 rounded-lg transition-colors" 
              title="Dupliquer"
              data-testid={`duplicate-form-${form?.id}`}
            >
              <Copy className="w-4 h-4 text-blue-600" />
            </button>
            <button 
              onClick={() => onDelete?.(form)}
              className="p-1.5 hover:bg-red-50 rounded-lg transition-colors" 
              title="Archiver"
              data-testid={`delete-form-${form?.id}`}
            >
              <Trash2 className="w-4 h-4 text-red-500" />
            </button>
          </div>
        </div>

        {/* Nom et code du formulaire */}
        <div className="mb-4">
          <h3 className="font-semibold text-slate-800 text-lg leading-tight mb-1 line-clamp-1">
            {form?.name || 'Sans nom'}
          </h3>
          <code className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
            {form?.code || 'N/A'}
          </code>
        </div>

        {/* Stats visuelles - Style Landbot */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="text-center p-3 bg-slate-50 rounded-lg">
            <div className="text-2xl font-bold text-slate-700">{stats.started}</div>
            <div className="text-xs text-slate-500">Démarrés</div>
          </div>
          <div className="text-center p-3 bg-emerald-50 rounded-lg">
            <div className="text-2xl font-bold text-emerald-600">{stats.completed}</div>
            <div className="text-xs text-slate-500">Terminés</div>
          </div>
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <div className={`text-2xl font-bold ${getConversionColor(conversionRate)}`}>
              {conversionRate}%
            </div>
            <div className="text-xs text-slate-500">Conversion</div>
          </div>
        </div>

        {/* Barre de progression visuelle */}
        <div className="mb-4">
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div 
              className={`h-full ${productConfig.color} transition-all duration-500`}
              style={{ width: `${Math.min(conversionRate, 100)}%` }}
            />
          </div>
        </div>

        {/* Footer: Source + Date + Statut */}
        <div className="flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            {form?.source_name && (
              <span className="bg-slate-100 px-2 py-0.5 rounded">{form.source_name}</span>
            )}
            <span>{formatDate(form?.created_at)}</span>
          </div>
          <div className="flex items-center gap-2">
            {form?.exclude_from_routing && (
              <span className="bg-red-100 text-red-600 px-2 py-0.5 rounded" title="Exclu du routage inter-CRM">
                🚫
              </span>
            )}
            {form?.status === 'archived' ? (
              <span className="bg-slate-200 text-slate-600 px-2 py-0.5 rounded">Archivé</span>
            ) : (
              <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">Actif</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FormCard;
