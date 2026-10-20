const URL_PATTERN = /https?:\/\/[^\s<>"']+/i;

export function formatBytes(bytes, decimals = 1) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(value >= 100 || exponent === 0 ? 0 : decimals)} ${units[exponent]}`;
}

export function formatSpeed(bytesPerSecond) {
  if (!bytesPerSecond) return '0 B/s';
  return `${formatBytes(bytesPerSecond)}/s`;
}

export function formatEta(seconds) {
  if (seconds == null) return '—';
  if (seconds <= 0) return 'Done';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  if (minutes < 60) return `${minutes}m ${rest}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export function fileExtension(name) {
  const match = name?.match(/\.([a-z0-9]+)$/i);
  return match ? match[1].toUpperCase() : 'FILE';
}

export function extractUrl(text) {
  const match = String(text || '').match(URL_PATTERN);
  return match ? match[0] : '';
}

export function filenameFromUrl(url) {
  try {
    const path = new URL(url).pathname;
    const name = decodeURIComponent(path.split('/').filter(Boolean).pop() || '');
    return name || 'download.bin';
  } catch {
    return 'download.bin';
  }
}

export const DOWNLOAD_CATEGORIES = [
  { id: 'applications', label: 'Applications', extensions: ['exe', 'msi', 'msix', 'appx', 'apk', 'dmg', 'pkg', 'deb', 'rpm'] },
  { id: 'videos', label: 'Videos', extensions: ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'm4v'] },
  { id: 'music', label: 'Music', extensions: ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'] },
  { id: 'documents', label: 'Documents', extensions: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'csv'] },
  { id: 'archives', label: 'Archives', extensions: ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'iso'] },
  { id: 'images', label: 'Images', extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'tif', 'tiff'] },
  { id: 'other', label: 'Other', extensions: [] },
];

export function categoryForFilename(filename) {
  const extension = fileExtension(filename).toLowerCase();
  return DOWNLOAD_CATEGORIES.find((category) => category.extensions.includes(extension))?.id || 'other';
}
