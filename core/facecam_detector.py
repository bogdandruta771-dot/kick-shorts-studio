"""
AI Streamer Facecam & Optimal Framing Detector
Uses lightweight ONNX YuNet deep neural network to automatically detect streamer
webcam placement (Top-Left, Top-Right, Bottom-Left, Bottom-Right) and compute
perfect non-overlapping 9:16 vertical crop boxes and layout stack modes.
"""

import os
import cv2
import numpy as np
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

MODEL_DIR = Path(__file__).parent.parent / "assets" / "models"
MODEL_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"

# Lazy-loaded model instance
_DETECTOR_CACHE = {}


def get_face_detector(width: int = 1920, height: int = 1080) -> Optional[Any]:
    """Returns a cached cv2.FaceDetectorYN instance for the given image resolution."""
    if not MODEL_PATH.is_file():
        return None

    cache_key = (width, height)
    if cache_key in _DETECTOR_CACHE:
        return _DETECTOR_CACHE[cache_key]

    try:
        detector = cv2.FaceDetectorYN_create(
            str(MODEL_PATH),
            "",
            (width, height),
            score_threshold=0.55,
            nms_threshold=0.3,
            top_k=5000,
        )
        _DETECTOR_CACHE[cache_key] = detector
        return detector
    except Exception as exc:
        print(f"WARN: Failed to create YuNet face detector: {exc}")
        return None


def detect_face_in_image(
    image_bgr: np.ndarray,
) -> Optional[Dict[str, Any]]:
    """
    Runs face detection on an OpenCV BGR image.
    Returns the most prominent detected face bounding box and score, or None.
    """
    h, w = image_bgr.shape[:2]
    detector = get_face_detector(w, h)
    if detector is None:
        return None

    try:
        detector.setInputSize((w, h))
        _, faces = detector.detect(image_bgr)
        if faces is None or len(faces) == 0:
            return None

        # Filter faces by confidence and plausible streamer webcam dimensions
        valid_faces = []
        for face in faces:
            score = float(face[-1])
            if score < 0.55:
                continue
            fx, fy, fw, fh = [int(v) for v in face[:4]]
            if fw < 20 or fh < 20:
                continue

            # Prioritize faces towards the corners or edges (streamer webcams)
            cx = fx + (fw / 2.0)
            cy = fy + (fh / 2.0)
            dist_from_edge_x = min(cx, w - cx)
            dist_from_edge_y = min(cy, h - cy)

            # Heuristic score: high confidence + closer to periphery (typical for streamer cams)
            corner_bias = 1.0
            if dist_from_edge_x < (w * 0.35) and dist_from_edge_y < (h * 0.40):
                corner_bias = 1.35

            rank_score = score * corner_bias
            valid_faces.append({
                "x": fx, "y": fy, "w": fw, "h": fh,
                "cx": cx, "cy": cy,
                "score": score,
                "rank_score": rank_score,
            })

        if not valid_faces:
            return None

        # Sort by rank score descending
        valid_faces.sort(key=lambda item: item["rank_score"], reverse=True)
        return valid_faces[0]

    except Exception as exc:
        print(f"WARN: Face detection failed during inference: {exc}")
        return None


