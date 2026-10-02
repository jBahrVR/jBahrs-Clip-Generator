import unittest
import unittest.mock
import os
import subprocess
import numpy as np
import torch
import editor

class TestEditorExtractAudioHidden(unittest.TestCase):
    @unittest.mock.patch('editor.get_audio_stream_count', return_value=1)
    @unittest.mock.patch('subprocess.Popen')
    def test_extract_audio_hidden_success_linux(self, mock_subprocess_popen, mock_stream_count):
        # Mocking os.name to be 'posix' (Linux/macOS)
        with unittest.mock.patch('os.name', 'posix'):
            # Mock the return value of subprocess.Popen
            mock_process = unittest.mock.MagicMock()
            mock_process.returncode = 0

            # Create a small mock audio output buffer (e.g., 4 bytes of int16 zeros)
            mock_stdout = np.zeros(10, dtype=np.int16).tobytes()
            mock_process.communicate.return_value = (mock_stdout, b"")
            mock_subprocess_popen.return_value = mock_process

            file_path = "test_audio.mp4"
            sr = 16000

            # Call the function
            result = editor.extract_audio_hidden(file_path, sr)

            # Assertions
            expected_cmd = [
                "ffmpeg", "-nostdin", "-threads", "0", "-i", file_path,
                "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", str(sr), "-"
            ]
            mock_subprocess_popen.assert_called_once_with(expected_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=None, cwd=None)

            # Check the output format (should be normalized float32)
            self.assertTrue(isinstance(result, np.ndarray))
            self.assertEqual(result.dtype, np.float32)
            self.assertEqual(len(result), 10)

    @unittest.mock.patch('subprocess.Popen')
    def test_extract_audio_hidden_success_windows(self, mock_subprocess_popen):
        # Mocking os.name to be 'nt' (Windows) and ensuring subprocess has STARTUPINFO
        with unittest.mock.patch('os.name', 'nt'):

            class DummyStartupInfo:
                def __init__(self):
                    self.dwFlags = 0
                    self.wShowWindow = 0

            with unittest.mock.patch.object(subprocess, 'STARTUPINFO', DummyStartupInfo, create=True), \
                 unittest.mock.patch.object(subprocess, 'STARTF_USESHOWWINDOW', 1, create=True), \
                 unittest.mock.patch.object(subprocess, 'SW_HIDE', 0, create=True):

                mock_process = unittest.mock.MagicMock()
                mock_process.returncode = 0
                mock_stdout = np.zeros(10, dtype=np.int16).tobytes()
                mock_process.communicate.return_value = (mock_stdout, b"")
                mock_subprocess_popen.return_value = mock_process

                file_path = "test_audio_win.mp4"

                # Call the function
                editor.extract_audio_hidden(file_path)

                # Retrieve the arguments passed to subprocess.Popen
                args, kwargs = mock_subprocess_popen.call_args

                expected_cmd = [
                    "ffmpeg", "-nostdin", "-threads", "0", "-i", file_path,
                    "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", "16000", "-"
                ]

                self.assertEqual(args[0], expected_cmd)
                self.assertEqual(kwargs['stdout'], subprocess.PIPE)
                self.assertEqual(kwargs['stderr'], subprocess.PIPE)

                # Verify that startupinfo was passed and configured correctly
                startupinfo = kwargs['startupinfo']
                self.assertIsNotNone(startupinfo)
                self.assertEqual(startupinfo.dwFlags, 1) # STARTF_USESHOWWINDOW
                self.assertEqual(startupinfo.wShowWindow, 0) # SW_HIDE

    @unittest.mock.patch('subprocess.Popen')
    def test_extract_audio_hidden_failure(self, mock_subprocess_popen):
        # Test when ffmpeg fails
        mock_process = unittest.mock.MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Mock FFmpeg Error")
        mock_subprocess_popen.return_value = mock_process

        with self.assertRaises(RuntimeError) as context:
            editor.extract_audio_hidden("bad_file.mp4")

        self.assertIn("FFmpeg audio extraction failed", str(context.exception))
        self.assertIn("Mock FFmpeg Error", str(context.exception))

    @unittest.mock.patch('subprocess.Popen')
    def test_extract_audio_hidden_ffmpeg_not_found(self, mock_subprocess_popen):
        mock_subprocess_popen.side_effect = FileNotFoundError("[WinError 2] The system cannot find the file specified")

        with self.assertRaises(FileNotFoundError) as context:
            editor.extract_audio_hidden("sample.mp4")

        self.assertIn("FFmpeg executable not found", str(context.exception))


class MockSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text

