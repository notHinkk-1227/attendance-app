"""
Model database untuk fitur face recognition + attendance log.

Skema:
- Employee          : data karyawan
- FaceEmbedding      : vektor wajah (bisa >1 per karyawan, dari beberapa foto)
- AttendanceLog      : catatan tiap kali ada percobaan absensi (match / no_match / spoof)
"""

import datetime
import json

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    position = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    embeddings = relationship(
        "FaceEmbedding", back_populates="employee", cascade="all, delete-orphan"
    )
    attendance_logs = relationship("AttendanceLog", back_populates="employee")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # Vektor disimpan sebagai JSON string (list of float).
    # Untuk skala <50 karyawan ini jauh lebih simpel daripada setup vector DB,
    # dan cukup cepat di-load + dihitung cosine similarity-nya di memori.
    vector_json = Column(Text, nullable=False)

    source_note = Column(String, nullable=True)  # misal: "enroll_photo_1"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("Employee", back_populates="embeddings")

    def get_vector(self) -> list[float]:
        return json.loads(self.vector_json)

    def set_vector(self, vector: list[float]) -> None:
        self.vector_json = json.dumps(vector)


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # null kalau no_match

    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_real = Column(Integer, nullable=False)  # 1 / 0, hasil anti-spoofing
    confidence = Column(Float, nullable=True)  # similarity score hasil recognition
    status = Column(String, nullable=False)  # "recognized" | "no_match" | "spoof_detected"

    employee = relationship("Employee", back_populates="attendance_logs")