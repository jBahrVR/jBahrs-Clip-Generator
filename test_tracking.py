import os
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import cv2

import tracking_engine
import editor


class TestTrajectorySmoother(unittest.TestCase):
    def test_initial_value(self):
        smoother = tracking_engine.TrajectorySmoother(alpha=0.5, deadband_px=20.0)
        self.assertEqual(smoother.update(100.0), 100.0)

    def test_deadband_rejection(self):
        smoother = tracking_engine.TrajectorySmoother(alpha=0.5, deadband_px=20.0)
        smoother.update(100.0)
        # Small twitch of 10px is below 20px deadband -> ignored
        self.assertEqual(smoother.update(110.0), 100.0)
        self.assertEqual(smoother.update(92.0), 100.0)

    def test_ema_smoothing(self):
        smoother = tracking_engine.TrajectorySmoother(alpha=0.5, deadband_px=10.0)
        smoother.update(100.0)
        # Movement of 50px exceeds deadband -> EMA applied: 0.5 * 150 + 0.5 * 100 = 125
        val = smoother.update(150.0)
        self.assertAlmostEqual(val, 125.0, places=1)

    def test_reset(self):
        smoother = tracking_engine.TrajectorySmoother()
        smoother.update(50.0)
        smoother.reset()
        self.assertIsNone(smoother.current_val)


class TestFaceTracker(unittest.TestCase):
    def test_detect_face_on_blank_frame(self):
        tracker = tracking_engine.FaceTracker()
        blank = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.assertIsNone(tracker.detect_face_candidate(blank))
        self.assertIsNone(tracker.detect_face_candidate(None))

    def test_detect_face_on_synthetic_skin_canvas(self):
        tracker = tracking_engine.FaceTracker()
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        # Draw a simulated streamer webcam rectangle in top-right
        # YCrCb skin tone: BGR approx (130, 160, 210)
        cv2.rectangle(frame, (1400, 100), (1700, 450), (130, 160, 210), -1)

        box = tracker.detect_face_candidate(frame)
        self.assertIsNotNone(box)
        bx, by, bw, bh = box
        # Bounding box should surround the simulated face region
        self.assertAlmostEqual(bx + bw / 2, 1550, delta=50)
        self.assertAlmostEqual(by + bh / 2, 275, delta=50)

    def test_extreme_aspect_ratio_rejection(self):
        tracker = tracking_engine.FaceTracker()
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # Draw a very thin vertical bar (aspect ratio >> 2.0 or << 0.5)
        cv2.rectangle(frame, (500, 100), (510, 800), (130, 160, 210), -1)
        self.assertIsNone(tracker.detect_face_candidate(frame))


class TestActionTracker(unittest.TestCase):
    def test_no_motion_returns_none(self):
        tracker = tracking_engine.ActionTracker()
        f1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        f2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertIsNone(tracker.detect_action_centroid(f1))
        self.assertIsNone(tracker.detect_action_centroid(f2))

    def test_motion_centroid_detection(self):
        tracker = tracking_engine.ActionTracker()
        f1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        f2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Draw motion event in right half of screen
        cv2.rectangle(f2, (900, 200), (1100, 400), (255, 255, 255), -1)

        tracker.detect_action_centroid(f1)
        res = tracker.detect_action_centroid(f2)
        self.assertIsNotNone(res)
        cx, cy = res
        self.assertAlmostEqual(cx, 1000, delta=30)
        self.assertAlmostEqual(cy, 300, delta=30)

    def test_reset(self):
        tracker = tracking_engine.ActionTracker()
        tracker.prev_gray = np.zeros((100, 100), dtype=np.uint8)
        tracker.reset()
        self.assertIsNone(tracker.prev_gray)


