import { useState, useEffect } from 'react';
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Search, ArrowUpDown } from "lucide-react";

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
      
      const renamed = data.renamed ? ` (renommé depuis ${selectedMapping.utm_campaign})` : '';
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
    const colors = {
      1: 'bg-green-100 text-green-800 border-green-300',
      2: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      3: 'bg-red-100 text-red-800 border-red-300'
    };
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium border ${colors[tier] || 'bg-gray-100'}`}>
        Tier {tier}
      </span>
    );
  };

  return (
    <div className="p-6 space-y-6" data-testid="quality-mappings-page">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Mappings Qualité</h1>
          <p className="text-gray-500 text-sm mt-1">
            utm_campaign → quality_tier (1/2/3)
          </p>
        </div>
        <Button onClick={openAddModal} data-testid="add-mapping-btn">
          <Plus className="w-4 h-4 mr-2" />
          Ajouter un mapping
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <Input
          placeholder="Rechercher par utm_campaign..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
          data-testid="search-input"
        />
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead 
                className="cursor-pointer hover:bg-gray-100"
                onClick={() => toggleSort('utm_campaign')}
              >
                <div className="flex items-center gap-2">
                  utm_campaign
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </TableHead>
              <TableHead 
                className="cursor-pointer hover:bg-gray-100 w-40"
                onClick={() => toggleSort('quality_tier')}
              >
                <div className="flex items-center gap-2">
                  quality_tier
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </TableHead>
              <TableHead className="w-32 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-8 text-gray-500">
                  Chargement...
                </TableCell>
              </TableRow>
            ) : filteredMappings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-8 text-gray-500">
                  {search ? "Aucun mapping trouvé" : "Aucun mapping configuré"}
                </TableCell>
              </TableRow>
            ) : (
              filteredMappings.map((mapping) => (
                <TableRow key={mapping.utm_campaign} data-testid={`mapping-row-${mapping.utm_campaign}`}>
                  <TableCell className="font-mono text-sm">
                    {mapping.utm_campaign}
                  </TableCell>
                  <TableCell>
                    <QualityBadge tier={mapping.quality_tier} />
                  </TableCell>
                  <TableCell className="text-right">
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
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Stats */}
      <div className="text-sm text-gray-500">
        {filteredMappings.length} mapping{filteredMappings.length > 1 ? 's' : ''} 
        {search && ` (sur ${mappings.length} total)`}
      </div>

      {/* Add Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent data-testid="add-modal">
          <DialogHeader>
            <DialogTitle>Ajouter un mapping</DialogTitle>
            <DialogDescription>
              Associer un utm_campaign à un niveau de qualité
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">utm_campaign</label>
              <Input
                placeholder="ex: premium_google_ads_2026"
                value={formUtmCampaign}
                onChange={(e) => setFormUtmCampaign(e.target.value)}
                data-testid="form-utm-campaign"
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">quality_tier</label>
              <Select value={formQualityTier} onValueChange={setFormQualityTier}>
                <SelectTrigger data-testid="form-quality-tier">
                  <SelectValue placeholder="Sélectionner un tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Tier 1 - Premium</SelectItem>
                  <SelectItem value="2">Tier 2 - Standard</SelectItem>
                  <SelectItem value="3">Tier 3 - Low cost</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {formError && (
              <p className="text-sm text-red-600" data-testid="form-error">{formError}</p>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddModal(false)}>
              Annuler
            </Button>
            <Button onClick={handleCreate} disabled={saving} data-testid="submit-add">
              {saving ? "Création..." : "Créer"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Modal */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent data-testid="edit-modal">
          <DialogHeader>
            <DialogTitle>Modifier le mapping</DialogTitle>
            <DialogDescription>
              Vous pouvez renommer le utm_campaign ou changer le tier
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">utm_campaign</label>
              <Input
                placeholder="ex: premium_google_ads_2026"
                value={formUtmCampaign}
                onChange={(e) => setFormUtmCampaign(e.target.value)}
                data-testid="edit-utm-campaign"
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">quality_tier</label>
              <Select value={formQualityTier} onValueChange={setFormQualityTier}>
                <SelectTrigger data-testid="edit-quality-tier">
                  <SelectValue placeholder="Sélectionner un tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Tier 1 - Premium</SelectItem>
                  <SelectItem value="2">Tier 2 - Standard</SelectItem>
                  <SelectItem value="3">Tier 3 - Low cost</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {formError && (
              <p className="text-sm text-red-600" data-testid="edit-form-error">{formError}</p>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditModal(false)}>
              Annuler
            </Button>
            <Button onClick={handleUpdate} disabled={saving} data-testid="submit-edit">
              {saving ? "Sauvegarde..." : "Sauvegarder"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent data-testid="delete-confirm">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Voulez-vous vraiment supprimer le mapping pour <strong>{selectedMapping?.utm_campaign}</strong> ?
              <br />
              Les leads existants avec ce utm_campaign garderont leur quality_tier actuel.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700"
              data-testid="confirm-delete"
            >
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
