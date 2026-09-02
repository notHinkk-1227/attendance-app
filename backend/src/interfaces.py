"""
Abstraksi (kontrak) yang dipakai oleh AttendanceOrchestrator.

Kenapa file ini penting untuk DIP (Dependency Inversion Principle):
Tanpa file ini, `AttendanceOrchestrator` akan bergantung LANGSUNG ke class
konkret `SpoofPredictor` dan `FaceRecognitionService`. Itu artinya:
  - Susah di-unit-test (harus load model AI sungguhan tiap test)
  - Susah diganti (misal mau pakai anti-spoof provider lain / mock untuk CI)

Dengan Protocol di bawah, orchestrator cukup tahu "bentuk" (interface) yang
dibutuhkan, bukan implementasi konkretnya. Ini pola yang SAMA dengan yang
sudah dipakai project ini di `face_backends.py` (FaceEmbeddingBackend) —
jadi konsisten dengan gaya desain yang sudah ada.

Python tidak punya `interface` seperti Java/C#, jadi kita pakai
`typing.Protocol` — ini disebut "structural typing" / "duck typing yang
di-declare": class apapun yang punya method dengan signature cocok otomatis
dianggap valid, TANPA perlu explicit `implements`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class AntiSpoofChecker(Protocol):
    """Kontrak untuk komponen yang bisa mengecek asli/palsu (anti-spoofing).

    `SpoofPredictor` (predictor_service.py) sudah otomatis memenuhi kontrak
    ini karena sudah punya method `predict(image) -> dict` dengan bentuk
    yang sama. Tidak perlu mengubah kode SpoofPredictor sama sekali.
    """

    def predict(self, image_bgr: np.ndarray) -> dict:
        """Return dict berisi minimal: {"is_real": bool, "score": float, "bbox": dict}."""
        ...


@runtime_checkable
class FaceMatcher(Protocol):
    """Kontrak untuk komponen yang bisa ekstrak embedding & mencocokkan wajah.

    `FaceRecognitionService` (face_recognition_service.py) sudah memenuhi
    kontrak ini secara otomatis.
    """

    def extract_embedding(self, image_bytes: bytes) -> np.ndarray | None: ...

    def average_embeddings(self, embeddings: list[np.ndarray]) -> np.ndarray: ...

    def find_best_match(
        self,
        query_embedding: np.ndarray,
        candidates: list[tuple[int, str, np.ndarray]],
    ) -> dict: ...
