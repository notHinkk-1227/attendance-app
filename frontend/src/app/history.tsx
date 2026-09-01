import React, { useCallback, useState } from "react";
import { View, Text, Image, FlatList, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { useFocusEffect } from "expo-router";

import { ambilSemuaAbsensi, hapusAbsensi, AbsensiRecord } from "@/services/attendanceService";
import { formatTanggalLengkap, formatJam } from "@/utils/dateUtils";

export default function HistoryScreen() {
  const [records, setRecords] = useState<AbsensiRecord[]>([]);

  const muatData = useCallback(async () => {
    const data = await ambilSemuaAbsensi();
    setRecords(data);
  }, []);

  useFocusEffect(
    useCallback(() => {
      muatData();
    }, [muatData])
  );

  function konfirmasiHapus(id: string) {
    Alert.alert("Hapus Record", "Yakin ingin menghapus data absensi ini?", [
      { text: "Batal", style: "cancel" },
      {
        text: "Hapus",
        style: "destructive",
        onPress: async () => {
          await hapusAbsensi(id);
          muatData();
        },
      },
    ]);
  }

  if (records.length === 0) {
    return (
      <View style={styles.kosong}>
        <Text style={styles.teksKosong}>Belum ada riwayat absensi.</Text>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.container}
      data={records}
      keyExtractor={(item) => item.id}
      contentContainerStyle={{ padding: 16 }}
      renderItem={({ item }) => (
        <View style={styles.kartu}>
          <Image source={{ uri: item.photoUri }} style={styles.thumbnail} />
          <View style={styles.info}>
            <Text style={styles.tipe}>
              {item.type === "masuk" ? "Absen Masuk" : "Absen Pulang"}
            </Text>
            <Text style={styles.tanggal}>{formatTanggalLengkap(new Date(item.timestamp))}</Text>
            <Text style={styles.jam}>{formatJam(new Date(item.timestamp))}</Text>
            {item.location && (
              <Text style={styles.lokasi}>
                {item.location.latitude.toFixed(5)}, {item.location.longitude.toFixed(5)}
              </Text>
            )}
          </View>
          <TouchableOpacity onPress={() => konfirmasiHapus(item.id)}>
            <Text style={styles.hapus}>Hapus</Text>
          </TouchableOpacity>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f6fa" },
  kosong: { flex: 1, justifyContent: "center", alignItems: "center" },
  teksKosong: { color: "#999", fontSize: 15 },
  kartu: {
    flexDirection: "row",
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
    alignItems: "center",
    elevation: 1,
  },
  thumbnail: { width: 56, height: 56, borderRadius: 8, marginRight: 12, backgroundColor: "#ddd" },
  info: { flex: 1 },
  tipe: { fontWeight: "700", fontSize: 14, color: "#222" },
  tanggal: { fontSize: 12, color: "#666", marginTop: 2 },
  jam: { fontSize: 12, color: "#666" },
  lokasi: { fontSize: 11, color: "#999", marginTop: 2 },
  hapus: { color: "#d32f2f", fontSize: 13, marginLeft: 8 },
});
