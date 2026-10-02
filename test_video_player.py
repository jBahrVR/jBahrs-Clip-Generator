import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from PIL import Image

import av
from video_player import VideoDecoder, DualVideoSyncController
import gui
from gui.video_preview import VideoPreviewWidget


def create_synthetic_mp4(filepath: str, width: int, height: int, fps: int = 24, num_frames: int = 24, rgb_color=(100, 150, 200)):
    """Encodes a synthetic test MP4 video using native PyAV."""
    container = av.open(filepath, mode="w")
    stream = container.add_stream("libx264", rate=fps)
    stream.width = width
    stream.height = height
    stream.pix_fmt = "yuv420p"

    img_data = np.zeros((height, width, 3), dtype=np.uint8)
    img_data[:, :] = rgb_color

    for i in range(num_frames):
        # Slightly alter first pixel each frame so frames are distinct
        frame_data = img_data.copy()
        frame_data[0, 0, 0] = (i * 10) % 255
        frame = av.VideoFrame.from_ndarray(frame_data, format="rgb24")
        frame.pts = i
        packet = stream.encode(frame)
        if packet:
            container.mux(packet)

    packet = stream.encode()
    if packet:
        container.mux(packet)

    container.close()


class TestVideoDecoder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.video_16_9 = os.path.join(cls.temp_dir, "clip_16_9.mp4")
        cls.video_9_16 = os.path.join(cls.temp_dir, "clip_9_16.mp4")
        create_synthetic_mp4(cls.video_16_9, width=320, height=180, fps=24, num_frames=24, rgb_color=(200, 50, 50))
        create_synthetic_mp4(cls.video_9_16, width=180, height=320, fps=24, num_frames=24, rgb_color=(50, 200, 50))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_decoder_properties_16_9(self):
        decoder = VideoDecoder(self.video_16_9)
        self.assertEqual(decoder.width, 320)
        self.assertEqual(decoder.height, 180)
        self.assertAlmostEqual(decoder.aspect_ratio, 320 / 180, places=2)
        self.assertEqual(decoder.fps, 24.0)
        self.assertGreater(decoder.duration, 0.8)
        self.assertFalse(decoder.is_closed)
        decoder.close()
        self.assertTrue(decoder.is_closed)

    def test_decoder_properties_9_16(self):
        decoder = VideoDecoder(self.video_9_16)
        self.assertEqual(decoder.width, 180)
        self.assertEqual(decoder.height, 320)
        self.assertLess(decoder.aspect_ratio, 1.0)
        self.assertEqual(decoder.fps, 24.0)
        decoder.close()

    def test_init_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            VideoDecoder(os.path.join(self.temp_dir, "nonexistent.mp4"))

    def test_read_next_frame(self):
        decoder = VideoDecoder(self.video_16_9)
        frame_res = decoder.read_next_frame()
        self.assertIsNotNone(frame_res)
        pts_sec, img = frame_res
        self.assertGreaterEqual(pts_sec, 0.0)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (320, 180))

        # Read next frame
        frame_res2 = decoder.read_next_frame()
        self.assertIsNotNone(frame_res2)
        pts_sec2, img2 = frame_res2
        self.assertGreater(pts_sec2, pts_sec)
        decoder.close()

    def test_read_until_eof(self):
        decoder = VideoDecoder(self.video_16_9)
        frames_read = 0
        while True:
            res = decoder.read_next_frame()
            if res is None:
                break
            frames_read += 1
        self.assertGreaterEqual(frames_read, 20)
        self.assertIsNone(decoder.read_next_frame())
        decoder.close()

    def test_seek_to_timestamp(self):
        decoder = VideoDecoder(self.video_16_9)
        seek_res = decoder.seek_to(0.5)
        self.assertIsNotNone(seek_res)
        t_sec, img = seek_res
        self.assertAlmostEqual(t_sec, 0.5, delta=0.2)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(decoder.current_time, t_sec)
        decoder.close()

    def test_seek_clamped_bounds(self):
        decoder = VideoDecoder(self.video_16_9)
        # Negative seek clamps to 0.0
        res_neg = decoder.seek_to(-10.0)
        self.assertIsNotNone(res_neg)
        self.assertAlmostEqual(res_neg[0], 0.0, delta=0.1)

        # Seek beyond duration clamps near end
        res_far = decoder.seek_to(999.0)
        self.assertIsNotNone(res_far)
        self.assertGreater(res_far[0], 0.5)
        decoder.close()

    def test_close_releases_resources(self):
        decoder = VideoDecoder(self.video_16_9)
        decoder.close()
        self.assertTrue(decoder.is_closed)
        self.assertIsNone(decoder.read_next_frame())
        self.assertIsNone(decoder.seek_to(0.5))


