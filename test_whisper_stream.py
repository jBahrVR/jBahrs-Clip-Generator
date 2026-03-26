import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock dependencies to avoid ImportError
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
    def test_whisper_progress_stream_parsing(self):
        logs = []
        def logger(msg):
            logs.append(msg)

        stream = WhisperProgressStream(logger)

        # Test 1st segment (counter = 0, should log)
        stream.write("[00:00.000 --> 00:05.000] Hello world\n")
        self.assertEqual(len(logs), 1)
        self.assertIn("00:00.000", logs[0])
        self.assertIn("Hello world", logs[0])

        # Test 2nd to 10th segments (should NOT log due to throttling)
        for i in range(1, 10):
            stream.write(f"[00:0{i}.000 --> 00:0{i+1}.000] Segment {i}\n")

        self.assertEqual(len(logs), 1) # Still 1

        # Test 11th segment (counter = 10, should log)
        stream.write("[00:10.000 --> 00:11.000] Tenth segment\n")
        self.assertEqual(len(logs), 2)
        self.assertIn("00:10.000", logs[1])
        self.assertIn("Tenth segment", logs[1])

    def test_whisper_progress_stream_no_bracket(self):
        logs = []
        def logger(msg):
            logs.append(msg)

        stream = WhisperProgressStream(logger)
        stream.write("00:00.000 --> 00:05.000 Hello world\n")
        self.assertEqual(len(logs), 1)
        self.assertIn("00:00.000", logs[0])
        self.assertIn("00:00.000 --> 00:05.000 Hello world", logs[0])

if __name__ == '__main__':
    unittest.main()
