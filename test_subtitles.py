import os
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

import subtitle_engine
import config_manager
import editor


class TestSubtitleEngineFormatting(unittest.TestCase):
    def test_format_ass_time(self):
        self.assertEqual(subtitle_engine.format_ass_time(0.0), "0:00:00.00")
        self.assertEqual(subtitle_engine.format_ass_time(12.34), "0:00:12.34")
        self.assertEqual(subtitle_engine.format_ass_time(75.5), "0:01:15.50")
        self.assertEqual(subtitle_engine.format_ass_time(3661.05), "1:01:01.05")
        # Negative timestamp clamped to 0
        self.assertEqual(subtitle_engine.format_ass_time(-5.0), "0:00:00.00")

    def test_escape_ffmpeg_filter_path(self):
        # Windows drive letter colon and backslashes
        escaped = subtitle_engine.escape_ffmpeg_filter_path(r"C:\Users\test\clips\sub.ass")
        self.assertEqual(escaped, r"C\:/Users/test/clips/sub.ass")

        # Brackets and single quotes
        escaped2 = subtitle_engine.escape_ffmpeg_filter_path(r"D:\path\[special] 'name'.ass")
        self.assertIn(r"\[special\]", escaped2)
        self.assertIn(r"\'name\'", escaped2)
        self.assertIn(r"D\:/", escaped2)


class TestSubtitlePhraseGrouping(unittest.TestCase):
    def test_group_words_respects_max_words_per_line(self):
        words = [
            {"word": f"word{i}", "start": float(i), "end": float(i + 0.3)}
            for i in range(10)
        ]
        phrases = subtitle_engine.group_words_into_phrases(words, max_words_per_line=3, max_pause_sec=1.0)
        self.assertEqual(len(phrases), 4)
        self.assertEqual(len(phrases[0]), 3)
        self.assertEqual(len(phrases[1]), 3)
        self.assertEqual(len(phrases[2]), 3)
        self.assertEqual(len(phrases[3]), 1)

    def test_group_words_splits_on_long_pause(self):
        words = [
            {"word": "First", "start": 0.0, "end": 0.4},
            {"word": "phrase", "start": 0.5, "end": 0.8},
            # 2.0s gap
            {"word": "Second", "start": 2.8, "end": 3.1},
            {"word": "phrase", "start": 3.2, "end": 3.5},
        ]
        phrases = subtitle_engine.group_words_into_phrases(words, max_words_per_line=5, max_pause_sec=0.5)
        self.assertEqual(len(phrases), 2)
        self.assertEqual([w["word"] for w in phrases[0]], ["First", "phrase"])
        self.assertEqual([w["word"] for w in phrases[1]], ["Second", "phrase"])

    def test_group_words_splits_on_punctuation(self):
        words = [
            {"word": "Stop!", "start": 0.0, "end": 0.4},
            {"word": "Look", "start": 0.5, "end": 0.8},
            {"word": "here.", "start": 0.9, "end": 1.2},
            {"word": "Done", "start": 1.3, "end": 1.6},
        ]
        phrases = subtitle_engine.group_words_into_phrases(words, max_words_per_line=5, max_pause_sec=1.0)
        self.assertEqual(len(phrases), 3)
        self.assertEqual([w["word"] for w in phrases[0]], ["Stop!"])
        self.assertEqual([w["word"] for w in phrases[1]], ["Look", "here."])
        self.assertEqual([w["word"] for w in phrases[2]], ["Done"])

    def test_group_words_skips_empty_text(self):
        words = [
            {"word": "", "start": 0.0, "end": 0.2},
            {"word": "   ", "start": 0.3, "end": 0.4},
            {"word": "Valid", "start": 0.5, "end": 0.8}
        ]
        phrases = subtitle_engine.group_words_into_phrases(words)
        self.assertEqual(len(phrases), 1)
        self.assertEqual(len(phrases[0]), 1)
        self.assertEqual(phrases[0][0]["word"], "Valid")


