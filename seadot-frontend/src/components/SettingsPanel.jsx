import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown, Copy, Gauge, Globe2, Palette, Power, RotateCw, X } from 'lucide-react';
import BrowserLogo from './BrowserLogo';

function SettingsRack({ title, description, icon, open, onToggle, children }) {
  return (
    <section className="settings-rack overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] shadow-lg shadow-black/10">
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition hover:bg-white/[0.04]"
      >
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.04]">
          {icon}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-slate-100">{title}</span>
          <span className="mt-0.5 block text-xs text-slate-500">{description}</span>
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && <div className="space-y-5 border-t border-white/[0.07] px-4 py-4">{children}</div>}
    </section>
  );
}

export default function SettingsPanel({
  open,
  onClose,
  theme,
  onThemeChange,
  bandwidthLimit,
  onBandwidthChange,
  clipboardEnabled,
  onClipboardToggle,
}) {
  const [systemSettings, setSystemSettings] = useState({
    auto_start: true,
    completion_action: 'none',
    countdown_minutes: 2,
    split_count: 4,
  });
  const [powerAction, setPowerAction] = useState({ pending: false });
  const [systemSettingsLoading, setSystemSettingsLoading] = useState(false);
  const [systemSettingsSaving, setSystemSettingsSaving] = useState(false);
  const [systemSettingsError, setSystemSettingsError] = useState('');
  const [systemSettingsMessage, setSystemSettingsMessage] = useState('');
  const [extensionFolder, setExtensionFolder] = useState('');
  const [extensionError, setExtensionError] = useState('');
  const [extensionMessage, setExtensionMessage] = useState('');
  const [openSections, setOpenSections] = useState({
    appearance: true,
    downloads: true,
    extension: window.localStorage.getItem('seadot-extension-onboarding-seen') !== 'true',
    clipboard: false,
    automation: true,
  });

  const toggleSection = (section) => {
    setOpenSections((sections) => ({ ...sections, [section]: !sections[section] }));
  };

  const openExtensionManager = async (browser) => {
    setExtensionError('');
    setExtensionMessage('');
    const browserNames = {
      chrome: 'Google Chrome',
      edge: 'Microsoft Edge',
      firefox: 'Mozilla Firefox',
      opera: 'Opera',
    };
    try {
      const api = window.pywebview?.api;
      if (api?.open_extension_manager) {
        await api.open_extension_manager(browser);
        setExtensionMessage(`Halaman integrasi ${browserNames[browser]} dibuka.`);
        return;
      }
      const managerUrls = {
        chrome: 'chrome://extensions/',
        edge: 'edge://extensions/',
        firefox: 'about:debugging#/runtime/this-firefox',
        opera: 'opera://extensions/',
      };
      const url = managerUrls[browser];
      await navigator.clipboard.writeText(url);
      setExtensionMessage(
        `URL ${url} disalin. Buka ${browserNames[browser]} dan tempelkan di address bar.`,
      );
    } catch (error) {
      setExtensionError(`Tidak dapat membuka pengaturan extension: ${error.message}`);
    }
  };

  const copyExtensionFolder = async () => {
    setExtensionError('');
    setExtensionMessage('');
    try {
      await navigator.clipboard.writeText(extensionFolder);
      setExtensionMessage('Lokasi folder extension disalin.');
    } catch (error) {
      setExtensionError(`Tidak dapat menyalin lokasi folder: ${error.message}`);
    }
  };

  useEffect(() => {
    if (!open) return undefined;

    let disposed = false;
    const loadSystemSettings = async () => {
      setSystemSettingsLoading(true);
      setSystemSettingsError('');
      try {
        const response = await fetch('/api/system/settings');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const settings = await response.json();
        if (!disposed) setSystemSettings(settings);
      } catch (error) {
        if (!disposed) setSystemSettingsError(`Tidak dapat memuat pengaturan sistem: ${error.message}`);
      } finally {
        if (!disposed) setSystemSettingsLoading(false);
      }
    };

    const loadPowerAction = async () => {
      try {
        const response = await fetch('/api/system/action');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const status = await response.json();
        if (!disposed) setPowerAction(status);
      } catch (error) {
        if (!disposed) setSystemSettingsError(`Tidak dapat memeriksa aksi daya: ${error.message}`);
      }
    };

    const loadExtensionInfo = async () => {
      try {
        const response = await fetch('/api/extension/info');
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
        if (!disposed) setExtensionFolder(result.folder);
      } catch (error) {
        if (!disposed) setExtensionError(`Tidak dapat menemukan file extension: ${error.message}`);
      }
    };

    loadSystemSettings();
    loadPowerAction();
    loadExtensionInfo();
    const timer = window.setInterval(loadPowerAction, 1000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [open]);

  const saveSystemSettings = async () => {
    if (
      systemSettings.completion_action !== 'none'
      && !window.confirm(
        `Seadot akan menjalankan aksi ini setelah semua unduhan selesai. Hitung mundur: ${systemSettings.countdown_minutes} menit. Anda bisa membatalkannya dari panel Settings. Lanjutkan?`,
      )
    ) {
      return;
    }

    setSystemSettingsSaving(true);
    setSystemSettingsError('');
    setSystemSettingsMessage('');
    try {
      const response = await fetch('/api/system/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(systemSettings),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
      setSystemSettings(result);
      setSystemSettingsMessage('Pengaturan sistem tersimpan.');
    } catch (error) {
      setSystemSettingsError(`Gagal menyimpan pengaturan: ${error.message}`);
    } finally {
      setSystemSettingsSaving(false);
    }
  };

  const cancelPowerAction = async () => {
    setSystemSettingsError('');
    try {
      const response = await fetch('/api/system/action/cancel', { method: 'POST' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setPowerAction(await response.json());
      setSystemSettingsMessage('Aksi daya dibatalkan.');
    } catch (error) {
      setSystemSettingsError(`Gagal membatalkan aksi daya: ${error.message}`);
    }
  };

  const updateSystemSetting = (key, value) => {
    setSystemSettings((settings) => ({ ...settings, [key]: value }));
    setSystemSettingsMessage('');
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="absolute inset-0 z-40 bg-black/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: 360, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 360, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="options-panel absolute right-0 top-0 z-50 flex h-full w-[360px] flex-col border-l border-white/10 bg-[#0B0F19]/95 backdrop-blur-2xl"
          >
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <h2 className="text-sm font-semibold text-white">Options</h2>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 overflow-y-auto p-4">
              <SettingsRack
                title="Tampilan"
                description="Tema dan preferensi visual"
                icon={<Palette className="h-4 w-4 text-violet-300" />}
                open={openSections.appearance}
                onToggle={() => toggleSection('appearance')}
              >
                <section>
                  <div className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Tema
                  </div>
                <div className="grid grid-cols-3 gap-2">
                  {['dark', 'light', 'auto'].map((value) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => onThemeChange(value)}
                      className={`rounded-xl border px-3 py-2 text-sm capitalize ${
                        theme === value
                          ? 'border-violet-400/40 bg-violet-500/15 text-violet-200'
                          : 'border-white/10 bg-white/5 text-slate-400'
                      }`}
                    >
                      {value}
                    </button>
                  ))}
                </div>
                {theme === 'auto' && (
                  <p className="mt-3 text-xs leading-relaxed text-slate-500">
                    Auto mengikuti tema yang dipilih di Windows dan berubah saat pengaturan sistem berubah.
                  </p>
                )}
                </section>
              </SettingsRack>

              <SettingsRack
                title="Unduhan"
                description="Atur penggunaan bandwidth"
                icon={<Gauge className="h-4 w-4 text-cyan-300" />}
                open={openSections.downloads}
                onToggle={() => toggleSection('downloads')}
              >
                <section>
                  <div className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Pembatas bandwidth
                  </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={bandwidthLimit}
                  onChange={(event) => onBandwidthChange(Number(event.target.value))}
                  className="w-full accent-violet-500"
                />
                <p className="mt-2 text-xs text-slate-500">
                  {bandwidthLimit === 0
                    ? 'Unlimited transfer rate'
                    : `Cap downloads at ${bandwidthLimit} MB/s`}
                </p>
                </section>
                <label className="block text-xs text-slate-400">
                  Default jumlah bagian download
                  <select
                    value={systemSettings.split_count}
                    disabled={systemSettingsLoading || systemSettingsSaving}
                    onChange={(event) => updateSystemSetting('split_count', Number(event.target.value))}
                    className="mt-2 w-full rounded-lg border border-white/10 bg-[#080c14] px-3 py-2 text-sm text-slate-200"
                  >
                    {[1, 2, 4, 8, 16].map((count) => (
                      <option key={count} value={count}>
                        {count === 1 ? 'Nonaktif (1 koneksi)' : `${count} bagian`}
                      </option>
                    ))}
                  </select>
                  <span className="mt-1 block text-[11px] leading-relaxed text-slate-500">
                    Dipakai sebagai pilihan awal saat menambahkan unduhan baru. Pilihan masih bisa diubah
                    untuk setiap unduhan.
                  </span>
                </label>
              </SettingsRack>

              <SettingsRack
                title="Browser Integration"
                description="Hubungkan Seadot ke browser Anda"
                icon={<Globe2 className="h-4 w-4 text-cyan-300" />}
                open={openSections.extension}
                onToggle={() => toggleSection('extension')}
              >
                <div className="space-y-4">
                  <p className="text-xs leading-relaxed text-slate-400">
                    Chrome, Edge, dan Opera: aktifkan Developer mode lalu pilih Load unpacked. Firefox:
                    buka about:debugging → This Firefox → Load Temporary Add-on, lalu pilih
                    manifest.firefox.json di folder Seadot Download Capture.
                  </p>
                  <div className="rounded-lg border border-white/[0.07] bg-black/20 p-3">
                    <p className="break-all font-mono text-xs text-slate-200">
                      {extensionFolder || 'Folder extension Seadot akan ditampilkan setelah backend desktop terbaru dijalankan.'}
                    </p>
                    <button
                      type="button"
                      disabled={!extensionFolder}
                      onClick={copyExtensionFolder}
                      className="mt-2 inline-flex items-center gap-1.5 text-xs text-cyan-200 hover:text-cyan-100 disabled:opacity-40"
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Salin lokasi folder
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'chrome', name: 'Google Chrome' },
                      { id: 'edge', name: 'Microsoft Edge' },
                      { id: 'firefox', name: 'Mozilla Firefox' },
                      { id: 'opera', name: 'Opera' },
                    ].map((browser) => (
                      <button
                        key={browser.id}
                        type="button"
                        onClick={() => openExtensionManager(browser.id)}
                        className="flex min-h-14 items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                      >
                        <BrowserLogo browser={browser.id} />
                        <span>{browser.name}</span>
                      </button>
                    ))}
                  </div>
                  {extensionError && <p role="alert" className="text-xs text-rose-300">{extensionError}</p>}
                  {extensionMessage && (
                    <p className="flex items-center gap-1.5 text-xs text-emerald-300">
                      <Check className="h-3.5 w-3.5" />
                      {extensionMessage}
                    </p>
                  )}
                  <p className="text-[11px] leading-relaxed text-slate-500">
                    Firefox memuat add-on sementara dan perlu dimuat ulang setelah browser ditutup. Setelah
                    dipasang, aktifkan Auto-capture dari popup Seadot Download Capture.
                  </p>
                </div>
              </SettingsRack>

              <SettingsRack
                title="Clipboard"
                description="Tawarkan link yang disalin"
                icon={<span className="text-xs font-bold text-cyan-200">URL</span>}
                open={openSections.clipboard}
                onToggle={() => toggleSection('clipboard')}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-200">Deteksi link salinan</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">
                      Capture copied HTTP/HTTPS links and offer to add them.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onClipboardToggle}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      clipboardEnabled ? 'bg-emerald-500/20 text-emerald-200' : 'bg-white/10 text-slate-400'
                    }`}
                  >
                    {clipboardEnabled ? 'On' : 'Off'}
                  </button>
                </div>
              </SettingsRack>

              <SettingsRack
                title="Otomatisasi"
                description="Startup dan aksi setelah unduhan"
                icon={<Power className="h-4 w-4 text-amber-300" />}
                open={openSections.automation}
                onToggle={() => toggleSection('automation')}
              >
                <div className="space-y-5">
                <label className="flex items-center justify-between gap-3">
                  <span>
                    <span className="block text-sm text-slate-200">Jalankan saat login Windows</span>
                    <span className="mt-1 block text-xs text-slate-500">
                      Aktif secara default. Seadot berjalan di latar belakang.
                    </span>
                  </span>
                  <input
                    type="checkbox"
                    checked={systemSettings.auto_start}
                    disabled={systemSettingsLoading || systemSettingsSaving}
                    onChange={(event) => updateSystemSetting('auto_start', event.target.checked)}
                    className="h-4 w-4 accent-violet-500"
                  />
                </label>

                <label className="block text-xs text-slate-400">
                  Aksi setelah semua unduhan selesai
                  <select
                    value={systemSettings.completion_action}
                    disabled={systemSettingsLoading || systemSettingsSaving}
                    onChange={(event) => updateSystemSetting('completion_action', event.target.value)}
                    className="mt-2 w-full rounded-lg border border-white/10 bg-[#080c14] px-3 py-2 text-sm text-slate-200"
                  >
                    <option value="none">Tidak ada aksi</option>
                    <option value="shutdown">Matikan komputer</option>
                    <option value="sleep">Sleep</option>
                    <option value="hibernate">Hibernate</option>
                    <option value="restart">Restart komputer</option>
                  </select>
                </label>

                {systemSettings.completion_action !== 'none' && (
                  <label className="block text-xs text-slate-400">
                    Hitung mundur sebelum aksi (menit)
                    <input
                      type="number"
                      min="1"
                      max="120"
                      value={systemSettings.countdown_minutes}
                      disabled={systemSettingsLoading || systemSettingsSaving}
                      onChange={(event) => updateSystemSetting(
                        'countdown_minutes',
                        Math.min(120, Math.max(1, Number(event.target.value) || 1)),
                      )}
                      className="mt-2 w-full rounded-lg border border-white/10 bg-[#080c14] px-3 py-2 text-sm text-slate-200"
                    />
                    <span className="mt-1 block">Default: 2 menit. Bisa dibatalkan saat hitung mundur.</span>
                  </label>
                )}

                <p className="rounded-lg bg-white/[0.035] p-3 text-xs leading-relaxed text-slate-500">
                  Aksi hanya dipicu ketika antrean tidak memiliki unduhan tertunda/aktif/jeda dan sedikitnya satu unduhan berhasil. Jika semua unduhan gagal, aksi tidak dijalankan.
                </p>

                {powerAction.pending && (
                  <div className="rounded-lg border border-amber-300/20 bg-amber-300/10 p-3">
                    <p className="text-xs text-amber-100">
                      {powerAction.action} dijalankan dalam {Math.ceil(powerAction.seconds_remaining / 60)} menit
                      {' '}({powerAction.seconds_remaining} detik).
                    </p>
                    <button
                      type="button"
                      onClick={cancelPowerAction}
                      className="mt-2 rounded-lg bg-amber-200/15 px-3 py-1.5 text-xs font-semibold text-amber-100 hover:bg-amber-200/25"
                    >
                      Batalkan aksi
                    </button>
                  </div>
                )}

                </div>
              </SettingsRack>
              {systemSettingsError && (
                <p role="alert" className="text-xs text-rose-300">{systemSettingsError}</p>
              )}
              {systemSettingsMessage && (
                <p className="text-xs text-emerald-300">{systemSettingsMessage}</p>
              )}
              <button
                type="button"
                onClick={saveSystemSettings}
                disabled={systemSettingsLoading || systemSettingsSaving}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-500/20 px-3 py-2 text-sm font-semibold text-violet-100 hover:bg-violet-500/30 disabled:opacity-50"
              >
                <RotateCw className="h-3.5 w-3.5" />
                {systemSettingsSaving ? 'Menyimpan...' : 'Simpan pengaturan'}
              </button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
