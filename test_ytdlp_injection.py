import unittest
import unittest.mock
import app
import watcher
import subprocess

class TestYTDLPInjection(unittest.TestCase):

    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch('config_manager.load_config')
    @unittest.mock.patch('customtkinter.CTk')
    def test_app_get_video_id_injection(self, mock_ctk, mock_load_config, mock_subprocess_run):
        # Mock the config load to avoid relying on actual files
        mock_load_config.return_value = {}

        # Mock result for subprocess.run
        mock_result = unittest.mock.MagicMock()
        mock_result.stdout = "mocked_id\n"
        mock_subprocess_run.return_value = mock_result

        # We need to bypass some GUI initialization to test `get_video_id` which is part of ClipGenApp
        # By patching CTk we can initialize ClipGenApp without actual GUI errors
        # Actually it's simpler to just mock the methods that might fail, but let's see.

        try:
            # We will test without fully initing the app if possible, or we just patch the class
            test_app = app.ClipGenApp.__new__(app.ClipGenApp)

            # Since get_video_id uses self.log_to_console, we need to mock it
            test_app.log_to_console = unittest.mock.MagicMock()

            # Call the target method with a potentially malicious URL that starts with a hyphen
            malicious_url = "-v"
            result = test_app.get_video_id(malicious_url)

            # Get the arguments passed to subprocess.run
            called_cmd = mock_subprocess_run.call_args[0][0]

            # Assert that "--" is present immediately before the malicious URL
            self.assertIn("--", called_cmd, "The '--' argument separator is missing.")

            malicious_idx = called_cmd.index(malicious_url)
            separator_idx = called_cmd.index("--")

            self.assertEqual(separator_idx, malicious_idx - 1, "'--' must immediately precede the URL to prevent argument injection.")
        except Exception as e:
            self.fail(f"Test failed due to an exception: {e}")

    @unittest.mock.patch('subprocess.Popen')
    @unittest.mock.patch('config_manager.load_config')
    def test_watcher_download_with_subprocess_injection(self, mock_load_config, mock_subprocess_popen):
        # Mock the config to have a valid download_dir so it doesn't return early
        mock_load_config.return_value = {
            "settings": {
                "download_dir": "test_dir",
                "auth_browser": "None"
            }
        }

        # Call the target method
        malicious_url = "-v"
        watcher.download_with_subprocess(malicious_url, "dummy_id")

        # Get the arguments passed to subprocess.Popen
        called_cmd = mock_subprocess_popen.call_args[0][0]

        # Assert that "--" is present immediately before the malicious URL
        self.assertIn("--", called_cmd, "The '--' argument separator is missing.")

        malicious_idx = called_cmd.index(malicious_url)
        separator_idx = called_cmd.index("--")

        self.assertEqual(separator_idx, malicious_idx - 1, "'--' must immediately precede the URL to prevent argument injection.")

    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch('config_manager.load_config')
    def test_watcher_main_injection(self, mock_load_config, mock_subprocess_run):
        # Mock config
        mock_load_config.return_value = {
            "auto_scheduler": {
                "platform": "YouTube"
            },
            "youtube": {
                "channel_id": "dummy_channel"
            }
        }

        # Mock subprocess to avoid real executions
        mock_result = unittest.mock.MagicMock()
        mock_result.stdout = "dummy_id\n"
        mock_subprocess_run.return_value = mock_result

        # We need to ensure that the mocked id is not found in the test dir to prevent it from going into download_with_subprocess,
        # or we just mock os.path.exists
        with unittest.mock.patch('os.path.exists', return_value=True), \
             unittest.mock.patch('os.listdir', return_value=["dummy_id.mp4"]):

            # Call main
            watcher.main()

            # The first subprocess.run is for getting the latest id
            called_cmd = mock_subprocess_run.call_args[0][0]

            target_url = "https://www.youtube.com/channel/dummy_channel/streams"

            # Assert that "--" is present immediately before the target URL
            self.assertIn("--", called_cmd, "The '--' argument separator is missing in watcher.main.")

            target_idx = called_cmd.index(target_url)
            separator_idx = called_cmd.index("--")

            self.assertEqual(separator_idx, target_idx - 1, "'--' must immediately precede the target URL in watcher.main.")

if __name__ == '__main__':
    unittest.main()
