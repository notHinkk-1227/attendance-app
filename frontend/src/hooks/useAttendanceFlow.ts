import { useState } from "react";
import { Alert } from "react-native";
import { useRouter } from "expo-router";

import { simpanAbsensi, AbsensiType } from "@/services/attendanceService";
import { recognizeFace } from "@/services/faceVerificationService";
import { ambilLokasiDenganTimeout } from "@/services/locationService";

/**
 * useAttendanceFlow — custom hook yang membungkus SELURUH alur bisnis absensi:
 * verifikasi wajah -> cek hasil -> ambil lokasi -> simpan record.
 *
 * SEBELUM refactor: seluruh logic ini (fungsi `konfirmasiSimpan`) hidup
 * LANGSUNG di dalam komponen `CameraScreen` (camera.tsx), tercampur dengan
 * JSX/render dan style. Ini melanggar SRP: satu file (`camera.tsx`) punya
 * lebih dari satu alasan untuk berubah — (1) kalau tampilan kamera berubah,
 * ATAU (2) kalau ATURAN BISNIS alur absensi berubah (misal nanti ditambah
 * validasi baru, ganti urutan tahap, dsb).
 *
 * SESUDAH refactor: logic bisnis dipindah ke hook ini. Komponen React
 * (camera.tsx) HANYA memanggil `useAttendanceFlow()` dan merender UI
 * berdasarkan state yang dikembalikan (`menyimpan`, `statusSimpan`) serta
 * memanggil `konfirmasiSimpan()` saat tombol ditekan.
 *
 * Manfaat konkret:
 * - `camera.tsx` jadi jauh lebih pendek & fokus HANYA ke rendering.
 * - Alur bisnis ini sekarang bisa dipakai ulang di layar lain (misal kalau
 *   nanti ada mode "absen tanpa preview foto") tanpa duplikasi logic.
 * - Lebih mudah di-test: hook ini bisa di-test dengan
 *   `@testing-library/react-hooks` tanpa perlu render UI kamera sungguhan.
 */
export function useAttendanceFlow(previewUri: string | null, type: AbsensiType | undefined) {
  const router = useRouter();
  const [menyimpan, setMenyimpan] = useState(false);
  const [statusSimpan, setStatusSimpan] = useState<string>("Menyimpan...");

  async function konfirmasiSimpan() {
    if (!previewUri || !type) return;
    setMenyimpan(true);
    try {
      setStatusSimpan("Memverifikasi wajah...");
      let hasilRecognize;
      try {
        hasilRecognize = await recognizeFace(previewUri);
      } catch (errRecognize) {
        Alert.alert(
          "Verifikasi Gagal",
          "Tidak bisa menghubungi server verifikasi wajah. Pastikan HP dan server terhubung ke jaringan yang sama, lalu coba lagi."
        );
        return;
      }

      if (!hasilRecognize.is_real) {
        // status === "spoof_detected" — foto terdeteksi bukan wajah asli, minta ambil ulang
        Alert.alert("Gagal", hasilRecognize.message ?? "Wajah tidak valid, coba lagi.");
        return;
      }

      if (hasilRecognize.status === "no_match") {
        Alert.alert("Tidak Dikenali", "Wajah tidak cocok dengan data karyawan manapun.");
        return;
      }

      if (hasilRecognize.status === "no_face_detected") {
        Alert.alert("Gagal", hasilRecognize.message ?? "Wajah tidak terdeteksi, coba lagi.");
        return;
      }

      // status === "recognized"
      setStatusSimpan("Mencari lokasi...");
      const location = await ambilLokasiDenganTimeout();

      setStatusSimpan("Menyimpan foto...");
      await simpanAbsensi({ photoUri: previewUri, type, location });

      Alert.alert(
        "Absensi Berhasil",
        `Selamat datang, ${hasilRecognize.name}! Absen ${type} berhasil dicatat.`,
        [{ text: "OK", onPress: () => router.replace("/") }]
      );
    } catch (err) {
      Alert.alert("Gagal", "Terjadi kesalahan saat menyimpan absensi. Coba lagi.");
    } finally {
      setMenyimpan(false);
      setStatusSimpan("Menyimpan...");
    }
  }

  return { menyimpan, statusSimpan, konfirmasiSimpan };
}
