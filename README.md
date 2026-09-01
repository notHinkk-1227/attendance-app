# Absensi App

Aplikasi absensi berbasis foto (dengan verifikasi anti-spoofing wajah) dan lokasi, terdiri dari 2 bagian:

- **`frontend/`** — Aplikasi mobile (Expo / React Native)
- **`backend/`** — Server API (FastAPI + Python) untuk verifikasi wajah asli/palsu

## Struktur Folder

```
absensi-app/
├── frontend/     → Aplikasi mobile (Expo Router)
├── backend/      → API anti-spoofing wajah (FastAPI)
└── README.md     → File ini
```

Detail lebih lengkap masing-masing bagian ada di README di dalam folder masing-masing:
- [`frontend/README.md`](./frontend/README.md)
- [`backend/README.md`](./backend/README.md)

## Cara Menjalankan Project

Project ini butuh **backend jalan dulu**, baru **frontend** bisa terhubung dengannya.

### 1. Jalankan Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Cek berhasil dengan buka `http://localhost:8000/health` di browser — harus muncul:
```json
{"status": "ok", "model_ready": true}
```

> Catatan: install `torch` cukup besar (~1-2GB) dan makan waktu beberapa menit tergantung koneksi internet.

### 2. Cari IP Lokal Komputer

HP kamu perlu tahu alamat IP komputer di jaringan WiFi yang sama (bukan `localhost`):

- **Windows**: `ipconfig` → lihat "IPv4 Address"
- **Mac/Linux**: `ifconfig` atau `ip addr` → biasanya berbentuk `192.168.x.x`

### 3. Jalankan Frontend

```bash
cd frontend
npm install
npx expo start
```

Scan QR code yang muncul dengan aplikasi **Expo Go** di HP. Pastikan HP dan komputer terhubung ke **WiFi yang sama**, dan sesuaikan alamat API (IP backend) di kode frontend sesuai IP yang didapat di langkah 2.

## Requirement

| Kebutuhan | Versi minimum |
|---|---|
| Node.js | LTS terbaru |
| Python | 3.10+ |
| Expo Go (di HP) | Versi terbaru dari App Store / Play Store |
| Ruang disk kosong | ~3GB (untuk dependency `torch` di backend) |

## Catatan Penting

- Backend saat ini hanya untuk **development/testing** — `CORS` masih mengizinkan semua origin (`*`). Untuk production, batasi ke domain/IP tertentu dan tambahkan autentikasi.
- Model anti-spoofing (`.pth` dan `.caffemodel`) sudah termasuk di `backend/resources/` (~5MB), tidak perlu download terpisah.
- File besar seperti `node_modules/` dan `venv/` sudah di-ignore lewat `.gitignore` di root — jangan commit folder tersebut.

## Troubleshooting

| Masalah | Solusi |
|---|---|
| HP tidak bisa connect ke backend | Pastikan backend dijalankan dengan `--host 0.0.0.0` (bukan `127.0.0.1`), dan HP + komputer satu jaringan WiFi |
| `pip install` gagal / disk penuh | Pastikan ada minimal ~3GB ruang kosong sebelum install `torch` |
| Response verifikasi wajah lambat | Wajar untuk inference CPU pertama kali; model sudah di-*warm up* saat backend startup |
| `npm install` error | Pastikan Node.js versi LTS terbaru terpasang, hapus `node_modules/` dan `package-lock.json` lalu install ulang jika perlu |