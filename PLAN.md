# Blueprint Proyek: Seadot (Modern Download Manager)

## Aturan Pengembangan (Workflow)
1. **Fase-per-Fase:** Eksekusi dilakukan secara bertahap (satu per satu).
2. **Stop and Report:** Setelah satu fase selesai, buat **Laporan Fase** dan perbarui checklist di `plan.md` ini sebelum lanjut ke fase berikutnya.
3. **Fokus Stabilitas:** Mengutamakan pencegahan masalah umum seperti *file corrupt* saat penggabungan *chunk*, *memory/RAM leak*, dan UI *freeze*.
4.  Ikuti stack dan struktur folder di PLAN.md, jangan diubah.

---
isi dengan [x] untuk setiap tugas yang sudah selesai dan teruji normal
## [ ] Fase 1: Setup Lingkungan & Fondasi Proyek
*Status: Pending*
- [ ] Membuat struktur direktori utama (`/seadot-backend`, `/seadot-frontend`, `/seadot-extension`).
- [ ] Inisialisasi *environment* Python (`venv`) dan instalasi dependensi inti (`fastapi`, `uvicorn`, `aiohttp`, `websockets`).
- [ ] Inisialisasi project React + Vite + TailwindCSS untuk UI.
- [ ] Membuat *script runner* (`run_dev.py`) untuk menjalankan *backend* dan *frontend* secara paralel.

## [ ] Fase 2: Core Download Engine (Python Async)
*Status: Pending*
- [ ] Membuat *class* `Downloader` untuk menangani HTTP/HTTPS requests menggunakan `aiohttp`.
- [ ] **Dynamic Chunking:** Logika pemecahan file otomatis berdasarkan ukuran dan batas koneksi maksimal.
- [ ] **Pause/Resume:** Sistem *state saving* (menyimpan file `.seadot.part`).
- [ ] **Safe Merge:** Penggabungan *chunk* berbasis *stream/block* untuk mencegah *memory leak* dan *file corrupt*.

## [ ] Fase 3: Local API, Database & Real-time Progress
*Status: Pending*
- [ ] Setup SQLite & SQLAlchemy untuk menyimpan antrean, riwayat, dan konfigurasi.
- [ ] Membangun REST API Endpoints: `POST /start`, `POST /pause`, `POST /resume`, `DELETE /remove`.
- [ ] Setup WebSockets: Mengirim metrik (kecepatan, ETA, progress) ke Frontend tiap 100ms.

## [ ] Fase 4: Frontend Development (Modern UI/UX)
*Status: Pending*
- [ ] **Tata Letak:** *Sidebar* kategori di kiri dan *Main Table* antrean di tengah (Layout ala IDM).
- [ ] **Visual Modern:** *Dark Mode*, *rounded corners*, animasi *fluid*, serta icon/logo vektor minimalis (tanpa elemen lawas).
- [ ] **Fitur Ekstra:** *Clipboard listener* (deteksi link copy-paste) dan panel *Settings* (tema, *bandwidth limiter*).

## [ ] Fase 5: Desktop Packaging & Integrasi System
*Status: Pending*
- [ ] Integrasi *desktop wrapper* (PyWebView / Electron) untuk *native window*.
- [ ] Implementasi *System Tray* (minimize ke background tanpa stop unduhan).
- [ ] Membuka *port* lokal khusus untuk komunikasi ekstensi browser.

## [ ] Fase 6: Browser Extension (Chrome & Edge)
*Status: Pending*
- [ ] Setup struktur ekstensi **Manifest V3**.
- [ ] Implementasi *background script* untuk intersep otomatis URL unduhan (video, audio, arsip).
- [ ] Mengirim payload (URL, *Headers*, *Cookies*) ke Local API Seadot via HTTP POST.
- [ ] Desain *popup* UI untuk *toggle auto-capture*.



selalu ingat apa yg sudah dilakukan sebelumnya termasuk semua fase