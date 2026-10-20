# 🚀 Seadot Backend API

Backend lokal Seadot dibangun dengan FastAPI, `aiohttp`, dan SQLite. Backend menyediakan REST API untuk mengelola unduhan, WebSocket untuk pembaruan status, serta extension bridge lokal untuk browser.

## Fitur

- Streaming unduhan dengan penggunaan memori yang terjaga.
- HTTP Range dan unduhan multi-bagian bila server sumber mendukungnya, dengan fallback ke streaming biasa.
- Pause, resume, status progres, riwayat, dan statistik unduhan.
- Pengelompokan file ke folder kategori di Downloads Windows.
- Extension bridge localhost untuk Chrome, Edge, Opera, dan Firefox.
- Pengaturan bandwidth, jumlah bagian, dan aksi opsional setelah antrean selesai.

## Menjalankan di Windows

Buka PowerShell dari root repository:

```powershell
Set-Location .\seadot-backend
python -m pip install -r requirements.txt
python run_dev.py
```

Server API secara default berjalan di `http://127.0.0.1:8000`. Dokumentasi interaktif tersedia di:

- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>
- Health check: <http://127.0.0.1:8000/api/health>

Konfigurasi opsional melalui environment variable: `HOST` (default `127.0.0.1`), `PORT` (default `8000`), `RELOAD` (default `false`), dan `WORKERS` (default `1`).

## API utama

Semua endpoint di bawah menggunakan base URL `http://127.0.0.1:8000`.

| Method | Endpoint | Keterangan |
| --- | --- | --- |
| `GET` | `/api/health` | Status backend |
| `POST` | `/api/downloads/create` | Buat dan langsung mulai unduhan |
| `GET` | `/api/downloads` | Daftar unduhan; filter opsional `status_filter` |
| `GET` | `/api/downloads/{download_id}` | Status/progres unduhan |
| `PUT` | `/api/downloads/{download_id}/options` | Atur opsi unduhan |
| `POST` | `/api/downloads/start?download_id=...` | Mulai record yang sudah ada |
| `POST` | `/api/downloads/pause?download_id=...` | Jeda unduhan aktif |
| `POST` | `/api/downloads/resume?download_id=...` | Lanjutkan unduhan |
| `DELETE` | `/api/downloads/{download_id}?delete_file=false` | Hapus record; file tidak dihapus secara default |
| `GET` | `/api/downloads/history` | Riwayat unduhan |
| `GET` | `/api/stats` | Statistik unduhan |
| `GET` | `/api/downloads/categories` | Daftar folder kategori |
| `GET` | `/api/system/settings` | Baca pengaturan sistem |
| `PUT` | `/api/system/settings` | Simpan pengaturan sistem |
| `GET` | `/api/system/action` | Status aksi daya tertunda |
| `POST` | `/api/system/action/cancel` | Batalkan aksi daya |
| `WS` | `/ws/{download_id}` | Pembaruan unduhan real-time |

### Membuat unduhan

`POST /api/downloads/create` membuat record sekaligus menjadwalkan transfer. `filename`, `category`, dan `destination_folder` dapat dihilangkan; backend menentukan nama/kategori/folder dari URL dan pengaturan folder.

```powershell
$body = @{
    url = "https://example.com/archive.zip"
    filename = "archive.zip"
    split_count = 4
    conflict_policy = "number"
} | ConvertTo-Json

$download = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/downloads/create" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$download
```

`split_count` menerima nilai 1–16 (UI menyediakan 1, 2, 4, 8, atau 16). `conflict_policy` dapat berupa `number` atau `overwrite`; tanpa kebijakan tersebut, nama file yang sudah ada menghasilkan HTTP 409. URL harus menggunakan HTTP atau HTTPS.

### Membuat record lalu mengendalikan lifecycle

Untuk memanggil `start`, `pause`, atau `resume` secara terpisah, buat record pending melalui endpoint kompatibilitas:

```powershell
$id = "qa-demo-01"
$record = @{
    download_id = $id
    url = "https://example.com/archive.zip"
    dest_path = "$HOME\Downloads\archive.zip"
    status = "pending"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/download/create" `
    -Method Post -ContentType "application/json" -Body $record

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/downloads/start?download_id=$id" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/downloads/pause?download_id=$id" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/downloads/resume?download_id=$id" -Method Post
```

### Opsi unduhan

`PUT /api/downloads/{download_id}/options` menerima objek JSON berikut:

```json
{
  "speed_limit_bps": 0,
  "split_count": 4,
  "completion_action": "none",
  "countdown_minutes": 2
}
```

`speed_limit_bps: 0` berarti tanpa batas. Nilai aksi: `none`, `shutdown`, `sleep`, `hibernate`, atau `restart`. Aksi daya dan pendaftaran startup didukung pada Windows; aksi setelah unduhan memerlukan konfirmasi di UI.

## Extension bridge

Aplikasi desktop menjalankan bridge lokal pada port default `47831`. Endpoint `GET /ping` dan `GET /status` memeriksa bridge; `POST /capture` menerima link dari ekstensi browser. Pengaturan bridge dan cara memasang ekstensi dijelaskan di [README ekstensi](../seadot-extension/README.md).

Jangan mengekspos port API atau bridge ke jaringan publik tanpa menambahkan autentikasi dan pembatasan akses yang sesuai. API lokal tidak menyediakan autentikasi secara default.

## Pengujian

Dari root repository:

```powershell
python -m pytest .\seadot-backend\tests -q
python -m pytest .\seadot-backend\desktop\test_phase6.py -q
```

Skrip QA berjalan saat backend aktif, dari terminal PowerShell terpisah:

```powershell
Set-Location .\seadot-backend
python agent_resume_test.py
python agent_stress_test.py
```

`agent_stress_test.py` mengirim 10 start request bersamaan dan memantau RSS backend selama 30 detik. Kedua skrip memakai fixture file 1 GB yang dialirkan lewat loopback lokal, bukan dari server pihak ketiga, dan mencoba menghentikan transfer uji setelah selesai. Lihat output agen untuk status hasil serta peringatan cleanup.

## Aplikasi desktop

Untuk menjalankan shell desktop Windows beserta API dan extension bridge:

```powershell
Set-Location .\seadot-backend
python run_desktop.py
```

Mode headless (server lokal tanpa jendela native):

```powershell
python run_desktop.py --headless
```

---

Dibuat sebagai bagian dari [Seadot](../README.md) oleh [@KazumaS0w0](https://github.com/KazumaS0w0).
