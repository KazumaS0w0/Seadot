import { motion } from 'framer-motion';
import { useState } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  Clipboard,
  Clock,
  Download,
  File,
  FileImage,
  FileText,
  Gauge,
  Layers,
  List,
  Music2,
  Monitor,
  Moon,
  Package,
  Pause,
  Settings,
  Sun,
  Video,
} from 'lucide-react';
import { DOWNLOAD_CATEGORIES } from '../utils/format';

const NAV_ITEMS = [
  { id: 'all', label: 'All Downloads', icon: List },
  { id: 'downloading', label: 'In Progress', icon: Download },
  { id: 'completed', label: 'Completed', icon: CheckCircle2 },
  { id: 'queued', label: 'Queues', icon: Layers },
  { id: 'paused', label: 'Paused', icon: Pause },
  { id: 'history', label: 'History', icon: Clock },
];

const THEMES = [
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'auto', label: 'Auto', icon: Monitor },
];

const CATEGORY_ICONS = {
  applications: Package,
  videos: Video,
  music: Music2,
  documents: FileText,
  archives: Layers,
  images: FileImage,
  other: File,
};

export default function Sidebar({
  counts,
  activeCategory,
  onCategoryChange,
  activeFileCategory,
  onFileCategoryChange,
  fileCategoryCounts,
  clipboardEnabled,
  onClipboardToggle,
  onOpenSettings,
  theme,
  onThemeChange,
  bandwidthLimit,
}) {
  const [downloadCategoriesOpen, setDownloadCategoriesOpen] = useState(false);

  return (
    <motion.aside
      initial={{ x: -16, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="sidebar-shell flex h-full w-64 shrink-0 flex-col border-r border-white/10 bg-[#0B0F19]/80 backdrop-blur-xl"
    >
      <div className="flex items-center gap-3 border-b border-white/10 px-5 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-cyan-400 shadow-[0_0_20px_rgba(139,92,246,0.35)]">
          <Download className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-white">Seadot</h1>
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Download Manager</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = item.id === 'all'
            ? activeCategory === item.id && activeFileCategory === 'all'
            : activeCategory === item.id;
          const badge = counts[item.id] ?? 0;

          return (
            <div key={item.id}>
              <motion.button
                type="button"
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  onCategoryChange(item.id);
                  if (item.id === 'all') setDownloadCategoriesOpen((open) => !open);
                }}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-all ${
                  active
                    ? 'border border-violet-500/30 bg-violet-500/15 text-violet-200 shadow-[0_0_18px_rgba(139,92,246,0.16)]'
                    : 'border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  {item.label}
                </span>
                <span className="flex items-center gap-2">
                  <span
                    className={`min-w-6 rounded-full px-1.5 py-0.5 text-center text-[11px] font-semibold ${
                      active ? 'bg-violet-500 text-white' : 'bg-white/5 text-slate-400'
                    }`}
                  >
                    {badge}
                  </span>
                  {item.id === 'all' && (
                    <ChevronDown className={`h-3.5 w-3.5 transition-transform ${downloadCategoriesOpen ? 'rotate-180' : ''}`} />
                  )}
                </span>
              </motion.button>
              {item.id === 'all' && downloadCategoriesOpen && (
                <div className="ml-5 mt-1 space-y-1 border-l border-white/10 pl-2">
                  {DOWNLOAD_CATEGORIES.map((category) => {
                    const CategoryIcon = CATEGORY_ICONS[category.id];
                    const categoryActive = activeCategory === 'all' && activeFileCategory === category.id;
                    return (
                      <button
                        key={category.id}
                        type="button"
                        onClick={() => onFileCategoryChange(category.id)}
                        className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-xs transition ${
                          categoryActive
                            ? 'bg-violet-500/15 text-violet-200'
                            : 'text-slate-500 hover:bg-white/5 hover:text-slate-200'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <CategoryIcon className="h-3.5 w-3.5" />
                          {category.label}
                        </span>
                        <span>{fileCategoryCounts[category.id] || 0}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="space-y-3 border-t border-white/10 p-4">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">Settings</p>

        <div className="sidebar-setting-card rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
            <Gauge className="h-3.5 w-3.5" />
            Bandwidth limiter
          </div>
          <p className="text-sm font-medium text-slate-200">
            {bandwidthLimit === 0 ? 'Unlimited' : `${bandwidthLimit} MB/s`}
          </p>
        </div>

        <div className="theme-picker flex gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
          {THEMES.map((item) => {
            const Icon = item.icon;
            const active = theme === item.id;
            return (
              <button
                key={item.id}
                type="button"
                title={item.id === 'auto' ? 'Follow the Windows appearance setting' : `${item.label} theme`}
                onClick={() => onThemeChange(item.id)}
                className={`flex flex-1 items-center justify-center gap-1 rounded-lg px-2 py-1.5 text-[11px] transition-all ${
                  active ? 'bg-violet-500/20 text-violet-200' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                <Icon className="h-3 w-3" />
                {item.label}
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onClipboardToggle}
          className={`sidebar-utility flex w-full items-center justify-between rounded-xl border px-3 py-3 text-sm transition-all ${
            clipboardEnabled
              ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
              : 'border-white/10 bg-white/5 text-slate-400 hover:border-white/20'
          }`}
        >
          <span className="flex items-center gap-2">
            <Clipboard className="h-4 w-4" />
            Clipboard Listener
          </span>
          <span
            className={`relative h-5 w-9 rounded-full transition-colors ${
              clipboardEnabled ? 'bg-emerald-400' : 'bg-slate-600'
            }`}
          >
            <motion.span
              layout
              className="absolute top-0.5 h-4 w-4 rounded-full bg-white"
              animate={{ left: clipboardEnabled ? 18 : 2 }}
              transition={{ type: 'spring', stiffness: 400, damping: 28 }}
            />
          </span>
        </button>

        <motion.button
          type="button"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          onClick={onOpenSettings}
          className="flex w-full items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-slate-300 hover:border-violet-500/30 hover:text-white"
        >
          <Settings className="h-4 w-4" />
          Open options
        </motion.button>
      </div>
    </motion.aside>
  );
}
