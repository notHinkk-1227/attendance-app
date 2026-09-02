import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.attendance_orchestrator import AttendanceOrchestrator, InvalidImageError
from src.database import get_db, init_db
from src.face_recognition_service import face_recognition_service
from src.predictor_service import SpoofPredictor
from src.repositories import AttendanceLogRepository, EmployeeRepository

app = FastAPI(title="Absensi - Face Anti-Spoofing API")

# Untuk development, izinkan semua origin supaya gampang testing dari HP.
# Saat production, ganti allow_origins ke domain/IP spesifik.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Dependency Injection (FastAPI `Depends`)
# =============================================================================
# `predictor` sebelumnya adalah variabel global bertipe `SpoofPredictor | None`
# yang di-assign manual di event `startup`. Sekarang ia disimpan di
# `app.state` (tempat resmi FastAPI untuk state aplikasi) dan diakses lewat
# fungsi dependency di bawah. Manfaatnya:
#   1. Endpoint tidak perlu tahu / peduli DARI MANA predictor berasal.
#   2. Saat unit test, `app.dependency_overrides[get_orchestrator] = ...`
#      bisa dipakai untuk mengganti orchestrator dengan versi palsu (mock),
#      tanpa perlu load model AI sungguhan.
# =============================================================================


@app.on_event("startup")
def load_model() -> None:
    app.state.predictor = SpoofPredictor()
    print("Model anti-spoofing siap digunakan.")

    # face_recognition_service sudah otomatis load modelnya saat modul ini
    # pertama kali diimport (singleton di src/face_recognition_service.py).
    init_db()
    print("Database face recognition siap digunakan.")


def get_predictor() -> SpoofPredictor:
    predictor = getattr(app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model belum siap, coba lagi sebentar.")
    return predictor


def get_orchestrator(
    predictor: SpoofPredictor = Depends(get_predictor),
) -> AttendanceOrchestrator:
    # `predictor` dan `face_recognition_service` sama-sama memenuhi kontrak
    # `AntiSpoofChecker` / `FaceMatcher` (lihat src/interfaces.py) secara
    # otomatis (duck typing) — tidak perlu ubah kode class aslinya sama sekali.
    return AttendanceOrchestrator(
        anti_spoof_checker=predictor,
        face_matcher=face_recognition_service,
    )


def get_employee_repo(db: Session = Depends(get_db)) -> EmployeeRepository:
    return EmployeeRepository(db)


def get_log_repo(db: Session = Depends(get_db)) -> AttendanceLogRepository:
    return AttendanceLogRepository(db)


@app.get("/health")
def health_check(predictor: SpoofPredictor | None = Depends(get_predictor)) -> dict:
    return {"status": "ok", "model_ready": predictor is not None}


@app.post("/api/verify-face")
async def verify_face(
    file: UploadFile = File(...),
    predictor: SpoofPredictor = Depends(get_predictor),
) -> dict:
    """
    Endpoint LAMA — tetap dipertahankan, dipertahankan apa adanya secara
    perilaku (behavior). Hanya cara mengambil `predictor` yang berubah
    (lewat Depends, bukan variabel global).

    Terima 1 file foto (multipart/form-data, field name = 'file').
    Balikan:
      {
        "is_real": true/false,
        "score": 0.0 - 1.0,
        "bbox": { "x", "y", "width", "height" }
      }
    """
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    import cv2  # import lokal, konsisten dengan gaya endpoint ini sebelumnya

    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="File yang dikirim bukan gambar yang valid.")

    try:
        result = predictor.predict(image)
    except Exception as exc:  # noqa: BLE001 - kita ingin tangkap semua error inferensi
        raise HTTPException(status_code=500, detail=f"Gagal memproses gambar: {exc}") from exc

    return result


# =============================================================================
# Face Recognition (enrollment + recognition untuk absensi)
# =============================================================================


@app.post("/api/employees")
async def create_employee(
    name: str = Form(...),
    position: str | None = Form(None),
    photos: list[UploadFile] = File(...),  # minta 2-3 foto sudut berbeda
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
):
    """Admin daftarkan karyawan baru beserta 1-3 foto wajahnya (enrollment)."""
    if len(photos) < 1:
        raise HTTPException(400, "Minimal 1 foto wajah dibutuhkan")

    embeddings = []
    for photo in photos:
        content = await photo.read()
        emb = face_recognition_service.extract_embedding(content)
        if emb is None:
            raise HTTPException(400, f"Tidak ada wajah terdeteksi di foto: {photo.filename}")
        embeddings.append(emb)

    employee = employee_repo.create_with_embeddings(name, position, embeddings)

    return {
        "employee_id": employee.id,
        "name": employee.name,
        "num_embeddings_saved": len(embeddings),
    }


@app.post("/api/recognize-face")
async def recognize_face(
    file: UploadFile = File(...),
    orchestrator: AttendanceOrchestrator = Depends(get_orchestrator),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    log_repo: AttendanceLogRepository = Depends(get_log_repo),
):
    """
    Dipanggil saat karyawan absen.

    SEBELUM refactor: endpoint ini ~60 baris berisi decode gambar, anti-spoof,
    face recognition, dan logging, semua dicampur jadi satu (melanggar SRP).

    SESUDAH refactor: endpoint ini HANYA (1) terima file, (2) delegasikan
    seluruh alur ke `AttendanceOrchestrator`, (3) format hasilnya jadi JSON.
    Endpoint ini disebut "thin controller" — tidak punya logic bisnis sama
    sekali, hanya menghubungkan HTTP request ke orchestrator.
    """
    contents = await file.read()

    try:
        result = orchestrator.process_attendance(contents, employee_repo, log_repo)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Gagal memproses gambar: {exc}") from exc

    return result.to_dict()


@app.get("/api/employees")
def list_employees(employee_repo: EmployeeRepository = Depends(get_employee_repo)):
    employees = employee_repo.get_all()
    return [
        {"id": e.id, "name": e.name, "position": e.position, "num_photos": len(e.embeddings)}
        for e in employees
    ]


@app.get("/api/attendance-logs")
def list_attendance_logs(log_repo: AttendanceLogRepository = Depends(get_log_repo)):
    logs = log_repo.get_recent(limit=100)
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
