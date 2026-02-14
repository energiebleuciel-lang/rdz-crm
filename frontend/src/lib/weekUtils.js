/**
 * Week utilities — standardized across the CRM
 * Internal: YYYY-W## (ISO week key)
 * Display: "Semaine du DD/MM/YYYY au DD/MM/YYYY"
 */

export function getCurrentWeekKey() {
  const d = new Date();
  const thu = new Date(d);
  thu.setUTCDate(thu.getUTCDate() + 3 - ((thu.getUTCDay() + 6) % 7));
  const yr = thu.getUTCFullYear();
  const wn = 1 + Math.round(((thu - new Date(Date.UTC(yr, 0, 4))) / 86400000 - 3 + ((new Date(Date.UTC(yr, 0, 4)).getUTCDay() + 6) % 7)) / 7);
  return `${yr}-W${String(wn).padStart(2, '0')}`;
}

export function shiftWeekKey(wk, dir) {
  const [y, w] = wk.split('-W').map(Number);
  const dt = new Date(Date.UTC(y, 0, 4));
  dt.setUTCDate(dt.getUTCDate() - dt.getUTCDay() + 1 + (w - 1) * 7 + dir * 7);
  const thu = new Date(dt);
  thu.setUTCDate(thu.getUTCDate() + 3 - ((thu.getUTCDay() + 6) % 7));
  const yr = thu.getUTCFullYear();
  const wn = 1 + Math.round(((thu - new Date(Date.UTC(yr, 0, 4))) / 86400000 - 3 + ((new Date(Date.UTC(yr, 0, 4)).getUTCDay() + 6) % 7)) / 7);
  return `${yr}-W${String(wn).padStart(2, '0')}`;
}

/** Parse YYYY-W## → { start: Date (Monday), end: Date (Sunday) } */
export function weekKeyToDates(wk) {
  const [y, w] = wk.split('-W').map(Number);
  const jan4 = new Date(Date.UTC(y, 0, 4));
  const monday = new Date(jan4);
  monday.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() + 6) % 7) + (w - 1) * 7);
  const sunday = new Date(monday);
  sunday.setUTCDate(monday.getUTCDate() + 6);
  return { start: monday, end: sunday };
}

function pad(n) { return String(n).padStart(2, '0'); }
function fmtDate(d) { return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()}`; }

/** "Semaine du 10/02/2026 au 16/02/2026" */
export function weekKeyToLabel(wk) {
  const { start, end } = weekKeyToDates(wk);
  return `Semaine du ${fmtDate(start)} au ${fmtDate(end)}`;
}

/** Short: "10/02 – 16/02" */
export function weekKeyToShort(wk) {
  const { start, end } = weekKeyToDates(wk);
  return `${pad(start.getUTCDate())}/${pad(start.getUTCMonth() + 1)} – ${pad(end.getUTCDate())}/${pad(end.getUTCMonth() + 1)}`;
}

// ═══════════════════════════════════════════════════
// Month utilities
// ═══════════════════════════════════════════════════

const MONTH_NAMES_FR = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

/** Current month key "YYYY-MM" */
export function getCurrentMonthKey() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

/** Shift month by dir (+1 / -1) */
export function shiftMonthKey(mk, dir) {
  const [y, m] = mk.split('-').map(Number);
  const d = new Date(Date.UTC(y, m - 1 + dir, 1));
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}`;
}

/** "Février 2026" */
export function monthKeyToLabel(mk) {
  const [y, m] = mk.split('-').map(Number);
  return `${MONTH_NAMES_FR[m - 1]} ${y}`;
}
