# Seadot

**Seadot** adalah aplikasi download manager desktop dengan backend FastAPI, antarmuka React, dan ekstensi browser opsional untuk mengirim unduhan ke aplikasi.

## Fitur

- Mengelola unduhan dengan progres, pause, resume, dan riwayat.
- Mengunduh secara streaming dan menggunakan HTTP Range bila server mendukungnya.
- Mengatur folder tujuan, kategori file, jumlah bagian unduhan, dan batas kecepatan.
- Integrasi ekstensi pengirim link untuk Chrome, Edge, Opera, dan Firefox.
- Pengaturan aksi opsional setelah antrean unduhan selesai.

## Struktur proyek

```text
seadot-backend/    FastAPI, mesin unduhan, API, dan aplikasi desktop Windows
seadot-frontend/   React + Vite
seadot-extension/  Ekstensi browser untuk mengirim link ke Seadot
```

## Menjalankan untuk pengembangan

Pastikan Python, Node.js, dan npm tersedia. Buka **dua terminal PowerShell** dari direktori repository.

### 1. Backend

```powershell
Set-Location .\seadot-backend
python -m pip install -r requirements.txt
python run_dev.py
```

Backend berjalan di `http://127.0.0.1:8000`. Dokumentasi API FastAPI tersedia di `http://127.0.0.1:8000/docs`.

### 2. Frontend

Di terminal kedua:

```powershell
Set-Location .\seadot-frontend
npm.cmd install
npm.cmd run dev
```

Buka alamat lokal yang ditampilkan oleh Vite di terminal.

### Aplikasi desktop Windows

Backend menyediakan runner desktop:

```powershell
Set-Location .\seadot-backend
python run_desktop.py
```

## Ekstensi browser

Ekstensi ada di folder [`seadot-extension`](./seadot-extension). Jalankan backend/extension bridge terlebih dahulu, lalu:

- **Chrome, Edge, Opera:** buka pengaturan extensions browser, aktifkan *Developer mode*, pilih **Load unpacked**, lalu pilih folder `seadot-extension`.
- **Firefox:** buka `about:debugging#/runtime/this-firefox`, pilih **Load Temporary Add-on**, lalu pilih `manifest.firefox.json`.

Auto-capture dan izin cookies bersifat opsional. Lihat [panduan ekstensi](./seadot-extension/README.md) untuk detail instalasi, privasi, dan batasannya.

## Pengujian

Dari root repository, jalankan:

```powershell
python -m pytest .\seadot-backend\tests -q
node --test .\seadot-extension\tests\service-worker.test.cjs
```

Untuk membangun dan memeriksa frontend:

```powershell
Set-Location .\seadot-frontend
npm.cmd run build
npm.cmd run lint
```

Skrip stress dan lifecycle backend serta cara menjalankannya dijelaskan di [README backend](./seadot-backend/README.md).

## Pengembang

Dibuat oleh [@KazumaS0w0](https://github.com/KazumaS0w0).

Repository: [KazumaS0w0/Seadot](https://github.com/KazumaS0w0/Seadot)
