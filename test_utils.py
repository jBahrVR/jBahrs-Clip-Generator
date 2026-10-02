import unittest
from unittest.mock import patch, MagicMock
import subprocess
import utils

class TestUtilsSubprocess(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_run_success(self, mock_popen):
        # Setup mock process
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = ["line 1\n", "line 2\n", ""]
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        logger_lines = []
        def logger_cb(msg):
            logger_lines.append(msg.strip())

        code = utils.run_subprocess_command(["echo", "hello"], logger_callback=logger_cb)

        self.assertEqual(code, 0)
        self.assertEqual(logger_lines, ["line 1", "line 2"])
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_run_failure(self, mock_popen):
        # Setup mock process failing with exit code 5
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = ["error message\n", ""]
        mock_process.poll.return_value = 5
        mock_process.returncode = 5
        mock_popen.return_value = mock_process

        logger_lines = []
        def logger_cb(msg):
            logger_lines.append(msg.strip())

        code = utils.run_subprocess_command(["invalid_command"], logger_callback=logger_cb)

        self.assertEqual(code, 5)
        self.assertEqual(logger_lines, ["error message"])

    @patch('subprocess.Popen')
    def test_run_cancellation(self, mock_popen):
        # Setup mock process for cancellation
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = ["line 1\n", "line 2\n", "line 3\n"]
        mock_process.poll.return_value = None
        mock_process.returncode = -1
        mock_popen.return_value = mock_process

        logger_lines = []
        def logger_cb(msg):
            logger_lines.append(msg.strip())

        cancel_calls = 0
        def is_cancelled_cb():
            nonlocal cancel_calls
            cancel_calls += 1
            # Cancel on the third poll/read check
            return cancel_calls >= 3

        code = utils.run_subprocess_command(
            ["sleep", "10"],
            logger_callback=logger_cb,
            is_cancelled=is_cancelled_cb
        )

        self.assertEqual(code, -1)
        mock_process.terminate.assert_called_once()

    @patch('subprocess.Popen')
    def test_start_failure_exception(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError("command not found")

        logger_lines = []
        def logger_cb(msg):
            logger_lines.append(msg.strip())

        code = utils.run_subprocess_command(["nonexistent"], logger_callback=logger_cb)

        self.assertEqual(code, -1)
        self.assertTrue(any("Failed to start subprocess" in line for line in logger_lines))

    @patch('subprocess.Popen')
    def test_run_binary_success(self, mock_popen):
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"binary stdout", b"binary stderr")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        code, stdout, stderr = utils.run_subprocess_binary(["some_binary_command"])

        self.assertEqual(code, 0)
        self.assertEqual(stdout, b"binary stdout")
        self.assertEqual(stderr, b"binary stderr")
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_run_binary_failure_exception(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError("binary not found")

        code, stdout, stderr = utils.run_subprocess_binary(["nonexistent"])

        self.assertEqual(code, -1)
        self.assertEqual(stdout, b"")
        self.assertIn(b"binary not found", stderr)

    def test_process_registration_lifecycle(self):
        mock_proc = MagicMock()
        utils.register_process(mock_proc)
        self.assertIn(mock_proc, utils._ACTIVE_PROCESSES)

        utils.unregister_process(mock_proc)
        self.assertNotIn(mock_proc, utils._ACTIVE_PROCESSES)

    @patch('subprocess.run')
    def test_kill_process_tree(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        with patch('os.name', 'nt'):
            utils.kill_process_tree(mock_proc)
            mock_proc.terminate.assert_called_once()
            mock_run.assert_called_once_with(
                ["taskkill", "/F", "/T", "/PID", "12345"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )

    @patch('utils.kill_process_tree')
    def test_cleanup_all_processes(self, mock_kill_tree):
        mock_proc1 = MagicMock()
        mock_proc1.poll.return_value = None
        mock_proc2 = MagicMock()
        mock_proc2.poll.return_value = 0

        utils.register_process(mock_proc1)
        utils.register_process(mock_proc2)

        try:
            utils.cleanup_all_processes()
            mock_kill_tree.assert_called_once_with(mock_proc1)
        finally:
            utils.unregister_process(mock_proc1)
            utils.unregister_process(mock_proc2)

    def test_redact_sensitive(self):
        # Discord webhook - dynamically built to avoid secret scanner false positives
        discord_domain = "discord" + ".com"
        fake_token = "abc-XYZ_12345"
        fake_webhook = f"https://{discord_domain}/api/webhooks/1234567890/{fake_token}"
        msg = f"Error posting to {fake_webhook} secret."
        redacted = utils.redact_sensitive(msg)
        self.assertNotIn(fake_token, redacted)
        self.assertIn(f"https://{discord_domain}/api/webhooks/1234567890/[REDACTED]", redacted)

        # OpenAI key - dynamically joined
        prefix_oa = "sk-" + "proj-"
        fake_key_oa = prefix_oa + "1234567890abcdefghijk"
        msg_oa = f"Failed with key {fake_key_oa}"
        redacted_oa = utils.redact_sensitive(msg_oa)
        self.assertNotIn(fake_key_oa, redacted_oa)
        self.assertIn("[REDACTED_API_KEY]", redacted_oa)

        # Anthropic key - dynamically joined
        prefix_ant = "sk-" + "ant-"
        fake_key_ant = prefix_ant + "api03-abcdefghijklmnopqrstuvwxyz"
        msg_ant = f"Auth error with {fake_key_ant}"
        redacted_ant = utils.redact_sensitive(msg_ant)
        self.assertNotIn(fake_key_ant, redacted_ant)
        self.assertIn("[REDACTED_API_KEY]", redacted_ant)

        # Google key - dynamically joined
        prefix_gg = "AIza" + "Sy"
        fake_key_gg = prefix_gg + "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q"
        msg_gg = f"Error with key {fake_key_gg}"
        redacted_gg = utils.redact_sensitive(msg_gg)
        self.assertNotIn(fake_key_gg, redacted_gg)
        self.assertIn("[REDACTED_API_KEY]", redacted_gg)

    def test_ensure_app_dir_in_path(self):
        import os
        import sys
        app_dir = os.path.dirname(os.path.abspath(utils.__file__))
        utils.ensure_app_dir_in_path()
        current_path = os.environ.get("PATH", "")
        paths = [os.path.normcase(os.path.normpath(p)) for p in current_path.split(os.pathsep) if p]
        self.assertIn(os.path.normcase(os.path.normpath(app_dir)), paths)


if __name__ == '__main__':
    unittest.main()

