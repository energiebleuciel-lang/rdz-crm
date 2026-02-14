import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API } from '../hooks/useApi';
import { Save, RefreshCw } from 'lucide-react';

export default function AdminSettings() {
  const { authFetch } = useAuth();
  const [denylist, setDenylist] = useState({ domains: [], simulation_mode: false, simulation_email: '' });
  const [calendar, setCalendar] = useState({ ZR7: { enabled_days: [0,1,2,3,4], disabled_dates: [] }, MDL: { enabled_days: [0,1,2,3,4], disabled_dates: [] } });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null);
  const [msg, setMsg] = useState('');

  const DAY_NAMES = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const [dlRes, calRes] = await Promise.all([
        authFetch(`${API}/api/settings/email-denylist`),
        authFetch(`${API}/api/settings/delivery-calendar`)
      ]);
      if (dlRes.ok) setDenylist(await dlRes.json());
      if (calRes.ok) setCalendar(await calRes.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const saveDenylist = async () => {
    setSaving('denylist');
    try {
      await authFetch(`${API}/api/settings/email-denylist`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(denylist)
      });
      setMsg('Denylist sauvegardee');
      setTimeout(() => setMsg(''), 2000);
    } catch (e) { console.error(e); }
    setSaving(null);
  };

  const saveCalendar = async (entity) => {
    setSaving(`calendar-${entity}`);
    try {
      await authFetch(`${API}/api/settings/delivery-calendar`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity, enabled_days: calendar[entity]?.enabled_days || [], disabled_dates: calendar[entity]?.disabled_dates || [] })
      });
      setMsg(`Calendar ${entity} sauvegardee`);
      setTimeout(() => setMsg(''), 2000);
    } catch (e) { console.error(e); }
    setSaving(null);
  };

  const toggleDay = (entity, day) => {
    setCalendar(prev => {
      const curr = prev[entity]?.enabled_days || [];
      const next = curr.includes(day) ? curr.filter(d => d !== day) : [...curr, day].sort();
      return { ...prev, [entity]: { ...prev[entity], enabled_days: next } };
    });
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div data-testid="admin-settings">
      <h1 className="text-lg font-semibold text-white mb-6">Settings</h1>
      {msg && <div className="mb-4 px-3 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-md text-xs text-emerald-400" data-testid="save-msg">{msg}</div>}

      <div className="space-y-6">
        {/* Email Denylist + Simulation */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="denylist-section">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Email Denylist & Simulation</h2>
            <button onClick={saveDenylist} disabled={saving === 'denylist'} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30 disabled:opacity-50" data-testid="save-denylist-btn">
              <Save className="w-3 h-3" /> Save
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-[10px] text-zinc-500 block mb-1">Domains (un par ligne)</label>
              <textarea
                value={(denylist.domains || []).join('\n')}
                onChange={e => setDenylist(d => ({ ...d, domains: e.target.value.split('\n').map(s => s.trim()).filter(Boolean) }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-xs text-zinc-300 resize-none font-mono"
                rows={4}
                data-testid="denylist-domains-input"
              />
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-[10px] text-zinc-500">Simulation Mode</label>
                <button onClick={() => setDenylist(d => ({ ...d, simulation_mode: !d.simulation_mode }))}
                  className={`w-8 h-4 rounded-full relative transition-colors ${denylist.simulation_mode ? 'bg-amber-500' : 'bg-zinc-700'}`} data-testid="simulation-mode-toggle">
                  <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${denylist.simulation_mode ? 'left-4' : 'left-0.5'}`} />
                </button>
                {denylist.simulation_mode && <span className="text-[10px] text-amber-400 font-medium">ON</span>}
              </div>

              {denylist.simulation_mode && (
                <div className="flex-1">
                  <input
                    value={denylist.simulation_email || ''}
                    onChange={e => setDenylist(d => ({ ...d, simulation_email: e.target.value }))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-xs text-zinc-300"
                    placeholder="Email de simulation"
                    data-testid="simulation-email-input"
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Delivery Calendar */}
        {['ZR7', 'MDL'].map(entity => (
          <div key={entity} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid={`calendar-section-${entity.toLowerCase()}`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${entity === 'ZR7' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>{entity}</span>
                <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Delivery Calendar</h2>
              </div>
              <button onClick={() => saveCalendar(entity)} disabled={saving === `calendar-${entity}`} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-teal-500/10 text-teal-400 rounded-md hover:bg-teal-500/20 border border-teal-500/30 disabled:opacity-50" data-testid={`save-calendar-${entity.toLowerCase()}-btn`}>
                <Save className="w-3 h-3" /> Save
              </button>
            </div>
            <div className="flex gap-2">
              {DAY_NAMES.map((name, i) => {
                const enabled = (calendar[entity]?.enabled_days || []).includes(i);
                return (
                  <button key={i} onClick={() => toggleDay(entity, i)}
                    className={`w-10 h-10 rounded-lg text-xs font-medium transition-colors ${
                      enabled ? 'bg-teal-500/20 text-teal-400 border border-teal-500/40' : 'bg-zinc-800 text-zinc-600 border border-zinc-700 hover:border-zinc-600'
                    }`} data-testid={`day-toggle-${entity.toLowerCase()}-${i}`}>
                    {name}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
