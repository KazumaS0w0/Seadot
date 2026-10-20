import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, Download, Link2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  categoryForFilename,
  DOWNLOAD_CATEGORIES,
  extractUrl,
  filenameFromUrl,
} from '../utils/format';

export default function AddLinkModal({
  open,
  initialUrl,
  folders,
  foldersError,
  onClose,
  onSubmit,
}) {
  const [url, setUrl] = useState(initialUrl || '');
  const [step, setStep] = useState('link');
  const [category, setCategory] = useState('other');
  const [destinationFolder, setDestinationFolder] = useState('');
  const [customFilename, setCustomFilename] = useState('');
  const [splitCount, setSplitCount] = useState(4);
  const [splitSettingError, setSplitSettingError] = useState('');
  const [fileConflict, setFileConflict] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const parsed = extractUrl(url);
  const filename = parsed ? filenameFromUrl(parsed) : '';
  const resolvedFilename = customFilename.trim() || filename;
  const resolvedDestinationFolder = destinationFolder
    || folders.find((folder) => folder.id === category)?.folder
    || '';

  useEffect(() => {
    if (!open) return undefined;

    let disposed = false;
    const loadDefaultSplitCount = async () => {
      setSplitSettingError('');
      try {
        const response = await fetch('/api/system/settings');
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
        if (![1, 2, 4, 8, 16].includes(result.split_count)) {
          throw new Error('Nilai split download default tidak valid.');
        }
        if (!disposed) setSplitCount(result.split_count);
      } catch (error) {
        if (!disposed) {
          setSplitSettingError(`Tidak dapat memuat preferensi split download: ${error.message}`);
        }
      }
    };

    loadDefaultSplitCount();
    return () => {
      disposed = true;
    };
  }, [open]);

  const continueToConfirmation = (event) => {
    event.preventDefault();
    if (!parsed) return;
    const guessedCategory = categoryForFilename(filename);
    setCategory(guessedCategory);
    setDestinationFolder(folders.find((folder) => folder.id === guessedCategory)?.folder || '');
    setCustomFilename(filename);
    setFileConflict('');
    setSubmitError('');
    setStep('confirm');
  };

  const startDownload = async (conflictPolicy = null) => {
    if (!parsed || !resolvedDestinationFolder || !resolvedFilename || submitting) return;

    setSubmitting(true);
    setSubmitError('');
    setFileConflict('');
    try {
      await onSubmit(
        parsed,
        resolvedFilename,
        category,
        resolvedDestinationFolder,
        splitCount,
        conflictPolicy,
      );
    } catch (error) {
      if (error.status === 409 && !conflictPolicy) {
        setFileConflict(error.message);
      } else {
        setSubmitError(`Gagal memulai unduhan: ${error.message}`);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDownload = (event) => {
    event.preventDefault();
    startDownload();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="absolute inset-0 z-50 flex items-center justify-center bg-black/55 p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.form
            onSubmit={step === 'link' ? continueToConfirmation : confirmDownload}
            initial={{ scale: 0.96, y: 12, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.96, y: 12, opacity: 0 }}
            className="add-link-modal w-full max-w-lg rounded-2xl border border-white/10 bg-[#0B0F19] p-5 shadow-[0_0_40px_rgba(139,92,246,0.18)]"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-white">
                {step === 'link'
                  ? <Link2 className="h-4 w-4 text-violet-300" />
                  : <Download className="h-4 w-4 text-violet-300" />}
                <h2 className="text-sm font-semibold">
                  {step === 'link' ? 'Add download link' : 'Confirm download'}
                </h2>
              </div>
              <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5">
                <X className="h-4 w-4" />
              </button>
            </div>

            {step === 'link' ? (
              <>
                <label className="mb-2 block text-xs uppercase tracking-[0.14em] text-slate-500">URL</label>
                <input
                  autoFocus
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://example.com/file.zip"
                  className="search-control mb-3 w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3 py-3 text-sm text-slate-100 outline-none focus:border-violet-400/40"
                />

                {filename && (
                  <p className="mb-4 text-xs text-slate-500">
                    Nama file terdeteksi: <span className="text-slate-300">{filename}</span>
                  </p>
                )}
              </>
            ) : (
              <div className="space-y-4">
                <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
                  <p className="text-xs text-slate-500">File</p>
                  <p className="mt-1 break-all text-sm font-medium text-slate-200">{resolvedFilename}</p>
                  <p className="mt-1 break-all text-xs text-slate-500">{parsed}</p>
                </div>
                <label className="block text-xs font-medium text-slate-400" htmlFor="download-filename">
                  Nama file
                  <input
                    id="download-filename"
                    value={customFilename}
                    onChange={(event) => setCustomFilename(event.target.value)}
                    className="search-control mt-2 w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3 py-2.5 text-sm text-slate-100 outline-none"
                  />
                </label>
                <label className="block text-xs font-medium text-slate-400" htmlFor="download-category">
                  Kategori file
                  <select
                    id="download-category"
                    value={category}
                    onChange={(event) => {
                      setCategory(event.target.value);
                      setDestinationFolder(
                        folders.find((folder) => folder.id === event.target.value)?.folder || '',
                      );
                    }}
                    className="search-control mt-2 w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3 py-2.5 text-sm text-slate-100 outline-none"
                  >
                    {DOWNLOAD_CATEGORIES.map((item) => (
                      <option key={item.id} value={item.id}>{item.label}</option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-medium text-slate-400" htmlFor="download-folder">
                  Folder penyimpanan
                  <input
                    id="download-folder"
                    value={resolvedDestinationFolder}
                    onChange={(event) => setDestinationFolder(event.target.value)}
                    placeholder="Pilih kategori atau masukkan path folder"
                    className="search-control mt-2 w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3 py-2.5 text-sm text-slate-100 outline-none"
                  />
                </label>
                <label className="block text-xs font-medium text-slate-400" htmlFor="download-split-count">
                  Jumlah bagian download
                  <select
                    id="download-split-count"
                    value={splitCount}
                    onChange={(event) => setSplitCount(Number(event.target.value))}
                    className="search-control mt-2 w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3 py-2.5 text-sm text-slate-100 outline-none"
                  >
                    {[1, 2, 4, 8, 16].map((count) => (
                      <option key={count} value={count}>{count === 1 ? 'Nonaktif' : `${count} bagian`}</option>
                    ))}
                  </select>
                </label>
                <p className="text-xs leading-relaxed text-slate-500">
                  Pembagian aktif jika server mendukung HTTP Range; jika tidak, unduhan otomatis memakai satu koneksi.
                </p>
                {splitSettingError && (
                  <p role="alert" className="text-xs text-amber-300">{splitSettingError}</p>
                )}
                {fileConflict && (
                  <div role="alert" className="space-y-2 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-3">
                    <p className="text-xs text-amber-200">{fileConflict}</p>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={submitting}
                        onClick={() => startDownload('overwrite')}
                        className="rounded-lg border border-amber-300/20 px-3 py-2 text-xs text-amber-100 hover:bg-amber-300/10 disabled:opacity-50"
                      >
                        Timpa file
                      </button>
                      <button
                        type="button"
                        disabled={submitting}
                        onClick={() => startDownload('number')}
                        className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-200 hover:bg-white/5 disabled:opacity-50"
                      >
                        Simpan dengan nomor
                      </button>
                    </div>
                  </div>
                )}
                {foldersError && <p role="alert" className="text-xs text-rose-400">{foldersError}</p>}
                {submitError && <p role="alert" className="text-xs text-rose-400">{submitError}</p>}
              </div>
            )}

            <div className="flex justify-end gap-2">
              {step === 'confirm' && (
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => {
                    setStep('link');
                    setSubmitError('');
                  }}
                  className="inline-flex items-center gap-1 rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-300 hover:bg-white/5 disabled:opacity-50"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Kembali
                </button>
              )}
              <button
                type="button"
                disabled={submitting}
                onClick={onClose}
                className="rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-300 hover:bg-white/5 disabled:opacity-50"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={
                  !parsed
                  || submitting
                  || (step === 'confirm' && (!resolvedDestinationFolder.trim() || Boolean(foldersError)))
                }
                className="rounded-xl bg-gradient-to-r from-violet-500 to-cyan-400 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              >
                {step === 'link' ? 'Lanjutkan' : submitting ? 'Memulai...' : 'Mulai download'}
              </button>
            </div>
          </motion.form>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
