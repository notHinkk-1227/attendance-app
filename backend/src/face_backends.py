"""
Abstraksi backend untuk ekstraksi face embedding.

TUJUAN: supaya kalau nanti perlu ganti model (misal dari facenet-pytorch ke
InsightFace karena alasan akurasi atau maintenance), yang diubah CUKUP file
ini + 1 baris konfigurasi — tidak perlu sentuh main.py, database schema,
atau endpoint sama sekali.

Semua backend WAJIB mengikuti kontrak yang sama:
- Input : bytes foto mentah (JPEG/PNG)
- Output: np.ndarray 1-dimensi (embedding), atau None kalau tidak ada
          wajah terdeteksi di foto

Cara kerja pemilihan backend: lihat FACE_BACKEND di bagian bawah file ini,
atau di config/environment variable saat production nanti.
"""

from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class FaceEmbeddingBackend(ABC):
    """Kontrak yang harus dipenuhi semua backend embedding wajah."""

    @abstractmethod
    def extract_embedding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Return embedding (np.ndarray) dari foto, atau None kalau wajah tidak terdeteksi."""
        raise NotImplementedError

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimensi vektor embedding yang dihasilkan backend ini (misal 512)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Backend 1: facenet-pytorch (MTCNN + InceptionResnetV1)
# ---------------------------------------------------------------------------
class FacenetPytorchBackend(FaceEmbeddingBackend):
    """
    Backend berbasis facenet-pytorch. Dipilih sebagai default karena:
    - Backend sudah pakai PyTorch (untuk anti-spoofing) -> tidak nambah
      runtime/dependency stack baru
    - Studi pada wajah Indonesia menunjukkan model berbasis FaceNet
      (khususnya Facenet512) bisa lebih akurat dibanding ArcFace untuk
      populasi ini -> perlu divalidasi ulang dengan data karyawan asli,
      tapi ini bukan pilihan yang lemah secara default

    Install: pip install facenet-pytorch
    """

    def __init__(self):
        import torch
        from facenet_pytorch import MTCNN, InceptionResnetV1

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"[FacenetPytorchBackend] Loading model on device={self.device}")

        self.mtcnn = MTCNN(image_size=160, margin=0, keep_all=False, device=self.device)
        self.resnet = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)
        self._torch = torch
        logger.info("[FacenetPytorchBackend] Model siap.")

    @property
    def embedding_dim(self) -> int:
        return 512

    def extract_embedding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            logger.warning(f"Gagal membuka gambar: {e}")
            return None

        face_tensor = self.mtcnn(img)
        if face_tensor is None:
            return None

        with self._torch.no_grad():
            embedding = self.resnet(face_tensor.unsqueeze(0).to(self.device))

        return embedding.squeeze(0).cpu().numpy()


# ---------------------------------------------------------------------------
# Backend 2: InsightFace (ArcFace / buffalo models)
# ---------------------------------------------------------------------------
class InsightFaceBackend(FaceEmbeddingBackend):
    """
    Backend berbasis InsightFace (model buffalo_l/buffalo_sc, ArcFace).

    Kapan pindah ke sini:
    - Kalau uji akurasi dengan data karyawan asli menunjukkan InsightFace
      lebih baik dari facenet-pytorch untuk kasus kamu
    - Kalau butuh dukungan komunitas/maintenance yang lebih aktif jangka
      panjang (InsightFace lebih sering di-update dibanding facenet-pytorch)

    Install: pip install insightface onnxruntime
    (Sejak InsightFace 1.0.1, instalasi dasar sudah tidak butuh C++ build
    tools lagi di kebanyakan kasus — ekstensi face3d opsional tidak lagi
    di-build default.)

    CATATAN: backend ini pakai ONNX Runtime, bukan PyTorch — artinya kalau
    dipilih, project akan punya 2 runtime inferensi berjalan bersamaan
    (torch untuk anti-spoof, onnxruntime untuk recognition). Ini bukan
    masalah besar, hanya menambah sedikit footprint memori.
    """

    def __init__(self, model_name: str = "buffalo_sc", ctx_id: int = -1):
        """
        model_name: "buffalo_sc" (ringan, cocok CPU) atau "buffalo_l" (lebih
                    akurat, lebih berat) — pilih sesuai hasil uji akurasi.
        ctx_id: -1 untuk CPU, 0+ untuk GPU
        """
        from insightface.app import FaceAnalysis

        logger.info(f"[InsightFaceBackend] Loading model={model_name}")
        self.app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        logger.info("[InsightFaceBackend] Model siap.")

    @property
    def embedding_dim(self) -> int:
        return 512

    def extract_embedding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(img)[:, :, ::-1]  # RGB -> BGR (format InsightFace)
        except Exception as e:
            logger.warning(f"Gagal membuka gambar: {e}")
            return None

        faces = self.app.get(img_array)
        if not faces:
            return None

        # Ambil wajah dengan bounding box terbesar (paling dominan di foto)
        largest_face = max(
            faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
        )
        return largest_face.normed_embedding


# ---------------------------------------------------------------------------
# Factory: pemilihan backend lewat 1 titik konfigurasi
# ---------------------------------------------------------------------------
def get_face_backend(name: str = "facenet") -> FaceEmbeddingBackend:
    """
    Titik tunggal untuk memilih backend yang dipakai aplikasi.

    Untuk ganti backend nanti (misal setelah uji akurasi dengan data
    karyawan asli), cukup ubah default value di sini atau baca dari
    environment variable, TIDAK perlu ubah main.py atau kode lain.

    Contoh pakai environment variable (disarankan untuk production):
        import os
        backend_name = os.getenv("FACE_BACKEND", "facenet")
    """
    name = name.lower()
    if name == "facenet":
        return FacenetPytorchBackend()
    elif name == "insightface":
        return InsightFaceBackend()
    else:
        raise ValueError(f"Backend tidak dikenal: {name}. Pilih 'facenet' atau 'insightface'.")