import { useCallback, useEffect, useMemo, useState } from 'react';
import AddLinkModal from './components/AddLinkModal';
import DeleteDownloadsModal from './components/DeleteDownloadsModal';
import DetachedDownloadWindow from './components/DetachedDownloadWindow';
import DownloadDetailsModal from './components/DownloadDetailsModal';
import DownloadTable from './components/DownloadTable';
import SettingsPanel from './components/SettingsPanel';
import Sidebar from './components/Sidebar';
import StatusBar from './components/StatusBar';
import TopActionBar from './components/TopActionBar';
import { INITIAL_DOWNLOADS } from './data/mockDownloads';
import { categoryForFilename, extractUrl, filenameFromUrl } from './utils/format';

function matchesCategory(item, category) {
  if (category === 'all') return true;
  if (category === 'history') return item.status === 'completed';
  return item.status === category;
}

function nextStatus(action, current) {
  if (action === 'pause') return 'paused';
  if (action === 'resume') return current === 'completed' ? current : 'downloading';
  if (action === 'stop') return 'queued';
  return current;
}

function MainApp() {
  const [downloads, setDownloads] = useState(INITIAL_DOWNLOADS);
  const [activeCategory, setActiveCategory] = useState('all');
  const [activeFileCategory, setActiveFileCategory] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [clipboardEnabled, setClipboardEnabled] = useState(false);
  const [theme, setTheme] = useState(() => {
    const savedTheme = window.localStorage.getItem('seadot-theme');
    return ['dark', 'light', 'auto'].includes(savedTheme) ? savedTheme : 'dark';
  });
  const [systemLight, setSystemLight] = useState(
    typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: light)').matches,
  );
  const [bandwidthLimit, setBandwidthLimit] = useState(0);
  const [isFirstRun] = useState(
    () => window.localStorage.getItem('seadot-extension-onboarding-seen') !== 'true',
  );
  const [settingsOpen, setSettingsOpen] = useState(isFirstRun);
  const [addLinkOpen, setAddLinkOpen] = useState(false);
  const [selectedDownload, setSelectedDownload] = useState(null);
  const [detailsMinimized, setDetailsMinimized] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteWorking, setDeleteWorking] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [pendingUrl, setPendingUrl] = useState('');
  const [toast, setToast] = useState('');
  const [downloadFolders, setDownloadFolders] = useState([]);
  const [downloadFoldersError, setDownloadFoldersError] = useState('');

  useEffect(() => {
    if (isFirstRun) {
      window.localStorage.setItem('seadot-extension-onboarding-seen', 'true');
    }
  }, [isFirstRun]);

  useEffect(() => {
    if (!addLinkOpen && downloadFolders.length > 0) return undefined;

    let cancelled = false;
    const loadDownloadFolders = async () => {
      setDownloadFoldersError('');
      try {
        const response = await fetch('/api/downloads/categories');
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
        if (!cancelled) setDownloadFolders(result.categories);
      } catch (error) {
        if (!cancelled) setDownloadFoldersError(`Tidak dapat memuat folder unduhan: ${error.message}`);
      }
    };

    loadDownloadFolders();
    return () => {
      cancelled = true;
    };
  }, [addLinkOpen, downloadFolders.length]);

  useEffect(() => {
    window.localStorage.setItem('seadot-theme', theme);
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: light)');
    const onChange = (event) => setSystemLight(event.matches);
    if (media.addEventListener) {
      media.addEventListener('change', onChange);
      return () => media.removeEventListener('change', onChange);
    }

    media.addListener(onChange);
    return () => media.removeListener(onChange);
  }, []);

  const resolvedTheme = theme === 'auto' ? (systemLight ? 'light' : 'dark') : theme;

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.classList.toggle('light', resolvedTheme === 'light');
  }, [resolvedTheme]);

  useEffect(() => {
    if (!clipboardEnabled) return undefined;

    const capture = (text) => {
      const url = extractUrl(text);
      if (!url) return;
      setPendingUrl(url);
      setAddLinkOpen(true);
      setToast('Clipboard URL captured');
    };

    const onPaste = (event) => capture(event.clipboardData?.getData('text') || '');
    window.addEventListener('paste', onPaste);

    let timer;
    if (navigator.clipboard?.readText) {
      timer = window.setInterval(async () => {
        try {
          const text = await navigator.clipboard.readText();
          if (extractUrl(text) && text !== pendingUrl) capture(text);
        } catch {
          /* Clipboard polling requires focus/permission; paste handler still works. */
        }
      }, 2500);
    }

    return () => {
      window.removeEventListener('paste', onPaste);
      if (timer) window.clearInterval(timer);
    };
  }, [clipboardEnabled, pendingUrl]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(''), 2200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const counts = useMemo(
    () => ({
      all: downloads.length,
      downloading: downloads.filter((item) => item.status === 'downloading').length,
      completed: downloads.filter((item) => item.status === 'completed').length,
      queued: downloads.filter((item) => item.status === 'queued').length,
      paused: downloads.filter((item) => item.status === 'paused').length,
      history: downloads.filter((item) => item.status === 'completed').length,
    }),
    [downloads],
  );

  const fileCategoryCounts = useMemo(
    () => downloads.reduce((categoryCounts, item) => {
      const category = item.category || categoryForFilename(item.name);
      categoryCounts[category] = (categoryCounts[category] || 0) + 1;
      return categoryCounts;
    }, {}),
    [downloads],
  );

  const visibleDownloads = useMemo(
    () =>
      downloads.filter((item) => {
        const byCategory = matchesCategory(item, activeCategory);
        const fileCategory = item.category || categoryForFilename(item.name);
        const byFileCategory = activeCategory !== 'all'
          || activeFileCategory === 'all'
          || fileCategory === activeFileCategory;
        const byStatus = statusFilter === 'all' || item.status === statusFilter;
        const bySearch = item.name.toLowerCase().includes(searchQuery.trim().toLowerCase());
        return byCategory && byFileCategory && byStatus && bySearch;
      }),
    [downloads, activeCategory, activeFileCategory, statusFilter, searchQuery],
  );

  const totalSpeed = downloads
    .filter((item) => item.status === 'downloading')
    .reduce((sum, item) => sum + item.speedBps, 0);

  const openAddLink = (url = '') => {
    const api = window.pywebview?.api;
    if (api?.open_download_confirmation) {
      api.open_download_confirmation(url).catch((error) => {
        setToast(`Tidak dapat membuka jendela unduhan: ${error.message}`);
      });
      return;
    }
    setPendingUrl(url);
    setAddLinkOpen(true);
  };

  useEffect(() => {
    let disposed = false;
    const syncDownloads = async () => {
      try {
        const response = await fetch('/api/downloads');
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
        if (disposed) return;
        const serverDownloads = result.downloads.map((record) => {
          const name = record.dest_path?.split(/[\\/]/).pop() || record.filename || 'Download';
          return {
            id: record.download_id || record.id,
            name,
            sizeBytes: record.total_size || 0,
            downloadedBytes: record.downloaded_size || 0,
            progress: record.progress || 0,
            speedBps: record.speed || 0,
            etaSeconds: record.eta ?? null,
            dateAdded: record.created_at?.slice(0, 16).replace('T', ' ') || '',
            status: record.status || 'queued',
            url: record.url,
            destPath: record.dest_path,
            category: categoryForFilename(name),
            splitCount: record.split_count || 4,
            speedLimitBps: record.speed_limit_bps || 0,
            completionAction: record.completion_action || 'none',
            countdownMinutes: record.countdown_minutes || 2,
          };
        });
        setDownloads((current) => {
          const byId = new Map(serverDownloads.map((item) => [item.id, item]));
          return current.map((item) => byId.get(item.id) || item)
            .concat(serverDownloads.filter((item) => !current.some((existing) => existing.id === item.id)));
        });
      } catch (error) {
        if (!disposed) console.error(`Could not sync downloads from backend: ${error.message}`);
      }
    };

    syncDownloads();
    window.addEventListener('focus', syncDownloads);
    return () => {
      disposed = true;
      window.removeEventListener('focus', syncDownloads);
    };
  }, []);

  const addDownload = async (url, name, category, destinationFolder, splitCount, conflictPolicy) => {
    const filename = name || filenameFromUrl(url);
    const response = await fetch('/api/downloads/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        filename,
        category,
        destination_folder: destinationFolder,
        split_count: splitCount,
        conflict_policy: conflictPolicy,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(
        typeof result.detail === 'string' ? result.detail : `HTTP ${response.status}`,
      );
      error.status = response.status;
      throw error;
    }

    setDownloads((current) => [
      {
        id: result.download_id,
        name: result.filename,
        sizeBytes: 0,
        progress: 0,
        speedBps: 0,
        etaSeconds: null,
        dateAdded: new Date().toISOString().slice(0, 16).replace('T', ' '),
        status: 'downloading',
        url: result.url,
        category: result.category || categoryForFilename(filename),
        destPath: result.dest_path,
        splitCount: result.split_count,
        speedLimitBps: 0,
        completionAction: 'none',
      },
      ...current,
    ]);
    setSelectedDownload({
      id: result.download_id,
      name: result.filename,
      sizeBytes: 0,
      downloadedBytes: 0,
      progress: 0,
      speedBps: 0,
      etaSeconds: null,
      dateAdded: new Date().toISOString().slice(0, 16).replace('T', ' '),
      status: 'downloading',
      url: result.url,
      category: result.category || categoryForFilename(filename),
      destPath: result.dest_path,
      splitCount: result.split_count,
      speedLimitBps: 0,
      completionAction: 'none',
    });
    setDetailsMinimized(false);
    setAddLinkOpen(false);
    setPendingUrl('');
    setActiveCategory('all');
    setToast(`Download started: ${result.dest_path}`);
  };

  const updateDownload = useCallback((updated) => {
    setDownloads((current) => current.map((item) => (
      item.id === updated.id ? { ...item, ...updated } : item
    )));
    setSelectedDownload((current) => (
      current?.id === updated.id ? { ...current, ...updated } : current
    ));
  }, []);

  const updateDownloadOptions = async (downloadId, options) => {
    const response = await fetch(`/api/downloads/${encodeURIComponent(downloadId)}/options`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    updateDownload({
      id: downloadId,
      speedLimitBps: result.speed_limit_bps,
      splitCount: result.split_count,
      completionAction: result.completion_action,
      countdownMinutes: result.countdown_minutes,
    });
  };

  const cancelDownload = useCallback((downloadId) => {
    setDownloads((current) => current.filter((item) => item.id !== downloadId));
    setSelectedDownload((current) => (current?.id === downloadId ? null : current));
    setSelectedIds((current) => current.filter((id) => id !== downloadId));
    setDetailsMinimized(false);
  }, []);

  const applyAction = (action) => {
    if (selectedIds.length === 0) return;
    if (action === 'remove') {
      setDeleteError('');
      setDeleteDialogOpen(true);
      return;
    }
    setDownloads((current) =>
      current.map((item) => {
        if (!selectedIds.includes(item.id)) return item;
        const status = nextStatus(action, item.status);
        return {
          ...item,
          status,
          speedBps: status === 'downloading' ? item.speedBps || 2 * 1024 * 1024 : 0,
        };
      }),
    );
  };

  const deleteSelectedDownloads = async (deleteFile) => {
    setDeleteWorking(true);
    setDeleteError('');
    const succeeded = [];
    const failures = [];
    const selected = downloads.filter((item) => selectedIds.includes(item.id));

    for (const item of selected) {
      if (item.id.startsWith('dl-')) {
        succeeded.push(item.id);
        continue;
      }

      try {
        const response = await fetch(
          `/api/downloads/${encodeURIComponent(item.id)}?delete_file=${deleteFile}`,
          { method: 'DELETE' },
        );
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || `HTTP ${response.status}`);
        }
        succeeded.push(item.id);
      } catch (error) {
        failures.push(`${item.name}: ${error.message}`);
      }
    }

    if (succeeded.length) {
      setDownloads((current) => current.filter((item) => !succeeded.includes(item.id)));
      setSelectedIds((current) => current.filter((id) => !succeeded.includes(id)));
      if (selectedDownload && succeeded.includes(selectedDownload.id)) {
        setSelectedDownload(null);
      }
    }
    setDeleteWorking(false);

    if (failures.length) {
      setDeleteError(`Sebagian unduhan gagal dihapus:\n${failures.join('\n')}`);
    } else {
      setDeleteDialogOpen(false);
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  };

  const toggleAll = () => {
    const visibleIds = visibleDownloads.map((item) => item.id);
    const allSelected = visibleIds.every((id) => selectedIds.includes(id));
    setSelectedIds(allSelected ? selectedIds.filter((id) => !visibleIds.includes(id)) : visibleIds);
  };

  return (
    <div className="app-shell relative flex h-screen flex-col overflow-hidden bg-[#0F0F11] text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(139,92,246,0.12),transparent_50%),radial-gradient(ellipse_at_bottom_left,rgba(34,211,238,0.08),transparent_45%)]" />

      <div className="relative flex min-h-0 flex-1">
        <Sidebar
          counts={counts}
          activeCategory={activeCategory}
          onCategoryChange={(category) => {
            setActiveCategory(category);
            if (category === 'all') setActiveFileCategory('all');
          }}
          activeFileCategory={activeFileCategory}
          onFileCategoryChange={(category) => {
            setActiveCategory('all');
            setActiveFileCategory(category);
          }}
          fileCategoryCounts={fileCategoryCounts}
          clipboardEnabled={clipboardEnabled}
          onClipboardToggle={() => setClipboardEnabled((value) => !value)}
          onOpenSettings={() => setSettingsOpen(true)}
          theme={theme}
          onThemeChange={setTheme}
          bandwidthLimit={bandwidthLimit}
        />

        <div className="flex min-w-0 flex-1 flex-col">
          <TopActionBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            selectedCount={selectedIds.length}
            onAction={applyAction}
            onAddLink={() => openAddLink('')}
            onOpenSettings={() => setSettingsOpen(true)}
          />
          <DownloadTable
            items={visibleDownloads}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleAll={toggleAll}
            onOpenDetails={(download) => {
              const api = window.pywebview?.api;
              if (api?.open_download_details && !download.id.startsWith('dl-')) {
                api.open_download_details(download.id).catch((error) => {
                  setToast(`Tidak dapat membuka detail download: ${error.message}`);
                });
                return;
              }
              setSelectedDownload(download);
              setDetailsMinimized(false);
            }}
          />
        </div>
      </div>

      <StatusBar
        totalSpeed={totalSpeed}
        activeCount={counts.downloading}
        clipboardEnabled={clipboardEnabled}
        bandwidthLimit={bandwidthLimit}
      />

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        theme={theme}
        onThemeChange={setTheme}
        bandwidthLimit={bandwidthLimit}
        onBandwidthChange={setBandwidthLimit}
        clipboardEnabled={clipboardEnabled}
        onClipboardToggle={() => setClipboardEnabled((value) => !value)}
      />

      <AddLinkModal
        key={addLinkOpen ? pendingUrl || 'new-link' : 'closed'}
        open={addLinkOpen}
        initialUrl={pendingUrl}
        folders={downloadFolders}
        foldersError={downloadFoldersError}
        onClose={() => setAddLinkOpen(false)}
        onSubmit={addDownload}
      />

      <DeleteDownloadsModal
        open={deleteDialogOpen}
        downloads={downloads.filter((item) => selectedIds.includes(item.id))}
        working={deleteWorking}
        error={deleteError}
        onClose={() => {
          if (!deleteWorking) setDeleteDialogOpen(false);
        }}
        onDelete={deleteSelectedDownloads}
      />

      {selectedDownload && (
        <DownloadDetailsModal
          key={selectedDownload.id}
          download={selectedDownload}
          bandwidthLimit={bandwidthLimit}
          minimized={detailsMinimized}
          onMinimize={() => setDetailsMinimized((value) => !value)}
          onClose={() => setSelectedDownload(null)}
          onUpdate={updateDownload}
          onUpdateOptions={updateDownloadOptions}
          onCancel={cancelDownload}
        />
      )}

      {toast && (
        <div className="absolute bottom-14 right-5 rounded-xl border border-emerald-400/30 bg-emerald-500/15 px-4 py-2 text-sm text-emerald-100">
          {toast}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const windowType = params.get('window');
  if (windowType === 'confirm' || windowType === 'details') {
    return (
      <DetachedDownloadWindow
        type={windowType}
        windowId={params.get('window_id') || ''}
        downloadId={params.get('id') || ''}
        initialUrl={params.get('url') || ''}
      />
    );
  }
  return <MainApp />;
}
