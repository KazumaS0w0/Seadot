import { useCallback, useEffect, useState } from 'react';
import AddLinkModal from './AddLinkModal';
import DownloadDetailsModal from './DownloadDetailsModal';
import { categoryForFilename } from '../utils/format';

async function readResponse(response) {
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}

function closeNativeWindow(windowId) {
  const api = window.pywebview?.api;
  if (api?.close_window) {
    api.close_window(windowId);
    return;
  }
  window.close();
}

function mapDownload(record) {
  const filename = record.dest_path?.split(/[\\/]/).pop() || record.filename || 'Download';
  return {
    id: record.download_id || record.id,
    name: filename,
    url: record.url,
    status: record.status || 'downloading',
    sizeBytes: record.total_size || 0,
    downloadedBytes: record.downloaded_size || 0,
    progress: record.progress || 0,
    speedBps: record.speed || 0,
    etaSeconds: record.eta ?? null,
    destPath: record.dest_path,
    dateAdded: record.created_at?.slice(0, 16).replace('T', ' ') || '',
    category: categoryForFilename(filename),
    splitCount: record.split_count || 4,
    speedLimitBps: record.speed_limit_bps || 0,
    completionAction: record.completion_action || 'none',
    countdownMinutes: record.countdown_minutes || 2,
  };
}

export default function DetachedDownloadWindow({ type, windowId, downloadId, initialUrl }) {
  const [download, setDownload] = useState(null);
  const [folders, setFolders] = useState([]);
  const [foldersError, setFoldersError] = useState('');
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (type !== 'confirm') return undefined;
    let disposed = false;
    const loadFolders = async () => {
      try {
        const result = await readResponse(await fetch('/api/downloads/categories'));
        if (!disposed) setFolders(result.categories);
      } catch (error) {
        if (!disposed) setFoldersError(`Tidak dapat memuat folder unduhan: ${error.message}`);
      }
    };
    loadFolders();
    return () => {
      disposed = true;
    };
  }, [type]);

  useEffect(() => {
    if (type !== 'details' || !downloadId) return undefined;
    let disposed = false;
    const loadDownload = async () => {
      try {
        const result = await readResponse(
          await fetch(`/api/downloads/${encodeURIComponent(downloadId)}`),
        );
        if (!disposed) setDownload(mapDownload(result));
      } catch (error) {
        if (!disposed) setLoadError(`Tidak dapat memuat detail unduhan: ${error.message}`);
      }
    };
    loadDownload();
    return () => {
      disposed = true;
    };
  }, [type, downloadId]);

  const createDownload = async (url, filename, category, destinationFolder, splitCount, conflictPolicy) => {
    await readResponse(await fetch('/api/downloads/create', {
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
    }));
    closeNativeWindow(windowId);
  };

  const updateOptions = async (id, options) => {
    const result = await readResponse(await fetch(
      `/api/downloads/${encodeURIComponent(id)}/options`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options),
      },
    ));
    setDownload((current) => ({
      ...current,
      speedLimitBps: result.speed_limit_bps,
      splitCount: result.split_count,
      completionAction: result.completion_action,
      countdownMinutes: result.countdown_minutes,
    }));
  };

  const cancelDownload = () => {
    setDownload(null);
  };

  const updateDownload = useCallback((updated) => {
    setDownload((current) => ({ ...current, ...updated }));
  }, []);

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[#0F0F11] p-4 text-slate-100">
      {type === 'confirm' && (
        <AddLinkModal
          open
          initialUrl={initialUrl}
          folders={folders}
          foldersError={foldersError}
          onClose={() => closeNativeWindow(windowId)}
          onSubmit={createDownload}
        />
      )}
      {type === 'details' && download && (
        <DownloadDetailsModal
          download={download}
          bandwidthLimit={0}
          minimized={false}
          onMinimize={() => {}}
          showMinimize={false}
          onClose={() => closeNativeWindow(windowId)}
          onUpdate={updateDownload}
          onUpdateOptions={updateOptions}
          onCancel={cancelDownload}
        />
      )}
      {loadError && <p role="alert" className="max-w-lg text-sm text-rose-300">{loadError}</p>}
    </div>
  );
}
