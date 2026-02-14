import { ChevronLeft, ChevronRight } from 'lucide-react';
import { weekKeyToLabel } from '../lib/weekUtils';

export function WeekNavStandard({ week, onChange }) {
  return (
    <div className="flex items-center gap-2" data-testid="week-nav">
      <button onClick={() => onChange(-1)} className="p-1.5 text-zinc-400 hover:text-white bg-zinc-800 border border-zinc-700 rounded-md hover:bg-zinc-700" data-testid="week-prev">
        <ChevronLeft className="w-3.5 h-3.5" />
      </button>
      <span className="text-xs text-zinc-300 min-w-[250px] text-center font-medium" data-testid="week-label">
        {weekKeyToLabel(week)}
      </span>
      <button onClick={() => onChange(1)} className="p-1.5 text-zinc-400 hover:text-white bg-zinc-800 border border-zinc-700 rounded-md hover:bg-zinc-700" data-testid="week-next">
        <ChevronRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