class TestDualVideoSyncController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.primary_path = os.path.join(cls.temp_dir, "primary.mp4")
        cls.companion_path = os.path.join(cls.temp_dir, "companion.mp4")
        create_synthetic_mp4(cls.primary_path, width=320, height=180, fps=24, num_frames=24)
        create_synthetic_mp4(cls.companion_path, width=180, height=320, fps=24, num_frames=24)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_init_single_video(self):
        controller = DualVideoSyncController(self.primary_path)
        self.assertIsNotNone(controller.primary_decoder)
        self.assertIsNone(controller.companion_decoder)
        self.assertGreater(controller.duration, 0.5)
        self.assertEqual(controller.fps, 24.0)
        self.assertFalse(controller.is_playing)
        controller.close()

    def test_init_dual_videos(self):
        controller = DualVideoSyncController(self.primary_path, self.companion_path)
        self.assertIsNotNone(controller.primary_decoder)
        self.assertIsNotNone(controller.companion_decoder)
        self.assertGreater(controller.duration, 0.5)
        controller.close()

    def test_seek_both_streams(self):
        frames_received = []

        def on_frame(t, prim, comp):
            frames_received.append((t, prim, comp))

        controller = DualVideoSyncController(
            self.primary_path, self.companion_path, on_frame=on_frame
        )
        prim_img, comp_img = controller.seek(0.4)
        self.assertIsNotNone(prim_img)
        self.assertIsNotNone(comp_img)
        self.assertEqual(len(frames_received), 1)
        t, p, c = frames_received[0]
        self.assertAlmostEqual(t, 0.4, delta=0.2)
        self.assertIs(p, prim_img)
        self.assertIs(c, comp_img)
        controller.close()

    def test_step_forward_and_backward(self):
        controller = DualVideoSyncController(self.primary_path)
        controller.seek(0.2)
        initial_time = controller.current_time

        controller.step(0.3)
        self.assertGreater(controller.current_time, initial_time)

        mid_time = controller.current_time
        controller.step(-0.2)
        self.assertLess(controller.current_time, mid_time)
        controller.close()

    def test_play_pause_and_stop_lifecycle(self):
        state_changes = []

        def on_state(s):
            state_changes.append(s)

        controller = DualVideoSyncController(self.primary_path, on_state_change=on_state)
        controller.play()
        self.assertTrue(controller.is_playing)
        self.assertIn("playing", state_changes)

        controller.pause()
        self.assertFalse(controller.is_playing)
        self.assertIn("paused", state_changes)

        controller.toggle_play()
        self.assertTrue(controller.is_playing)

        controller.toggle_play()
        self.assertFalse(controller.is_playing)

        controller.seek(0.5)
        self.assertGreater(controller.current_time, 0.0)
        controller.stop()
        self.assertFalse(controller.is_playing)
        self.assertEqual(controller.current_time, 0.0)
        self.assertIn("stopped", state_changes)

        controller.close()


class TestVideoPreviewWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.horizontal_path = os.path.join(cls.temp_dir, "clip.mp4")
        cls.vertical_path = os.path.join(cls.temp_dir, "clip_vertical.mp4")
        create_synthetic_mp4(cls.horizontal_path, width=320, height=180, fps=24, num_frames=24)
        create_synthetic_mp4(cls.vertical_path, width=180, height=320, fps=24, num_frames=24)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        self.widget = VideoPreviewWidget.__new__(VideoPreviewWidget)
        self.widget.viewport_container = MagicMock()
        self.widget.badge_left = MagicMock()
        self.widget.badge_right = MagicMock()
        self.widget.display_left = MagicMock()
        self.widget.display_right = MagicMock()
        self.widget.timeline_slider = MagicMock()
        self.widget.play_btn = MagicMock()
        self.widget.step_back_btn = MagicMock()
        self.widget.step_fwd_btn = MagicMock()
        self.widget.timecode_label = MagicMock()
        self.widget.mode_selector = MagicMock()
        self.widget.loop_var = MagicMock()
        self.widget.loop_var.get.return_value = True
        self.widget.loop_switch = MagicMock()
        self.widget.ext_player_btn = MagicMock()
        self.widget.controller = None
        self.widget.primary_path = None
        self.widget.companion_path = None
        self.widget.view_mode = "side_by_side"
        self.widget._is_scrubbing = False
        self.widget._render_pending = False
        self.widget._cached_primary_img = None
        self.widget._cached_companion_img = None
        self.widget.after = MagicMock()

    def test_load_video_success(self):
        loaded = self.widget.load_video(self.horizontal_path, self.vertical_path)
        self.assertTrue(loaded)
        self.assertIsNotNone(self.widget.controller)
        self.assertEqual(self.widget.primary_path, self.horizontal_path)
        self.assertEqual(self.widget.companion_path, self.vertical_path)
        self.assertEqual(self.widget.view_mode, "side_by_side")
        self.widget.timeline_slider.configure.assert_called()
        self.widget.play_btn.configure.assert_called_with(state="normal", text="▶ Play")
        self.widget.close()

    def test_load_video_missing_file_returns_false(self):
        loaded = self.widget.load_video("nonexistent_path.mp4")
        self.assertFalse(loaded)
        self.assertIsNone(self.widget.controller)
        self.widget.display_left.configure.assert_called_with(text="Video file not found", image=None)

    def test_load_video_single_horizontal(self):
        loaded = self.widget.load_video(self.horizontal_path)
        self.assertTrue(loaded)
        self.assertEqual(self.widget.view_mode, "horizontal")
        self.widget.mode_selector.set.assert_called_with("16:9 Only")
        self.widget.close()

    def test_load_video_single_vertical(self):
        loaded = self.widget.load_video(self.vertical_path)
        self.assertTrue(loaded)
        self.assertEqual(self.widget.view_mode, "vertical")
        self.widget.mode_selector.set.assert_called_with("9:16 Only")
        self.widget.close()

    def test_view_mode_selection(self):
        self.widget._on_mode_selected("Side-by-Side")
        self.assertEqual(self.widget.view_mode, "side_by_side")

        self.widget._on_mode_selected("16:9 Only")
        self.assertEqual(self.widget.view_mode, "horizontal")

        self.widget._on_mode_selected("9:16 Only")
        self.assertEqual(self.widget.view_mode, "vertical")

    def test_apply_view_layout_modes(self):
        self.widget.view_mode = "side_by_side"
        self.widget._apply_view_layout()
        self.widget.badge_left.grid.assert_called()
        self.widget.badge_right.grid.assert_called()

        self.widget.view_mode = "horizontal"
        self.widget._apply_view_layout()
        self.widget.badge_right.grid_forget.assert_called()
        self.widget.display_right.grid_forget.assert_called()

        self.widget.view_mode = "vertical"
        self.widget._apply_view_layout()
        self.widget.badge_left.grid_forget.assert_called()
        self.widget.display_left.grid_forget.assert_called()

    def test_controller_delegations(self):
        mock_ctrl = MagicMock()
        self.widget.controller = mock_ctrl

        self.widget.toggle_play()
        mock_ctrl.toggle_play.assert_called_once()

        self.widget.play()
        mock_ctrl.play.assert_called_once()

        self.widget.pause()
        mock_ctrl.pause.assert_called_once()

        self.widget.stop()
        mock_ctrl.stop.assert_called_once()

        self.widget.step(1.5)
        mock_ctrl.step.assert_called_with(1.5)

        self.widget.loop_var.get.return_value = False
        self.widget._on_loop_toggle()
        self.assertFalse(mock_ctrl.loop)

    def test_scrubber_events(self):
        mock_ctrl = MagicMock()
        mock_ctrl.is_playing = True
        self.widget.controller = mock_ctrl

        # Press slider pauses playback
        self.widget._on_slider_press()
        self.assertTrue(self.widget._is_scrubbing)
        mock_ctrl.pause.assert_called_once()

        # Moving slider scrubs video
        self.widget._on_slider_moved(0.75)
        mock_ctrl.seek.assert_called_with(0.75)

        # Release completes scrubbing
        self.widget.timeline_slider.get.return_value = 0.75
        self.widget._on_slider_release()
        self.assertFalse(self.widget._is_scrubbing)

    def test_external_player_launcher(self):
        self.widget.primary_path = self.horizontal_path
        with patch("os.startfile", create=True) as mock_startfile:
            self.widget._open_external_player()
            mock_startfile.assert_called_with(os.path.abspath(self.horizontal_path))

    def test_close_resets_state(self):
        mock_ctrl = MagicMock()
        self.widget.controller = mock_ctrl
        self.widget._cached_primary_img = Image.new("RGB", (100, 100))
        self.widget._cached_companion_img = Image.new("RGB", (100, 100))

        self.widget.close()
        mock_ctrl.close.assert_called_once()
        self.assertIsNone(self.widget.controller)
        self.assertIsNone(self.widget._cached_primary_img)
        self.assertIsNone(self.widget._cached_companion_img)


if __name__ == "__main__":
    unittest.main()
