import unittest
from unittest.mock import patch, MagicMock
import os
import watcher

class TestWatcherDownloadWithSubprocess(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()
        self.url = "https://example.com/video"
        self.video_id = "12345"

    @patch('config_manager.load_config')
    def test_missing_download_dir(self, mock_load_config):
        # Setup mock config with missing download_dir
        mock_load_config.return_value = {"settings": {}}

        result = watcher.download_with_subprocess(self.url, self.video_id, logger_callback=self.mock_logger)

        self.assertIsNone(result)
        self.mock_logger.assert_called_with("❌ Error: Download directory not set in Settings.")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('subprocess.Popen')
    @patch('config_manager.load_config')
    def test_quality_pref_1080p(self, mock_load_config, mock_popen, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads", "download_quality": "1080p"},
            "auto_scheduler": {"video_type": "All"}
        }
        mock_exists.return_value = True

        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        watcher.download_with_subprocess(self.url, self.video_id)

        called_cmd = mock_popen.call_args[0][0]
        self.assertIn("-f", called_cmd)
        f_index = called_cmd.index("-f")
        self.assertEqual(called_cmd[f_index + 1], "bestvideo[height<=1080]+bestaudio/best[height<=1080]")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('subprocess.Popen')
    @patch('config_manager.load_config')
    def test_auth_browser_injection(self, mock_load_config, mock_popen, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads", "auth_browser": "firefox"},
            "auto_scheduler": {"video_type": "All"}
        }
        mock_exists.return_value = True

        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        watcher.download_with_subprocess(self.url, self.video_id)

        called_cmd = mock_popen.call_args[0][0]
        self.assertIn("--cookies-from-browser", called_cmd)
        browser_index = called_cmd.index("--cookies-from-browser")
        self.assertEqual(called_cmd[browser_index + 1], "firefox")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('subprocess.Popen')
    @patch('config_manager.load_config')
    def test_livestreams_only_filter(self, mock_load_config, mock_popen, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"},
            "auto_scheduler": {"video_type": "Livestreams Only"}
        }
        mock_exists.return_value = True

        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        watcher.download_with_subprocess(self.url, self.video_id, force_manual=False)

        called_cmd = mock_popen.call_args[0][0]
        self.assertIn("--match-filter", called_cmd)
        filter_index = called_cmd.index("--match-filter")
        self.assertEqual(called_cmd[filter_index + 1], "live_status=?was_live")

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('subprocess.Popen')
    @patch('config_manager.load_config')
    def test_successful_download_parsing(self, mock_load_config, mock_popen, mock_makedirs, mock_exists, mock_listdir):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"}
        }
        mock_exists.return_value = True

        mock_process = MagicMock()
        mock_process.stdout = ['[download] some info', 'Merging formats into "mock_path.mp4"']
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # We need to ensure os.path.exists returns True for the downloaded file path check
        def side_effect(path):
            if path == "/tmp/downloads": return True
            if path == "mock_path.mp4": return True
            return False
        mock_exists.side_effect = side_effect

        result = watcher.download_with_subprocess(self.url, self.video_id)
        self.assertEqual(result, "mock_path.mp4")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('subprocess.Popen')
    @patch('config_manager.load_config')
    def test_failed_download_error_log(self, mock_load_config, mock_popen, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"}
        }
        mock_exists.return_value = True

        mock_process = MagicMock()
        mock_process.stdout = ['ERROR: Video unavailable', 'Something went wrong']
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = watcher.download_with_subprocess(self.url, self.video_id, logger_callback=self.mock_logger)

        self.assertIsNone(result)
        # Should contain the last lines
        self.mock_logger.assert_called_with("❌ Download failed! yt-dlp says:\nERROR: Video unavailable\nSomething went wrong")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('subprocess.Popen')
    @patch('config_manager.load_config')
    def test_exception_handling(self, mock_load_config, mock_popen, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"}
        }
        mock_exists.return_value = True

        mock_popen.side_effect = Exception("Mocked exception")

        result = watcher.download_with_subprocess(self.url, self.video_id, logger_callback=self.mock_logger)

        self.assertIsNone(result)
        self.mock_logger.assert_called_with("❌ Exception during download: Mocked exception")

if __name__ == '__main__':
    unittest.main()
