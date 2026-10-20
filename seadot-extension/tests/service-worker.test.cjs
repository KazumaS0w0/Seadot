const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const extensionDir = path.resolve(__dirname, '..');

function loadServiceWorker({
  settings = {},
  fetch = async () => ({ ok: true, json: async () => ({ accepted: true, download_id: 'test-id' }) }),
  permissionGranted = false,
  cookies = [],
  cancel = async () => {},
} = {}) {
  const source = fs.readFileSync(path.join(extensionDir, 'service-worker.js'), 'utf8');
  const canceled = [];
  let cookieReads = 0;
  const context = {
    URL,
    console,
    fetch,
    chrome: {
      runtime: { onInstalled: { addListener() {} } },
      downloads: {
        onCreated: { addListener() {} },
        async cancel(id) {
          canceled.push(id);
          await cancel(id);
        },
      },
      permissions: {
        async contains() {
          return permissionGranted;
        },
      },
      cookies: {
        async getAll() {
          cookieReads += 1;
          return cookies;
        },
      },
      storage: {
        local: {
          async get(keys) {
            return Object.fromEntries(keys.map((key) => [key, settings[key]]));
          },
          async set(values) {
            Object.assign(settings, values);
          },
        },
      },
    },
  };
  vm.runInNewContext(`${source}\nglobalThis.testCaptureDownload = captureDownload;`, context);
  return {
    captureDownload: context.testCaptureDownload,
    settings,
    canceled,
    get cookieReads() {
      return cookieReads;
    },
  };
}

test('forwards HTTP(S) download URL and filename to local bridge', async () => {
  let request;
  const { captureDownload, settings } = loadServiceWorker({
    settings: { autoCapture: true, bridgeUrl: 'http://localhost:47831/' },
    fetch: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => ({ accepted: true, download_id: 'download-123' }) };
    },
  });

  await captureDownload({
    url: 'https://example.test/files/package.zip?token=secret',
    filename: 'C:\\Users\\test\\Downloads\\package.zip',
  });

  assert.equal(request.url, 'http://localhost:47831/capture');
  assert.equal(request.options.method, 'POST');
  assert.deepEqual(JSON.parse(request.options.body), {
    url: 'https://example.test/files/package.zip?token=secret',
    filename: 'package.zip',
  });
  assert.equal(settings.lastCapture.ok, true);
  assert.equal(settings.lastCapture.downloadId, 'download-123');
  assert.equal(settings.lastCapture.browserCanceled, null);
});

test('does not forward downloads until auto-capture is enabled', async () => {
  let requested = false;
  const { captureDownload, canceled } = loadServiceWorker({
    settings: { autoCapture: false },
    fetch: async () => {
      requested = true;
      return { ok: true, json: async () => ({}) };
    },
  });

  await captureDownload({ url: 'https://example.test/file.zip' });
  assert.equal(requested, false);
  assert.deepEqual(canceled, []);
});

test('forwards cookies and referrer only after the cookie option and site permission are enabled', async () => {
  let request;
  const worker = loadServiceWorker({
    settings: { autoCapture: true, includeCookies: true },
    permissionGranted: true,
    cookies: [{ name: 'session', value: 'secret' }],
    fetch: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => ({ accepted: true, download_id: 'private-download' }) };
    },
  });

  await worker.captureDownload({
    id: 42,
    url: 'https://example.test/files/private.zip',
    referrer: 'https://example.test/account',
  });

  assert.deepEqual(JSON.parse(request.options.body), {
    url: 'https://example.test/files/private.zip',
    headers: {
      Cookie: 'session=secret',
      Referer: 'https://example.test/account',
    },
  });
  assert.equal(worker.cookieReads, 1);
  assert.deepEqual(worker.canceled, [42]);
  assert.equal(worker.settings.lastCapture.cookiesSent, true);
  assert.equal(worker.settings.lastCapture.browserCanceled, true);
});

test('does not read or send cookies when the site permission is missing', async () => {
  let request;
  const worker = loadServiceWorker({
    settings: { autoCapture: true, includeCookies: true },
    permissionGranted: false,
    cookies: [{ name: 'session', value: 'secret' }],
    fetch: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => ({ accepted: true, download_id: 'public-download' }) };
    },
  });

  await worker.captureDownload({
    url: 'https://example.test/public.zip',
    referrer: 'https://example.test/',
  });

  assert.deepEqual(JSON.parse(request.options.body), {
    url: 'https://example.test/public.zip',
  });
  assert.equal(worker.cookieReads, 0);
});

test('does not read cookies while the consent option is disabled', async () => {
  let request;
  const worker = loadServiceWorker({
    settings: { autoCapture: true, includeCookies: false },
    permissionGranted: true,
    cookies: [{ name: 'session', value: 'secret' }],
    fetch: async (url, options) => {
      request = { url, options };
      return { ok: true, json: async () => ({ accepted: true, download_id: 'public-download' }) };
    },
  });

  await worker.captureDownload({
    id: 43,
    url: 'https://example.test/public.zip',
  });

  assert.deepEqual(JSON.parse(request.options.body), {
    url: 'https://example.test/public.zip',
  });
  assert.equal(worker.cookieReads, 0);
  assert.deepEqual(worker.canceled, [43]);
});

test('does not cancel a browser download when the bridge rejects it', async () => {
  const worker = loadServiceWorker({
    settings: { autoCapture: true },
    fetch: async () => ({ ok: true, json: async () => ({ accepted: false }) }),
  });

  await assert.rejects(
    worker.captureDownload({
      id: 44,
      url: 'https://example.test/file.zip',
    }),
    /did not accept/,
  );
  assert.deepEqual(worker.canceled, []);
  assert.equal(worker.settings.lastCapture.ok, false);
});

test('ignores non-HTTP downloads and rejects non-local bridge addresses', async () => {
  let requested = false;
  const { captureDownload, settings } = loadServiceWorker({
    settings: { autoCapture: true, bridgeUrl: 'http://example.test:47831' },
    fetch: async () => {
      requested = true;
      return { ok: true, json: async () => ({}) };
    },
  });

  await captureDownload({ url: 'file:///tmp/file.zip' });
  await assert.rejects(captureDownload({ url: 'https://example.test/file.zip' }));
  assert.equal(requested, false);
  assert.equal(settings.lastCapture.ok, false);
});

test('manifest requests cookies and website access only as optional permissions', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(extensionDir, 'manifest.json'), 'utf8'));
  assert.equal(manifest.manifest_version, 3);
  assert.ok(manifest.permissions.includes('downloads'));
  assert.ok(manifest.permissions.includes('storage'));
  assert.equal(manifest.permissions.includes('cookies'), false);
  assert.ok(manifest.optional_permissions.includes('cookies'));
  assert.deepEqual(manifest.optional_host_permissions, ['http://*/*', 'https://*/*']);
  assert.equal(manifest.permissions.includes('webRequest'), false);
});

test('Firefox manifest uses background scripts and a stable Gecko id', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(extensionDir, 'manifest.firefox.json'), 'utf8'));
  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.browser_specific_settings.gecko.id, 'seadot-download-capture@seadot.local');
  assert.deepEqual(manifest.background.scripts, ['service-worker.js']);
  assert.equal('service_worker' in manifest.background, false);
});
