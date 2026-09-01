"""
Setup database SQLite untuk fitur face recognition.

Kenapa SQLite: untuk prototype <50 karyawan, SQLite lebih dari cukup —
file tunggal, tidak perlu server DB terpisah. Kalau nanti mau migrasi ke
PostgreSQL, cukup ganti SQLALCHEMY_DATABASE_URL di bawah (SQLAlchemy
menangani sisanya, query tidak perlu diubah).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# File database akan dibuat di backend/attendance.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./attendance.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args ini WAJIB untuk SQLite dipakai dengan FastAPI (multi-thread)
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency untuk FastAPI — pastikan session selalu ditutup setelah request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Panggil sekali saat startup untuk membuat semua tabel kalau belum ada."""
    # Import di sini (bukan di top-level) supaya menghindari circular import
    # antara database.py dan models.py
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)