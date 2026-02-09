/**
 * Page Commandes - Gestion des commandes de leads par CRM
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Card, Modal, Button, Select, Loading, Badge } from '../components/UI';
import { Package, Plus, Trash2, Check, X, RefreshCw } from 'lucide-react';

export default function Commandes() {
  const { authFetch } = useAuth();
  const [commandes, setCommandes] = useState([]);
  const [crms, setCrms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    crm_id: '',
    product_type: '*',
    departements: ['*'],
    active: true,
    prix_unitaire: 0
  });

  // Départements métropole (01-95 sauf 2A/2B)
  const DEPARTEMENTS = [];
  for (let i = 1; i <= 95; i++) {
    if (i !== 20) { // Pas 20 (Corse)
      DEPARTEMENTS.push(String(i).padStart(2, '0'));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [commandesRes, crmsRes] = await Promise.all([
        authFetch(`${API}/api/commandes`),
        authFetch(`${API}/api/crms`)
      ]);

      if (commandesRes.ok) {
        const data = await commandesRes.json();
        setCommandes(data.commandes || []);
      }
      if (crmsRes.ok) {
        const data = await crmsRes.json();
        setCrms(data.crms || []);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const initDefaults = async () => {
    if (!window.confirm('Initialiser les commandes par défaut pour tous les CRMs ?')) return;
    
    try {
      const res = await authFetch(`${API}/api/commandes/init-defaults`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        alert(`${data.message}`);
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const openCreate = () => {
    setFormData({
      crm_id: crms[0]?.id || '',
      product_type: '*',
      departements: ['*'],
      active: true,
      prix_unitaire: 0
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const res = await authFetch(`${API}/api/commandes`, {
        method: 'POST',
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        setShowModal(false);
        loadData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Erreur');
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const toggleActive = async (commande) => {
    try {
      const res = await authFetch(`${API}/api/commandes/${commande.id}`, {
        method: 'PUT',
        body: JSON.stringify({ active: !commande.active })
      });

      if (res.ok) {
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const updatePrice = async (commande, price) => {
    try {
      const res = await authFetch(`${API}/api/commandes/${commande.id}`, {
        method: 'PUT',
        body: JSON.stringify({ prix_unitaire: price })
      });

      if (res.ok) {
        // Mise à jour locale pour éviter un rechargement
        setCommandes(prev => prev.map(c => 
          c.id === commande.id ? { ...c, prix_unitaire: price } : c
        ));
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleDelete = async (commande) => {
    if (!window.confirm('Supprimer cette commande ?')) return;
    
    try {
      const res = await authFetch(`${API}/api/commandes/${commande.id}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        loadData();
      }
    } catch (e) {
      alert('Erreur: ' + e.message);
    }
  };

  const handleDeptChange = (dept, checked) => {
    let newDepts = [...formData.departements].filter(d => d !== '*');
    
    if (dept === '*') {
      // Si on coche "Tous", mettre uniquement "*"
      setFormData({ ...formData, departements: checked ? ['*'] : [] });
      return;
    }
    
    if (checked) {
      newDepts.push(dept);
    } else {
      newDepts = newDepts.filter(d => d !== dept);
    }
    
    setFormData({ ...formData, departements: newDepts });
  };

  const productColors = {
    '*': 'bg-purple-500',
    'PV': 'bg-amber-500',
    'PAC': 'bg-blue-500',
    'ITE': 'bg-green-500'
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Commandes</h1>
          <p className="text-sm text-slate-500 mt-1">
            Gérez les commandes de leads par CRM, produit et département
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button variant="secondary" onClick={initDefaults}>
            <RefreshCw className="w-4 h-4" />
            Init. par défaut
          </Button>
          <Button onClick={openCreate}>
            <Plus className="w-4 h-4" />
            Nouvelle commande
          </Button>
        </div>
      </div>

      {/* Stats par CRM */}
      <div className="grid grid-cols-2 gap-4">
        {crms.map(crm => {
          const crmCommandes = commandes.filter(c => c.crm_id === crm.id);
          const activeCount = crmCommandes.filter(c => c.active).length;
          
          return (
            <Card key={crm.id} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg text-slate-800">{crm.name}</h3>
                  <p className="text-sm text-slate-500">{crm.slug?.toUpperCase()}</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-slate-800">{activeCount}</p>
                  <p className="text-xs text-slate-500">commandes actives</p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Liste des commandes */}
      {commandes.length === 0 ? (
        <Card className="p-8 text-center">
          <Package className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-700 mb-2">Aucune commande</h3>
          <p className="text-slate-500 mb-4">Initialisez les commandes par défaut ou créez-en une nouvelle</p>
          <Button onClick={initDefaults}>Initialiser les commandes par défaut</Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {crms.map(crm => {
            const crmCommandes = commandes.filter(c => c.crm_id === crm.id);
            if (crmCommandes.length === 0) return null;
            
            return (
              <Card key={crm.id} className="overflow-hidden">
                <div className="bg-slate-800 text-white px-4 py-3">
                  <h3 className="font-semibold">{crm.name}</h3>
                </div>
                
                <div className="divide-y">
                  {crmCommandes.map(cmd => (
                    <div key={cmd.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                      <div className="flex items-center gap-4">
                        <span className={`${productColors[cmd.product_type]} text-white px-3 py-1 rounded-full text-sm font-medium`}>
                          {cmd.product_type === '*' ? 'TOUS' : cmd.product_type}
                        </span>
                        
                        <div>
                          <p className="font-medium text-slate-800">
                            {cmd.departements?.includes('*') 
                              ? 'Tous les départements (01-95)' 
                              : `${cmd.departements?.length || 0} département(s)`
                            }
                          </p>
                          {!cmd.departements?.includes('*') && (
                            <p className="text-sm text-slate-500">
                              {cmd.departements?.slice(0, 10).join(', ')}
                              {cmd.departements?.length > 10 && ` +${cmd.departements.length - 10} autres`}
                            </p>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        {/* Prix par lead */}
                        <div className="flex items-center gap-2 bg-amber-50 px-3 py-1.5 rounded-lg">
                          <span className="text-sm text-amber-700">Prix:</span>
                          <input
                            type="number"
                            value={cmd.prix_unitaire || 0}
                            onChange={(e) => updatePrice(cmd, parseFloat(e.target.value) || 0)}
                            className="w-16 px-2 py-1 text-sm font-bold text-amber-800 bg-white border border-amber-200 rounded text-right"
                            min="0"
                            step="0.5"
                          />
                          <span className="text-sm text-amber-700">€</span>
                        </div>
                        
                        <Badge variant={cmd.active ? 'success' : 'secondary'}>
                          {cmd.active ? 'Active' : 'Inactive'}
                        </Badge>
                        
                        <button
                          onClick={() => toggleActive(cmd)}
                          className={`p-2 rounded-lg transition-colors ${
                            cmd.active 
                              ? 'text-green-600 hover:bg-green-50' 
                              : 'text-slate-400 hover:bg-slate-100'
                          }`}
                          title={cmd.active ? 'Désactiver' : 'Activer'}
                        >
                          {cmd.active ? <Check className="w-5 h-5" /> : <X className="w-5 h-5" />}
                        </button>
                        
                        <button
                          onClick={() => handleDelete(cmd)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                          title="Supprimer"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Modal Créer */}
      <Modal 
        isOpen={showModal} 
        onClose={() => setShowModal(false)}
        title="Nouvelle commande"
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Select
            label="CRM"
            value={formData.crm_id}
            onChange={e => setFormData({...formData, crm_id: e.target.value})}
            options={crms.map(c => ({ value: c.id, label: c.name }))}
            required
          />
          
          <Select
            label="Type de produit"
            value={formData.product_type}
            onChange={e => setFormData({...formData, product_type: e.target.value})}
            options={[
              { value: '*', label: 'Tous les produits' },
              { value: 'PV', label: 'PV - Panneaux solaires' },
              { value: 'PAC', label: 'PAC - Pompe à chaleur' },
              { value: 'ITE', label: 'ITE - Isolation' }
            ]}
          />

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Départements
            </label>
            
            {/* Option tous */}
            <label className="flex items-center gap-2 p-3 bg-purple-50 rounded-lg mb-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.departements.includes('*')}
                onChange={e => handleDeptChange('*', e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-purple-500 focus:ring-purple-500"
              />
              <span className="font-medium text-purple-700">Tous les départements (01-95)</span>
            </label>
            
            {/* Grille départements */}
            {!formData.departements.includes('*') && (
              <div className="grid grid-cols-10 gap-1 max-h-48 overflow-y-auto p-2 bg-slate-50 rounded-lg">
                {DEPARTEMENTS.map(dept => (
                  <label 
                    key={dept}
                    className={`flex items-center justify-center p-2 rounded cursor-pointer text-sm font-mono
                      ${formData.departements.includes(dept) 
                        ? 'bg-amber-500 text-white' 
                        : 'bg-white text-slate-600 hover:bg-slate-100'
                      }`}
                  >
                    <input
                      type="checkbox"
                      checked={formData.departements.includes(dept)}
                      onChange={e => handleDeptChange(dept, e.target.checked)}
                      className="sr-only"
                    />
                    {dept}
                  </label>
                ))}
              </div>
            )}
            
            <p className="text-xs text-slate-500 mt-2">
              {formData.departements.includes('*') 
                ? 'Tous les départements de France métropolitaine (hors Corse)' 
                : `${formData.departements.length} département(s) sélectionné(s)`
              }
            </p>
          </div>

          {/* Prix unitaire */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Prix par lead (€)
            </label>
            <input
              type="number"
              value={formData.prix_unitaire}
              onChange={e => setFormData({...formData, prix_unitaire: parseFloat(e.target.value) || 0})}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
              min="0"
              step="0.5"
              placeholder="0.00"
            />
            <p className="text-xs text-slate-500 mt-1">
              Prix utilisé pour la facturation inter-CRM
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="secondary" onClick={() => setShowModal(false)}>
              Annuler
            </Button>
            <Button type="submit">
              Créer la commande
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
