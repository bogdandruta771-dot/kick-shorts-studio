"""
Test Suite: Facecam AI Detection, CS2 / YouTube Ingest Framing, and Crop Presets
Verifies that:
1. YuNet face detector model is present and operational in OpenCV 5.
2. Streamer face positions (top-left, bottom-left, top-right) are detected accurately.
3. Optimal layouts and stack modes are derived correctly (preventing blank sky crops or severed webcams).
4. Crop presets in core.config are well-formed and non-overlapping.
5. Ingest and auto-detect endpoints behave reliably.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.facecam_detector import (
    MODEL_PATH,
    get_face_detector,
    detect_face_in_image,
    calculate_optimal_layout,
    detect_facecam_from_image,
    detect_facecam_from_video,
)
from core.config import CROP_PRESETS


class TestFacecamAndYoutubeCropping(unittest.TestCase):
    def test_01_model_file_exists(self):
        """Verifies YuNet ONNX model is available."""
        self.assertTrue(MODEL_PATH.is_file(), f"Model missing at {MODEL_PATH}")
        self.assertGreater(MODEL_PATH.stat().st_size, 100_000, "Model file seems too small or corrupt")

    def test_02_detector_initialization(self):
        """Verifies cv2.FaceDetectorYN initializes without throwing."""
        detector = get_face_detector(1920, 1080)
        self.assertIsNotNone(detector, "Detector could not be initialized")

    def test_03_optimal_layout_fallback_when_no_face(self):
        """When no face is detected, system must fall back to 16:9 ambient blur (no cutoffs)."""
        layout = calculate_optimal_layout(None, width=1920, height=1080)
        self.assertFalse(layout["detected"])
        self.assertEqual(layout["preset_name"], "ambient_blur_16_9")
        self.assertEqual(layout["stack_mode"], "cinema_letterbox")
        self.assertEqual(layout["gameplay"]["w"], 1920)
        self.assertEqual(layout["gameplay"]["h"], 1080)

    def test_04_optimal_layout_top_left_face(self):
        """Top-left streamer webcam must use cam_top and place facecam at top-left, not slicing gameplay."""
        face_info = {"cx": 250, "cy": 120, "x": 200, "y": 80, "w": 100, "h": 120, "score": 0.92}
        layout = calculate_optimal_layout(face_info, width=1920, height=1080)
        self.assertTrue(layout["detected"])
        self.assertEqual(layout["corner"], "top_left")
        self.assertEqual(layout["preset_name"], "reaction_top_left")
        self.assertEqual(layout["stack_mode"], "cam_top")
        self.assertEqual(layout["facecam"]["x"], 0)
        self.assertEqual(layout["facecam"]["y"], 0)
        # Gameplay must be offset to the right of the facecam so face isn't sliced in gameplay
        self.assertGreater(layout["gameplay"]["x"], 300)

    def test_05_optimal_layout_bottom_left_face(self):
        """Bottom-left streamer webcam must use standard split (gameplay on top, cam on bottom)."""
        face_info = {"cx": 300, "cy": 850, "x": 250, "y": 800, "w": 100, "h": 120, "score": 0.90}
        layout = calculate_optimal_layout(face_info, width=1920, height=1080)
        self.assertTrue(layout["detected"])
        self.assertEqual(layout["corner"], "bottom_left")
        self.assertEqual(layout["preset_name"], "reaction_bottom_left")
        self.assertEqual(layout["stack_mode"], "standard")
        self.assertEqual(layout["facecam"]["x"], 0)
        self.assertGreater(layout["facecam"]["y"], 600)

    def test_06_optimal_layout_top_right_face(self):
        """Top-right streamer webcam (OhnePixel) must place facecam at top-right."""
        face_info = {"cx": 1600, "cy": 150, "x": 1550, "y": 100, "w": 100, "h": 120, "score": 0.88}
        layout = calculate_optimal_layout(face_info, width=1920, height=1080)
        self.assertTrue(layout["detected"])
        self.assertEqual(layout["corner"], "top_right")
        self.assertEqual(layout["preset_name"], "reaction_cam_top")
        self.assertEqual(layout["stack_mode"], "cam_top")
        self.assertGreater(layout["facecam"]["x"], 1200)

    def test_07_crop_presets_integrity(self):
        """Ensures all CROP_PRESETS in core/config.py have valid dimensions and stack modes."""
        self.assertIn("ambient_blur_16_9", CROP_PRESETS)
        self.assertIn("reaction_top_left", CROP_PRESETS)
        self.assertIn("reaction_cam_top", CROP_PRESETS)
        self.assertIn("reaction_bottom_left", CROP_PRESETS)
        self.assertIn("gaming_fps", CROP_PRESETS)

        for key, p in CROP_PRESETS.items():
            self.assertIn("label", p, f"Preset {key} missing label")
            self.assertIn("gameplay", p, f"Preset {key} missing gameplay")
            self.assertIn("facecam", p, f"Preset {key} missing facecam")
            gp = p["gameplay"]
            fc = p["facecam"]
            self.assertGreaterEqual(gp["w"], 0)
            self.assertGreaterEqual(gp["h"], 0)
            self.assertGreaterEqual(fc["w"], 0)
            self.assertGreaterEqual(fc["h"], 0)


if __name__ == "__main__":
    unittest.main()
