import React, { useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert,
} from "react-native";
import { CameraView, useCameraPermissions, CameraCapturedPicture } from "expo-camera";
import * as Location from "expo-location";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

import { simpanAbsensi, AbsensiType } from "@/services/attendanceService";

const WARNA_AKSEN = "#2563eb";
const WARNA_AKSEN_PULANG = "#7c3aed";

export default function CameraScreen() {
  const router = useRouter();
  const { type } = useLocalSearchParams<{ type: AbsensiType }>();

  const [permission, requestPermission] = useCameraPermissions();
  const [previewUri, setPreviewUri] = useState<string | null>(null);
  const [menyimpan, setMenyimpan] = useState(false);
  const [statusSimpan, setStatusSimpan] = useState<string>("Menyimpan...");
  const cameraRef = useRef<CameraView>(null);

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.pusatKonten}>
        <View style={styles.ikonIzinLingkaran}>
          <Ionicons name="camera-outline" size={40} color={WARNA_AKSEN} />
        </View>
        <Text style={styles.judulIzin}>Izin Kamera Diperlukan</Text>
        <Text style={styles.pesanIzin}>
          Aplikasi membutuhkan akses kamera untuk mengambil foto saat absensi.
        </Text>
        <TouchableOpacity style={styles.tombolIzin} onPress={requestPermission}>
          <Text style={styles.tombolTeks}>Izinkan Akses Kamera</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  async function ambilFoto() {
    if (!cameraRef.current) return;
    const foto: CameraCapturedPicture | undefined =
      await cameraRef.current.takePictureAsync({ quality: 0.6 });
    if (foto) setPreviewUri(foto.uri);
  }

  // Ambil lokasi dengan akurasi "Balanced" (lebih cepat dari "Highest") dan
  // batas waktu maksimal, supaya proses tidak menggantung lama kalau sinyal GPS lemah.
  async function ambilLokasiDenganTimeout(timeoutMs = 6000) {
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

  async function konfirmasiSimpan() {
    if (!previewUri || !type) return;
    setMenyimpan(true);
    try {
      setStatusSimpan("Mencari lokasi...");
      const location = await ambilLokasiDenganTimeout();

      setStatusSimpan("Menyimpan foto...");
      await simpanAbsensi({ photoUri: previewUri, type, location });

      Alert.alert("Berhasil", `Absen ${type} berhasil dicatat.`, [
        { text: "OK", onPress: () => router.replace("/") },
      ]);
    } catch (err) {
      Alert.alert("Gagal", "Terjadi kesalahan saat menyimpan absensi. Coba lagi.");
    } finally {
      setMenyimpan(false);
      setStatusSimpan("Menyimpan...");
    }
  }

  if (previewUri) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.headerPreview} edges={["top"]}>
          <Text style={styles.judulPreview}>Pratinjau Foto</Text>
        </SafeAreaView>

        <View style={styles.bingkaiPreview}>
          <Image source={{ uri: previewUri }} style={styles.preview} />
        </View>

        <SafeAreaView style={styles.aksiPreview} edges={["bottom"]}>
          <TouchableOpacity
            style={[styles.tombolAksi, styles.tombolUlangi]}
            onPress={() => setPreviewUri(null)}
            disabled={menyimpan}
          >
            <Ionicons name="refresh" size={18} color="#fff" />
            <Text style={styles.tombolTeks}>Ambil Ulang</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.tombolAksi,
              styles.tombolKonfirmasi,
              { backgroundColor: type === "pulang" ? WARNA_AKSEN_PULANG : WARNA_AKSEN },
            ]}
            onPress={konfirmasiSimpan}
            disabled={menyimpan}
          >
            {menyimpan ? (
              <>
                <ActivityIndicator color="#fff" />
                <Text style={styles.tombolTeks}>{statusSimpan}</Text>
              </>
            ) : (
              <>
                <Ionicons name="checkmark-circle" size={18} color="#fff" />
                <Text style={styles.tombolTeks}>Gunakan Foto Ini</Text>
              </>
            )}
          </TouchableOpacity>
        </SafeAreaView>
      </View>
    );
  }

  const warnaBadge = type === "pulang" ? WARNA_AKSEN_PULANG : WARNA_AKSEN;

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.kamera} facing="front" />

      {/* Header transparan: tombol kembali + badge jenis absen */}
      <SafeAreaView style={styles.headerKamera} edges={["top"]}>
        <TouchableOpacity style={styles.tombolKembali} onPress={() => router.back()}>
          <Ionicons name="close" size={26} color="#fff" />
        </TouchableOpacity>
        <View style={[styles.badgeJenis, { backgroundColor: warnaBadge }]}>
          <Ionicons
            name={type === "pulang" ? "log-out-outline" : "log-in-outline"}
            size={16}
            color="#fff"
          />
          <Text style={styles.badgeTeks}>
            Absen {type === "masuk" ? "Masuk" : "Pulang"}
          </Text>
        </View>
      </SafeAreaView>

      {/* Panduan oval untuk memposisikan wajah */}
      <View pointerEvents="none" style={styles.panduanWajahWrapper}>
        <View style={styles.panduanWajah} />
        <Text style={styles.teksPanduan}>Posisikan wajah di dalam bingkai</Text>
      </View>

      {/* Tombol jepret */}
      <SafeAreaView style={styles.overlayBawah} edges={["bottom"]}>
        <TouchableOpacity style={styles.tombolJepretLuar} onPress={ambilFoto}>
          <View style={styles.tombolJepret} />
        </TouchableOpacity>
      </SafeAreaView>
    </View>
  );
}

