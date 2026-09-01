"""
Service untuk face recognition (1:N matching).

Mengikuti pola yang sama dengan predictor_service.py yang sudah ada di
project ini: model di-load SEKALI saat startup (bukan tiap request),
lalu disimpan di memori.

PENTING — perubahan dari versi sebelumnya:
Service ini SEKARANG TIDAK terikat ke satu model tertentu (facenet-pytorch).
Model embedding (facenet-pytorch, InsightFace, dll) diinjeksikan lewat
`FaceEmbeddingBackend` dari face_backends.py. Kalau nanti perlu ganti model
(misal setelah uji akurasi dengan foto karyawan asli menunjukkan hasil
lebih baik di backend lain), yang diubah CUKUP 1 baris di konfigurasi
(lihat get_face_backend() di face_backends.py) — logika matching, endpoint,
dan database schema di file ini SAMA SEKALI TIDAK PERLU DIUBAH.

Pipeline:
  foto -> backend.extract_embedding() -> embedding vector
       -> cosine similarity ke semua embedding karyawan di DB -> match terbaik
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from .face_backends import FaceEmbeddingBackend, get_face_backend

logger = logging.getLogger(__name__)

# Threshold cosine similarity untuk menentukan match valid.
# Titik awal yang wajar untuk embedding 512-dim (facenet-pytorch maupun
# InsightFace sama-sama pakai skala serupa untuk cosine similarity).
# WAJIB di-tuning pakai data asli (foto karyawan sungguhan, di lokasi/lighting
# yang mirip kondisi pemakaian nyata) sebelum dipakai serius — dan WAJIB
# di-tuning ULANG kalau backend diganti, karena distribusi similarity tiap
# model bisa sedikit berbeda.
DEFAULT_MATCH_THRESHOLD = 0.65


class FaceRecognitionService:
    """
    Wrapper: pegang 1 backend embedding + logika matching (1:N).

    Logika matching (average_embeddings, cosine_similarity, find_best_match)
    sengaja dipisah dari backend model, karena logika ini generik dan tidak
    tergantung model embedding yang dipakai.
    """

    def __init__(
        self,
        backend: Optional[FaceEmbeddingBackend] = None,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
    ):
        # Kalau backend tidak diberikan, ambil dari konfigurasi default
        # (lihat get_face_backend di face_backends.py untuk ganti model).
        self.backend: FaceEmbeddingBackend = backend or get_face_backend("facenet")
        self.match_threshold = match_threshold
        logger.info(
            f"[FaceRecognitionService] Siap pakai backend={type(self.backend).__name__}, "
            f"threshold={self.match_threshold}"
        )

    def extract_embedding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Ambil embedding wajah dari bytes foto. Return None kalau wajah tidak terdeteksi."""
        return self.backend.extract_embedding(image_bytes)

    @staticmethod
    def average_embeddings(embeddings: list[np.ndarray]) -> np.ndarray:
        """
        Gabungkan beberapa embedding (misal dari 2-3 foto enrollment) jadi satu
        representasi yang lebih robust, dengan normalisasi ulang.
        """
        stacked = np.stack(embeddings, axis=0)
        avg = stacked.mean(axis=0)
        return avg / np.linalg.norm(avg)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        a_norm = a / np.linalg.norm(a)
        b_norm = b / np.linalg.norm(b)
        return float(np.dot(a_norm, b_norm))

    def find_best_match(
        self,
        query_embedding: np.ndarray,
        candidates: list[tuple[int, str, np.ndarray]],
    ) -> dict:
        """
        Cari kecocokan terbaik dari daftar kandidat (1:N matching).

        candidates: list of (employee_id, employee_name, embedding_vector)
        Kandidat sebaiknya sudah 1 embedding representatif per karyawan
        (hasil average_embeddings), bukan tiap-tiap embedding mentah,
        supaya hasil lebih stabil.

        Return dict: { matched, employee_id, name, confidence }
        """
        if not candidates:
            return {"matched": False, "employee_id": None, "name": None, "confidence": 0.0}

        best_score = -1.0
        best_employee_id = None
        best_name = None

        for employee_id, name, emb in candidates:
            score = self.cosine_similarity(query_embedding, emb)
            if score > best_score:
                best_score = score
                best_employee_id = employee_id
                best_name = name

        if best_score >= self.match_threshold:
            return {
                "matched": True,
                "employee_id": best_employee_id,
                "name": best_name,
                "confidence": round(best_score, 4),
            }

        # Similarity tertinggi tetap dikembalikan (confidence) untuk keperluan
        # debugging/logging, meski status akhirnya no_match.
        return {
            "matched": False,
            "employee_id": None,
            "name": None,
            "confidence": round(best_score, 4),
        }


# Instance singleton — di-load sekali saat modul ini pertama kali diimport
# (biasanya dari main.py saat startup), persis seperti predictor_service.py
#
# Backend yang dipakai ditentukan di get_face_backend() (face_backends.py).
# Untuk ganti backend: edit default di get_face_backend(), atau baca dari
# environment variable di sana — TIDAK perlu ubah baris ini.
face_recognition_service = FaceRecognitionService()