class TestCalculateOptimalCropWindow(unittest.TestCase):
    def test_missing_video_fallback(self):
        x, y, w, h = tracking_engine.calculate_optimal_crop_window(
            video_path="nonexistent_video.mp4",
            start_time=0.0,
            end_time=5.0,
            video_width=1920,
            video_height=1080
        )
        self.assertEqual(h, 1080)
        self.assertEqual(w, 606)  # Even width 1080 * 9 / 16
        # Center fallback: (1920 - 606) // 2 = 657
        self.assertEqual(x, (1920 - 606) // 2)
        self.assertEqual(y, 0)

    def test_crop_window_bounds_clamping(self):
        dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # Draw face far off to right side
        cv2.rectangle(dummy_frame, (1700, 100), (1900, 350), (130, 160, 210), -1)

        samples = [(0.0, dummy_frame), (1.0, dummy_frame)]

        with patch("tracking_engine.sample_frames_from_video", return_value=samples):
            x, y, w, h = tracking_engine.calculate_optimal_crop_window(
                video_path="mock.mp4",
                start_time=0.0,
                end_time=2.0,
                mode="face",
                video_width=1920,
                video_height=1080
            )

        # Crop window must stay fully within [0, 1920 - w]
        self.assertGreaterEqual(x, 0)
        self.assertLessEqual(x + w, 1920)
        # Target was at 1800, so x should be shifted toward the right side
        self.assertGreater(x, 1000)

    def test_action_tracking_mode(self):
        f1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        f2 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # Action happening in left third
        cv2.rectangle(f2, (100, 300), (300, 500), (255, 255, 255), -1)

        samples = [(0.0, f1), (1.0, f2)]

        with patch("tracking_engine.sample_frames_from_video", return_value=samples):
            x, y, w, h = tracking_engine.calculate_optimal_crop_window(
                video_path="mock.mp4",
                start_time=0.0,
                end_time=2.0,
                mode="action",
                video_width=1920,
                video_height=1080
            )

        self.assertGreaterEqual(x, 0)
        self.assertLessEqual(x + w, 1920)
        # Target was at 200, so x should be shifted toward the left side
        self.assertLess(x, 500)


class TestEditorTrackingIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dummy_video = os.path.join(self.temp_dir, "clip.mp4")
        with open(self.dummy_video, "wb") as f:
            f.write(b"video data")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_auto_face_tracking_invokes_tracker(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run), \
             patch("tracking_engine.calculate_optimal_crop_window", return_value=(850, 0, 608, 1080)) as mock_track:

            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "vert.mp4"),
                start_time=2.0,
                end_time=8.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Auto-Face Tracking (AI)",
                config={},
                logger=None
            )

        mock_track.assert_called_once_with(
            video_path=self.dummy_video,
            start_time=2.0,
            end_time=8.0,
            mode="face"
        )
        self.assertEqual(len(executed_cmds), 1)
        cmd_str = " ".join(executed_cmds[0])
        self.assertIn("crop=608:1080:850:0", cmd_str)

    def test_smart_action_tracking_invokes_tracker(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run), \
             patch("tracking_engine.calculate_optimal_crop_window", return_value=(320, 0, 608, 1080)) as mock_track:

            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "vert.mp4"),
                start_time=0.0,
                end_time=10.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Smart Action Tracking (AI)",
                config={},
                logger=None
            )

        mock_track.assert_called_once_with(
            video_path=self.dummy_video,
            start_time=0.0,
            end_time=10.0,
            mode="action"
        )
        cmd_str = " ".join(executed_cmds[0])
        self.assertIn("crop=608:1080:320:0", cmd_str)

    def test_standard_crop_does_not_invoke_tracking(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run), \
             patch("tracking_engine.calculate_optimal_crop_window") as mock_track:

            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "vert.mp4"),
                start_time=0.0,
                end_time=10.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Standard Center Crop",
                config={},
                logger=None
            )

        # Standard crop must NEVER invoke tracking engine (zero tracking overhead!)
        mock_track.assert_not_called()

    def test_tracking_exception_graceful_fallback(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run), \
             patch("tracking_engine.calculate_optimal_crop_window", side_effect=RuntimeError("GPU out of memory")):

            # Must not crash; must fall back to center crop
            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "vert.mp4"),
                start_time=0.0,
                end_time=10.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Auto-Face Tracking (AI)",
                config={},
                logger=None
            )

        cmd_str = " ".join(executed_cmds[0])
        self.assertIn("crop=608:1080:656:0", cmd_str)


if __name__ == "__main__":
    unittest.main()
