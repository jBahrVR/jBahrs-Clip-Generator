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
            mock_subprocess_popen.assert_called_once_with(expected_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=None)

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

if __name__ == '__main__':
    unittest.main()
