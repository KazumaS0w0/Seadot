# Seadot Browser Integration

Seadot Download Capture mengirim URL dan nama file unduhan browser ke bridge Seadot lokal saat **Auto-capture** diaktifkan. Chrome, Microsoft Edge, dan Opera menggunakan manifest Chromium `manifest.json`; Firefox memakai manifest `manifest.firefox.json` dengan background script yang kompatibel.

## Memasang untuk pengembangan

1. Jalankan Seadot desktop atau extension bridge. Port default bridge adalah `47831`.
2. **Chrome / Edge / Opera:** buka halaman extensions browser, aktifkan **Developer mode**, pilih **Load unpacked**, lalu pilih folder `seadot-extension`.
3. **Firefox:** buka `about:debugging#/runtime/this-firefox`, pilih **Load Temporary Add-on**, lalu pilih `manifest.firefox.json` di folder `seadot-extension`. Temporary add-on perlu dimuat kembali setelah Firefox ditutup.
4. Buka popup Seadot Download Capture, pastikan status bridge terhubung, lalu aktifkan **Auto-capture**. Jika Seadot menerima unduhan, unduhan browser dibatalkan dan transfer dilakukan oleh engine Seadot.
5. Opsi **Sertakan cookies & referrer** nonaktif secara default. Untuk unduhan yang perlu login, buka situsnya, aktifkan opsi, lalu klik **Izinkan cookies untuk situs ini**. Browser akan meminta izin hanya untuk host situs yang sedang dibuka.
6. Mulai unduhan HTTP/HTTPS dan periksa popup untuk hasil terakhir. Unduhan yang dialihkan tercatat pada daftar Seadot.

Alamat bridge dapat diubah ke host localhost lain atau port khusus di popup. Ekstensi hanya mengizinkan HTTP ke `localhost` atau `127.0.0.1`.

## Privasi dan batasan

- Auto-capture dan pengiriman cookies nonaktif secara default. Tanpa opsi dan izin host terpisah, hanya URL dan nama file yang dikirim.
- Cookies hanya dibaca untuk URL unduhan saat izin cookies diberikan untuk host tersebut. Referrer ikut dikirim hanya dengan opsi yang sama. Izin host dapat dicabut dari pengaturan ekstensi browser.
- Kredensial tidak disimpan di database atau riwayat. Saat redirect berpindah origin, engine menghapus Cookie, Authorization, Proxy-Authorization, dan Referer sebelum permintaan berikutnya.
- Jika bridge menolak permintaan, unduhan browser tidak dibatalkan. Setelah bridge menerima permintaan, engine Seadot menangani transfer; kegagalan transfer dapat dilihat pada status unduhan di Seadot.
- URL HTTPS tetap dikirim sebagai URL HTTPS. Isi unduhan tidak diinspeksi.

## Validasi lokal

Dari root repo, jalankan:

```powershell
node --check seadot-extension/service-worker.js
node --check seadot-extension/popup.js
node --test seadot-extension/tests/service-worker.test.cjs
python -m pytest seadot-backend/desktop/test_phase6.py
```

Validasi pemuatan penuh dilakukan secara manual di masing-masing browser. Firefox memuat extension sementara, bukan pemasangan permanen.