const LEBAR_OVAL = 250;
const TINGGI_OVAL = 320;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  kamera: { flex: 1 },

  // Header di atas kamera
  headerKamera: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  tombolKembali: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(0,0,0,0.45)",
    alignItems: "center",
    justifyContent: "center",
  },
  badgeJenis: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 20,
  },
  badgeTeks: { color: "#fff", fontSize: 13, fontWeight: "700" },

  // Panduan oval wajah
  panduanWajahWrapper: {
    position: "absolute",
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  panduanWajah: {
    width: LEBAR_OVAL,
    height: TINGGI_OVAL,
    borderRadius: LEBAR_OVAL / 2,
    borderWidth: 3,
    borderColor: "rgba(255,255,255,0.85)",
    borderStyle: "dashed",
  },
  teksPanduan: {
    marginTop: 16,
    color: "rgba(255,255,255,0.9)",
    fontSize: 13,
    backgroundColor: "rgba(0,0,0,0.4)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    overflow: "hidden",
  },

  // Tombol jepret
  overlayBawah: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: "center",
    paddingBottom: 24,
  },
  tombolJepretLuar: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 4,
    borderColor: "rgba(255,255,255,0.6)",
    alignItems: "center",
    justifyContent: "center",
  },
  tombolJepret: {
    width: 66,
    height: 66,
    borderRadius: 33,
    backgroundColor: "#fff",
  },

  // Halaman preview
  headerPreview: {
    backgroundColor: "#000",
    paddingHorizontal: 20,
    paddingBottom: 12,
    paddingTop: 8,
  },
  judulPreview: { color: "#fff", fontSize: 16, fontWeight: "700" },
  bingkaiPreview: { flex: 1, padding: 16, backgroundColor: "#000" },
  preview: { flex: 1, borderRadius: 20, backgroundColor: "#111" },
  aksiPreview: {
    flexDirection: "row",
    paddingHorizontal: 16,
    paddingTop: 4,
    paddingBottom: 12,
    gap: 12,
    backgroundColor: "#000",
  },
  tombolAksi: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 15,
    borderRadius: 14,
  },
  tombolUlangi: { backgroundColor: "#3a3a3a" },
  tombolKonfirmasi: { backgroundColor: WARNA_AKSEN },
  tombolTeks: { color: "#fff", fontSize: 15, fontWeight: "700" },

  // Halaman izin kamera
  pusatKonten: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 32,
    backgroundColor: "#f5f6fa",
  },
  ikonIzinLingkaran: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: "#e8efff",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 20,
  },
  judulIzin: { fontSize: 18, fontWeight: "700", color: "#222", marginBottom: 8 },
  pesanIzin: { textAlign: "center", marginBottom: 24, fontSize: 14, color: "#666", lineHeight: 20 },
  tombolIzin: {
    backgroundColor: WARNA_AKSEN,
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 12,
  },
});