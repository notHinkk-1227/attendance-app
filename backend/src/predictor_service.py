import os

import numpy as np

from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "anti_spoof_models",
)


class CachedAntiSpoofPredict(AntiSpoofPredict):
    """Versi AntiSpoofPredict yang meng-cache model yang sudah dimuat.

    Kode resmi (test.py) memanggil `_load_model()` di setiap `predict()`,
    yang berarti bobot model dibaca ulang dari disk setiap kali — sangat
    tidak efisien untuk server yang melayani banyak request. Di sini kita
    override supaya model hanya dimuat sekali dan disimpan di memori.
    """

    def __init__(self, device_id: int = 0):
        super().__init__(device_id)
        self._model_cache = {}

    def _load_model(self, model_path: str):
        if model_path in self._model_cache:
            self.model = self._model_cache[model_path]
            return None
        super()._load_model(model_path)
        self._model_cache[model_path] = self.model
        return None


class SpoofPredictor:
    """Membungkus pipeline resmi Silent-Face-Anti-Spoofing:
    deteksi wajah -> crop di beberapa skala -> jumlahkan skor dari tiap model.
    """

    def __init__(self, model_dir: str = MODEL_DIR, device_id: int = 0):
        self.model_dir = model_dir
        self.model_test = CachedAntiSpoofPredict(device_id)
        self.image_cropper = CropImage()
        self.model_names = os.listdir(model_dir)
        self._warm_up()

    def _warm_up(self):
        # Muat semua model saat server start, bukan saat request pertama masuk,
        # supaya request pertama dari user tidak kena delay ekstra.
        for model_name in self.model_names:
            self.model_test._load_model(os.path.join(self.model_dir, model_name))

    def predict(self, image_bgr: np.ndarray) -> dict:
        image_bbox = self.model_test.get_bbox(image_bgr)
        prediction = np.zeros((1, 3))

        for model_name in self.model_names:
            h_input, w_input, model_type, scale = parse_model_name(model_name)
            param = {
                "org_img": image_bgr,
                "bbox": image_bbox,
                "scale": scale,
                "out_w": w_input,
                "out_h": h_input,
                "crop": True,
            }
            if scale is None:
                param["crop"] = False
            img = self.image_cropper.crop(**param)
            prediction += self.model_test.predict(img, os.path.join(self.model_dir, model_name))

        label = int(np.argmax(prediction))
        score = float(prediction[0][label] / 2)
        is_real = label == 1

        return {
            "is_real": is_real,
            "score": round(score, 4),
            "bbox": {
                "x": int(image_bbox[0]),
                "y": int(image_bbox[1]),
                "width": int(image_bbox[2]),
                "height": int(image_bbox[3]),
            },
        }
