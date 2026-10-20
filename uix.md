Berperanlah sebagai Spesialis Frontend & UI/UX Engineer yang ahli dalam merancang antarmuka modern menggunakan React, Tailwind CSS, dan Framer Motion. 

Tugas utama kamu adalah membaca dan menganalisis file `plan.md`. Lakukan implementasi UI/UX khusus untuk Fase 4 (Seadot Desktop Client) dengan mengacu pada ketentuan berikut:

Arah Visual & Tata Letak (Modernisasi Ala IDM):
1. Mengambil DNA fungsional dari IDM (Internet Download Manager) tetapi dirombak total menjadi antarmuka modern yang futuristik, estetik, dan minimalis.
2. Skema Warna (Dark Mode): Gunakan warna dasar gelap yang elegan (contoh: Deep Slate/Near-Black #0F0F11 atau #0B0F19) dipadukan dengan aksen neon yang lembut (seperti Electric Violet, Cyan, dan Emerald Green untuk status aktif/unduhan).
3. Efek Visual: Terapkan rounded corners yang konsisten (12px - 16px), border tipis bernuansa glassmorphism, serta efek bayangan/backlight yang halus saat item di-hover. Gunakan library seperti Lucide Icons untuk semua ikon minimalis.
4. Layout Utama:
   - Sidebar Kiri: Menu kategori (All Downloads, In Progress, Completed, Queues, dll.) dengan indikator lencana (badge) berisi angka. Pada bagian bawah, tampilkan panel ringkas "Settings" (untuk Tema, Bandwidth Limiter) dan toggle "Clipboard Listener".
   - Top Action Bar: Toolbar di atas tabel utama yang menampung tombol aksi modern nan ikonik (Add Link dengan icon "+", Resume, Pause, Stop, Remove, Options) lengkap dengan kolom pencarian & filter di kanan.
   - Main Table (Antrean Tengah): Tabel interaktif dengan kolom File Name (berdasarkan icon format file seperti MP4, ZIP, EXE), Size, Progress (gunakan visual Progress Bar gradient yang mulus, dinamis, dan menampilkan persentase serta kecepatan unduh, misal: '74% @ 8.2 MB/s'), Time Left, Transfer Rate, dan Date Added. 
   - Status Bar Bawah: Area mungil di bagian bawah layar untuk total kecepatan download (misal: "Total Speed: 48.5 MB/s") lengkap dengan grafik visualisator gelombang (wave) kecil yang menandakan aktivitas jaringan yang aktif.

Fungsionalitas & Animasi:
- Tambahkan animasi fluid (micro-interactions) menggunakan Framer Motion saat berpindah tab, hover tombol, atau saat mengaktifkan toggle/fitur baru.
- Buat tampilan transisi yang luwes saat baris antrean unduhan bertambah, dihapus, atau berubah status.

Ketentuan Pelaksanaan:
- Lakukan implementasi kode hanya berdasarkan instruksi di file `plan.md` dan panduan visual di atas.
- Selesaikan seluruh komponen UI, Sidebar, Main Table, serta panel Settings/Clipboard Listener pendukung tanpa mengorbankan kualitas visualnya.
- Jika sudah selesai, segera hentikan proses dan buatkan laporan ringkas tentang komponen visual apa saja yang sudah terpasang.

Aturan Sangat Penting: 
Jangan lakukan testing, debugging lanjutan, atau mencoba menjalankan aplikasi. Hentikan pekerjaan tepat setelah kode selesai ditulis dan laporan dibuat. Untuk fase testing, tunggu perintah selanjutnya dari saya.