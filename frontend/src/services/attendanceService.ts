import AsyncStorage from "@react-native-async-storage/async-storage";
import { Directory, File, Paths } from "expo-file-system";

const STORAGE_KEY = "@absensi_records";
// Direktori permanen untuk menyimpan foto absensi (menggantikan documentDirectory lama)
const photoDir = new Directory(Paths.document, "absensi_photos");

export type AbsensiType = "masuk" | "pulang";

export interface AbsensiLocation {
  latitude: number;
  longitude: number;
}

export interface AbsensiRecord {
  id: string;
  timestamp: number;
  type: AbsensiType;
  photoUri: string;
  location: AbsensiLocation | null;
}

interface SimpanAbsensiInput {
  photoUri: string;
  type: AbsensiType;
  location?: AbsensiLocation | null;
}

function pastikanDirektoriAda(): void {
  // `exists` adalah properti sinkron di API baru, bukan lagi Promise
  if (!photoDir.exists) {
    photoDir.create({ intermediates: true });
  }
}

export async function simpanAbsensi({
  photoUri,
  type,
  location,
}: SimpanAbsensiInput): Promise<AbsensiRecord> {
  pastikanDirektoriAda();

  const timestamp = Date.now();
  const namaFile = `absensi_${timestamp}.jpg`;

  // Pindahkan foto dari cache sementara ke penyimpanan permanen aplikasi.
  // `photoUri` dari kamera dibungkus jadi instance File, lalu di-copy ke tujuan.
  const sourceFile = new File(photoUri);
  const destFile = new File(photoDir, namaFile);
  await sourceFile.copy(destFile);

  const record: AbsensiRecord = {
    id: String(timestamp),
    timestamp,
    type,
    photoUri: destFile.uri,
    location: location ?? null,
  };

  const semuaRecord = await ambilSemuaAbsensi();
  semuaRecord.unshift(record); // record terbaru di paling atas

  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(semuaRecord));
  return record;
}

export async function ambilSemuaAbsensi(): Promise<AbsensiRecord[]> {
  const json = await AsyncStorage.getItem(STORAGE_KEY);
  return json ? (JSON.parse(json) as AbsensiRecord[]) : [];
}

export async function ambilAbsensiHariIni(): Promise<AbsensiRecord[]> {
  const semua = await ambilSemuaAbsensi();
  const awalHariIni = new Date();
  awalHariIni.setHours(0, 0, 0, 0);
  return semua.filter((r) => r.timestamp >= awalHariIni.getTime());
}

export async function hapusAbsensi(id: string): Promise<void> {
  const semua = await ambilSemuaAbsensi();
  const target = semua.find((r) => r.id === id);
  if (target) {
    const file = new File(target.photoUri);
    if (file.exists) {
      file.delete();
    }
  }
  const sisaRecord = semua.filter((r) => r.id !== id);
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(sisaRecord));
}
