import unittest
from unittest.mock import patch, MagicMock
import app
import subprocess
import os

class TestAppLogic(unittest.TestCase):

    def setUp(self):
        # Instantiate without running __init__ to avoid GUI setup issues
        self.app_instance = app.ClipGenApp.__new__(app.ClipGenApp)
        # Mock the logging so tests don't fail when logging to UI
        self.app_instance.log_to_console = MagicMock()

    @patch('subprocess.run')
    def test_get_video_id_success(self, mock_subprocess_run):
        """Test successful retrieval of video ID."""
        # Setup the mock to return a valid result
        mock_result = MagicMock()
        mock_result.stdout = "dummy_video_id\n"
        mock_subprocess_run.return_value = mock_result

        # Call the method
        url = "https://www.youtube.com/watch?v=dummy_video_id"
        result = self.app_instance.get_video_id(url)

        # Assertions
        self.assertEqual(result, "dummy_video_id")

        # Ensure subprocess.run was called correctly
        # The exact command varies by OS, but we check if our URL is in it
        called_args = mock_subprocess_run.call_args[0][0]
        self.assertIn(url, called_args)
        self.assertIn("--get-id", called_args)

    @patch('subprocess.run')
    def test_get_video_id_subprocess_error(self, mock_subprocess_run):
        """Test failure due to subprocess throwing an Exception."""
        # Setup the mock to raise an exception
        mock_subprocess_run.side_effect = subprocess.SubprocessError("Mocked subprocess failure")

        # Call the method
        url = "https://www.youtube.com/watch?v=dummy_video_id"
        result = self.app_instance.get_video_id(url)

        # Assertions
        self.assertIsNone(result)

        # Ensure log_to_console was called to report the error
        self.app_instance.log_to_console.assert_called_once()
        log_message = self.app_instance.log_to_console.call_args[0][0]
        self.assertIn("yt-dlp error", log_message)
        self.assertIn("Mocked subprocess failure", log_message)

if __name__ == '__main__':
    unittest.main()
