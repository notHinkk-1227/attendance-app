# Backend — Absensi App

Server FastAPI dengan 2 kemampuan utama:
1. **Anti-spoofing** — cek apakah foto wajah asli atau palsu (foto dari layar/kertas), pakai model resmi **Silent-Face-Anti-Spoofing** (minivision-ai).
2. **Face recognition** — mengenali foto itu wajah karyawan yang mana (1:N matching), pakai **InsightFace** (ArcFace).

Kedua tahap digabung jadi satu alur di endpoint `/api/recognize-face`, yang juga langsung mencatat hasilnya sebagai data absensi lengkap (foto, waktu, jenis masuk/pulang, lokasi).

## Cara Kerja Singkat

1. App mobile kirim foto + `type` (masuk/pulang) + lokasi ke `POST /api/recognize-face`
2. Server jalankan anti-spoofing dulu — kalau terdeteksi palsu, langsung ditolak (`status: "spoof_detected"`)
3. Kalau asli, server ekstrak *face embedding* dan bandingkan ke semua karyawan terdaftar
4. Server simpan **satu baris data lengkap** ke `attendance_logs` (foto, identitas, type, lokasi, status) — berhasil atau gagal, semua tercatat untuk keperluan audit
5. Server balas hasilnya ke app (`recognized` / `no_match` / `spoof_detected` / `no_face_detected`)

## Struktur Folder

```
backend/
├── main.py                          → entry point FastAPI ("thin controller", tidak ada logic bisnis)
├── requirements.txt
├── attendance.db                    → database SQLite (auto-dibuat, JANGAN di-commit ke git)
├── attendance_photos/                → foto hasil absensi tersimpan di sini (auto-dibuat)
└── src/
    ├── interfaces.py                 → kontrak (Protocol) AntiSpoofChecker & FaceMatcher
    ├── attendance_orchestrator.py    → alur bisnis lengkap 1x percobaan absensi
    ├── repositories.py               → akses database (EmployeeRepository, AttendanceLogRepository)
    ├── database.py                   → setup SQLAlchemy + init_db()
    ├── models.py                     → skema tabel (Employee, FaceEmbedding, AttendanceLog)
    ├── face_backends.py              → pilihan model embedding wajah (InsightFace / facenet-pytorch)
    ├── face_recognition_service.py   → logika matching 1:N (cosine similarity)
    ├── predictor_service.py          → wrapper anti-spoofing (load model sekali, cache di memori)
    ├── anti_spoof_predict.py         → kode resmi minivision-ai (deteksi wajah + inferensi)
    ├── generate_patches.py           → kode resmi (crop wajah sesuai skala)
    ├── utility.py                    → helper resmi (parsing nama file model)
    ├── model_lib/MiniFASNet.py       → arsitektur CNN resmi (anti-spoofing)
    └── data_io/                      → transform gambar resmi (anti-spoofing)
```

## Step 1 — Install Python & Dependencies

Butuh Python 3.10+.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: source venv/Scripts/activate
pip install -r requirements.txt
```

Instalasi `torch` + `insightface` cukup besar (~2-3GB total) dan makan waktu
beberapa menit, tergantung koneksi internet.

## Step 2 — Jalankan Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` **wajib** (bukan `127.0.0.1`) supaya HP di jaringan WiFi
yang sama bisa mengakses server ini.

Cek server sudah jalan: buka `http://localhost:8000/health` di browser —
harusnya muncul `{"status":"ok","model_ready":true}`.

## Step 3 — Cari IP Lokal Komputer

- **Windows**: `ipconfig` → lihat "IPv4 Address"
- **Mac/Linux**: `ifconfig` atau `ip addr` → biasanya `192.168.x.x`

Catat IP ini, dipakai di `API_BASE_URL` sisi frontend.

## Step 4 — Daftarkan Karyawan (Enrollment)

Sebelum bisa dikenali sistem, setiap karyawan perlu didaftarkan dulu lewat
`POST /api/employees`:

