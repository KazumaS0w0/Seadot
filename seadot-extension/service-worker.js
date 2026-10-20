const DEFAULT_BRIDGE_URL = 'http://127.0.0.1:47831';

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(['autoCapture', 'bridgeUrl', 'includeCookies']).then((settings) => {
    const defaults = {};
    if (typeof settings.autoCapture !== 'boolean') defaults.autoCapture = false;
    if (!settings.bridgeUrl) defaults.bridgeUrl = DEFAULT_BRIDGE_URL;
    if (typeof settings.includeCookies !== 'boolean') defaults.includeCookies = false;
    if (Object.keys(defaults).length) return chrome.storage.local.set(defaults);
    return undefined;
  });
});

chrome.downloads.onCreated.addListener((item) => {
  captureDownload(item).catch((error) => {
    console.error('Seadot capture failed:', error);
  });
});

async function captureDownload(item) {
  const {
    autoCapture,
    bridgeUrl = DEFAULT_BRIDGE_URL,
    includeCookies = false,
  } = await chrome.storage.local.get(['autoCapture', 'bridgeUrl', 'includeCookies']);
  if (!autoCapture || !item.url) return;

  let url;
  try {
    url = new URL(item.url);
  } catch {
    return;
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

  const filename = item.filename?.split(/[\\/]/).pop();
  const payload = { url: item.url };
  if (filename) payload.filename = filename;
  let cookiesSent = false;

  if (includeCookies) {
    const originPattern = `${url.protocol}//${url.hostname}/*`;
    const hasSitePermission = await chrome.permissions.contains({
      permissions: ['cookies'],
      origins: [originPattern],
    });
    if (hasSitePermission) {
      const cookies = await chrome.cookies.getAll({ url: item.url });
      if (cookies.length) {
        payload.headers = {
          Cookie: cookies.map(({ name, value }) => `${name}=${value}`).join('; '),
        };
        cookiesSent = true;
      }
      if (item.referrer) {
        payload.headers = { ...payload.headers, Referer: item.referrer };
      }
    }
  }

  try {
    const endpoint = normalizeBridgeUrl(bridgeUrl);
    const response = await fetch(`${endpoint}/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || `Bridge responded with ${response.status}`);
    }
    if (!result.accepted) {
      throw new Error('Seadot did not accept the download.');
    }

    let browserCanceled = null;
    let warning;
    if (result.accepted && Number.isInteger(item.id)) {
      try {
        await chrome.downloads.cancel(item.id);
        browserCanceled = true;
      } catch (error) {
        browserCanceled = false;
        warning = `Browser download could not be canceled: ${error.message}`;
        console.warn(warning);
      }
    }
    await chrome.storage.local.set({
      lastCapture: {
        ok: true,
        filename: filename || url.pathname.split('/').pop() || item.url,
        downloadId: result.download_id,
        capturedAt: Date.now(),
        cookiesSent,
        browserCanceled,
        warning,
      },
    });
  } catch (error) {
    await chrome.storage.local.set({
      lastCapture: {
        ok: false,
        filename: filename || url.pathname.split('/').pop() || item.url,
        error: error.message,
        capturedAt: Date.now(),
      },
    });
    throw error;
  }
}

function normalizeBridgeUrl(value) {
  const url = new URL(value || DEFAULT_BRIDGE_URL);
  const isLocalHost = url.hostname === '127.0.0.1' || url.hostname === 'localhost';
  if (url.protocol !== 'http:' || !isLocalHost || url.username || url.password) {
    throw new Error('Bridge URL must be a local HTTP address.');
  }
  return url.origin;
}
