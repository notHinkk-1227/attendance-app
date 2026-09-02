import { File } from "expo-file-system";

// Ganti sesuai IP lokal komputer tempat backend dijalankan (lihat README backend, Step 3).
// Contoh: "http://192.168.1.10:8000". JANGAN pakai "localhost" — itu tidak akan
// terjangkau dari HP karena localhost di HP merujuk ke HP itu sendiri, bukan komputer kamu.
export const API_BASE_URL = "http://192.168.100.145:8000";

export interface VerifikasiWajahResult {
  is_real: boolean;
  score: number;
  bbox: { x: number; y: number; width: number; height: number };
}

export interface RecognizeFaceResult {
  is_real: boolean;
  // "recognized" | "no_match" | "spoof_detected" | "no_face_detected"
  status: "recognized" | "no_match" | "spoof_detected" | "no_face_detected";
  employee_id: number | null;
  name: string | null;
  confidence: number | null;
  // hanya ada kalau status === "spoof_detected" atau "no_face_detected"
  message?: string;
}

/**
 * Kirim foto ke backend anti-spoofing untuk diverifikasi apakah wajah asli
 * atau palsu (foto dari layar/kertas). Ada batas waktu (timeout) supaya
 * proses tidak menggantung kalau server tidak bisa dihubungi.
 */
export async function verifikasiWajah(
  photoUri: string,
  timeoutMs = 15000
): Promise<VerifikasiWajahResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    // Class File dari expo-file-system (SDK 54+) sudah mengimplementasikan
    // interface Blob secara native, jadi bisa langsung dilampirkan ke
    // FormData TANPA konversi manual. Ini menghindari jalur lama
    // fetch(uri).blob() yang memakai RN Blob store (base64 round-trip) dan
    // berisiko merusak data biner foto — itu penyebab 400 Bad Request kemarin.
    const file = new File(photoUri);

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/verify-face`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Server merespons status ${response.status}`);
    }

    return (await response.json()) as VerifikasiWajahResult;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function recognizeFace(
  photoUri: string,
  timeoutMs = 15000
): Promise<RecognizeFaceResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
 
  try {
    const file = new File(photoUri);
 
    const formData = new FormData();
    formData.append("file", file);
 
    const response = await fetch(`${API_BASE_URL}/api/recognize-face`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
 
    if (!response.ok) {
      throw new Error(`Server merespons status ${response.status}`);
    }
 
    return (await response.json()) as RecognizeFaceResult;
  } finally {
    clearTimeout(timeoutId);
  }
}