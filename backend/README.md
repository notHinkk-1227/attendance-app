# Backend Anti-Spoofing — Absensi App

Server FastAPI yang membungkus model resmi **Silent-Face-Anti-Spoofing**
(minivision-ai) untuk memverifikasi apakah foto yang diambil saat absensi
adalah wajah asli atau palsu (foto dari layar HP/kertas).

## Cara Kerja Singkat

1. App mobile mengirim foto (multipart/form-data) ke `POST /api/verify-face`
2. Server mendeteksi wajah, crop di 2 skala berbeda, jalankan 2 model CNN kecil
3. Server balas JSON `{ is_real, score, bbox }`
4. App memutuskan lanjut simpan absensi (kalau `is_real: true`) atau minta
   ambil ulang (kalau `is_real: false`)

## Struktur Folder

```
backend/
├── main.py                        → entry point FastAPI, endpoint API
├── requirements.txt
├── src/
│   ├── predictor_service.py       → wrapper (load model sekali, cache di memori)
│   ├── anti_spoof_predict.py      → kode resmi minivision-ai (deteksi wajah + inferensi)
│   ├── generate_patches.py        → kode resmi (crop wajah sesuai skala)
│   ├── utility.py                 → helper resmi (parsing nama file model)
│   ├── model_lib/MiniFASNet.py    → arsitektur CNN resmi
│   └── data_io/                   → transform gambar resmi
└── resources/
    ├── anti_spoof_models/         → 2 file bobot model (.pth) resmi
    └── detection_model/           → model deteksi wajah RetinaFace (caffemodel)
```

Semua file di `src/` dan `resources/` diambil dari repo resmi
[minivision-ai/Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing)
tanpa modifikasi logika inti — hanya `predictor_service.py` yang baru saya
tulis untuk membungkusnya jadi lebih efisien untuk server (load model sekali
saat startup, bukan setiap request).

## Step 1 — Install Python & Dependencies

Butuh Python 3.10+.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Instalasi `torch` cukup besar (~1-2GB) dan makan waktu beberapa menit,
tergantung koneksi internet.

## Step 2 — Jalankan Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` **wajib** (bukan `127.0.0.1`) supaya HP di jaringan WiFi
yang sama bisa mengakses server ini, bukan cuma dari komputer itu sendiri.

Cek server sudah jalan dengan buka `http://localhost:8000/health` di
browser — harusnya muncul `{"status":"ok","model_ready":true}`.

## Step 3 — Cari IP Lokal Komputer

App di HP perlu tahu alamat IP komputer kamu di jaringan WiFi (bukan
`localhost`, karena itu cuma berlaku di komputer itu sendiri).

- **Windows**: `ipconfig` → lihat "IPv4 Address"
- **Mac/Linux**: `ifconfig` atau `ip addr` → biasanya `192.168.x.x`

Catat IP ini (misal `192.168.1.10`), akan dipakai di sisi frontend.

## Step 4 — Test Manual (opsional tapi disarankan)

```bash
curl -X POST http://localhost:8000/api/verify-face \
  -F "file=@/path/ke/foto/wajah.jpg"
```

Harusnya balas JSON seperti:
```json
{"is_real": true, "score": 0.99, "bbox": {"x": 106, "y": 147, "width": 207, "height": 213}}
```

## Catatan Penting

- **Hanya untuk development/testing.** Untuk production: batasi
  `allow_origins` di `main.py` (sekarang `"*"`), tambahkan HTTPS, dan
  pertimbangkan autentikasi API key supaya endpoint tidak bisa diakses
  sembarang orang.
- **HP dan komputer wajib satu jaringan WiFi** — sama seperti requirement
  Expo Go sebelumnya.
- Kalau nanti mau di-deploy ke cloud (Railway, Render, VPS, dst.), ganti
  `API_BASE_URL` di frontend ke domain/IP publik server tersebut.
- File model (`.pth` dan `.caffemodel`) sekitar 5MB total, sudah termasuk
  di folder `resources/` — tidak perlu download terpisah.

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `pip install` gagal karena `torch` kehabisan disk | Pastikan ada minimal ~3GB ruang kosong |
| HP tidak bisa connect ke server | Pastikan `--host 0.0.0.0` (bukan default `127.0.0.1`), dan HP+komputer satu WiFi |
| Response lambat (>5 detik) | Wajar untuk CPU inference pertama kali (model warm-up saat startup harusnya sudah menghindari ini di request pertama) |
| `model_ready: false` terus | Cek log terminal, kemungkinan file `.pth`/`.caffemodel` corrupt atau path salah |
