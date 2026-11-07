import cv2
import numpy as np
import math
from typing import List, Dict, Tuple

# ==========================================
# DEFAULT CONFIG (BISA DI-OVERRIDE)
# ==========================================

DEFAULT_CONFIG = {
    # HSV range untuk cabai merah
    "hsv_lower_1": (0, 120, 70),
    "hsv_upper_1": (10, 255, 255),
    "hsv_lower_2": (170, 120, 70),
    "hsv_upper_2": (180, 255, 255),

    # Filter area (pixel)
    "min_area": 300,
    "max_area": 8000,

    # Filter bentuk
    "min_aspect": 0.3,
    "max_aspect": 1.8,

    # Scoring weight
    "score_weight_distance": 1.0,
    "score_weight_area": 0.5,

    # Morphology
    "kernel_size": 5
}

# ==========================================
# UTILITIES
# ==========================================

def distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


# ==========================================
# PREPROCESS
# ==========================================

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Basic preprocessing:
    - blur untuk reduksi noise
    """
    return cv2.GaussianBlur(image, (5, 5), 0)


# ==========================================
# HSV SEGMENTATION
# ==========================================

def segment_red_hsv(image: np.ndarray, config: dict) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    mask1 = cv2.inRange(
        hsv,
        np.array(config["hsv_lower_1"]),
        np.array(config["hsv_upper_1"])
    )
    mask2 = cv2.inRange(
        hsv,
        np.array(config["hsv_lower_2"]),
        np.array(config["hsv_upper_2"])
    )

    mask = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones(
        (config["kernel_size"], config["kernel_size"]),
        np.uint8
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    return mask


# ==========================================
# EKSTRAKSI KANDIDAT CABAI
# ==========================================

def extract_candidates(
    mask: np.ndarray,
    image_shape: Tuple[int, int],
    config: dict
) -> List[Dict]:

    h, w = image_shape
    frame_center = (w // 2, h // 2)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < config["min_area"] or area > config["max_area"]:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect = bw / bh if bh > 0 else 0
        if aspect < config["min_aspect"] or aspect > config["max_aspect"]:
            continue

        cx = x + bw // 2
        cy = y + bh // 2

        dist = distance((cx, cy), frame_center)

        candidates.append({
            "center_x": cx,
            "center_y": cy,
            "area": area,
            "aspect": aspect,
            "distance": dist
        })

    return candidates


# ==========================================
# SCORING & REKOMENDASI
# ==========================================

def score_candidates(
    candidates: List[Dict],
    config: dict
) -> List[Dict]:
    """
    Score lebih kecil = lebih baik
    """
    scored = []

    for c in candidates:
        score = (
            config["score_weight_distance"] * c["distance"]
            /
            (math.sqrt(c["area"]) ** config["score_weight_area"])
        )

        c_scored = c.copy()
        c_scored["score"] = score
        scored.append(c_scored)

    scored.sort(key=lambda x: x["score"])
    return scored


# ==========================================
# MAIN PIPELINE
# ==========================================

def process_image_to_json(
    image: np.ndarray,
    config: dict = None
) -> Dict:
    """
    Fungsi utama yang akan dipanggil modul lain.
    Input  : BGR image (OpenCV)
    Output : dict siap JSON
    """

    if config is None:
        config = DEFAULT_CONFIG

    processed = preprocess_image(image)
    mask = segment_red_hsv(processed, config)

    candidates = extract_candidates(
        mask,
        image.shape[:2],
        config
    )

    scored = score_candidates(candidates, config)

    response = {
        "detected_count": len(scored),
        "candidates": [],
        "recommended": None
    }

    for c in scored:
        response["candidates"].append({
            "x": int(c["center_x"]),
            "y": int(c["center_y"]),
            "area": int(c["area"]),
            "distance": round(c["distance"], 2),
            "score": round(c["score"], 3)
        })

    if scored:
        best = scored[0]
        response["recommended"] = {
            "x": int(best["center_x"]),
            "y": int(best["center_y"]),
            "score": round(best["score"], 3)
        }

    return response

def draw_detection_overlay(
    image: np.ndarray,
    result_json: Dict
) -> np.ndarray:
    """
    Menggambar:
    - Titik biru: semua cabai terdeteksi
    - Titik hijau: cabai rekomendasi
    """

    output = image.copy()

    # Semua kandidat → biru
    for c in result_json["candidates"]:
        x, y = int(c["x"]), int(c["y"])
        cv2.circle(
            output,
            (x, y),
            radius=6,
            color=(255, 0, 0),   # biru (BGR)
            thickness=-1
        )

    # Rekomendasi → hijau
    rec = result_json.get("recommended")
    if rec:
        x, y = int(rec["x"]), int(rec["y"])
        cv2.circle(
            output,
            (x, y),
            radius=9,
            color=(0, 255, 0),   # hijau
            thickness=2
        )
        cv2.putText(
            output,
            "RECOMMENDED",
            (x + 10, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA
        )

    return output

print("proses_gambar.py dimuat.")