const DEFAULT_BRIDGE_URL = 'http://127.0.0.1:47831';
const captureToggle = document.querySelector('#auto-capture');
const cookiesToggle = document.querySelector('#include-cookies');
const grantSiteAccessButton = document.querySelector('#grant-site-access');
const permissionStatus = document.querySelector('#permission-status');
const bridgeInput = document.querySelector('#bridge-url');
const connectionLabel = document.querySelector('#connection-status');
const connectionDot = document.querySelector('#connection-dot');
const lastCapture = document.querySelector('#last-capture');

async function loadSettings() {
  const settings = await chrome.storage.local.get([
    'autoCapture',
    'includeCookies',
    'bridgeUrl',
    'lastCapture',
  ]);
  captureToggle.checked = settings.autoCapture === true;
  cookiesToggle.checked = settings.includeCookies === true;
  bridgeInput.value = settings.bridgeUrl || DEFAULT_BRIDGE_URL;
  renderLastCapture(settings.lastCapture);
  await updatePermissionStatus();
  await checkConnection(bridgeInput.value);
}

async function getActiveSite() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!tab?.url) return null;

  try {
    const url = new URL(tab.url);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    return {
      hostname: url.hostname,
      originPattern: `${url.protocol}//${url.hostname}/*`,
    };
  } catch {
    return null;
  }
}

async function updatePermissionStatus() {
  const site = await getActiveSite();
  if (!site) {
    permissionStatus.textContent = 'Buka situs HTTP(S) untuk mengatur izin cookies.';
    return;
  }

  const granted = await chrome.permissions.contains({
    permissions: ['cookies'],
    origins: [site.originPattern],
  });
  permissionStatus.textContent = granted
    ? `Izin cookies aktif untuk ${site.hostname}.`
    : `Izin cookies belum diberikan untuk ${site.hostname}.`;
}

async function checkConnection(value) {
  try {
    const endpoint = normalizeBridgeUrl(value);
    const response = await fetch(`${endpoint}/ping`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    connectionLabel.textContent = result.ok
      ? `Terhubung · port ${result.port}`
      : 'Bridge tidak tersedia';
    connectionDot.className = `status-dot ${result.ok ? 'online' : 'offline'}`;
  } catch {
    connectionLabel.textContent = 'Tidak terhubung ke Seadot';
    connectionDot.className = 'status-dot offline';
  }
}

function normalizeBridgeUrl(value) {
  const url = new URL(value || DEFAULT_BRIDGE_URL);
  const isLocalHost = url.hostname === '127.0.0.1' || url.hostname === 'localhost';
  if (url.protocol !== 'http:' || !isLocalHost || url.username || url.password) {
    throw new Error('Gunakan alamat HTTP localhost.');
  }
  return url.origin;
}

function renderLastCapture(capture) {
  if (!capture) return;
  const time = new Date(capture.capturedAt).toLocaleTimeString();
  lastCapture.className = `last-capture ${capture.ok ? 'success' : 'error'}`;
  if (!capture.ok) {
    lastCapture.textContent = `Gagal: ${capture.error} · ${time}`;
    return;
  }

  const details = [
    capture.browserCanceled === false ? 'unduhan browser masih berjalan' : null,
    capture.cookiesSent ? 'cookies disertakan' : null,
    capture.warning,
  ].filter(Boolean);
  lastCapture.textContent = `Dialihkan ke Seadot: ${capture.filename} · ${time}${
    details.length ? ` · ${details.join(' · ')}` : ''
  }`;
}

captureToggle.addEventListener('change', async () => {
  await chrome.storage.local.set({ autoCapture: captureToggle.checked });
});

cookiesToggle.addEventListener('change', async () => {
  await chrome.storage.local.set({ includeCookies: cookiesToggle.checked });
  await updatePermissionStatus();
});

grantSiteAccessButton.addEventListener('click', async () => {
  const site = await getActiveSite();
  if (!site) {
    permissionStatus.textContent = 'Izin hanya dapat diberikan untuk situs HTTP(S).';
    return;
  }

  const granted = await chrome.permissions.request({
    permissions: ['cookies'],
    origins: [site.originPattern],
  });
  permissionStatus.textContent = granted
    ? `Izin cookies aktif untuk ${site.hostname}.`
    : `Izin cookies ditolak untuk ${site.hostname}.`;
});

bridgeInput.addEventListener('change', async () => {
  try {
    const bridgeUrl = normalizeBridgeUrl(bridgeInput.value);
    bridgeInput.value = bridgeUrl;
    await chrome.storage.local.set({ bridgeUrl });
    await checkConnection(bridgeUrl);
  } catch {
    bridgeInput.value = DEFAULT_BRIDGE_URL;
    connectionLabel.textContent = 'Alamat harus localhost dengan HTTP.';
    connectionDot.className = 'status-dot offline';
  }
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'local' && changes.lastCapture) {
    renderLastCapture(changes.lastCapture.newValue);
  }
});

chrome.tabs?.onActivated?.addListener(() => {
  updatePermissionStatus();
});

loadSettings();
