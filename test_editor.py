import unittest
import unittest.mock
import os
import subprocess
import numpy as np
import editor

class TestEditorExtractAudioHidden(unittest.TestCase):
    @unittest.mock.patch('subprocess.Popen')
    def test_extract_audio_hidden_success_linux(self, mock_subprocess_popen):
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

class TestEditorTranscribeAudioToSegments(unittest.TestCase):
    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('whisper.load_model')
    @unittest.mock.patch('torch.cuda.is_available', return_value=False)
    def test_transcribe_audio_to_segments_passes_language(self, mock_cuda, mock_load_model, mock_extract_audio):
        mock_model = unittest.mock.MagicMock()
        mock_model.transcribe.return_value = {"segments": [{"start": 0.0, "end": 2.5, "text": "Hola"}]}
        mock_load_model.return_value = mock_model
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

        mock_load_model.assert_called_once_with("base", device="cpu")
        mock_model.transcribe.assert_called_once()
        called_args, called_kwargs = mock_model.transcribe.call_args
        self.assertEqual(called_kwargs.get("language"), "es")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hola")

    @unittest.mock.patch('editor.extract_audio_hidden')
    @unittest.mock.patch('whisper.load_model')
    @unittest.mock.patch('torch.cuda.is_available', return_value=False)
    def test_transcribe_audio_to_segments_autodetect_language(self, mock_cuda, mock_load_model, mock_extract_audio):
        mock_model = unittest.mock.MagicMock()
        mock_model.transcribe.return_value = {"segments": [{"start": 0.0, "end": 2.5, "text": "Hello"}]}
        mock_load_model.return_value = mock_model
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

        mock_load_model.assert_called_once_with("base", device="cpu")
        mock_model.transcribe.assert_called_once()
        called_args, called_kwargs = mock_model.transcribe.call_args
        self.assertNotIn("language", called_kwargs)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hello")

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

if __name__ == '__main__':
    unittest.main()
