// Kumpulan fungsi bantu untuk format tanggal & waktu dalam Bahasa Indonesia

const NAMA_HARI = [
  "Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu",
];

const NAMA_BULAN = [
  "Januari", "Februari", "Maret", "April", "Mei", "Juni",
  "Juli", "Agustus", "September", "Oktober", "November", "Desember",
];

export function formatTanggalLengkap(date: Date = new Date()): string {
  const hari = NAMA_HARI[date.getDay()];
  const tanggal = date.getDate();
  const bulan = NAMA_BULAN[date.getMonth()];
  const tahun = date.getFullYear();
  return `${hari}, ${tanggal} ${bulan} ${tahun}`;
}

export function formatJam(date: Date = new Date()): string {
  const jam = String(date.getHours()).padStart(2, "0");
  const menit = String(date.getMinutes()).padStart(2, "0");
  const detik = String(date.getSeconds()).padStart(2, "0");
  return `${jam}:${menit}:${detik}`;
}
