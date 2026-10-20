import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Download, 
  Play, 
  Pause, 
  StopCircle, 
  Trash2, 
  Settings, 
  Clipboard, 
  Search, 
  Filter, 
  CheckCircle2, 
  Clock, 
  Zap,
  FileVideo,
  FileArchive,
  FileImage,
  FileType
} from 'lucide-react';

// Modern Download Manager - Seadot Desktop Client
export default function App() {
  const [activeTab, setActiveTab] = useState('in-progress');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [clipboardEnabled, setClipboardEnabled] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [items, setItems] = useState([
    {
      id: 1,
      name: 'Seadot_Setup.mp4',
      size: '256.7 MB',
      progress: 79.5,
      speed: '8.2 MB/s',
      eta: '12s',
      dateAdded: '2026-10-18',
      status: 'downloading',
      icon: FileVideo,
      url: 'https://example.com/video.mp4'
    },
    {
      id: 2,
      name: 'project_files.zip',
      size: '1.2 GB',
      progress: 37.8,
      speed: '12.5 MB/s',
      eta: '45s',
      dateAdded: '2026-10-18',
      status: 'downloading',
      icon: FileArchive,
      url: 'https://example.com/files.zip'
    },
    {
      id: 3,
      name: 'banner_design.png',
      size: '45.2 MB',
      progress: 100,
      speed: '0 MB/s',
      eta: 'Completed',
      dateAdded: '2026-10-18',
      status: 'completed',
      icon: FileImage,
      url: 'https://example.com/banner.png'
    }
  ]);

  // Progress bar gradient component
  const ProgressBar = ({ progress }) => (
    <div className="relative h-2 bg-gray-700/50 rounded-full overflow-hidden backdrop-blur-sm">
      <motion.div
        className="absolute left-0 top-0 h-full rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
      >
        <div className={`h-full gradient-${getProgressColor(progress)} bg-gradient-to-r from-current via-current to-current opacity-80`}>
          {progress === 100 ? (
            <div className="w-full h-full flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
          ) : null}
        </div>
      </motion.div>
      {progress < 100 && (
        <motion.div
          className="absolute inset-0 border-l border-r border-white/10"
          initial={{ x: '-100%' }}
          animate={{ x: `-${100 - progress}%` }}
          transition={{ duration: 0.2, ease: "linear" }}
        />
      )}
    </div>
  );

  // Status badge component
  const StatusBadge = ({ status }) => {
    const getStatusStyle = () => {
      switch (status) {
        case 'downloading':
          return 'bg-violet-500/20 text-violet-300 border-violet-500/30';
        case 'paused':
          return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
        case 'completed':
          return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
        default:
          return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
      }
    };

    const getStatusIcon = () => {
      switch (status) {
        case 'downloading':
          return <Download className="w-3 h-3" />;
        case 'paused':
          return <Pause className="w-3 h-3" />;
        case 'completed':
          return <CheckCircle2 className="w-3 h-3" />;
        default:
          return null;
      }
    };

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm ${getStatusStyle()}`}>
        {getStatusIcon()}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  // Sidebar navigation item
  const NavItem = ({ icon: Icon, label, id, badge }) => (
    <motion.button
      whileHover={{ scale: 1.02, backgroundColor: 'rgba(30, 41, 59, 0.8)' }}
      whileTap={{ scale: 0.98 }}
      onClick={() => setActiveTab(id)}
      className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 ${
        activeTab === id
          ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
          : 'text-gray-400 hover:border-violet-500/20'
      }`}
    >
      <div className="flex items-center gap-3">
        <Icon className={`w-5 h-5 ${activeTab === id ? 'text-violet-300' : 'text-gray-400'}`} />
        <span className="font-medium">{label}</span>
      </div>
      {badge > 0 && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="flex items-center justify-center w-6 h-6 text-xs font-bold bg-violet-500 text-white rounded-full shadow-lg shadow-violet-500/20"
        >
          {badge}
        </motion.span>
      )}
    </motion.button>
  );

  // Main download row component
  const DownloadRow = ({ item }) => (
    <motion.tr
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ backgroundColor: 'rgba(30, 41, 59, 0.5)' }}
      className="group cursor-pointer border-b border-gray-700/30 hover:border-violet-500/30 transition-colors duration-200"
    >
      <td className="p-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-700/50 flex items-center justify-center border border-gray-600/50 group-hover:border-violet-500/50 transition-colors">
            <item.icon className="w-4 h-4 text-violet-300" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-200 truncate">{item.name}</p>
            <StatusBadge status={item.status} />
          </div>
        </div>
      </td>
      
      <td className="p-4 text-right font-mono text-gray-300">
        {item.size}
      </td>
      
      <td className="p-4">
        <ProgressBar progress={item.progress} />
        <div className="mt-1 flex items-center justify-end gap-2 text-xs text-gray-400 font-mono">
          <span>{Math.round(item.progress)}%</span>
          {item.speed !== '0 MB/s' && (
            <>
              <Zap className="w-3 h-3 text-violet-400" />
              <span>@ {item.speed}</span>
            </>
          )}
        </div>
      </td>
      
      <td className="p-4 text-right font-mono text-gray-300">
        {item.eta}
      </td>
      
      <td className="p-4 text-right font-mono text-gray-300 hidden md:table-cell">
        {item.speed}
      </td>
      
      <td className="p-4 text-right text-gray-300 hidden lg:table-cell">
        {item.dateAdded}
      </td>
    </motion.tr>
  );

  // Stats card component
  const StatsCard = ({ label, value, icon: Icon, color }) => (
    <div className="bg-gray-800/40 backdrop-blur-sm rounded-xl p-4 border border-gray-700/30">
      <div className="flex items-center gap-3 mb-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-xs text-gray-400 font-medium">{label}</span>
      </div>
      <p className="text-xl font-bold text-gray-100">{value}</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0B0F19] via-[#0D1221] to-[#0A0E17] text-gray-100">
      {/* Main Container */}
      <div className="flex h-screen overflow-hidden">
        
        {/* Sidebar - Left Panel */}
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: isSidebarOpen ? 240 : 0, opacity: 1 }}
          className="bg-gray-900/80 backdrop-blur-xl border-r border-gray-700/30 flex-shrink-0 overflow-hidden"
        >
          <div className="flex flex-col h-full">
            {/* Sidebar Header */}
            <div className="p-5 border-b border-gray-700/30">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                  <Download className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold bg-gradient-to-r from-violet-300 to-indigo-300 bg-clip-text text-transparent">
                    Seadot
                  </h1>
                  <p className="text-xs text-gray-500">Download Manager</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 overflow-y-auto">
              <div className="space-y-2">
                <NavItem icon={CheckCircle2} label="All Downloads" id="all" badge={items.length} />
                <NavItem icon={Download} label="In Progress" id="in-progress" badge={items.filter(i => i.status === 'downloading').length} />
                <NavItem icon={Clock} label="Completed" id="completed" badge={items.filter(i => i.status === 'completed').length} />
                <NavItem icon={Play} label="Queued" id="queued" badge={0} />
              </div>

              {/* Divider */}
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-700/30"></div>
                </div>
                <div className="relative px-4 text-xs text-gray-500 bg-gray-900/80">
                  Settings
                </div>
              </div>

              {/* Quick Settings Panel */}
              <div className="space-y-3 pt-2">
                <button
                  onClick={() => setClipboardEnabled(!clipboardEnabled)}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all ${
                    clipboardEnabled 
                      ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30' 
                      : 'bg-gray-800/40 text-gray-400 border border-gray-700/30 hover:border-gray-600/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Clipboard className="w-5 h-5" />
                    <span className="font-medium text-sm">Clipboard Listener</span>
                  </div>
                  <motion.div
                    animate={{ scale: clipboardEnabled ? 1 : 0 }}
                    className={`w-10 h-5 rounded-full border-2 transition-colors ${
                      clipboardEnabled ? 'bg-emerald-500 border-emerald-500' : 'bg-gray-600 border-gray-600'
                    }`}
                  >
                    <motion.div
                      animate={{ x: clipboardEnabled ? 24 : 4 }}
                      className="w-3 h-3 rounded-full bg-white mt-1"
                    />
                  </motion.div>
                </button>

                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-800/40 text-gray-400 border border-gray-700/30 hover:bg-gray-800/60 hover:border-gray-600/50 transition-all">
                  <Settings className="w-5 h-5" />
                  <span className="font-medium text-sm">Bandwidth Limiter</span>
                </button>
              </div>

              {/* Theme Toggle */}
              <div className="pt-4 space-y-2">
                <p className="px-4 text-xs text-gray-500 mb-2 font-medium">Theme</p>
                <div className="space-y-2">
                  {['dark', 'light', 'auto'].map((theme) => (
                    <button
                      key={theme}
                      onClick={() => console.log(`Switch to ${theme} theme`)}
                      className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl transition-all text-sm ${
                        theme === 'dark'
                          ? 'bg-violet-500/10 text-violet-300 border border-violet-500/30'
                          : 'text-gray-400 hover:bg-gray-800/40 border border-transparent'
                      }`}
                    >
                      <span className="capitalize">{theme}</span>
                      {theme === 'dark' && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="w-1.5 h-1.5 rounded-full bg-violet-400"
                        />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </nav>

            {/* Sidebar Footer */}
            <div className="p-4 border-t border-gray-700/30">
              <button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gray-800/40 text-gray-400 border border-gray-700/30 hover:bg-gray-800/60 transition-all text-sm font-medium"
              >
                <svg className={`w-5 h-5 transition-transform ${isSidebarOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                {isSidebarOpen ? 'Collapse' : 'Expand'}
              </button>
            </div>
          </div>
        </motion.aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          
          {/* Top Action Bar */}
          <header className="bg-gray-900/60 backdrop-blur-xl border-b border-gray-700/30 px-6 py-4 flex-shrink-0">
            <div className="flex items-center justify-between gap-4">
              
              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-600 text-white font-medium shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 transition-shadow"
                >
                  <PlusIcon />
                  <span>Add Link</span>
                </motion.button>

                <button className="p-2.5 rounded-xl bg-gray-800/60 text-gray-300 border border-gray-700/30 hover:bg-gray-800 hover:text-white transition-all">
                  <Play className="w-4 h-4" />
                </button>

                <button className="p-2.5 rounded-xl bg-gray-800/60 text-gray-300 border border-gray-700/30 hover:bg-gray-800 hover:text-white transition-all">
                  <Pause className="w-4 h-4" />
                </button>

                <button className="p-2.5 rounded-xl bg-gray-800/60 text-gray-300 border border-gray-700/30 hover:bg-gray-800 hover:text-white transition-all">
                  <StopCircle className="w-4 h-4" />
                </button>

                <button className="p-2.5 rounded-xl bg-gray-800/60 text-gray-300 border border-gray-700/30 hover:bg-gray-800 hover:text-white transition-all">
                  <Trash2 className="w-4 h-4" />
                </button>

                <button className="p-2.5 rounded-xl bg-gray-800/60 text-gray-300 border border-gray-700/30 hover:bg-gray-800 hover:text-white transition-all">
                  <Settings className="w-4 h-4" />
                </button>
              </div>

              {/* Search & Filter */}
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search files..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-64 pl-10 pr-4 py-2.5 rounded-xl bg-gray-800/60 border border-gray-700/30 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/10 transition-all"
                  />
                </div>

                <button className="p-2.5 rounded-xl bg-gray-800/60 text-gray-300 border border-gray-700/30 hover:bg-gray-800 hover:text-white transition-all">
                  <Filter className="w-4 h-4" />
                </button>

                {/* Tab Navigation */}
                <div className="flex items-center gap-1 ml-2">
                  {['all', 'downloading', 'paused', 'completed'].map((tab) => (
                    <motion.button
                      key={tab}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setActiveTab(tab)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        activeTab === tab
                          ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                          : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-transparent'
                      }`}
                    >
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </motion.button>
                  ))}
                </div>
              </div>

            </div>
          </header>

          {/* Main Table Area */}
          <div className="flex-1 overflow-auto p-6">
            <div className="bg-gray-900/40 backdrop-blur-sm rounded-2xl border border-gray-700/30 shadow-2xl">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700/30">
                    <th className="p-4 text-left font-semibold text-gray-300 w-64">File</th>
                    <th className="p-4 text-right font-semibold text-gray-300 w-32">Size</th>
                    <th className="p-4 font-semibold text-gray-300 w-48">Progress</th>
                    <th className="p-4 text-right font-semibold text-gray-300 w-32 hidden md:table-cell">Time Left</th>
                    <th className="p-4 text-right font-semibold text-gray-300 w-32 hidden md:table-cell">Speed</th>
                    <th className="p-4 text-right font-semibold text-gray-300 hidden lg:table-cell">Date Added</th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence mode="popLayout">
                    {items.filter(item => 
                      item.name.toLowerCase().includes(searchQuery.toLowerCase())
                    ).map((item) => (
                      <DownloadRow key={item.id} item={item} />
                    ))}
                  </AnimatePresence>
                  
                  {/* Empty State */}
                  {items.filter(item => 
                    item.name.toLowerCase().includes(searchQuery.toLowerCase())
                  ).length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-12 text-center">
                        <div className="flex flex-col items-center justify-center gap-3">
                          <div className="w-16 h-16 rounded-2xl bg-gray-800/60 border border-gray-700/30 flex items-center justify-center">
                            <Download className="w-8 h-8 text-gray-500" />
                          </div>
                          <p className="text-gray-400 font-medium">No downloads found</p>
                          <p className="text-sm text-gray-500 max-w-md text-center">
                            Add a download link to get started. Use the + button above or enable clipboard listener for automatic capture.
                          </p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </main>

        {/* Status Bar dengan Wave Visualizer */}
        <footer className="bg-gray-900/80 backdrop-blur-xl border-t border-gray-700/30 px-6 py-2 flex-shrink-0">
          <div className="flex items-center justify-between gap-4">
            {/* Total Speed with Wave Visualizer */}
            <div className="flex items-center gap-3">
              <div className="relative w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20 border border-violet-500/30 flex items-center justify-center overflow-hidden">
                {/* Wave Visualizer - Animasi gelombang aktif */}
                <motion.div
                  className="absolute inset-0 flex items-end justify-center gap-0.5 pb-1"
                  animate={{ 
                    y: [0, -2, 0],
                    opacity: [0.3, 0.6, 0.3]
                  }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                >
                  {[...Array(8)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="w-1 rounded-full"
                      animate={{ 
                        height: [6, 12 + Math.sin(i * 0.5) * 4, 6],
                        opacity: [0.4, 0.8, 0.4]
                      }}
                      transition={{ 
                        duration: 1,
                        repeat: Infinity, 
                        ease: "easeInOut",
                        delay: i * 0.1
                      }}
                      style={{
                        backgroundColor: `hsla(${265 - i * 10}, 80%, 60%, 0.6)`,
                        borderRadius: '4px'
                      }}
                    />
                  ))}
                </motion.div>
                
                {/* Total Speed Display */}
                <div className="relative z-10 text-center">
                  <p className="text-xs text-gray-400 font-medium">Total</p>
                  <p className="text-sm font-bold text-violet-300">{calculateTotalSpeed().toFixed(1)} MB/s</p>
                </div>
              </div>
              
              <div className="flex flex-col gap-1">
                <span className="text-xs text-gray-400 font-medium">Download Speed</span>
                <span className="text-sm text-gray-200 font-medium">{calculateTotalSpeed().toFixed(1)} MB/s</span>
              </div>
            </div>

            {/* Active Downloads Count */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-800/60 border border-gray-700/30 flex items-center justify-center">
                <Download className="w-4 h-4 text-violet-400" />
              </div>
              <span className="text-sm text-gray-300 font-medium">
                {items.filter(i => i.status === 'downloading').length} Active
              </span>
            </div>

            {/* Total Progress */}
            <div className="flex items-center gap-4">
              <div className="text-right">
                <span className="text-xs text-gray-400 font-medium">Total Down</span>
                <p className="text-sm text-violet-300 font-bold">
                  {formatBytes(calculateTotalDownloaded())} / {formatBytes(calculateTotalSize())}
                </p>
              </div>
              
              {/* Mini Progress Bar */}
              <div className="w-24 h-1.5 rounded-full bg-gray-800/60 border border-gray-700/30 overflow-hidden flex-shrink-0">
                <motion.div
                  className="h-full bg-gradient-to-r from-violet-500 to-indigo-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${calculateTotalProgress()}%` }}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                />
              </div>
            </div>

          </div>
        </footer>
      </div>
    </div>
  );
}

// Custom Plus Icon component
const PlusIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
  </svg>
);

// Helper function to get progress bar gradient color
function getProgressColor(progress) {
  if (progress >= 100) return 'emerald';
  if (progress >= 75) return 'blue';
  if (progress >= 50) return 'violet';
  return 'indigo';
}

// Helper functions for Status Bar calculations
function calculateTotalSpeed() {
  let total = 0;
  items.forEach(item => {
    const speedMatch = item.speed?.match(/(\d+.\d+)\s*MB\/s/);
    if (speedMatch) {
      total += parseFloat(speedMatch[1]);
    }
  });
  return total;
}

function calculateTotalDownloaded() {
  let total = 0;
  items.forEach(item => {
    const sizeMatch = item.size?.match(/(\d+.\d+)\s*(MB|GB)/);
    if (sizeMatch) {
      const value = parseFloat(sizeMatch[1]);
      const unit = sizeMatch[2];
      total += unit === 'GB' ? value * 1024 : value;
      total *= item.progress / 100;
    }
  });
  return total;
}

function calculateTotalSize() {
  let total = 0;
  items.forEach(item => {
    const sizeMatch = item.size?.match(/(\d+.\d+)\s*(MB|GB)/);
    if (sizeMatch) {
      const value = parseFloat(sizeMatch[1]);
      const unit = sizeMatch[2];
      total += unit === 'GB' ? value * 1024 : value;
    }
  });
  return total;
}

function calculateTotalProgress() {
  if (calculateTotalSize() === 0) return 0;
  return (calculateTotalDownloaded() / calculateTotalSize()) * 100;
}

function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 MB';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['MB', 'KB'];
  const i = -1 < Math.floor(Math.log(bytes) / Math.log(k)) ? -1 : 0;
  return (bytes / Math.pow(k, i)).toFixed(dm) + ' ' + sizes[i];
}