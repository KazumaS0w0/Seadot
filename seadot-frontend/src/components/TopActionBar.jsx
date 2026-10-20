import { motion } from 'framer-motion';
import { Filter, Pause, Play, Plus, Search, Settings, Square, Trash2 } from 'lucide-react';

const ACTIONS = [
  { id: 'resume', label: 'Resume', icon: Play },
  { id: 'pause', label: 'Pause', icon: Pause },
  { id: 'stop', label: 'Stop', icon: Square },
  { id: 'remove', label: 'Remove', icon: Trash2 },
];

export default function TopActionBar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  selectedCount,
  onAction,
  onAddLink,
  onOpenSettings,
}) {
  return (
    <header className="action-bar flex shrink-0 flex-col items-stretch justify-between gap-3 border-b border-white/10 bg-[#0B0F19]/70 px-3 py-3 backdrop-blur-xl sm:px-5 lg:flex-row lg:items-center lg:gap-4">
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <motion.button
          type="button"
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={onAddLink}
          className="inline-flex shrink-0 flex-nowrap items-center gap-2 whitespace-nowrap rounded-xl bg-gradient-to-r from-violet-500 to-cyan-400 px-3 py-2.5 text-sm font-semibold text-white shadow-[0_0_18px_rgba(139,92,246,0.28)] sm:px-4"
        >
          <Plus className="h-4 w-4" />
          Add Link
        </motion.button>

        {ACTIONS.map((action) => {
          const Icon = action.icon;
          return (
            <motion.button
              key={action.id}
              type="button"
              title={action.label}
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.96 }}
              disabled={selectedCount === 0}
              onClick={() => onAction(action.id)}
              className="shrink-0 rounded-xl border border-white/10 bg-white/5 p-2 text-slate-300 transition hover:border-violet-400/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-35 sm:p-2.5"
            >
              <Icon className="h-4 w-4" />
            </motion.button>
          );
        })}

        <motion.button
          type="button"
          title="Options"
          whileHover={{ y: -1 }}
          whileTap={{ scale: 0.96 }}
          onClick={onOpenSettings}
          className="shrink-0 rounded-xl border border-white/10 bg-white/5 p-2 text-slate-300 transition hover:border-violet-400/30 hover:text-white sm:p-2.5"
        >
          <Settings className="h-4 w-4" />
        </motion.button>
      </div>

      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
        <div className="search-control flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-white/10 bg-[#0A0E17] px-2 py-2.5 text-slate-500 transition focus-within:border-violet-400/40 focus-within:ring-2 focus-within:ring-violet-500/15 sm:px-3">
          <Search className="h-4 w-4 shrink-0" />
          <input
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search files..."
            className="w-20 min-w-0 bg-transparent text-sm text-slate-200 placeholder:text-slate-500 outline-none sm:w-32 lg:w-64"
          />
        </div>

        <div className="flex shrink-0 items-center gap-1 rounded-xl border border-white/10 bg-white/5 px-2 py-2 text-slate-400 sm:gap-2 sm:px-3">
          <Filter className="h-4 w-4 shrink-0" />
          <select
            value={statusFilter}
            onChange={(event) => onStatusFilterChange(event.target.value)}
            className="status-filter max-w-20 bg-transparent text-xs text-slate-200 outline-none sm:max-w-none sm:text-sm"
          >
            <option value="all">All statuses</option>
            <option value="downloading">Downloading</option>
            <option value="paused">Paused</option>
            <option value="queued">Queued</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>
    </header>
  );
}
