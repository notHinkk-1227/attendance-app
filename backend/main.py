import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.predictor_service import SpoofPredictor

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


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "model_ready": predictor is not None}


@app.post("/api/verify-face")
async def verify_face(file: UploadFile = File(...)) -> dict:
    """
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
