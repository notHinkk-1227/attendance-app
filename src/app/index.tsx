import React, { useCallback, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";

import { ambilAbsensiHariIni, AbsensiRecord } from "@/services/attendanceService";
import { formatTanggalLengkap, formatJam } from "@/utils/dateUtils";

export default function Index() {
  const router = useRouter();
  const [absensiHariIni, setAbsensiHariIni] = useState<AbsensiRecord[]>([]);

  // Refresh data setiap kali halaman ini kembali menjadi fokus
  useFocusEffect(
    useCallback(() => {
      let aktif = true;
      (async () => {
        const data = await ambilAbsensiHariIni();
        if (aktif) setAbsensiHariIni(data);
      })();
      return () => {
        aktif = false;
      };
    }, [])
  );

  const recordMasuk = absensiHariIni.find((r) => r.type === "masuk");
  const recordPulang = absensiHariIni.find((r) => r.type === "pulang");
  const sudahAbsenMasuk = Boolean(recordMasuk);
  const sudahAbsenPulang = Boolean(recordPulang);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.tanggal}>{formatTanggalLengkap()}</Text>
      </View>

      <View style={styles.statusCard}>
        <StatusBaris
          label="Absen Masuk"
          sudah={sudahAbsenMasuk}
          jam={recordMasuk ? formatJam(new Date(recordMasuk.timestamp)) : null}
        />
        <StatusBaris
          label="Absen Pulang"
          sudah={sudahAbsenPulang}
          jam={recordPulang ? formatJam(new Date(recordPulang.timestamp)) : null}
        />
      </View>

      <TouchableOpacity
        style={[styles.tombol, sudahAbsenMasuk && styles.tombolNonaktif]}
        disabled={sudahAbsenMasuk}
        onPress={() => router.push({ pathname: "/camera", params: { type: "masuk" } })}
      >
        <Text style={styles.tombolTeks}>Absen Masuk</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[
          styles.tombol,
          styles.tombolPulang,
          (!sudahAbsenMasuk || sudahAbsenPulang) && styles.tombolNonaktif,
        ]}
        disabled={!sudahAbsenMasuk || sudahAbsenPulang}
        onPress={() => router.push({ pathname: "/camera", params: { type: "pulang" } })}
      >
        <Text style={styles.tombolTeks}>Absen Pulang</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.tombolSekunder} onPress={() => router.push("/history")}>
        <Text style={styles.tombolSekunderTeks}>Lihat Riwayat Absensi</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

function StatusBaris({
  label,
  sudah,
  jam,
}: {
  label: string;
  sudah: boolean;
  jam: string | null;
}) {
  return (
    <View style={styles.statusBaris}>
      <Text style={styles.statusLabel}>{label}</Text>
      <Text style={[styles.statusNilai, sudah ? styles.statusSukses : styles.statusBelum]}>
        {sudah ? jam : "Belum absen"}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f6fa", padding: 20 },
  header: { marginBottom: 20, marginTop: 10 },
  tanggal: { fontSize: 16, color: "#555" },
  statusCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    elevation: 2,
  },
  statusBaris: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
  },
  statusLabel: { fontSize: 15, color: "#333" },
  statusNilai: { fontSize: 15, fontWeight: "600" },
  statusSukses: { color: "#2e7d32" },
  statusBelum: { color: "#999" },
  tombol: {
    backgroundColor: "#2563eb",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    marginBottom: 12,
  },
  tombolPulang: { backgroundColor: "#7c3aed" },
  tombolNonaktif: { backgroundColor: "#c7c7c7" },
  tombolTeks: { color: "#fff", fontSize: 16, fontWeight: "600" },
  tombolSekunder: { alignItems: "center", marginTop: 12 },
  tombolSekunderTeks: { color: "#2563eb", fontSize: 15 },
});