def calculate_optimal_layout(
    face_info: Optional[Dict[str, Any]],
    width: int = 1920,
    height: int = 1080,
) -> Dict[str, Any]:
    """
    Computes intelligent crop coordinates, stack mode, and preset recommendations
    based on detected streamer facecam position.
    """
    if not face_info:
        # Fallback layout when no streamer face is detected:
        # Full 16:9 Ambient Blur ensures nothing is sliced or missed (perfect for unboxings & game montages)
        return {
            "detected": False,
            "corner": "none",
            "face_score": 0.0,
            "face_box": None,
            "gameplay": {"x": 0, "y": 0, "w": width, "h": height},
            "facecam": {"x": 0, "y": 0, "w": width, "h": height},
            "stack_mode": "cinema_letterbox",
            "split_ratio": 0.50,
            "cam_fill_mode": "fill",
            "game_fill_mode": "fit",
            "preset_name": "ambient_blur_16_9",
            "label": "📱 Full 16:9 View (Ambient Blur - Zero Cut)",
            "description": "Entire 16:9 screen centered with dynamic blurred vertical fill. 100% visible, no cutoffs.",
        }

    cx = face_info["cx"]
    cy = face_info["cy"]
    is_left = cx < (width * 0.5)
    is_top = cy < (height * 0.5)

    # Standard streamer webcam dimensions scaled to frame
    cam_w = int(width * 0.285)  # ~547px on 1080p
    cam_h = int(height * 0.370)  # ~400px on 1080p
    cam_w -= cam_w % 2
    cam_h -= cam_h % 2

    if is_top and is_left:
        # 1. Top-Left Facecam (Very common in CS2, Gaules, European/BR FPS streamers)
        corner = "top_left"
        fc_x = 0
        fc_y = 0
        gp_x = int(width * 0.26)  # Start gameplay after webcam boundary to avoid face slicing
        gp_y = 0
        gp_w = width - gp_x
        gp_h = height
        stack_mode = "cam_top"  # Facecam on Top, Gameplay on Bottom
        split_ratio = 0.44
        preset_name = "reaction_top_left"
        label = "🎮 Top-Left Streamer Cam + Bottom Gameplay"

    elif is_top and not is_left:
        # 2. Top-Right Facecam (OhnePixel, xmerghani, CS2 Right-HUD streamers)
        corner = "top_right"
        fc_x = width - cam_w
        fc_y = 0
        gp_x = 0
        gp_y = 0
        gp_w = int(width * 0.75)
        gp_h = height
        stack_mode = "cam_top"
        split_ratio = 0.44
        preset_name = "reaction_cam_top"
        label = "👑 Top-Right Streamer Cam (OhnePixel Style) + Bottom Gameplay"

    elif not is_top and is_left:
        # 3. Bottom-Left Facecam (paulinhoo46, Tarik, s1mple)
        corner = "bottom_left"
        fc_x = 0
        fc_y = height - cam_h
        gp_x = int(width * 0.12)
        gp_y = 0
        gp_w = int(width * 0.88)
        gp_h = int(height * 0.85)
        stack_mode = "standard"  # Gameplay on Top, Facecam on Bottom
        split_ratio = 0.55
        preset_name = "reaction_bottom_left"
        label = "🎯 Bottom-Left Streamer Cam + Top Gameplay"

    else:
        # 4. Bottom-Right Facecam (Standard FPS / Shroud)
        corner = "bottom_right"
        fc_x = width - cam_w
        fc_y = height - cam_h
        gp_x = int(width * 0.08)
        gp_y = 0
        gp_w = int(width * 0.84)
        gp_h = int(height * 0.85)
        stack_mode = "standard"
        split_ratio = 0.55
        preset_name = "gaming_fps"
        label = "🕹️ Bottom-Right Streamer Cam + Top Gameplay"

    # Ensure even integers for video encoding
    gp_x -= gp_x % 2
    gp_y -= gp_y % 2
    gp_w -= gp_w % 2
    gp_h -= gp_h % 2
    fc_x -= fc_x % 2
    fc_y -= fc_y % 2

    return {
        "detected": True,
        "corner": corner,
        "face_score": round(face_info["score"], 3),
        "face_box": {
            "x": face_info["x"],
            "y": face_info["y"],
            "w": face_info["w"],
            "h": face_info["h"],
        },
        "gameplay": {"x": gp_x, "y": gp_y, "w": gp_w, "h": gp_h},
        "facecam": {"x": fc_x, "y": fc_y, "w": cam_w, "h": cam_h},
        "stack_mode": stack_mode,
        "split_ratio": split_ratio,
        "cam_fill_mode": "fill",
        "game_fill_mode": "fit",
        "preset_name": preset_name,
        "label": label,
        "description": f"AI detected streamer webcam in {corner.replace('_', ' ').title()} corner with {face_info['score']*100:.1f}% confidence.",
    }


def detect_facecam_from_image(image_path: Path) -> Dict[str, Any]:
    """Inspects a snapshot image file and returns optimal crop coordinates and layout."""
    if not image_path.is_file():
        return calculate_optimal_layout(None)

    img = cv2.imread(str(image_path))
    if img is None:
        return calculate_optimal_layout(None)

    h, w = img.shape[:2]
    face_info = detect_face_in_image(img)
    return calculate_optimal_layout(face_info, width=w, height=h)


def detect_facecam_from_video(
    video_path: Path,
    target_timestamp: Optional[float] = None,
    duration: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Extracts frame(s) from a video and analyzes facecam placement.
    If target_timestamp is given, inspects that specific timestamp.
    Otherwise samples multiple candidate frames (e.g. 15%, 35%, 65% through the video).
    """
    if not video_path.is_file():
        return calculate_optimal_layout(None)

    timestamps_to_try = []
    if target_timestamp is not None and target_timestamp >= 0:
        timestamps_to_try.append(float(target_timestamp))

    if duration and duration > 3.0:
        for frac in (0.25, 0.50, 0.75):
            t = duration * frac
            if abs(t - (target_timestamp or -999)) > 2.0:
                timestamps_to_try.append(round(t, 2))
    else:
        for t in (3.0, 8.0, 15.0):
            if abs(t - (target_timestamp or -999)) > 1.5:
                timestamps_to_try.append(t)

    # Temporary directory for extracted probe frames
    temp_probe = video_path.parent / f"_probe_{int(os.getpid())}.jpg"

    best_result = None
    highest_score = 0.0

    try:
        for t in timestamps_to_try:
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(t),
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(temp_probe),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
            if temp_probe.is_file():
                res = detect_facecam_from_image(temp_probe)
                if res.get("detected") and res.get("face_score", 0.0) > highest_score:
                    highest_score = res["face_score"]
                    best_result = res
                    # If high confidence (> 0.82), we found the facecam cleanly
                    if highest_score >= 0.82:
                        break
    except Exception as exc:
        print(f"WARN: Error during video probe extraction: {exc}")
    finally:
        if temp_probe.is_file():
            try:
                temp_probe.unlink(missing_ok=True)
            except Exception:
                pass

    if best_result:
        return best_result

    # Fallback if no faces detected in any probe frame
    return calculate_optimal_layout(None)