class TestEditorTranscribeAudioToSegments(unittest.TestCase):
    def setUp(self):
        editor.free_whisper_model()

    def tearDown(self):
        editor.free_whisper_model()

    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('editor.WhisperModel')
    @unittest.mock.patch('torch.cuda.is_available', return_value=False)
    def test_faster_whisper_transcribe_passes_language(self, mock_cuda, mock_whisper_model, mock_extract_audio):
        mock_model = unittest.mock.MagicMock()
        mock_model.transcribe.return_value = ([MockSegment(0.0, 2.5, "Hola")], None)
        mock_whisper_model.return_value = mock_model
        mock_extract_audio.return_value = np.zeros(100, dtype=np.float32)
        mock_logger = unittest.mock.MagicMock()

        config = {
            "openai": {
                "whisper_model": "base",
                "whisper_language": "Spanish"
            },
            "settings": {
                "audio_peak_detection": False,
                "combat_detection": False
            }
        }

        result = editor._transcribe_audio_to_segments("mock_video.mp4", config, mock_logger, None)

        mock_whisper_model.assert_called_once_with("base", device="cpu", compute_type="int8")
        mock_model.transcribe.assert_called_once()
        called_args, called_kwargs = mock_model.transcribe.call_args
        self.assertEqual(called_kwargs.get("language"), "es")
        self.assertTrue(called_kwargs.get("vad_filter"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hola")

    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('editor.WhisperModel')
    @unittest.mock.patch('torch.cuda.is_available', return_value=False)
    def test_faster_whisper_autodetect_language(self, mock_cuda, mock_whisper_model, mock_extract_audio):
        mock_model = unittest.mock.MagicMock()
        mock_model.transcribe.return_value = ([MockSegment(0.0, 2.5, "Hello")], None)
        mock_whisper_model.return_value = mock_model
        mock_extract_audio.return_value = np.zeros(100, dtype=np.float32)
        mock_logger = unittest.mock.MagicMock()

        config = {
            "openai": {
                "whisper_model": "base",
                "whisper_language": "Auto-Detect"
            },
            "settings": {
                "audio_peak_detection": False,
                "combat_detection": False
            }
        }

        result = editor._transcribe_audio_to_segments("mock_video.mp4", config, mock_logger, None)

        mock_whisper_model.assert_called_once_with("base", device="cpu", compute_type="int8")
        mock_model.transcribe.assert_called_once()
        called_args, called_kwargs = mock_model.transcribe.call_args
        self.assertNotIn("language", called_kwargs)
        self.assertTrue(called_kwargs.get("vad_filter"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hello")

    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('editor.WhisperModel')
    @unittest.mock.patch('torch.cuda.empty_cache')
    @unittest.mock.patch('torch.cuda.get_device_name', return_value="NVIDIA RTX 4090")
    @unittest.mock.patch('torch.cuda.is_available', return_value=True)
    def test_faster_whisper_cuda_fp16_and_cache_cleared(self, mock_cuda, mock_gpu_name, mock_empty_cache, mock_whisper_model, mock_extract_audio):
        mock_model = unittest.mock.MagicMock()
        mock_model.transcribe.return_value = ([MockSegment(0.0, 3.0, "Clutch play")], None)
        mock_whisper_model.return_value = mock_model
        mock_extract_audio.return_value = np.zeros(100, dtype=np.float32)

        config = {
            "openai": {"whisper_model": "medium", "whisper_language": "English"},
            "settings": {"audio_peak_detection": False, "combat_detection": False}
        }

        result = editor._transcribe_audio_to_segments("mock_video.mp4", config, None, None)
        mock_whisper_model.assert_called_once_with("medium", device="cuda", compute_type="float16")
        self.assertEqual(len(result), 1)
        mock_empty_cache.assert_called()

    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('editor.WhisperModel')
    @unittest.mock.patch('torch.cuda.is_available', return_value=False)
    def test_faster_whisper_cancellation_during_iteration(self, mock_cuda, mock_whisper_model, mock_extract_audio):
        mock_model = unittest.mock.MagicMock()
        def seg_generator():
            yield MockSegment(0.0, 1.0, "First")
            yield MockSegment(1.0, 2.0, "Second")
        mock_model.transcribe.return_value = (seg_generator(), None)
        mock_whisper_model.return_value = mock_model
        mock_extract_audio.return_value = np.zeros(100, dtype=np.float32)

        call_count = [0]
        def is_cancelled():
            call_count[0] += 1
            return call_count[0] > 1

        config = {
            "openai": {"whisper_model": "base", "whisper_language": "English"},
            "settings": {"audio_peak_detection": False, "combat_detection": False}
        }

        result = editor._transcribe_audio_to_segments("mock_video.mp4", config, None, is_cancelled)
        self.assertIsNone(result)

    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('whisper.load_model')
    @unittest.mock.patch('editor.HAS_FASTER_WHISPER', False)
    @unittest.mock.patch('torch.cuda.is_available', return_value=False)
    def test_vanilla_whisper_fallback(self, mock_cuda, mock_load_model, mock_extract_audio):
        mock_model = unittest.mock.MagicMock()
        mock_model.transcribe.return_value = {"segments": [{"start": 0.0, "end": 2.5, "text": "Fallback"}]}
        mock_load_model.return_value = mock_model
        mock_extract_audio.return_value = np.zeros(100, dtype=np.float32)

        config = {
            "openai": {"whisper_model": "base", "whisper_language": "English"},
            "settings": {"audio_peak_detection": False, "combat_detection": False}
        }

        result = editor._transcribe_audio_to_segments("mock_video.mp4", config, None, None)
        mock_load_model.assert_called_once_with("base", device="cpu")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Fallback")

    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('editor.get_whisper_model')
    @unittest.mock.patch('editor.is_cuda_available', return_value=True)
    def test_transcribe_cuda_load_failure_falls_back_to_cpu(self, mock_is_cuda, mock_get_model, mock_extract):
        mock_cpu_model = unittest.mock.MagicMock()
        mock_cpu_model.transcribe.return_value = ([MockSegment(0.0, 2.0, "CPU Fallback")], None)
        mock_get_model.side_effect = [RuntimeError("CUDA out of memory"), mock_cpu_model]
        mock_extract.return_value = np.zeros(100, dtype=np.float32)
        mock_logger = unittest.mock.MagicMock()

        config = {
            "openai": {"whisper_model": "base", "whisper_language": "English"},
            "settings": {"audio_peak_detection": False, "combat_detection": False}
        }
        result = editor._transcribe_audio_to_segments("mock.mp4", config, mock_logger, None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "CPU Fallback")
        self.assertEqual(mock_get_model.call_count, 2)
        mock_get_model.assert_any_call("base", "cuda", logger=mock_logger)
        mock_get_model.assert_any_call("base", "cpu", logger=mock_logger)

class TestEditorGenerateClipsWithLLM(unittest.TestCase):
    @unittest.mock.patch('editor.HAS_GEMINI', True)
    def test_generate_clips_with_llm_gemini(self):
        # Create mock elements
        mock_client = unittest.mock.MagicMock()
        mock_response = unittest.mock.MagicMock()
        mock_response.text = '{"clips": [{"start_time": 10.0, "end_time": 15.0, "virality_score": 90, "reasoning": "funny banter"}]}'
        mock_client.models.generate_content.return_value = mock_response

        # Mock the genai module
        mock_genai = unittest.mock.MagicMock()
        mock_genai.Client.return_value = mock_client

        with unittest.mock.patch('editor.genai', mock_genai):
            segments = [
                {"start": 10.0, "end": 15.0, "text": "funny banter text"}
            ]
            config = {
                "google": {
                    "api_key": "test-google-key"
                }
            }
            logger = unittest.mock.MagicMock()

            # Call function
            result = editor._generate_clips_with_llm(
                segments=segments,
                config=config,
                chat_model="gemini-3-flash-preview",
                prompt_text="system instruction",
                logger=logger
            )

            # Assertions
            mock_genai.Client.assert_called_once_with(api_key="test-google-key")
            mock_client.models.generate_content.assert_called_once_with(
                model="gemini-3-flash-preview",
                contents="Analyze this entire gaming transcript. The timestamps for each line are in brackets. Return strictly JSON.\n\n[10.0s - 15.0s] funny banter text\n",
                config={
                    "system_instruction": "system instruction",
                    "response_mime_type": "application/json"
                }
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["start_time"], 10.0)
            self.assertEqual(result[0]["virality_score"], 90)

    @unittest.mock.patch('editor.OpenAI')
    def test_generate_clips_with_llm_deepseek_reasoner(self, mock_openai_cls):
        mock_client = unittest.mock.MagicMock()
        mock_response = unittest.mock.MagicMock()
        # Simulate reasoning model output wrapped in markdown fences
        mock_choice = unittest.mock.MagicMock()
        mock_choice.message.content = '```json\n{"clips": [{"start_time": 5.0, "end_time": 12.0, "virality_score": 85, "reasoning": "great play"}]}\n```'
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        segments = [{"start": 5.0, "end": 12.0, "text": "great play"}]
        config = {"openai": {"api_key": "test-deepseek-key"}}

        result = editor._generate_clips_with_llm(
            segments=segments,
            config=config,
            chat_model="deepseek-reasoner",
            prompt_text="system instruction",
            logger=None
        )

        # Ensure base URL defaulted to deepseek and response_format was NOT passed
        mock_openai_cls.assert_called_once_with(api_key="test-deepseek-key", base_url="https://api.deepseek.com")
        called_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(called_kwargs["model"], "deepseek-reasoner")
        self.assertNotIn("response_format", called_kwargs)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["virality_score"], 85)

    @unittest.mock.patch('editor.OpenAI')
    def test_generate_clips_with_llm_openai_standard(self, mock_openai_cls):
        mock_client = unittest.mock.MagicMock()
        mock_response = unittest.mock.MagicMock()
        mock_choice = unittest.mock.MagicMock()
        mock_choice.message.content = '{"clips": [{"start_time": 2.0, "end_time": 8.0, "virality_score": 75, "reasoning": "clutch"}]}'
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        segments = [{"start": 2.0, "end": 8.0, "text": "clutch"}]
        config = {"openai": {"api_key": "test-openai-key"}}

        result = editor._generate_clips_with_llm(
            segments=segments,
            config=config,
            chat_model="gpt-4o",
            prompt_text="system instruction",
            logger=None
        )

        called_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(called_kwargs["model"], "gpt-4o")
        self.assertEqual(called_kwargs.get("response_format"), {"type": "json_object"})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["virality_score"], 75)

class TestEditorCodecAndEncoderFlags(unittest.TestCase):
    @unittest.mock.patch('torch.cuda.is_available', return_value=False)
    def test_get_gpu_codec_cpu_fallback(self, mock_cuda):
        codec = editor._get_gpu_codec()
        self.assertEqual(codec, "libx264")

    @unittest.mock.patch('torch.cuda.get_device_name', return_value="NVIDIA GeForce RTX 4090")
    @unittest.mock.patch('torch.cuda.is_available', return_value=True)
    def test_get_gpu_codec_nvidia(self, mock_cuda, mock_device):
        codec = editor._get_gpu_codec()
        self.assertEqual(codec, "h264_nvenc")

    @unittest.mock.patch('torch.cuda.get_device_name', return_value="AMD Radeon RX 7900 XTX")
    @unittest.mock.patch('torch.cuda.is_available', return_value=True)
    def test_get_gpu_codec_amd(self, mock_cuda, mock_device):
        codec = editor._get_gpu_codec()
        self.assertEqual(codec, "h264_amf")

    def test_get_video_encoder_flags_nvenc(self):
        flags = editor._get_video_encoder_flags("h264_nvenc", hardware_encoding=True)
        self.assertIn("-cq", flags)
        self.assertIn("-rc", flags)
        self.assertIn("vbr", flags)

    def test_get_video_encoder_flags_amf(self):
        flags = editor._get_video_encoder_flags("h264_amf", hardware_encoding=True)
        self.assertNotIn("-cq", flags)
        self.assertIn("-rc", flags)
        self.assertIn("cqp", flags)
        self.assertIn("-qp_p", flags)

    def test_get_video_encoder_flags_software(self):
        flags = editor._get_video_encoder_flags("libx264", hardware_encoding=False)
        self.assertIn("-crf", flags)
        self.assertIn("23", flags)

    @unittest.mock.patch('editor.HAS_FASTER_WHISPER', True)
    def test_is_cuda_available_ctranslate2_fallback(self):
        mock_ct2 = unittest.mock.MagicMock()
        mock_ct2.get_cuda_device_count.return_value = 1
        with unittest.mock.patch.dict('sys.modules', {'ctranslate2': mock_ct2}):
            with unittest.mock.patch('torch.cuda.is_available', lambda: False):
                self.assertTrue(editor.is_cuda_available())

    @unittest.mock.patch('shutil.which', return_value="C:\\Windows\\system32\\nvidia-smi.exe")
    @unittest.mock.patch('subprocess.check_output', return_value="NVIDIA GeForce RTX 5070 Ti Laptop GPU\n")
    def test_get_gpu_name_from_nvidia_smi(self, mock_subp, mock_which):
        with unittest.mock.patch('torch.cuda.is_available', lambda: False):
            name = editor.get_gpu_name()
            self.assertEqual(name, "NVIDIA GeForce RTX 5070 Ti Laptop GPU")

    @unittest.mock.patch('utils.run_subprocess_binary')
    def test_get_video_dimensions_and_aspect_vertical(self, mock_run):
        mock_run.return_value = (0, b"", b"Stream #0:0: Video: h264, yuv420p, 360x640 [SAR 1:1 DAR 9:16], 356 kb/s, 30 fps")
        w, h, desc = editor.get_video_dimensions_and_aspect("test_vert.mp4")
        self.assertEqual(w, 360)
        self.assertEqual(h, 640)
        self.assertIn("9:16", desc)
        self.assertIn("Vertical", desc)

    @unittest.mock.patch('utils.run_subprocess_binary')
    def test_get_video_dimensions_and_aspect_horizontal(self, mock_run):
        mock_run.return_value = (0, b"", b"Stream #0:0: Video: h264, yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 5000 kb/s, 60 fps")
        w, h, desc = editor.get_video_dimensions_and_aspect("test_horiz.mp4")
        self.assertEqual(w, 1920)
        self.assertEqual(h, 1080)
        self.assertIn("16:9", desc)
        self.assertIn("Horizontal", desc)


class TestEditorGenerateClipsFFmpeg(unittest.TestCase):
    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_horizontal_clip_includes_sync_flags(self, mock_run):
        editor._generate_horizontal_clip(
            file_path="input.mp4",
            output_file="output.mp4",
            start_time=10.0,
            end_time=20.0,
            video_codec="h264_nvenc",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=True,
            vr_stabilization=True,
            logger=None
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-avoid_negative_ts", called_cmd)
        self.assertIn("make_zero", called_cmd)
        self.assertIn("-vf", called_cmd)
        self.assertIn("deshake=rx=64:ry=64:edge=mirror", called_cmd)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_standard_crop(self, mock_run):
        editor._generate_vertical_clip(
            file_path="input.mp4",
            vert_output="vert.mp4",
            start_time=5.0,
            end_time=15.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vertical_mode="Standard Center Crop",
            config={},
            logger=None
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-avoid_negative_ts", called_cmd)
        self.assertIn("-vf", called_cmd)
        vf_index = called_cmd.index("-vf")
        vf_expr = called_cmd[vf_index + 1]
        self.assertIn("min(in_w,in_h*9/16)", vf_expr)
        self.assertIn("scale=1080:1920", vf_expr)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_resolution_independent_game_crop(self, mock_run):
        editor._generate_vertical_clip(
            file_path="input.mp4",
            vert_output="vert.mp4",
            start_time=0.0,
            end_time=10.0,
            video_codec="h264_amf",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=True,
            vertical_mode="Facecam Top-Right",
            config={},
            logger=None
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_index = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_index + 1]
        
        # Check dynamic square game crop and 1080 canvas scaling
        self.assertIn("[0:v]scale=1920:1080[v_1080]", fc_expr)
        self.assertIn("min(in_w,in_h)", fc_expr)
        self.assertIn("scale=1080:1080", fc_expr)
        self.assertIn("vstack=inputs=2[out]", fc_expr)
        # AMF flags
        self.assertNotIn("-cq", called_cmd)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_sanitizes_custom_coordinates(self, mock_run):
        malicious_config = {
            "settings": {
                "crop_x": "-100",
                "crop_y": "5000",
                "crop_w": "malicious;injection",
                "crop_h": "9999"
            }
        }
        editor._generate_vertical_clip(
            file_path="input.mp4",
            vert_output="vert.mp4",
            start_time=0.0,
            end_time=10.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vertical_mode="Custom Coordinates",
            config=malicious_config,
            logger=None
        )
        called_cmd = mock_run.call_args[0][0]
        fc_index = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_index + 1]
        
        # Injection string must not appear, values clamped safely
        self.assertNotIn("malicious", fc_expr)
        self.assertNotIn("injection", fc_expr)
        self.assertIn("[cam]", fc_expr)

    @unittest.mock.patch('editor._generate_thumbnail')
    @unittest.mock.patch('editor._generate_horizontal_clip')
    @unittest.mock.patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_process_single_clip_sanitizes_score_in_filepath(self, mock_open, mock_horiz, mock_thumb):
        clip = {
            "start_time": 10.0,
            "end_time": 20.0,
            "virality_score": "../../traversal_attack",
            "reasoning": "test"
        }
        files = editor._process_single_clip(
            i=0,
            clip=clip,
            file_path="vod.mp4",
            base_name="vod",
            output_dir="C:/output",
            video_codec="libx264",
            audio_codec_flags=[],
            hardware_encoding=False,
            vr_stabilization=False,
            vertical_export=False,
            vertical_mode="Standard Center Crop",
            config={},
            logger=None,
            is_cancelled=None
        )
        created_file = files[0]
        self.assertNotIn("../", created_file)
        self.assertNotIn("..\\", created_file)
        self.assertIn("scoretraversalattack.mp4", created_file.replace("_", ""))

class TestGetAudioStreamCount(unittest.TestCase):
    @unittest.mock.patch('utils.run_subprocess_binary')
    def test_ffprobe_multitrack(self, mock_run):
        mock_run.return_value = (0, b"0\n1\n", b"")
        count = editor.get_audio_stream_count("vod.mp4")
        self.assertEqual(count, 2)
        mock_run.assert_called_once()
        self.assertIn("ffprobe", mock_run.call_args[0][0])

    @unittest.mock.patch('utils.run_subprocess_binary')
    def test_ffprobe_singletrack(self, mock_run):
        mock_run.return_value = (0, b"0\n", b"")
        count = editor.get_audio_stream_count("vod.mp4")
        self.assertEqual(count, 1)

    @unittest.mock.patch('utils.run_subprocess_binary')
    def test_ffmpeg_fallback_multitrack(self, mock_run):
        ffmpeg_stderr = (
            b"Input #0, mov,mp4:\n"
            b"  Stream #0:0: Video: h264\n"
            b"  Stream #0:1: Audio: aac (default)\n"
            b"  Stream #0:2: Audio: aac\n"
        )
        mock_run.side_effect = [
            (1, b"", b"ffprobe error"),
            (0, b"", ffmpeg_stderr)
        ]
        count = editor.get_audio_stream_count("vod.mp4")
        self.assertEqual(count, 2)
        self.assertEqual(mock_run.call_count, 2)

    @unittest.mock.patch('utils.run_subprocess_binary')
    def test_all_fail_defaults_to_one(self, mock_run):
        mock_run.side_effect = Exception("Subprocess failure")
        count = editor.get_audio_stream_count("vod.mp4")
        self.assertEqual(count, 1)


class TestBuildAmixFilter(unittest.TestCase):
    def test_single_track_empty(self):
        self.assertEqual(editor.build_amix_filter(1), "")
        self.assertEqual(editor.build_amix_filter(0), "")

    def test_two_tracks_amix(self):
        filt = editor.build_amix_filter(2)
        self.assertEqual(filt, "[0:a:0][0:a:1]amix=inputs=2:duration=longest:dropout_transition=2,volume=2")

    def test_three_tracks_custom_label(self):
        filt = editor.build_amix_filter(3, input_label="a")
        self.assertEqual(filt, "[a:0][a:1][a:2]amix=inputs=3:duration=longest:dropout_transition=2,volume=3")


class TestAudioDownmixing(unittest.TestCase):
    @unittest.mock.patch('utils.run_subprocess_binary')
    def test_extract_audio_hidden_multitrack_uses_amix(self, mock_run):
        mock_run.return_value = (0, np.zeros(10, dtype=np.int16).tobytes(), b"")
        editor.extract_audio_hidden("test_vod.mp4", sr=16000, stream_count=2)
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_idx = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_idx + 1]
        self.assertIn("amix=inputs=2", fc_expr)
        self.assertIn("[0:a:0][0:a:1]", fc_expr)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_horizontal_clip_multitrack_amix(self, mock_run):
        editor._generate_horizontal_clip(
            file_path="multi.mp4",
            output_file="out.mp4",
            start_time=0.0,
            end_time=10.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vr_stabilization=False,
            logger=None,
            stream_count=2,
            audio_downmix=True
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_idx = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_idx + 1]
        self.assertIn("amix=inputs=2", fc_expr)
        self.assertIn("[aout]", fc_expr)
        self.assertIn("-map", called_cmd)
        self.assertIn("[aout]", called_cmd)
        self.assertIn("192k", called_cmd)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_horizontal_clip_multitrack_vr_amix(self, mock_run):
        editor._generate_horizontal_clip(
            file_path="multi.mp4",
            output_file="out.mp4",
            start_time=0.0,
            end_time=10.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vr_stabilization=True,
            logger=None,
            stream_count=2,
            audio_downmix=True
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_idx = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_idx + 1]
        self.assertIn("deshake", fc_expr)
        self.assertIn("amix=inputs=2", fc_expr)
        self.assertIn("[vout]", called_cmd)
        self.assertIn("[aout]", called_cmd)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_standard_crop_multitrack(self, mock_run):
        editor._generate_vertical_clip(
            file_path="multi.mp4",
            vert_output="vert.mp4",
            start_time=0.0,
            end_time=10.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vertical_mode="Standard Center Crop",
            config={},
            logger=None,
            stream_count=2,
            audio_downmix=True
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_idx = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_idx + 1]
        self.assertIn("min(in_w,in_h*9/16)", fc_expr)
        self.assertIn("amix=inputs=2", fc_expr)
        self.assertIn("[vout]", called_cmd)
        self.assertIn("[aout]", called_cmd)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_facecam_multitrack(self, mock_run):
        editor._generate_vertical_clip(
            file_path="multi.mp4",
            vert_output="vert.mp4",
            start_time=0.0,
            end_time=10.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vertical_mode="Facecam Top-Left",
            config={},
            logger=None,
            stream_count=2,
            audio_downmix=True
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_idx = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_idx + 1]
        self.assertIn("vstack=inputs=2", fc_expr)
        self.assertIn("amix=inputs=2", fc_expr)
        self.assertIn("[out]", called_cmd)
        self.assertIn("[aout]", called_cmd)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_blurred_background_singletrack(self, mock_run):
        editor._generate_vertical_clip(
            file_path="input.mp4",
            vert_output="vert_blur.mp4",
            start_time=5.0,
            end_time=15.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vertical_mode="Blurred Background (Letterbox)",
            config={},
            logger=None,
            stream_count=1,
            audio_downmix=False
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_idx = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_idx + 1]
        self.assertIn("boxblur=20:5", fc_expr)
        self.assertIn("scale=1080:-2", fc_expr)
        self.assertIn("overlay=(W-w)/2:(H-h)/2", fc_expr)
        self.assertIn("-map", called_cmd)
        self.assertIn("[out]", called_cmd)
        self.assertIn("0:a:0?", called_cmd)

    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_blurred_background_multitrack(self, mock_run):
        editor._generate_vertical_clip(
            file_path="multi.mp4",
            vert_output="vert_blur.mp4",
            start_time=0.0,
            end_time=10.0,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vertical_mode="Blurred Background (Letterbox)",
            config={},
            logger=None,
            stream_count=2,
            audio_downmix=True
        )
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-filter_complex", called_cmd)
        fc_idx = called_cmd.index("-filter_complex")
        fc_expr = called_cmd[fc_idx + 1]
        self.assertIn("boxblur=20:5", fc_expr)
        self.assertIn("amix=inputs=2", fc_expr)
        self.assertIn("[out]", called_cmd)
        self.assertIn("[aout]", called_cmd)
        self.assertIn("192k", called_cmd)

class TestContinuousAudioEnergyEnvelope(unittest.TestCase):
    def test_non_verbal_combat_synthesis_during_silent_gap(self):
        sr = 16000
        # 30-second audio track
        audio = np.random.randn(sr * 30).astype(np.float32) * 0.01
        # Insert sharp combat transients between 10s and 20s
        for t in range(sr * 10, sr * 20, 2000):
            audio[t:t+40] = 0.6

        speech_segments = [
            {"start": 0.0, "end": 4.0, "text": "Beginning discussion"},
            {"start": 26.0, "end": 29.0, "text": "Ending celebration"}
        ]

        result = editor.analyze_audio_peaks(audio, speech_segments, sample_rate=sr)

        # Result must contain more than the original 2 speech segments
        self.assertGreater(len(result), 2)

        # Check chronological ordering
        starts = [s["start"] for s in result]
        self.assertEqual(starts, sorted(starts))

        # Check that synthesized action segments exist in the gap
        action_segs = [s for s in result if "[ACTION: COMBAT]" in s["text"]]
        self.assertTrue(len(action_segs) > 0)
        for act in action_segs:
            self.assertGreaterEqual(act["start"], 4.0)
            self.assertLessEqual(act["end"], 26.0)

    def test_silent_gap_without_action_no_synthesis(self):
        sr = 16000
        # 30-second low noise audio track without loud spikes
        audio = np.random.randn(sr * 30).astype(np.float32) * 0.005

        speech_segments = [
            {"start": 0.0, "end": 4.0, "text": "Beginning"},
            {"start": 25.0, "end": 28.0, "text": "Ending"}
        ]

        result = editor.analyze_audio_peaks(audio, speech_segments, sample_rate=sr)
        # Low noise gap should not synthesize false positive action segments
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"].split("]")[-1].strip(), "Beginning")
        self.assertEqual(result[1]["text"].split("]")[-1].strip(), "Ending")

    def test_percentile_loudness_scaling(self):
        sr = 16000
        # Create audio with distinct quiet vs loud sections
        audio = np.zeros(sr * 20, dtype=np.float32)
        audio[:sr * 10] = 0.01  # Quiet floor
        audio[sr * 10:] = 0.30  # Loud peak

        segments = [
            {"start": 1.0, "end": 3.0, "text": "Quiet moment"},
            {"start": 12.0, "end": 15.0, "text": "Loud moment"}
        ]

        result = editor.analyze_audio_peaks(audio, segments, sample_rate=sr)
        self.assertEqual(len(result), 2)

        # Verify quiet moment has low loudness and loud moment has high loudness
        self.assertIn("[LOUDNESS:", result[0]["text"])
        self.assertIn("[LOUDNESS:", result[1]["text"])

        import re
        loudness_0 = int(re.search(r'\[LOUDNESS:\s*(\d+)%\]', result[0]["text"]).group(1))
        loudness_1 = int(re.search(r'\[LOUDNESS:\s*(\d+)%\]', result[1]["text"]).group(1))
        self.assertLess(loudness_0, 20)
        self.assertGreater(loudness_1, 80)

    def test_empty_segments_with_combat_creates_action_segments(self):
        sr = 16000
        # 20-second video with zero speech (Whisper returns []) but intense gunfire
        audio = np.random.randn(sr * 20).astype(np.float32) * 0.01
        for t in range(0, sr * 20, 2000):
            audio[t:t+40] = 0.6

        result = editor.analyze_audio_peaks(audio, [], sample_rate=sr)
        self.assertTrue(len(result) > 0)
        self.assertIn("[ACTION: COMBAT]", result[0]["text"])

class TestVerticalRenderOptimization(unittest.TestCase):
    @unittest.mock.patch('utils.run_subprocess_command', return_value=0)
    def test_generate_vertical_clip_from_pretrimmed_source(self, mock_run):
        """Verifies that rendering from a cut clip skips seeking (-ss / -to)."""
        editor._generate_vertical_clip(
            file_path="output_cut.mp4",
            vert_output="output_cut_vertical.mp4",
            start_time=None,
            end_time=None,
            video_codec="libx264",
            audio_codec_flags=["-c:a", "copy"],
            hardware_encoding=False,
            vertical_mode="Standard Center Crop",
            config={},
            logger=None,
            stream_count=1,
            audio_downmix=False
        )
        called_cmd = mock_run.call_args[0][0]
        # Should NOT contain seeking parameters
        self.assertNotIn("-ss", called_cmd)
        self.assertNotIn("-to", called_cmd)
        self.assertNotIn("-avoid_negative_ts", called_cmd)
        # Should contain input file and audio stream copy
        self.assertIn("output_cut.mp4", called_cmd)
        self.assertIn("-c:a", called_cmd)
        self.assertIn("copy", called_cmd)

    @unittest.mock.patch('editor._generate_thumbnail')
    @unittest.mock.patch('editor._generate_vertical_clip')
    @unittest.mock.patch('editor._generate_horizontal_clip')
    @unittest.mock.patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_process_single_clip_crops_from_cut_horizontal_clip(self, mock_open, mock_horiz, mock_vert, mock_thumb):
        """Verifies that _process_single_clip passes the cut horizontal clip to vertical rendering."""
        clip = {
            "start_time": 45.0,
            "end_time": 75.0,
            "virality_score": 9.2,
            "reasoning": "Insane clutch round"
        }
        files = editor._process_single_clip(
            i=0,
            clip=clip,
            file_path="C:/vods/raw_stream_30gb.mp4",
            base_name="raw_stream_30gb",
            output_dir="C:/output",
            video_codec="libx264",
            audio_codec_flags=["-c:a", "aac"],
            hardware_encoding=False,
            vr_stabilization=False,
            vertical_export=True,
            vertical_mode="Blurred Background (Letterbox)",
            config={},
            logger=None,
            is_cancelled=None,
            stream_count=2,
            audio_downmix=True
        )

        mock_horiz.assert_called_once()
        mock_vert.assert_called_once()

        vert_args = mock_vert.call_args[0]
        source_for_vert = vert_args[0]
        vert_output = vert_args[1]
        v_start = vert_args[2]
        v_end = vert_args[3]
        v_audio_flags = vert_args[5]

        # Verify source is the horizontal cut clip, NOT the 30GB raw stream
        self.assertTrue(source_for_vert.endswith(".mp4"))
        self.assertFalse(source_for_vert.endswith("_vertical.mp4"))
        self.assertNotIn("raw_stream_30gb.mp4", source_for_vert)
        self.assertIn("raw_stream_30gb_clip1_score92.mp4", source_for_vert)

        # Verify seeking is omitted
        self.assertIsNone(v_start)
        self.assertIsNone(v_end)

        # Verify audio stream copy is used
        self.assertEqual(v_audio_flags, ["-c:a", "copy"])

if __name__ == '__main__':
    unittest.main()
