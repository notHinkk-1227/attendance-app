"""
Repository Pattern — memisahkan "cara mengambil/menyimpan data" dari
"logic bisnis apa yang dilakukan dengan data itu".

SEBELUM refactor ini, main.py memanggil `db.query(Employee).all()` dan
`db.add(log)` LANGSUNG di dalam endpoint. Ini melanggar SRP: endpoint jadi
punya 2 alasan untuk berubah — (1) kalau alur bisnis absensi berubah, ATAU
(2) kalau cara kita query/simpan data ke database berubah (misal pindah dari
SQLAlchemy ORM ke raw SQL, atau ganti skema tabel).

Dengan Repository, endpoint (dan orchestrator) HANYA bicara lewat method
seperti `employee_repo.get_all_with_embeddings()` — tidak peduli itu
diimplementasikan pakai SQLAlchemy, raw SQL, atau bahkan API eksternal.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from .models import AttendanceLog, Employee, FaceEmbedding


class EmployeeRepository:
    """Semua akses data terkait `Employee` & `FaceEmbedding` lewat sini."""

    def __init__(self, db: Session):
        self.db = db

    def create_with_embeddings(
        self, name: str, position: str | None, embeddings: list[np.ndarray]
    ) -> Employee:
        employee = Employee(name=name, position=position)
        self.db.add(employee)
        self.db.flush()  # supaya employee.id terisi sebelum dipakai di bawah

        for i, emb in enumerate(embeddings):
            face_emb = FaceEmbedding(employee_id=employee.id, source_note=f"enroll_{i}")
            face_emb.set_vector(emb.tolist())
            self.db.add(face_emb)

        self.db.commit()
        self.db.refresh(employee)
        return employee

    def get_all(self) -> list[Employee]:
        return self.db.query(Employee).all()

    def get_all_as_match_candidates(self) -> list[tuple[int, str, np.ndarray]]:
        """
        Ambil semua karyawan yang sudah punya minimal 1 foto terdaftar,
        dan gabungkan (average) embedding mereka jadi 1 vektor representatif.

        Return: list of (employee_id, employee_name, averaged_embedding_vector)
        siap dipakai langsung oleh FaceMatcher.find_best_match().
        """
        candidates: list[tuple[int, str, np.ndarray]] = []
        for emp in self.get_all():
            if not emp.embeddings:
                continue
            vectors = [np.array(e.get_vector()) for e in emp.embeddings]
            avg_vector = _average(vectors)
            candidates.append((emp.id, emp.name, avg_vector))
        return candidates


def _average(vectors: list[np.ndarray]) -> np.ndarray:
    stacked = np.stack(vectors, axis=0)
    avg = stacked.mean(axis=0)
    return avg / np.linalg.norm(avg)


class AttendanceLogRepository:
    """Semua akses data terkait `AttendanceLog` lewat sini."""

    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        employee_id: int | None,
        is_real: bool,
        confidence: float | None,
        status: str,
    ) -> AttendanceLog:
        log = AttendanceLog(
            employee_id=employee_id,
            is_real=1 if is_real else 0,
            confidence=confidence,
            status=status,
        )
        self.db.add(log)
        self.db.commit()
        return log

    def get_recent(self, limit: int = 100) -> list[AttendanceLog]:
        return (
            self.db.query(AttendanceLog)
            .order_by(AttendanceLog.timestamp.desc())
            .limit(limit)
            .all()
        )