class TestAssFileGeneration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_ass_subtitles_viral_yellow(self):
        words = [
            {"word": "That", "start": 10.0, "end": 10.3},
            {"word": "was", "start": 10.4, "end": 10.6},
            {"word": "insane!", "start": 10.7, "end": 11.2},
        ]
        out_path = os.path.join(self.temp_dir, "test_clip.ass")
        res_path = subtitle_engine.generate_ass_subtitles(
            words=words,
            output_ass_path=out_path,
            clip_start=10.0,
            clip_end=15.0,
            style_preset="Viral Yellow Highlight",
            position_preset="Bottom Third"
        )
        self.assertEqual(res_path, out_path)
        self.assertTrue(os.path.exists(out_path))

        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check ASS headers
        self.assertIn("[Script Info]", content)
        self.assertIn("PlayResX: 1080", content)
        self.assertIn("PlayResY: 1920", content)
        self.assertIn("[V4+ Styles]", content)
        self.assertIn("[Events]", content)

        # Check Yellow highlight hex code & Bottom-Third alignment (2)
        self.assertIn("&H0000FFFF&", content)
        self.assertIn(",2,40,40,280,1", content)

        # Check dialogue events with karaoke word highlighting
        self.assertIn(r"{\c&H0000FFFF&}That{\c&H00FFFFFF&} was insane!", content)
        self.assertIn(r"That {\c&H0000FFFF&}was{\c&H00FFFFFF&} insane!", content)
        self.assertIn(r"That was {\c&H0000FFFF&}insane!{\c&H00FFFFFF&}", content)

    def test_generate_ass_subtitles_presets(self):
        words = [{"word": "Test", "start": 0.0, "end": 0.5}]

        # Test Neon Green
        green_path = os.path.join(self.temp_dir, "green.ass")
        subtitle_engine.generate_ass_subtitles(words, green_path, style_preset="Neon Green Highlight", position_preset="Center")
        with open(green_path, "r", encoding="utf-8") as f:
            c = f.read()
            self.assertIn("&H0000FF00&", c)
            self.assertIn(",5,40,40,0,1", c)  # Center alignment 5

        # Test Top Third
        top_path = os.path.join(self.temp_dir, "top.ass")
        subtitle_engine.generate_ass_subtitles(words, top_path, position_preset="Top Third")
        with open(top_path, "r", encoding="utf-8") as f:
            c = f.read()
            self.assertIn(",8,40,40,260,1", c)  # Top alignment 8

    def test_clip_boundary_filtering(self):
        words = [
            {"word": "Before", "start": 1.0, "end": 2.0},
            {"word": "Inside", "start": 5.0, "end": 6.0},
            {"word": "After", "start": 12.0, "end": 13.0},
        ]
        out_path = os.path.join(self.temp_dir, "clamped.ass")
        subtitle_engine.generate_ass_subtitles(words, out_path, clip_start=4.0, clip_end=10.0)
        with open(out_path, "r", encoding="utf-8") as f:
            c = f.read()
            self.assertNotIn("Before", c)
            self.assertIn("Inside", c)
            self.assertNotIn("After", c)


class TestSubtitleConfiguration(unittest.TestCase):
    def test_settings_config_defaults(self):
        cfg = config_manager.SettingsConfig()
        # Strictly optional & disabled by default
        self.assertFalse(cfg.burn_subtitles)
        self.assertEqual(cfg.subtitle_style, "Viral Yellow Highlight")
        self.assertEqual(cfg.subtitle_position, "Bottom Third")
        self.assertEqual(cfg.subtitle_font_size, 24)

    def test_app_config_serialization(self):
        raw = config_manager.get_raw_default_dict()
        self.assertFalse(raw["settings"]["burn_subtitles"])

        raw["settings"]["burn_subtitles"] = True
        raw["settings"]["subtitle_style"] = "Neon Green Highlight"
        app_cfg = config_manager.AppConfig.from_dict(raw)
        self.assertTrue(app_cfg.settings.burn_subtitles)
        self.assertEqual(app_cfg.settings.subtitle_style, "Neon Green Highlight")

        exported = app_cfg.to_dict()
        self.assertTrue(exported["settings"]["burn_subtitles"])
        self.assertEqual(exported["settings"]["subtitle_style"], "Neon Green Highlight")


class TestEditorSubtitleIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dummy_video = os.path.join(self.temp_dir, "clip.mp4")
        with open(self.dummy_video, "wb") as f:
            f.write(b"dummy video data")

        self.dummy_ass = os.path.join(self.temp_dir, "clip_subtitles.ass")
        with open(self.dummy_ass, "w", encoding="utf-8") as f:
            f.write("[Script Info]\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_vertical_clip_no_subtitles(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run):
            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "out_vert.mp4"),
                start_time=0.0,
                end_time=5.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Standard Center Crop",
                config={},
                logger=None,
                subtitle_file=None
            )

        self.assertEqual(len(executed_cmds), 1)
        cmd_str = " ".join(executed_cmds[0])
        # Verify NO ass filter is added when subtitles are None/disabled
        self.assertNotIn("ass=", cmd_str)

    def test_generate_vertical_clip_with_subtitles(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run):
            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "out_vert.mp4"),
                start_time=0.0,
                end_time=5.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Standard Center Crop",
                config={},
                logger=None,
                subtitle_file=self.dummy_ass
            )

        self.assertEqual(len(executed_cmds), 1)
        cmd_str = " ".join(executed_cmds[0])
        # Verify ass filter IS present with escaped filename
        self.assertIn("ass=", cmd_str)

    def test_generate_vertical_blurred_background_with_subtitles(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run):
            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "out_vert.mp4"),
                start_time=0.0,
                end_time=5.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Blurred Background (Letterbox)",
                config={},
                logger=None,
                subtitle_file=self.dummy_ass
            )

        self.assertEqual(len(executed_cmds), 1)
        cmd_str = " ".join(executed_cmds[0])
        self.assertIn("boxblur", cmd_str)
        self.assertIn("ass=", cmd_str)

    def test_generate_vertical_facecam_with_subtitles(self):
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            return 0

        with patch("utils.run_subprocess_command", side_effect=mock_run):
            editor._generate_vertical_clip(
                file_path=self.dummy_video,
                vert_output=os.path.join(self.temp_dir, "out_vert.mp4"),
                start_time=0.0,
                end_time=5.0,
                video_codec="libx264",
                audio_codec_flags=["-c:a", "copy"],
                hardware_encoding=False,
                vertical_mode="Facecam Top-Left",
                config={},
                logger=None,
                subtitle_file=self.dummy_ass
            )

        self.assertEqual(len(executed_cmds), 1)
        cmd_str = " ".join(executed_cmds[0])
        self.assertIn("vstack", cmd_str)
        self.assertIn("ass=", cmd_str)

    def test_process_single_clip_subtitles_disabled_by_default(self):
        config = {
            "settings": {
                "vertical_export": True,
                "burn_subtitles": False
            }
        }
        clip = {
            "start_time": 0.0,
            "end_time": 5.0,
            "virality_score": 9,
            "words": [{"word": "test", "start": 1.0, "end": 2.0}]
        }

        with patch("editor._generate_horizontal_clip"), \
             patch("editor._generate_vertical_clip") as mock_vert, \
             patch("editor._generate_thumbnail"), \
             patch("subtitle_engine.generate_ass_subtitles") as mock_gen_ass:

            editor._process_single_clip(
                0, clip, self.dummy_video, "base", self.temp_dir,
                "libx264", ["-c:a", "copy"], False,
                False, True, "Standard Center Crop",
                config, None, None
            )

            # Subtitle engine must NOT be called when disabled
            mock_gen_ass.assert_not_called()
            # subtitle_file passed to _generate_vertical_clip must be None
            mock_vert.assert_called_once()
            self.assertIsNone(mock_vert.call_args[1].get("subtitle_file"))

    def test_process_single_clip_subtitles_enabled(self):
        config = {
            "settings": {
                "vertical_export": True,
                "burn_subtitles": True,
                "subtitle_style": "Viral Yellow Highlight",
                "subtitle_position": "Bottom Third",
                "subtitle_font_size": 48
            }
        }
        clip = {
            "start_time": 0.0,
            "end_time": 5.0,
            "virality_score": 9,
            "words": [{"word": "Epic", "start": 1.0, "end": 2.0}]
        }

        with patch("editor._generate_horizontal_clip"), \
             patch("editor._generate_vertical_clip") as mock_vert, \
             patch("editor._generate_thumbnail"):

            editor._process_single_clip(
                0, clip, self.dummy_video, "base", self.temp_dir,
                "libx264", ["-c:a", "copy"], False,
                False, True, "Standard Center Crop",
                config, None, None
            )

            mock_vert.assert_called_once()
            passed_sub = mock_vert.call_args[1].get("subtitle_file")
            self.assertIsNotNone(passed_sub)
            self.assertTrue(passed_sub.endswith("_subtitles.ass"))
            self.assertTrue(os.path.exists(passed_sub))


if __name__ == "__main__":
    unittest.main()
