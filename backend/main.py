import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.predictor_service import SpoofPredictor
from src.database import get_db, init_db
from src.models import Employee, FaceEmbedding, AttendanceLog
from src.face_recognition_service import face_recognition_service

app = FastAPI(title="Absensi - Face Anti-Spoofing API")

# Untuk development, izinkan semua origin supaya gampang testing dari HP.
# Saat production, ganti allow_origins ke domain/IP spesifik.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor: SpoofPredictor | None = None


@app.on_event("startup")
def load_model() -> None:
    global predictor
    predictor = SpoofPredictor()
    print("Model anti-spoofing siap digunakan.")

    # BARU: siapkan tabel database untuk face recognition (employees,
    # face_embeddings, attendance_logs). face_recognition_service sendiri
    # sudah otomatis load modelnya saat modul ini pertama kali diimport
    # (lihat singleton di src/face_recognition_service.py), jadi tidak
    # perlu di-load manual di sini.
    init_db()
    print("Database face recognition siap digunakan.")


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "model_ready": predictor is not None}


@app.post("/api/verify-face")
async def verify_face(file: UploadFile = File(...)) -> dict:
    """
    Endpoint LAMA — tetap dipertahankan apa adanya, tidak diubah.

    Terima 1 file foto (multipart/form-data, field name = 'file').
    Balikan:
      {
        "is_real": true/false,
        "score": 0.0 - 1.0,
        "bbox": { "x", "y", "width", "height" }
      }
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model belum siap, coba lagi sebentar.")

    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="File yang dikirim bukan gambar yang valid.")

    try:
        result = predictor.predict(image)
    except Exception as exc:  # noqa: BLE001 - kita ingin tangkap semua error inferensi
        raise HTTPException(status_code=500, detail=f"Gagal memproses gambar: {exc}") from exc

    return result


# =============================================================================
# BARU — Face Recognition (enrollment + recognition untuk absensi)
# =============================================================================


@app.post("/api/employees")
async def create_employee(
    name: str = Form(...),
    position: str | None = Form(None),
    photos: list[UploadFile] = File(...),  # minta 2-3 foto sudut berbeda
    db: Session = Depends(get_db),
):
    """Admin daftarkan karyawan baru beserta 1-3 foto wajahnya (enrollment)."""
    if len(photos) < 1:
        raise HTTPException(400, "Minimal 1 foto wajah dibutuhkan")

    embeddings = []
    for photo in photos:
        content = await photo.read()
        emb = face_recognition_service.extract_embedding(content)
        if emb is None:
            raise HTTPException(
                400, f"Tidak ada wajah terdeteksi di foto: {photo.filename}"
            )
        embeddings.append(emb)

    employee = Employee(name=name, position=position)
    db.add(employee)
    db.flush()  # supaya employee.id sudah terisi sebelum dipakai di bawah

    for i, emb in enumerate(embeddings):
        face_emb = FaceEmbedding(employee_id=employee.id, source_note=f"enroll_{i}")
        face_emb.set_vector(emb.tolist())
        db.add(face_emb)

    db.commit()
    db.refresh(employee)

    return {
        "employee_id": employee.id,
        "name": employee.name,
        "num_embeddings_saved": len(embeddings),
    }


@app.post("/api/recognize-face")
async def recognize_face(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Dipanggil saat karyawan absen.

    Alur: decode gambar sekali (sama seperti /api/verify-face) -> jalankan
    anti-spoofing pakai predictor yang SUDAH ADA -> kalau lolos, baru
    jalankan face recognition (1:N matching) ke database karyawan.
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model belum siap, coba lagi sebentar.")

    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="File yang dikirim bukan gambar yang valid.")

    # --- Tahap 1: anti-spoofing, PAKAI predictor yang sudah ada (sama seperti /api/verify-face) ---
    try:
        spoof_result = predictor.predict(image)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Gagal memproses gambar: {exc}") from exc

    is_real = spoof_result["is_real"]

    if not is_real:
        log = AttendanceLog(
            employee_id=None,
            is_real=0,
            confidence=spoof_result.get("score"),
            status="spoof_detected",
        )
        db.add(log)
        db.commit()
        return {
            "is_real": False,
            "status": "spoof_detected",
            "score": spoof_result.get("score"),
            "message": "Foto terdeteksi bukan wajah asli, silakan coba lagi.",
        }

    # --- Tahap 2: face recognition (1:N matching) ---
    # Catatan: face_recognition_service pakai PIL untuk buka gambar (bukan cv2),
    # jadi kita kirim `contents` (bytes mentah), bukan `image` (hasil cv2.imdecode).
    query_embedding = face_recognition_service.extract_embedding(contents)
    if query_embedding is None:
        return {
            "is_real": True,
            "status": "no_face_detected",
            "message": "Wajah tidak terdeteksi dengan jelas, silakan coba lagi.",
        }

    employees = db.query(Employee).all()
    candidates = []
    for emp in employees:
        if not emp.embeddings:
            continue
        vectors = [np.array(e.get_vector()) for e in emp.embeddings]
        avg_vector = face_recognition_service.average_embeddings(vectors)
        candidates.append((emp.id, emp.name, avg_vector))

    result = face_recognition_service.find_best_match(query_embedding, candidates)

    status = "recognized" if result["matched"] else "no_match"
    log = AttendanceLog(
        employee_id=result["employee_id"],
        is_real=1,
        confidence=result["confidence"],
        status=status,
    )
    db.add(log)
    db.commit()

    return {
        "is_real": True,
        "status": status,
        "employee_id": result["employee_id"],
        "name": result["name"],
        "confidence": result["confidence"],
    }


@app.get("/api/employees")
def list_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    return [
        {"id": e.id, "name": e.name, "position": e.position, "num_photos": len(e.embeddings)}
        for e in employees
    ]


@app.get("/api/attendance-logs")
def list_attendance_logs(db: Session = Depends(get_db)):
    logs = db.query(AttendanceLog).order_by(AttendanceLog.timestamp.desc()).limit(100).all()
    return [
        {
            "id": log.id,
            "employee_id": log.employee_id,
            "employee_name": log.employee.name if log.employee else None,
            "timestamp": log.timestamp.isoformat(),
            "status": log.status,
            "confidence": log.confidence,
        }
        for log in logs
    ]