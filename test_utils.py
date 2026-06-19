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

