import * as Location from "expo-location";

export type Koordinat = {
  latitude: number;
  longitude: number;
};

/**
 * SEBELUM refactor: function ini ada DI DALAM camera.tsx (dicampur dengan
 * logic UI kamera). Dipindah ke sini karena "cara mendapatkan lokasi GPS"
 * adalah tanggung jawab yang berbeda dari "menampilkan UI kamera" — SRP.
 *
 * Manfaat konkret setelah dipindah:
 * - Bisa dipakai ulang di layar lain (misal halaman riwayat/history yang
 *   butuh re-fetch lokasi) tanpa copy-paste kode.
 * - Bisa di-unit-test terpisah dari komponen React (tidak perlu render
 *   komponen kamera untuk test logic timeout-nya).
 *
 * Ambil lokasi dengan akurasi "Balanced" (lebih cepat dari "Highest") dan
 * batas waktu maksimal, supaya proses tidak menggantung lama kalau sinyal
 * GPS lemah.
 */
export async function ambilLokasiDenganTimeout(
  timeoutMs = 6000
): Promise<Koordinat | null> {
  try {
    const izinLokasi = await Location.requestForegroundPermissionsAsync();
    if (izinLokasi.status !== "granted") return null;

    const posisiPromise = Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    const timeoutPromise = new Promise<null>((resolve) =>
      setTimeout(() => resolve(null), timeoutMs)
    );

    const posisi = await Promise.race([posisiPromise, timeoutPromise]);
    if (!posisi) return null; // timeout tercapai, lanjut tanpa lokasi

    return {
      latitude: posisi.coords.latitude,
      longitude: posisi.coords.longitude,
    };
  } catch {
    return null; // gagal ambil lokasi tidak menggagalkan proses absen
  }
}
