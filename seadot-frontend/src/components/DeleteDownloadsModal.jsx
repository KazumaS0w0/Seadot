import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, HardDrive, ListMinus, X } from 'lucide-react';

export default function DeleteDownloadsModal({
  downloads,
  open,
  working,
  error,
  onClose,
  onDelete,
}) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="absolute inset-0 z-[70] flex items-center justify-center bg-black/65 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !working) onClose();
          }}
        >
          <motion.section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-downloads-title"
            initial={{ scale: 0.97, y: 10, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.97, y: 10, opacity: 0 }}
            className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#0B0F19] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.45)]"
          >
            <header className="mb-4 flex items-start justify-between">
              <div className="flex gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-amber-400/10 text-amber-300">
                  <AlertTriangle className="h-5 w-5" />
                </span>
                <div>
                  <h2 id="delete-downloads-title" className="text-sm font-semibold text-slate-100">
                    Hapus unduhan?
                  </h2>
                  <p className="mt-1 text-xs text-slate-400">
                    Pilih apakah file di perangkat juga perlu dihapus.
                  </p>
                </div>
              </div>
              <button
                type="button"
                aria-label="Tutup konfirmasi hapus"
                disabled={working}
                onClick={onClose}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white disabled:opacity-40"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            <ul className="mb-4 max-h-32 space-y-1 overflow-y-auto rounded-xl border border-white/[0.07] bg-white/[0.025] p-3">
              {downloads.map((download) => (
                <li key={download.id} className="truncate text-xs text-slate-300">
                  {download.name}
                </li>
              ))}
            </ul>

            {error && <p role="alert" className="mb-4 text-xs text-rose-300">{error}</p>}

            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                disabled={working}
                onClick={() => onDelete(false)}
                className="flex min-h-14 items-center gap-3 rounded-xl border border-white/10 px-3 py-2 text-left hover:bg-white/5 disabled:opacity-50"
              >
                <ListMinus className="h-4 w-4 shrink-0 text-violet-300" />
                <span>
                  <span className="block text-xs font-semibold text-slate-100">
                    {working ? 'Menghapus...' : 'Hapus dari Seadot saja'}
                  </span>
                  <span className="mt-1 block text-[11px] text-slate-500">File tetap di folder.</span>
                </span>
              </button>
              <button
                type="button"
                disabled={working}
                onClick={() => onDelete(true)}
                className="flex min-h-14 items-center gap-3 rounded-xl border border-rose-400/20 bg-rose-500/[0.06] px-3 py-2 text-left hover:bg-rose-500/10 disabled:opacity-50"
              >
                <HardDrive className="h-4 w-4 shrink-0 text-rose-300" />
                <span>
                  <span className="block text-xs font-semibold text-rose-100">
                    {working ? 'Menghapus...' : 'Hapus dari Seadot dan folder'}
                  </span>
                  <span className="mt-1 block text-[11px] text-rose-200/60">File di perangkat ikut dihapus.</span>
                </span>
              </button>
            </div>
            <button
              type="button"
              disabled={working}
              onClick={onClose}
              className="mt-3 w-full rounded-xl border border-white/10 px-3 py-2 text-xs text-slate-400 hover:bg-white/5 disabled:opacity-50"
            >
              Batal
            </button>
          </motion.section>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
