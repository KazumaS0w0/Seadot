# Blueprint Proyek: Seadot (Modern Download Manager)

## Aturan Pengembangan (Workflow)
1. **Fase-per-Fase:** Eksekusi dilakukan secara bertahap (satu per satu).
2. **Stop and Report:** Setelah satu fase selesai, buat **Laporan Fase** dan perbarui checklist di `plan.md` ini sebelum lanjut ke fase berikutnya.
3. **Fokus Stabilitas:** Mengutamakan pencegahan masalah umum seperti *file corrupt* saat penggabungan *chunk*, *memory/RAM leak*, dan UI *freeze*.
4.  Ikuti stack dan struktur folder di PLAN.md, jangan diubah.

---
isi dengan [x] untuk setiap tugas yang sudah selesai dan teruji normal
## [ ] Fase 1: Setup Lingkungan & Fondasi Proyek
*Status: In Progress*
- [x] Membuat struktur direktori utama (`/seadot-backend`, `/seadot-frontend`, `/seadot-extension`).
- [x] Inisialisasi *environment* Python (`venv`) dan instalasi dependensi inti (`fastapi`, `uvicorn`, `aiohttp`, `websockets`).
- [x] Inisialisasi project React + Vite + TailwindCSS untuk UI.
- [ ] Membuat *script runner* (`run_dev.py`) untuk menjalankan *backend* dan *frontend* secara paralel.

## [x] Fase 2: Core Download Engine (Python Async)
*Status: Complete (unit tests passed)*
- [x] Membuat *class* `Downloader` untuk menangani HTTP/HTTPS requests menggunakan `aiohttp`.
- [x] **Dynamic Chunking:** Logika pemecahan file otomatis berdasarkan ukuran dan batas koneksi maksimal.
- [x] **Pause/Resume:** Sistem *state saving* (menyimpan file `.seadot.part`).
- [x] **Safe Merge:** Penggabungan *chunk* berbasis *stream/block* untuk mencegah *memory leak* dan *file corrupt*.

## [ ] Fase 3: Local API, Database & Real-time Progress
*Status: In Progress (database/API tests pass; real-time WebSocket progress remains incomplete)*
- [x] Setup SQLite & SQLAlchemy untuk menyimpan antrean, riwayat, dan konfigurasi.
- [x] Membangun REST API Endpoints: `POST /start`, `POST /pause`, `POST /resume`, `DELETE /remove`.
- [ ] Setup WebSockets: Mengirim metrik (kecepatan, ETA, progress) ke Frontend tiap 100ms.

## [x] Fase 4: Frontend Development (Modern UI/UX)
*Status: Complete (build, lint, and browser layout checks passed)*
- [x] **Tata Letak:** *Sidebar* kategori di kiri dan *Main Table* antrean di tengah (Layout ala IDM).
- [x] **Visual Modern:** *Dark Mode*, *rounded corners*, animasi *fluid*, serta icon/logo vektor minimalis (tanpa elemen lawas).
- [x] **Fitur Ekstra:** *Clipboard listener* (deteksi link copy-paste) dan panel *Settings* (tema, *bandwidth limiter*).

## [x] Fase 5: Desktop Packaging & Integrasi System
*Status: Complete (Phase 5 report and bridge smoke checks)*
- [x] Integrasi *desktop wrapper* (PyWebView / Electron) untuk *native window*.
- [x] Implementasi *System Tray* (minimize ke background tanpa stop unduhan).
- [x] Membuka *port* lokal khusus untuk komunikasi ekstensi browser.

## [ ] Fase 6: Browser Extension (Chrome & Edge)
*Status: Implementasi dan pengujian otomatis selesai; verifikasi manual Chrome/Edge masih tertunda*
- [x] Setup struktur ekstensi **Manifest V3**.
- [x] Background service worker menangkap URL unduhan HTTP/HTTPS dan meneruskannya ke bridge lokal.
- [x] Popup UI dengan toggle *auto-capture* dan status koneksi bridge.
- [x] Pengiriman cookies dan referrer hanya dengan opsi aktif serta izin host yang diminta eksplisit.
- [x] Alihkan transfer unduhan ke engine Seadot dan validasi otomatis end-to-end.
- [ ] Uji instalasi unpacked, prompt izin per situs, dan alih unduhan di Chrome serta Edge.



selalu ingat apa yg sudah dilakukan sebelumnya termasuk semua fase