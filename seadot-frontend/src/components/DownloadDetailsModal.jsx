import { AnimatePresence, motion } from 'framer-motion';
import {
  CheckCircle2,
  Gauge,
  Info,
  Maximize2,
  Minimize2,
  Pause,
  Play,
  Power,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import FileTypeIcon from './FileTypeIcon';
import { formatBytes, formatEta, formatSpeed } from '../utils/format';

const TABS = [
  { id: 'info', label: 'Info', icon: Info },
  { id: 'speed', label: 'Speed', icon: Gauge },
  { id: 'completion', label: 'On Completion', icon: Power },
];

export default function DownloadDetailsModal({
  download,
  onClose,
  onUpdate,
  onUpdateOptions,
  onCancel,
  bandwidthLimit,
  minimized,
  onMinimize,
  showMinimize = true,
}) {
  const [tab, setTab] = useState('info');
  const [details, setDetails] = useState(download);
  const [actionError, setActionError] = useState('');
  const [working, setWorking] = useState(false);
  const [optionsSaving, setOptionsSaving] = useState(false);
  const [optionsError, setOptionsError] = useState('');
  const [speedLimitMb, setSpeedLimitMb] = useState((download?.speedLimitBps || 0) / (1024 * 1024));
  const [completionAction, setCompletionAction] = useState(download?.completionAction || 'none');
  const [countdownMinutes, setCountdownMinutes] = useState(download?.countdownMinutes || 2);
  const detailsRef = useRef(details);
  const downloadId = download?.id;

  useEffect(() => {
    if (!downloadId || !['downloading', 'paused', 'queued'].includes(details.status)) return undefined;

    let disposed = false;
    const refresh = async () => {
      try {
        const response = await fetch(`/api/downloads/${downloadId}`);
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
        if (disposed) return;

        const current = detailsRef.current;
        const updated = {
          ...current,
          progress: result.progress ?? current.progress,
          sizeBytes: result.total_size || current.sizeBytes,
          downloadedBytes: result.downloaded_size || 0,
          speedBps: result.speed ?? 0,
          etaSeconds: result.eta ?? null,
          status: result.status || current.status,
        };
        detailsRef.current = updated;
        setDetails(updated);
        onUpdate(updated);
      } catch (error) {
        if (!disposed) setActionError(`Tidak dapat memperbarui status unduhan: ${error.message}`);
      }
    };

    refresh();
    const timer = window.setInterval(refresh, 1000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [downloadId, details.status, onUpdate]);

  const controlDownload = async (action) => {
    setWorking(true);
    setActionError('');
    try {
      const endpoint = action === 'pause'
        ? `/api/downloads/pause?download_id=${encodeURIComponent(downloadId)}`
        : `/api/downloads/resume?download_id=${encodeURIComponent(downloadId)}`;
      const response = await fetch(endpoint, { method: 'POST' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
      const updated = { ...details, status: action === 'pause' ? 'paused' : 'downloading' };
      detailsRef.current = updated;
      setDetails(updated);
      onUpdate(updated);
    } catch (error) {
      setActionError(`Gagal ${action === 'pause' ? 'menjeda' : 'melanjutkan'} unduhan: ${error.message}`);
    } finally {
      setWorking(false);
    }
  };

  const cancelDownload = async () => {
    setWorking(true);
    setActionError('');
    try {
      const response = await fetch(`/api/downloads/remove/${encodeURIComponent(downloadId)}`, {
        method: 'DELETE',
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
      onCancel(downloadId);
      onClose();
    } catch (error) {
      setActionError(`Gagal membatalkan unduhan: ${error.message}`);
    } finally {
      setWorking(false);
    }
  };

  const saveOptions = async () => {
    setOptionsSaving(true);
    setOptionsError('');
    try {
      await onUpdateOptions(downloadId, {
        speed_limit_bps: Math.round(Number(speedLimitMb || 0) * 1024 * 1024),
        split_count: details.splitCount || 4,
        completion_action: completionAction,
        countdown_minutes: Number(countdownMinutes),
      });
    } catch (error) {
      setOptionsError(`Gagal menyimpan pengaturan download: ${error.message}`);
    } finally {
      setOptionsSaving(false);
    }
  };

  if (!download) return null;

  const progress = Math.min(100, Math.max(0, Number(details.progress) || 0));
  const downloadedBytes = details.downloadedBytes ?? Math.round((details.sizeBytes || 0) * progress / 100);
  const isActive = details.status === 'downloading';
  const isComplete = details.status === 'completed';

  return (
    <AnimatePresence>
      {download && (
        minimized ? (
          <motion.div
            className="absolute bottom-4 right-4 z-[60] flex max-w-[min(24rem,calc(100%-2rem))] items-center gap-2 rounded-xl border border-white/10 bg-[#0B0F19] p-2 shadow-2xl"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
          >
            <button
              type="button"
              onClick={onMinimize}
              aria-label={`Restore download details for ${details.name}`}
              className="flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1 text-left hover:bg-white/5"
            >
              <Maximize2 className="h-4 w-4 shrink-0 text-violet-300" />
              <span className="truncate text-xs text-slate-200">{details.name}</span>
              <span className="shrink-0 text-xs text-cyan-300">{Math.round(progress)}%</span>
            </button>
            <button
              type="button"
              aria-label="Close download details"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </motion.div>
        ) : <motion.div
          className="absolute inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !working) onClose();
          }}
        >
          <motion.section
            role="dialog"
            aria-modal="true"
            aria-label={`Download details: ${details.name}`}
            initial={{ scale: 0.97, y: 10, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.97, y: 10, opacity: 0 }}
            className="download-details-modal w-full max-w-xl overflow-hidden rounded-2xl border border-white/10 bg-[#0B0F19] shadow-[0_24px_80px_rgba(0,0,0,0.45)]"
          >
            <header className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <div className="flex min-w-0 items-center gap-2">
                <FileTypeIcon name={details.name} />
                <div className="min-w-0">
                  <h2 className="truncate text-sm font-semibold text-slate-100">{details.name}</h2>
                  <p className="text-xs text-slate-500">{Math.round(progress)}% · {details.status}</p>
                </div>
              </div>
              {showMinimize && (
                <button
                  type="button"
                  aria-label="Minimize download details"
                  onClick={onMinimize}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
                >
                  <Minimize2 className="h-4 w-4" />
                </button>
              )}
              <button
                type="button"
                aria-label="Close download details"
                onClick={onClose}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            <nav className="flex gap-1 border-b border-white/10 px-3 pt-2">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTab(id)}
                  className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition ${
                    tab === id
                      ? 'border-violet-400 text-violet-200'
                      : 'border-transparent text-slate-500 hover:text-slate-300'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </nav>

            <div className="min-h-48 px-5 py-4">
              {tab === 'info' && (
                <dl className="grid grid-cols-[120px_minmax(0,1fr)] gap-x-3 gap-y-2 text-xs">
                  <dt className="text-slate-500">Name:</dt>
                  <dd className="break-all text-slate-200">{details.name}</dd>
                  <dt className="text-slate-500">Status:</dt>
                  <dd className="capitalize text-cyan-300">{details.status}</dd>
                  <dt className="text-slate-500">Size:</dt>
                  <dd className="text-slate-200">{details.sizeBytes ? formatBytes(details.sizeBytes) : 'Detecting...'}</dd>
                  <dt className="text-slate-500">Downloaded:</dt>
                  <dd className="text-slate-200">
                    {formatBytes(downloadedBytes)}{details.sizeBytes ? ` (${Math.round(progress)}%)` : ''}
                  </dd>
                  <dt className="text-slate-500">Speed:</dt>
                  <dd className="text-slate-200">{formatSpeed(details.speedBps)}</dd>
                  <dt className="text-slate-500">Time Left:</dt>
                  <dd className="text-slate-200">{isComplete ? 'Done' : formatEta(details.etaSeconds)}</dd>
                  <dt className="text-slate-500">Save to:</dt>
                  <dd className="break-all text-slate-200">{details.destPath}</dd>
                </dl>
              )}

              {tab === 'speed' && (
                <div className="space-y-4 text-xs">
                  <div className="flex items-center justify-between border-b border-white/[0.07] pb-3">
                    <span className="text-slate-400">Current speed</span>
                    <span className="font-medium text-cyan-300">{formatSpeed(details.speedBps)}</span>
                  </div>
                  <label className="block text-slate-400" htmlFor="download-speed-limit">
                    Batas kecepatan untuk download ini (MB/s; 0 = tanpa batas)
                    <input
                      id="download-speed-limit"
                      type="number"
                      min="0"
                      max="1024"
                      step="0.1"
                      value={speedLimitMb}
                      onChange={(event) => setSpeedLimitMb(event.target.value)}
                      className="search-control mt-2 w-full rounded-lg border border-white/10 bg-[#080c14] px-3 py-2 text-sm text-slate-200"
                    />
                  </label>
                  <p className="text-slate-500">
                    Batas global: {bandwidthLimit ? `${bandwidthLimit} MB/s` : 'Tanpa batas'}
                  </p>
                  {optionsError && <p role="alert" className="text-rose-300">{optionsError}</p>}
                  <button
                    type="button"
                    disabled={optionsSaving}
                    onClick={saveOptions}
                    className="rounded-lg bg-violet-500/20 px-3 py-2 text-xs font-medium text-violet-100 hover:bg-violet-500/30 disabled:opacity-50"
                  >
                    {optionsSaving ? 'Menyimpan...' : 'Simpan batas kecepatan'}
                  </button>
                </div>
              )}

              {tab === 'completion' && (
                <div className="space-y-4 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                  <div className="flex gap-3">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                    <p className="text-sm font-medium text-slate-200">Aksi setelah semua unduhan selesai</p>
                  </div>
                  <label className="block text-xs text-slate-400" htmlFor="download-completion-action">
                    Aktifkan aksi daya
                    <select
                      id="download-completion-action"
                      value={completionAction}
                      onChange={(event) => {
                        const nextAction = event.target.value;
                        if (
                          nextAction !== 'none'
                          && !window.confirm(
                            `Aksi ${nextAction} akan dijalankan setelah semua unduhan selesai. Lanjutkan?`,
                          )
                        ) return;
                        setCompletionAction(nextAction);
                      }}
                      className="mt-2 w-full rounded-lg border border-white/10 bg-[#080c14] px-3 py-2 text-sm text-slate-200"
                    >
                      <option value="none">Nonaktif</option>
                      <option value="shutdown">Matikan komputer</option>
                      <option value="sleep">Sleep</option>
                      <option value="hibernate">Hibernate</option>
                      <option value="restart">Restart komputer</option>
                    </select>
                  </label>
                  {completionAction !== 'none' && (
                    <label className="block text-xs text-slate-400" htmlFor="download-action-countdown">
                      Hitung mundur sebelum aksi (menit)
                      <input
                        id="download-action-countdown"
                        type="number"
                        min="1"
                        max="120"
                        value={countdownMinutes}
                        onChange={(event) => setCountdownMinutes(event.target.value)}
                        className="mt-2 w-full rounded-lg border border-white/10 bg-[#080c14] px-3 py-2 text-sm text-slate-200"
                      />
                    </label>
                  )}
                  {optionsError && <p role="alert" className="text-xs text-rose-300">{optionsError}</p>}
                  <button
                    type="button"
                    disabled={optionsSaving}
                    onClick={saveOptions}
                    className="rounded-lg bg-violet-500/20 px-3 py-2 text-xs font-medium text-violet-100 hover:bg-violet-500/30 disabled:opacity-50"
                  >
                    {optionsSaving ? 'Menyimpan...' : 'Simpan aksi'}
                  </button>
                </div>
              )}
              {actionError && <p role="alert" className="mt-4 text-xs text-rose-300">{actionError}</p>}
            </div>

            <div className="space-y-3 border-t border-white/10 px-4 py-3">
              <div
                role="progressbar"
                aria-label="Download progress"
                aria-valuenow={Math.round(progress)}
                aria-valuemin="0"
                aria-valuemax="100"
                className="h-2 overflow-hidden rounded-full bg-white/10"
              >
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-violet-500"
                  animate={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  disabled={working || isComplete || details.status === 'failed'}
                  onClick={() => controlDownload(isActive ? 'pause' : 'resume')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-white/10 disabled:opacity-40"
                >
                  {isActive ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                  {isActive ? 'Pause' : 'Resume'}
                </button>
                <button
                  type="button"
                  disabled={working || isComplete || details.status === 'failed'}
                  onClick={cancelDownload}
                  className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:border-rose-400/30 hover:text-rose-300 disabled:opacity-40"
                >
                  Cancel
                </button>
              </div>
            </div>
          </motion.section>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
