import { Stack } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <Stack>
        <Stack.Screen name="index" options={{ title: "Absensi" }} />
        <Stack.Screen name="camera" options={{ title: "Ambil Foto Absensi" }} />
        <Stack.Screen name="history" options={{ title: "Riwayat Absensi" }} />
    </Stack>
    </SafeAreaProvider>
  );
}
