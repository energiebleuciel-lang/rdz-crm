import { useState, useEffect } from 'react';
import { Card, Loading, Badge, Button, Modal, Input, Select } from '../components/UI';
import { toast } from 'sonner';
import { Plus, Pencil, Trash2, Search, ArrowUpDown, AlertTriangle } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function QualityMappings() {
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState('utm_campaign');
  const [sortOrder, setSortOrder] = useState('asc');
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState(null);
  
  // Form states
  const [formUtmCampaign, setFormUtmCampaign] = useState('');
  const [formQualityTier, setFormQualityTier] = useState('');
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  const token = localStorage.getItem('token');

  // Fetch mappings
  const fetchMappings = async () => {
    try {
      const res = await fetch(`${API_URL}/api/quality-mappings`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setMappings(data.mappings || []);
    } catch (err) {
      toast.error("Erreur lors du chargement des mappings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappings();
  }, []);

  // Filter and sort
  const filteredMappings = mappings
    .filter(m => m.utm_campaign.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const aVal = sortField === 'quality_tier' ? a.quality_tier : a.utm_campaign.toLowerCase();
      const bVal = sortField === 'quality_tier' ? b.quality_tier : b.utm_campaign.toLowerCase();
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      }
      return aVal < bVal ? 1 : -1;
    });

  // Toggle sort
  const toggleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Reset form
  const resetForm = () => {
    setFormUtmCampaign('');
    setFormQualityTier('');
    setFormError('');
  };

  // Open add modal
  const openAddModal = () => {
    resetForm();
    setShowAddModal(true);
  };

  // Open edit modal
  const openEditModal = (mapping) => {
    setSelectedMapping(mapping);
    setFormUtmCampaign(mapping.utm_campaign);
    setFormQualityTier(mapping.quality_tier.toString());
    setFormError('');
    setShowEditModal(true);
  };

  // Open delete confirm
  const openDeleteConfirm = (mapping) => {
    setSelectedMapping(mapping);
    setShowDeleteConfirm(true);
  };

  // Create mapping
  const handleCreate = async () => {
    if (!formUtmCampaign.trim()) {
      setFormError("utm_campaign est requis");
      return;
    }
    if (!formQualityTier) {
      setFormError("quality_tier est requis");
      return;
    }

    // Check uniqueness
    if (mappings.some(m => m.utm_campaign === formUtmCampaign.trim())) {
      setFormError("Ce utm_campaign existe déjà");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/quality-mappings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          utm_campaign: formUtmCampaign.trim(),
          quality_tier: parseInt(formQualityTier)
        })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        setFormError(data.detail || "Erreur lors de la création");
        return;
      }
      
      toast.success(`Mapping créé : ${formUtmCampaign} → Tier ${formQualityTier}`);
      setShowAddModal(false);
      fetchMappings();
    } catch (err) {
      setFormError("Erreur réseau");
    } finally {
      setSaving(false);
    }
  };

  // Update mapping
  const handleUpdate = async () => {
    if (!formUtmCampaign.trim()) {
      setFormError("utm_campaign est requis");
      return;
    }
    if (!formQualityTier) {
      setFormError("quality_tier est requis");
      return;
    }

    // Check uniqueness if renamed
    if (formUtmCampaign.trim() !== selectedMapping.utm_campaign) {
      if (mappings.some(m => m.utm_campaign === formUtmCampaign.trim())) {
        setFormError("Ce utm_campaign existe déjà");
        return;
      }
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/quality-mappings/${encodeURIComponent(selectedMapping.utm_campaign)}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          utm_campaign: formUtmCampaign.trim(),
          quality_tier: parseInt(formQualityTier)
        })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        setFormError(data.detail || "Erreur lors de la mise à jour");
        return;
      }
      
      const renamed = data.renamed ? ` (renommé)` : '';
      toast.success(`Mapping mis à jour : ${formUtmCampaign} → Tier ${formQualityTier}${renamed}`);
      setShowEditModal(false);
      fetchMappings();
    } catch (err) {
      setFormError("Erreur réseau");
    } finally {
      setSaving(false);
    }
  };

  // Delete mapping
  const handleDelete = async () => {
    try {
      const res = await fetch(`${API_URL}/api/quality-mappings/${encodeURIComponent(selectedMapping.utm_campaign)}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) {
        const data = await res.json();
        toast.error(data.detail || "Erreur lors de la suppression");
        return;
      }
      
      toast.success(`Mapping supprimé : ${selectedMapping.utm_campaign}`);
      setShowDeleteConfirm(false);
      fetchMappings();
    } catch (err) {
      toast.error("Erreur réseau");
    }
  };

  // Quality tier badge
  const QualityBadge = ({ tier }) => {
    const variants = {
      1: 'success',
      2: 'warning',
      3: 'danger'
    };
    const labels = {
      1: 'Tier 1 - Premium',
      2: 'Tier 2 - Standard',
      3: 'Tier 3 - Low cost'
    };
    return <Badge variant={variants[tier] || 'default'}>{labels[tier] || `Tier ${tier}`}</Badge>;
  };

  const tierOptions = [
    { value: '', label: 'Sélectionner un tier' },
    { value: '1', label: 'Tier 1 - Premium' },
    { value: '2', label: 'Tier 2 - Standard' },
    { value: '3', label: 'Tier 3 - Low cost' }
  ];

  if (loading) return <Loading />;

  return (
    <div className="p-6 space-y-6" data-testid="quality-mappings-page">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Mappings Qualité</h1>
          <p className="text-slate-500 text-sm mt-1">
            utm_campaign → quality_tier (1/2/3)
          </p>
        </div>
        <Button onClick={openAddModal} data-testid="add-mapping-btn">
          <Plus className="w-4 h-4" />
          Ajouter un mapping
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
        <input
          type="text"
          placeholder="Rechercher par utm_campaign..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none"
          data-testid="search-input"
        />
      </div>

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th 
                  className="text-left px-6 py-3 text-sm font-semibold text-slate-600 cursor-pointer hover:bg-slate-100"
                  onClick={() => toggleSort('utm_campaign')}
                >
                  <div className="flex items-center gap-2">
                    utm_campaign
                    <ArrowUpDown className="w-4 h-4" />
                  </div>
                </th>
                <th 
                  className="text-left px-6 py-3 text-sm font-semibold text-slate-600 cursor-pointer hover:bg-slate-100 w-48"
                  onClick={() => toggleSort('quality_tier')}
                >
                  <div className="flex items-center gap-2">
                    quality_tier
                    <ArrowUpDown className="w-4 h-4" />
                  </div>
                </th>
                <th className="text-right px-6 py-3 text-sm font-semibold text-slate-600 w-32">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredMappings.length === 0 ? (
                <tr>
                  <td colSpan={3} className="text-center py-8 text-slate-500">
                    {search ? "Aucun mapping trouvé" : "Aucun mapping configuré"}
                  </td>
                </tr>
              ) : (
                filteredMappings.map((mapping) => (
                  <tr key={mapping.utm_campaign} className="hover:bg-slate-50" data-testid={`mapping-row-${mapping.utm_campaign}`}>
                    <td className="px-6 py-4 font-mono text-sm text-slate-700">
                      {mapping.utm_campaign}
                    </td>
                    <td className="px-6 py-4">
                      <QualityBadge tier={mapping.quality_tier} />
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => openEditModal(mapping)}
                          data-testid={`edit-${mapping.utm_campaign}`}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => openDeleteConfirm(mapping)}
                          data-testid={`delete-${mapping.utm_campaign}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Stats */}
      <p className="text-sm text-slate-500">
        {filteredMappings.length} mapping{filteredMappings.length > 1 ? 's' : ''} 
        {search && ` (sur ${mappings.length} total)`}
      </p>

      {/* Add Modal */}
      <Modal isOpen={showAddModal} onClose={() => setShowAddModal(false)} title="Ajouter un mapping">
        <div className="space-y-4">
          <Input
            label="utm_campaign"
            placeholder="ex: premium_google_ads_2026"
            value={formUtmCampaign}
            onChange={(e) => setFormUtmCampaign(e.target.value)}
            data-testid="form-utm-campaign"
          />
          
          <Select
            label="quality_tier"
            options={tierOptions}
            value={formQualityTier}
            onChange={(e) => setFormQualityTier(e.target.value)}
            data-testid="form-quality-tier"
          />
          
          {formError && (
            <p className="text-sm text-red-600" data-testid="form-error">{formError}</p>
          )}
          
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" onClick={() => setShowAddModal(false)}>
              Annuler
            </Button>
            <Button onClick={handleCreate} loading={saving} data-testid="submit-add">
              Créer
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal isOpen={showEditModal} onClose={() => setShowEditModal(false)} title="Modifier le mapping">
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            Vous pouvez renommer le utm_campaign ou changer le tier
          </p>
          
          <Input
            label="utm_campaign"
            placeholder="ex: premium_google_ads_2026"
            value={formUtmCampaign}
            onChange={(e) => setFormUtmCampaign(e.target.value)}
            data-testid="edit-utm-campaign"
          />
          
          <Select
            label="quality_tier"
            options={tierOptions}
            value={formQualityTier}
            onChange={(e) => setFormQualityTier(e.target.value)}
            data-testid="edit-quality-tier"
          />
          
          {formError && (
            <p className="text-sm text-red-600" data-testid="edit-form-error">{formError}</p>
          )}
          
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="secondary" onClick={() => setShowEditModal(false)}>
              Annuler
            </Button>
            <Button onClick={handleUpdate} loading={saving} data-testid="submit-edit">
              Sauvegarder
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal isOpen={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)} title="Confirmer la suppression" size="sm">
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-red-50 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-red-800">
                Voulez-vous vraiment supprimer le mapping pour <strong>{selectedMapping?.utm_campaign}</strong> ?
              </p>
              <p className="text-xs text-red-600 mt-1">
                Les leads existants garderont leur quality_tier actuel.
              </p>
            </div>
          </div>
          
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)}>
              Annuler
            </Button>
            <Button variant="danger" onClick={handleDelete} data-testid="confirm-delete">
              Supprimer
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