```bash
curl -X POST http://localhost:8000/api/employees \
  -F "name=Budi Santoso" \
  -F "position=Staff IT" \
  -F "photos=@/path/ke/foto1.jpg" \
  -F "photos=@/path/ke/foto2.jpg"
```

| Field | Wajib? | Keterangan |
|---|---|---|
| `name` | Ya | Nama lengkap karyawan |
| `position` | Tidak | Jabatan (boleh dikosongkan) |
| `photos` | Ya | 1-3 foto wajah, idealnya sudut sedikit berbeda |

Response sukses:
```json
{"employee_id": 1, "name": "Budi Santoso", "num_embeddings_saved": 2}
```

**Tips foto enrollment:** pencahayaan cukup, wajah menghadap depan/tidak
tertutup, tidak perlu restart server setelah mendaftarkan karyawan baru.

Cek daftar karyawan terdaftar: `curl http://localhost:8000/api/employees`

## Step 5 — Test Manual Absensi

```bash
curl -X POST http://localhost:8000/api/recognize-face \
  -F "file=@/path/ke/foto/wajah.jpg" \
  -F "type=masuk" \
  -F "latitude=-6.9147" \
  -F "longitude=107.6098"
```

Kemungkinan hasil (field `status`):

| Status | Arti |
|---|---|
| `recognized` | Wajah asli & cocok dengan karyawan terdaftar — absensi tercatat |
| `no_match` | Wajah asli tapi tidak cocok dengan karyawan manapun |
| `spoof_detected` | Foto terdeteksi bukan wajah asli (dari layar/kertas) |
| `no_face_detected` | Tidak ada wajah yang terdeteksi di foto |

Semua percobaan (termasuk yang gagal) tetap tercatat di `attendance_logs`
untuk keperluan audit.

## Endpoint Lengkap

| Method | Path | Kegunaan |
|---|---|---|
| GET | `/health` | Cek status server & model |
| POST | `/api/employees` | Daftarkan karyawan baru + foto wajah |
| GET | `/api/employees` | Daftar karyawan terdaftar |
| POST | `/api/recognize-face` | Proses absensi (anti-spoof + recognition + simpan) |
| GET | `/api/attendance-logs` | Riwayat absensi (dipakai layar History di app) |
| DELETE | `/api/attendance-logs/{id}` | Hapus satu record absensi + foto terkait |
| POST | `/api/verify-face` | Endpoint lama, cuma anti-spoofing tanpa identifikasi (dipertahankan untuk kompatibilitas) |

## Catatan Penting

- **Hanya untuk development/testing.** Untuk production: batasi
  `allow_origins` di `main.py`, tambahkan HTTPS, dan autentikasi API key.
- **`attendance.db` dan `attendance_photos/` berisi data biometrik & foto
  asli karyawan — JANGAN pernah di-commit ke git**, pastikan ada di
  `.gitignore`. Kalau tidak sengaja ter-commit, hapus dari git history
  (bukan cuma dari commit terbaru) pakai `git filter-repo`.
- **HP dan komputer wajib satu jaringan WiFi.**
- Threshold pengenalan wajah (`DEFAULT_MATCH_THRESHOLD` di
  `face_recognition_service.py`) adalah titik awal — **wajib** ditest ulang
  dengan foto karyawan asli sebelum dipakai serius.

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `pip install` gagal karena disk penuh | Pastikan ada minimal ~4GB ruang kosong |
| HP tidak bisa connect ke server | Pastikan `--host 0.0.0.0`, dan HP+komputer satu WiFi |
| Enrollment gagal "Tidak ada wajah terdeteksi" | Coba foto lain, pastikan wajah menghadap depan & pencahayaan cukup |
| Wajah asli tidak dikenali (`no_match`) terus | Cek `confidence` di response — kalau selalu rendah, threshold mungkin perlu diturunkan, atau enrollment ulang dengan foto lebih jelas |
| `model_ready: false` terus | Cek log terminal, kemungkinan file model corrupt atau path salah |
