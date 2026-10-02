import unittest
from unittest.mock import patch, MagicMock
import os
import watcher
import utils

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
    @patch('utils.run_subprocess_command')
    @patch('config_manager.load_config')
    def test_quality_pref_1080p(self, mock_load_config, mock_run, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads", "download_quality": "1080p"},
            "auto_scheduler": {"video_type": "All"}
        }
        mock_exists.return_value = True
        mock_run.return_value = 0

        watcher.download_with_subprocess(self.url, self.video_id)

        called_cmd = mock_run.call_args[0][0]
        self.assertIn("-f", called_cmd)
        f_index = called_cmd.index("-f")
        self.assertEqual(called_cmd[f_index + 1], "bestvideo+bestaudio/best")
        self.assertIn("-S", called_cmd)
        s_index = called_cmd.index("-S")
        self.assertEqual(called_cmd[s_index + 1], "res:1080")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('utils.run_subprocess_command')
    @patch('config_manager.load_config')
    def test_auth_browser_injection(self, mock_load_config, mock_run, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads", "auth_browser": "firefox"},
            "auto_scheduler": {"video_type": "All"}
        }
        mock_exists.return_value = True
        mock_run.return_value = 0

        watcher.download_with_subprocess(self.url, self.video_id)

        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--cookies-from-browser", called_cmd)
        browser_index = called_cmd.index("--cookies-from-browser")
        self.assertEqual(called_cmd[browser_index + 1], "firefox")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('utils.run_subprocess_command')
    @patch('config_manager.load_config')
    def test_livestreams_only_filter(self, mock_load_config, mock_run, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"},
            "auto_scheduler": {"video_type": "Livestreams Only"}
        }
        mock_exists.return_value = True
        mock_run.return_value = 0

        watcher.download_with_subprocess(self.url, self.video_id, force_manual=False)

        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--match-filter", called_cmd)
        filter_index = called_cmd.index("--match-filter")
        self.assertEqual(called_cmd[filter_index + 1], "live_status=?was_live")

    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('utils.run_subprocess_command')
    @patch('config_manager.load_config')
    def test_successful_download_parsing(self, mock_load_config, mock_run, mock_makedirs, mock_exists, mock_listdir):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"}
        }
        mock_exists.return_value = True

        def side_effect(cmd, logger_callback=None, is_cancelled=None, cwd=None):
            if logger_callback:
                logger_callback("[download] some info")
                logger_callback('Merging formats into "mock_path.mp4"')
            return 0
        mock_run.side_effect = side_effect

        # We need to ensure os.path.exists returns True for the downloaded file path check
        def exists_side_effect(path):
            if path == "/tmp/downloads": return True
            if path == "mock_path.mp4": return True
            return False
        mock_exists.side_effect = exists_side_effect

        result = watcher.download_with_subprocess(self.url, self.video_id)
        self.assertEqual(result, "mock_path.mp4")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('utils.run_subprocess_command')
    @patch('config_manager.load_config')
    def test_failed_download_error_log(self, mock_load_config, mock_run, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"}
        }
        mock_exists.return_value = True

        def side_effect(cmd, logger_callback=None, is_cancelled=None, cwd=None):
            if logger_callback:
                logger_callback('ERROR: Video unavailable')
                logger_callback('Something went wrong')
            return 1
        mock_run.side_effect = side_effect

        result = watcher.download_with_subprocess(self.url, self.video_id, logger_callback=self.mock_logger)

        self.assertIsNone(result)
        # Should contain the last lines
        self.mock_logger.assert_called_with("❌ Download failed! yt-dlp says:\nERROR: Video unavailable\nSomething went wrong")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('utils.run_subprocess_command')
    @patch('config_manager.load_config')
    def test_exception_handling(self, mock_load_config, mock_run, mock_makedirs, mock_exists):
        mock_load_config.return_value = {
            "settings": {"download_dir": "/tmp/downloads"}
        }
        mock_exists.return_value = True

        mock_run.side_effect = Exception("Mocked exception")

        result = watcher.download_with_subprocess(self.url, self.video_id, logger_callback=self.mock_logger)

        self.assertIsNone(result)
        self.mock_logger.assert_called_with("❌ Exception during download: Mocked exception")

if __name__ == '__main__':
    unittest.main()
