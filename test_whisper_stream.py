import unittest
import sys
from unittest.mock import MagicMock

# Mocking external dependencies
sys.modules['torch'] = MagicMock()
sys.modules['whisper'] = MagicMock()
sys.modules['config_manager'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()
sys.modules['anthropic'] = MagicMock()

from editor import WhisperProgressStream

class TestWhisperProgressStream(unittest.TestCase):
    def test_whisper_progress_stream_logging(self):
        logs = []
        def logger(msg):
            logs.append(msg)

        stream = WhisperProgressStream(logger)

        # Test 1: Log with timestamp (should be logged because counter=0)
        stream.write("[00:00.000 --> 00:05.000] Hello World")
        self.assertEqual(len(logs), 1)
        self.assertIn("⏳ Processed up to 00:00.000", logs[0])

        # Test 2: Throttling (should NOT log next 9 segments)
        for i in range(1, 10):
            stream.write(f"[00:0{i}.000 --> 00:0{i+1}.000] Segment {i}")
            self.assertEqual(len(logs), 1, f"Logged at counter {i}")

        # Test 3: Log after 10th segment (should log because counter=10)
        stream.write("[00:10.000 --> 00:11.000] Tenth Segment")
        self.assertEqual(len(logs), 2)
        self.assertIn("⏳ Processed up to 00:10.000", logs[1])

    def test_whisper_progress_stream_no_timestamp(self):
        logs = []
        def logger(msg):
            logs.append(msg)

        stream = WhisperProgressStream(logger)
        stream.write("No timestamp here")
        self.assertEqual(len(logs), 0)

    def test_whisper_progress_stream_flush(self):
        # Even after removal, flush should still be callable because it's in io.StringIO
        stream = WhisperProgressStream(None)
        try:
            stream.flush()
        except AttributeError:
            self.fail("flush() method not found on WhisperProgressStream")

if __name__ == '__main__':
    unittest.main()
