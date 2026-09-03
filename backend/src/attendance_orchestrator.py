"""
AttendanceOrchestrator — Facade untuk seluruh alur "proses absensi".

SEBELUM refactor ini, seluruh alur (decode gambar -> cek anti-spoof ->
cek kecocokan wajah -> catat log) ada di dalam SATU function endpoint
`recognize_face()` di main.py (~60 baris, banyak tanggung jawab campur
jadi satu). Ini melanggar SRP.

SESUDAH refactor: seluruh alur bisnis dipindah ke class ini.
- Endpoint FastAPI di main.py jadi "thin controller": hanya terima request,
  panggil orchestrator, kembalikan response.
- Class ini bergantung ke ABSTRAKSI (`AntiSpoofChecker`, `FaceMatcher`),
  bukan ke class konkret `SpoofPredictor`/`FaceRecognitionService` -> DIP.
  Konsekuensi praktis: unit test bisa kirim FAKE/mock checker & matcher,
  tanpa perlu load model AI sungguhan.
- Class ini juga TIDAK menyentuh `db.query(...)` langsung — semua akses data
  lewat `EmployeeRepository` / `AttendanceLogRepository` -> konsisten dengan
  Repository pattern yang baru ditambahkan.

Ini disebut pola "Facade" karena dari luar (main.py), pemanggil cukup
panggil SATU method (`process_attendance`) untuk mendapat hasil akhir,
tanpa perlu tahu ada beberapa subsistem (anti-spoof, face matching,
repository) yang bekerja sama di baliknya.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .interfaces import AntiSpoofChecker, FaceMatcher
from .repositories import AttendanceLogRepository, EmployeeRepository


@dataclass
class AttendanceResult:
    """Hasil akhir 1 kali percobaan absensi — bentuk response yang konsisten."""

    is_real: bool
    status: str  # "spoof_detected" | "no_face_detected" | "recognized" | "no_match"
    employee_id: int | None = None
    name: str | None = None
    confidence: float | None = None
    message: str | None = None

    def to_dict(self) -> dict:
        # Hanya sertakan field yang relevan, sama seperti response asli di main.py
        data = {"is_real": self.is_real, "status": self.status}
        if self.employee_id is not None:
            data["employee_id"] = self.employee_id
        if self.name is not None:
            data["name"] = self.name
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.message is not None:
            data["message"] = self.message
        return data


class InvalidImageError(ValueError):
    """Dilempar kalau bytes yang dikirim bukan gambar valid."""


class AttendanceOrchestrator:
    """Menyatukan anti-spoofing + face recognition + pencatatan log absensi."""

    def __init__(
        self,
        anti_spoof_checker: AntiSpoofChecker,
        face_matcher: FaceMatcher,
    ):
        # Bergantung pada ABSTRAKSI (Protocol), bukan implementasi konkret.
        # Ini inti dari Dependency Inversion Principle.
        self.anti_spoof_checker = anti_spoof_checker
        self.face_matcher = face_matcher

    @staticmethod
    def _decode_image(raw_bytes: bytes) -> np.ndarray:
        np_arr = np.frombuffer(raw_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidImageError("File yang dikirim bukan gambar yang valid.")
        return image

    def process_attendance(
        self,
        raw_bytes: bytes,
        employee_repo: EmployeeRepository,
        log_repo: AttendanceLogRepository,
    ) -> AttendanceResult:
        """
        Alur lengkap 1 kali percobaan absensi. Dipanggil oleh endpoint
        `/api/recognize-face`.

        Tahapan (sama persis dengan alur asli, HANYA dipindah lokasinya):
          1. Decode gambar
          2. Anti-spoofing check
          3. Kalau spoof -> catat log, return early
          4. Face recognition (1:N matching)
          5. Catat log hasil akhir (recognized / no_match)
        """
        image_bgr = self._decode_image(raw_bytes)

        # --- Tahap 1: anti-spoofing ---
        spoof_result = self.anti_spoof_checker.predict(image_bgr)
        is_real = spoof_result["is_real"]

        if not is_real:
            log_repo.record(
                employee_id=None,
                is_real=False,
                confidence=spoof_result.get("score"),
                status="spoof_detected",
            )
            return AttendanceResult(
                is_real=False,
                status="spoof_detected",
                confidence=spoof_result.get("score"),
                message="Foto terdeteksi bukan wajah asli, silakan coba lagi.",
            )

        # --- Tahap 2: face recognition (1:N matching) ---
        # Catatan: face matcher pakai PIL untuk buka gambar (bukan cv2), jadi
        # kirim `raw_bytes` (bytes mentah asli), bukan `image_bgr` (hasil cv2.imdecode).
        query_embedding = self.face_matcher.extract_embedding(raw_bytes)
        if query_embedding is None:
            return AttendanceResult(
                is_real=True,
                status="no_face_detected",
                message="Wajah tidak terdeteksi dengan jelas, silakan coba lagi.",
            )

        candidates = employee_repo.get_all_as_match_candidates()
        match = self.face_matcher.find_best_match(query_embedding, candidates)

        status = "recognized" if match["matched"] else "no_match"
        log_repo.record(
            employee_id=match["employee_id"],
            is_real=True,
            confidence=match["confidence"],
            status=status,
        )

        return AttendanceResult(
            is_real=True,
            status=status,
            employee_id=match["employee_id"],
            name=match["name"],
            confidence=match["confidence"],
        )
