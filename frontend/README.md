# Frontend — Absensi App

Aplikasi mobile absensi (Expo Router + TypeScript) dengan verifikasi wajah
(anti-spoofing + face recognition) dan lokasi GPS.

## Struktur Folder

```
frontend/
└── src/
    ├── app/                          → layar aplikasi (Expo Router, 1 file = 1 route)
    │   ├── _layout.tsx               → root layout (Stack + SafeAreaProvider)
    │   ├── index.tsx                 → halaman utama (tombol Absen Masuk/Pulang)
    │   ├── camera.tsx                → ambil foto absensi
    │   └── history.tsx               → riwayat absensi (data dari server)
    ├── hooks/
    │   └── useAttendanceFlow.ts      → logic bisnis alur absensi (lokasi -> verifikasi -> simpan)
    ├── services/
    │   ├── faceVerificationService.ts → panggil API backend (recognizeFace, API_BASE_URL)
    │   ├── locationService.ts         → ambil lokasi GPS dengan timeout
    │   └── attendanceService.ts       → TIDAK terpakai lagi (peninggalan versi local-storage, aman dihapus)
    └── utils/
        └── dateUtils.ts               → format tanggal/jam Bahasa Indonesia
```

## Cara Kerja Singkat

1. User pilih **Absen Masuk** atau **Absen Pulang** di halaman utama
2. Kamera depan aktif, ambil foto selfie
3. Lokasi GPS diambil, lalu foto+type+lokasi dikirim sekaligus ke backend
4. Backend jalankan anti-spoofing + pengenalan wajah, simpan hasilnya
5. App menampilkan hasil: nama karyawan (kalau dikenali) atau pesan gagal

**Penting:** server (backend) adalah satu-satunya sumber data absensi.
Aplikasi ini tidak menyimpan riwayat apa pun secara lokal di HP — layar
History selalu mengambil data langsung dari `GET /api/attendance-logs`.

## Step 1 — Install Dependencies

```bash
cd frontend
npm install
```

## Step 2 — Sambungkan ke Backend

Buka `src/services/faceVerificationService.ts`, ganti baris ini dengan IP
lokal komputer tempat backend dijalankan (lihat `backend/README.md` Step 3):

```typescript
export const API_BASE_URL = "http://IP_KOMPUTER_KAMU:8000";
```

**Jangan pakai `localhost`** — itu tidak akan terjangkau dari HP.

## Step 3 — Jalankan

```bash
npx expo start
```

Scan QR code dengan **Expo Go** di HP. Pastikan HP dan komputer terhubung
ke **WiFi yang sama** dengan backend.

## Requirement

- Backend harus sudah jalan duluan (lihat `backend/README.md`)
- Minimal 1 karyawan sudah terdaftar (`POST /api/employees` di backend),
  kalau belum ada karyawan terdaftar, absen akan selalu `no_match`

## Troubleshooting

| Masalah | Solusi |
|---|---|
| "Verifikasi Gagal — tidak bisa menghubungi server" | Cek `API_BASE_URL` sudah IP yang benar (bukan `localhost`), dan HP+komputer satu WiFi |
| Wajah selalu "Tidak Dikenali" | Pastikan sudah ada karyawan terdaftar di backend, coba enrollment ulang dengan foto lebih jelas |
| Warning `SafeAreaView` deprecated | Sudah ditangani — pastikan import dari `react-native-safe-area-context`, bukan `react-native` |
| Error `Unsupported FormDataPart implementation` | Pastikan pakai `new File(uri)` dari `expo-file-system`, bukan `fetch(uri).blob()` atau object `{uri, name, type}` |
