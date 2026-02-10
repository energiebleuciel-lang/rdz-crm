/**
 * Page Médias - Bibliothèque d'images partagées
 */

import { useState, useEffect, useCallback } from 'react';
import { useCRM } from '../hooks/useCRM';
import { 
  Image, Upload, Trash2, Search, Filter, Copy, Check,
  FolderOpen, Grid, List, Download, Eye, X, Plus
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Catégories de médias
const CATEGORIES = [
  { key: 'all', label: 'Tous', icon: FolderOpen },
  { key: 'logo', label: 'Logos', icon: Image },
  { key: 'banner', label: 'Bannières', icon: Image },
  { key: 'icon', label: 'Icônes', icon: Image },
  { key: 'background', label: 'Arrière-plans', icon: Image },
  { key: 'other', label: 'Autres', icon: FolderOpen }
];

export default function Media() {
  const { crms, selectedCRM } = useCRM();
  const [media, setMedia] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filtres
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [viewMode, setViewMode] = useState('grid'); // grid ou list
  
  // Modal upload
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadData, setUploadData] = useState({
    name: '',
    category: 'other',
    description: '',
    shared: true,
    crm_id: ''
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  
  // Modal preview
  const [previewMedia, setPreviewMedia] = useState(null);
  
  // Copié
  const [copiedId, setCopiedId] = useState(null);

  // Charger les médias
  const fetchMedia = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      let url = `${API}/api/media?limit=200`;
      
      if (selectedCategory !== 'all') {
        url += `&category=${selectedCategory}`;
      }
      
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Erreur chargement médias');
      
      const data = await res.json();
      setMedia(data.media || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    fetchMedia();
  }, [fetchMedia]);

  // Filtrer les médias
  const filteredMedia = media.filter(m => {
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      return (
        m.name?.toLowerCase().includes(search) ||
        m.description?.toLowerCase().includes(search) ||
        m.original_name?.toLowerCase().includes(search)
      );
    }
    return true;
  });

  // Gérer la sélection de fichier
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setUploadData(prev => ({ ...prev, name: file.name.split('.')[0] }));
      
      // Preview
      const reader = new FileReader();
      reader.onloadend = () => setPreviewUrl(reader.result);
      reader.readAsDataURL(file);
    }
  };

  // Upload
  const handleUpload = async () => {
    if (!selectedFile || !uploadData.name) return;
    
    setUploading(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('name', uploadData.name);
      formData.append('category', uploadData.category);
      formData.append('description', uploadData.description);
      formData.append('shared', uploadData.shared);
      if (uploadData.crm_id) {
        formData.append('crm_id', uploadData.crm_id);
      }
      
      const res = await fetch(`${API}/api/media`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erreur upload');
      }
      
      // Fermer et rafraîchir
      setShowUpload(false);
      setSelectedFile(null);
      setPreviewUrl(null);
      setUploadData({ name: '', category: 'other', description: '', shared: true, crm_id: '' });
      fetchMedia();
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Supprimer
  const handleDelete = async (mediaId) => {
    if (!window.confirm('Supprimer cette image ?')) return;
    
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/media/${mediaId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Erreur suppression');
      
      fetchMedia();
    } catch (err) {
      alert(err.message);
    }
  };

  // Copier l'URL
  const copyUrl = (mediaItem) => {
    const url = `${API}${mediaItem.url}`;
    navigator.clipboard.writeText(url);
    setCopiedId(mediaItem.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Formater la taille
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  // Trouver le CRM par ID
  const getCRMName = (crmId) => {
    const crm = crms.find(c => c.id === crmId);
    return crm?.name || 'Partagé';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Bibliothèque Médias</h1>
          <p className="text-slate-500 mt-1">Images partagées entre ZR7 et MDL</p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg hover:from-amber-600 hover:to-orange-600 transition-all shadow-lg"
        >
          <Plus className="w-5 h-5" />
          Ajouter une image
        </button>
      </div>

      {/* Filtres */}
      <div className="bg-white rounded-xl shadow-sm border p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Recherche */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
            />
          </div>
          
          {/* Catégories */}
          <div className="flex items-center gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat.key}
                onClick={() => setSelectedCategory(cat.key)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedCategory === cat.key
                    ? 'bg-amber-500 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
          
          {/* Vue */}
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded ${viewMode === 'grid' ? 'bg-white shadow' : ''}`}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded ${viewMode === 'list' ? 'bg-white shadow' : ''}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Contenu */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
        </div>
      ) : error ? (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
      ) : filteredMedia.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <Image className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-600">Aucun média</h3>
          <p className="text-slate-400 mt-1">Commencez par ajouter une image</p>
        </div>
      ) : viewMode === 'grid' ? (
        /* Vue Grille */
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {filteredMedia.map(m => (
            <div
              key={m.id}
              className="bg-white rounded-xl shadow-sm border overflow-hidden group hover:shadow-lg transition-all"
            >
              {/* Image */}
              <div 
                className="aspect-square bg-slate-100 relative cursor-pointer"
                onClick={() => setPreviewMedia(m)}
              >
                <img
                  src={`${API}${m.url}`}
                  alt={m.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
                {/* Overlay au hover */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); setPreviewMedia(m); }}
                    className="p-2 bg-white rounded-full hover:bg-slate-100"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); copyUrl(m); }}
                    className="p-2 bg-white rounded-full hover:bg-slate-100"
                  >
                    {copiedId === m.id ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(m.id); }}
                    className="p-2 bg-white rounded-full hover:bg-red-100"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>
              
              {/* Info */}
              <div className="p-3">
                <h4 className="font-medium text-sm text-slate-800 truncate">{m.name}</h4>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-slate-400">{formatSize(m.size)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    m.shared ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {m.shared ? 'Partagé' : getCRMName(m.crm_id)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Vue Liste */
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left p-4 font-medium text-slate-600">Image</th>
                <th className="text-left p-4 font-medium text-slate-600">Nom</th>
                <th className="text-left p-4 font-medium text-slate-600">Catégorie</th>
                <th className="text-left p-4 font-medium text-slate-600">Taille</th>
                <th className="text-left p-4 font-medium text-slate-600">CRM</th>
                <th className="text-right p-4 font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredMedia.map(m => (
                <tr key={m.id} className="border-b hover:bg-slate-50">
                  <td className="p-4">
                    <div className="w-12 h-12 rounded-lg bg-slate-100 overflow-hidden">
                      <img
                        src={`${API}${m.url}`}
                        alt={m.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="font-medium text-slate-800">{m.name}</span>
                    {m.description && (
                      <p className="text-xs text-slate-400 mt-1">{m.description}</p>
                    )}
                  </td>
                  <td className="p-4">
                    <span className="text-sm text-slate-600 capitalize">{m.category}</span>
                  </td>
                  <td className="p-4">
                    <span className="text-sm text-slate-500">{formatSize(m.size)}</span>
                  </td>
                  <td className="p-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      m.shared ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                    }`}>
                      {m.shared ? 'Partagé' : getCRMName(m.crm_id)}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => copyUrl(m)}
                        className="p-2 hover:bg-slate-100 rounded-lg"
                        title="Copier l'URL"
                      >
                        {copiedId === m.id ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-slate-400" />}
                      </button>
                      <button
                        onClick={() => setPreviewMedia(m)}
                        className="p-2 hover:bg-slate-100 rounded-lg"
                        title="Voir"
                      >
                        <Eye className="w-4 h-4 text-slate-400" />
                      </button>
                      <button
                        onClick={() => handleDelete(m.id)}
                        className="p-2 hover:bg-red-50 rounded-lg"
                        title="Supprimer"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>{filteredMedia.length} média(s)</span>
        <span>
          Partagés: {filteredMedia.filter(m => m.shared).length} | 
          ZR7: {filteredMedia.filter(m => !m.shared && getCRMName(m.crm_id) === 'ZR7').length} | 
          MDL: {filteredMedia.filter(m => !m.shared && getCRMName(m.crm_id) === 'MDL').length}
        </span>
      </div>

      {/* Modal Upload */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-auto">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-800">Ajouter une image</h2>
              <button onClick={() => setShowUpload(false)} className="p-2 hover:bg-slate-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              {/* Zone upload */}
              <div className="border-2 border-dashed rounded-xl p-8 text-center">
                {previewUrl ? (
                  <div className="space-y-4">
                    <img src={previewUrl} alt="Preview" className="max-h-48 mx-auto rounded-lg" />
                    <button
                      onClick={() => { setSelectedFile(null); setPreviewUrl(null); }}
                      className="text-sm text-red-500 hover:underline"
                    >
                      Changer d'image
                    </button>
                  </div>
                ) : (
                  <label className="cursor-pointer">
                    <Upload className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-600">Cliquez pour sélectionner une image</p>
                    <p className="text-xs text-slate-400 mt-1">JPG, PNG, GIF, WebP, SVG (max 5 MB)</p>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
              
              {/* Nom */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nom</label>
                <input
                  type="text"
                  value={uploadData.name}
                  onChange={(e) => setUploadData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-amber-500"
                  placeholder="Nom de l'image"
                />
              </div>
              
              {/* Catégorie */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Catégorie</label>
                <select
                  value={uploadData.category}
                  onChange={(e) => setUploadData(prev => ({ ...prev, category: e.target.value }))}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-amber-500"
                >
                  <option value="logo">Logo</option>
                  <option value="banner">Bannière</option>
                  <option value="icon">Icône</option>
                  <option value="background">Arrière-plan</option>
                  <option value="other">Autre</option>
                </select>
              </div>
              
              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description (optionnel)</label>
                <textarea
                  value={uploadData.description}
                  onChange={(e) => setUploadData(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-amber-500"
                  rows={2}
                  placeholder="Description de l'image"
                />
              </div>
              
              {/* Partage */}
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={uploadData.shared}
                    onChange={(e) => setUploadData(prev => ({ ...prev, shared: e.target.checked, crm_id: '' }))}
                    className="w-4 h-4 text-amber-500 rounded"
                  />
                  <span className="text-sm text-slate-700">Partagé (disponible pour ZR7 et MDL)</span>
                </label>
              </div>
              
              {/* CRM spécifique */}
              {!uploadData.shared && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">CRM spécifique</label>
                  <select
                    value={uploadData.crm_id}
                    onChange={(e) => setUploadData(prev => ({ ...prev, crm_id: e.target.value }))}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-amber-500"
                  >
                    <option value="">Sélectionner un CRM</option>
                    {crms.map(crm => (
                      <option key={crm.id} value={crm.id}>{crm.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            
            <div className="p-6 border-t bg-slate-50 flex justify-end gap-3">
              <button
                onClick={() => setShowUpload(false)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg"
              >
                Annuler
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || !uploadData.name || uploading}
                className="px-6 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg hover:from-amber-600 hover:to-orange-600 disabled:opacity-50"
              >
                {uploading ? 'Upload...' : 'Ajouter'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Preview */}
      {previewMedia && (
        <div 
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setPreviewMedia(null)}
        >
          <div className="max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
            <div className="bg-white rounded-2xl overflow-hidden">
              <div className="relative">
                <img
                  src={`${API}${previewMedia.url}`}
                  alt={previewMedia.name}
                  className="w-full max-h-[70vh] object-contain bg-slate-100"
                />
                <button
                  onClick={() => setPreviewMedia(null)}
                  className="absolute top-4 right-4 p-2 bg-black/50 text-white rounded-full hover:bg-black/70"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800">{previewMedia.name}</h3>
                  <p className="text-sm text-slate-500">
                    {formatSize(previewMedia.size)} • {previewMedia.category}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyUrl(previewMedia)}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg hover:bg-slate-200"
                  >
                    {copiedId === previewMedia.id ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                    Copier l'URL
                  </button>
                  <a
                    href={`${API}${previewMedia.url}`}
                    download={previewMedia.original_name}
                    className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600"
                  >
                    <Download className="w-4 h-4" />
                    Télécharger
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
