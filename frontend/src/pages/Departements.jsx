/**
 * Page Départements - Statistiques des leads par département, produit et source
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { useCRM } from '../hooks/useCRM';
import { Card, Loading, Badge, Button } from '../components/UI';
import { MapPin, Package, Globe, TrendingUp, Calendar, Filter, X } from 'lucide-react';

// Départements métropole
const DEPARTEMENTS = [];
for (let i = 1; i <= 95; i++) {
  if (i !== 20) DEPARTEMENTS.push(String(i).padStart(2, '0'));
}

const DEPT_NAMES = {
  "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes",
  "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes", "09": "Ariège", "10": "Aube",
  "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal",
  "16": "Charente", "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "21": "Côte-d'Or",
  "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme",
  "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère", "30": "Gard", "31": "Haute-Garonne",
  "32": "Gers", "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine", "36": "Indre",
  "37": "Indre-et-Loire", "38": "Isère", "39": "Jura", "40": "Landes", "41": "Loir-et-Cher",
  "42": "Loire", "43": "Haute-Loire", "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot",
  "47": "Lot-et-Garonne", "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne",
  "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse", "56": "Morbihan",
  "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise", "61": "Orne",
  "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques", "65": "Hautes-Pyrénées",
  "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône",
  "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie", "75": "Paris",
  "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres",
  "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse",
  "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne",
  "90": "Territoire de Belfort", "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
  "94": "Val-de-Marne", "95": "Val-d'Oise"
};

export default function Departements() {
  const { authFetch } = useAuth();
  const { selectedCRM } = useCRM();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Filtres
  const [selectedDepts, setSelectedDepts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [period, setPeriod] = useState('month');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showDeptSelector, setShowDeptSelector] = useState(false);

  useEffect(() => {
    loadStats();
  }, [selectedCRM, selectedDepts, selectedProduct, period, dateFrom, dateTo]);

  const loadStats = async () => {
    try {
      setLoading(true);
      
      let url = `${API}/api/stats/departements?`;
      
      if (selectedCRM?.id) url += `crm_id=${selectedCRM.id}&`;
      if (selectedDepts.length > 0) url += `departements=${selectedDepts.join(',')}&`;
      if (selectedProduct) url += `product_type=${selectedProduct}&`;
      if (period !== 'custom') url += `period=${period}&`;
      if (period === 'custom' && dateFrom) url += `date_from=${dateFrom}&`;
      if (period === 'custom' && dateTo) url += `date_to=${dateTo}&`;
      
      const res = await authFetch(url);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('Load error:', e);
    } finally {
      setLoading(false);
    }
  };

  const toggleDept = (dept) => {
    if (selectedDepts.includes(dept)) {
      setSelectedDepts(selectedDepts.filter(d => d !== dept));
    } else {
      setSelectedDepts([...selectedDepts, dept]);
    }
  };

  const clearFilters = () => {
    setSelectedDepts([]);
    setSelectedProduct('');
    setPeriod('month');
    setDateFrom('');
    setDateTo('');
  };

  const productColors = {
    PV: 'bg-amber-500',
    PAC: 'bg-blue-500',
    ITE: 'bg-green-500'
  };

  if (loading && !stats) return <Loading />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Statistiques Départements</h1>
          <p className="text-sm text-slate-500 mt-1">
            Analyse des leads par département, produit et source
          </p>
        </div>
        
        {(selectedDepts.length > 0 || selectedProduct || period !== 'month') && (
          <Button variant="secondary" onClick={clearFilters}>
            <X className="w-4 h-4" />
            Effacer filtres
          </Button>
        )}
      </div>

      {/* Filtres */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Période */}
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Période</label>
            <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
              {[
                { value: 'today', label: "Aujourd'hui" },
                { value: 'week', label: '7 jours' },
                { value: 'month', label: '30 jours' },
                { value: 'custom', label: 'Personnalisé' }
              ].map(p => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    period === p.value 
                      ? 'bg-white text-slate-800 shadow-sm' 
                      : 'text-slate-600 hover:text-slate-800'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dates personnalisées */}
          {period === 'custom' && (
            <div className="flex gap-2 items-end">
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Du</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={e => setDateFrom(e.target.value)}
                  className="px-3 py-1.5 border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Au</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={e => setDateTo(e.target.value)}
                  className="px-3 py-1.5 border rounded-lg text-sm"
                />
              </div>
            </div>
          )}

          {/* Produit */}
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Produit</label>
            <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
              {[
                { value: '', label: 'Tous' },
                { value: 'PV', label: 'PV' },
                { value: 'PAC', label: 'PAC' },
                { value: 'ITE', label: 'ITE' }
              ].map(p => (
                <button
                  key={p.value}
                  onClick={() => setSelectedProduct(p.value)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    selectedProduct === p.value 
                      ? 'bg-white text-slate-800 shadow-sm' 
                      : 'text-slate-600 hover:text-slate-800'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Départements */}
          <div className="relative">
            <label className="text-xs text-slate-500 mb-1 block">Départements</label>
            <button
              onClick={() => setShowDeptSelector(!showDeptSelector)}
              className="px-4 py-1.5 border rounded-lg text-sm flex items-center gap-2 hover:bg-slate-50"
            >
              <MapPin className="w-4 h-4" />
              {selectedDepts.length === 0 ? 'Tous' : `${selectedDepts.length} sélectionné(s)`}
            </button>
            
            {showDeptSelector && (
              <div className="absolute top-full mt-2 left-0 bg-white border rounded-lg shadow-xl z-50 p-4 w-[500px] max-h-[400px] overflow-y-auto">
                <div className="flex justify-between items-center mb-3">
                  <span className="font-medium">Sélectionner les départements</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setSelectedDepts(DEPARTEMENTS)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Tout sélectionner
                    </button>
                    <button
                      onClick={() => setSelectedDepts([])}
                      className="text-xs text-slate-500 hover:underline"
                    >
                      Tout effacer
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-6 gap-1">
                  {DEPARTEMENTS.map(dept => (
                    <button
                      key={dept}
                      onClick={() => toggleDept(dept)}
                      className={`p-2 rounded text-sm font-mono transition-colors ${
                        selectedDepts.includes(dept)
                          ? 'bg-amber-500 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                      title={DEPT_NAMES[dept]}
                    >
                      {dept}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => setShowDeptSelector(false)}
                  className="w-full mt-3 py-2 bg-slate-800 text-white rounded-lg text-sm"
                >
                  Appliquer
                </button>
              </div>
            )}
          </div>
        </div>
        
        {/* Tags des départements sélectionnés */}
        {selectedDepts.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t">
            {selectedDepts.map(dept => (
              <span
                key={dept}
                className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs"
              >
                {dept} - {DEPT_NAMES[dept]}
                <button onClick={() => toggleDept(dept)} className="hover:text-amber-900">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </Card>

      {/* Stats globales */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="p-4 bg-gradient-to-br from-slate-800 to-slate-900 text-white">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-white/10 rounded-xl">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <p className="text-3xl font-bold">{stats?.total_leads || 0}</p>
              <p className="text-sm opacity-80">Total Leads</p>
            </div>
          </div>
        </Card>
        
        {['PV', 'PAC', 'ITE'].map(product => (
          <Card key={product} className={`p-4 ${productColors[product]} text-white`}>
            <div className="flex items-center gap-3">
              <div className="p-3 bg-white/20 rounded-xl">
                <Package className="w-6 h-6" />
              </div>
              <div>
                <p className="text-3xl font-bold">{stats?.by_product?.[product] || 0}</p>
                <p className="text-sm opacity-90">{product}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Par Département */}
        <Card className="overflow-hidden">
          <div className="bg-slate-800 text-white px-4 py-3 flex items-center gap-2">
            <MapPin className="w-5 h-5" />
            <h3 className="font-semibold">Par Département</h3>
          </div>
          <div className="max-h-[400px] overflow-y-auto">
            <table className="w-full">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="text-left p-3 text-sm font-medium text-slate-600">Dept</th>
                  <th className="text-left p-3 text-sm font-medium text-slate-600">Nom</th>
                  <th className="text-right p-3 text-sm font-medium text-slate-600">Total</th>
                  <th className="text-right p-3 text-sm font-medium text-amber-600">PV</th>
                  <th className="text-right p-3 text-sm font-medium text-blue-600">PAC</th>
                  <th className="text-right p-3 text-sm font-medium text-green-600">ITE</th>
                </tr>
              </thead>
              <tbody>
                {stats?.by_departement && Object.entries(stats.by_departement).map(([dept, data]) => (
                  <tr key={dept} className="border-t hover:bg-slate-50">
                    <td className="p-3 font-mono font-bold text-slate-800">{dept}</td>
                    <td className="p-3 text-sm text-slate-600">{DEPT_NAMES[dept] || '-'}</td>
                    <td className="p-3 text-right font-bold">{data.total}</td>
                    <td className="p-3 text-right text-amber-600">{data.PV || 0}</td>
                    <td className="p-3 text-right text-blue-600">{data.PAC || 0}</td>
                    <td className="p-3 text-right text-green-600">{data.ITE || 0}</td>
                  </tr>
                ))}
                {(!stats?.by_departement || Object.keys(stats.by_departement).length === 0) && (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      Aucune donnée pour cette période
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Par Source */}
        <Card className="overflow-hidden">
          <div className="bg-slate-800 text-white px-4 py-3 flex items-center gap-2">
            <Globe className="w-5 h-5" />
            <h3 className="font-semibold">Par Source</h3>
          </div>
          <div className="max-h-[400px] overflow-y-auto">
            <table className="w-full">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="text-left p-3 text-sm font-medium text-slate-600">Source</th>
                  <th className="text-right p-3 text-sm font-medium text-slate-600">Total</th>
                  <th className="text-right p-3 text-sm font-medium text-amber-600">PV</th>
                  <th className="text-right p-3 text-sm font-medium text-blue-600">PAC</th>
                  <th className="text-right p-3 text-sm font-medium text-green-600">ITE</th>
                </tr>
              </thead>
              <tbody>
                {stats?.by_source && Object.entries(stats.by_source).map(([source, data]) => (
                  <tr key={source} className="border-t hover:bg-slate-50">
                    <td className="p-3">
                      <Badge variant="info">{source || 'Direct'}</Badge>
                    </td>
                    <td className="p-3 text-right font-bold">{data.total}</td>
                    <td className="p-3 text-right text-amber-600">{data.PV || 0}</td>
                    <td className="p-3 text-right text-blue-600">{data.PAC || 0}</td>
                    <td className="p-3 text-right text-green-600">{data.ITE || 0}</td>
                  </tr>
                ))}
                {(!stats?.by_source || Object.keys(stats.by_source).length === 0) && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-500">
                      Aucune donnée pour cette période
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Par Status */}
      <Card className="p-4">
        <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          Répartition par Status
        </h3>
        <div className="grid grid-cols-5 gap-4">
          {[
            { key: 'success', label: 'Envoyés', color: 'bg-green-500' },
            { key: 'duplicate', label: 'Doublons', color: 'bg-yellow-500' },
            { key: 'failed', label: 'Échoués', color: 'bg-red-500' },
            { key: 'no_crm', label: 'Sans CRM', color: 'bg-slate-500' },
            { key: 'queued', label: 'En queue', color: 'bg-blue-500' }
          ].map(s => (
            <div key={s.key} className="text-center p-4 bg-slate-50 rounded-xl">
              <div className={`w-4 h-4 ${s.color} rounded-full mx-auto mb-2`}></div>
              <p className="text-2xl font-bold text-slate-800">{stats?.by_status?.[s.key] || 0}</p>
              <p className="text-xs text-slate-500">{s.label}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
