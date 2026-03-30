import unittest
from unittest.mock import patch, MagicMock
import app
import urllib.parse
import threading

class TestDiscordURLValidation(unittest.TestCase):
    def setUp(self):
        self.app_instance = app.ClipGenApp.__new__(app.ClipGenApp)
        self.app_instance.log_to_console = MagicMock()
        self.app_instance.config = {"integrations": {"discord_webhook": ""}}
        self.app_instance.after = MagicMock()
        self.app_instance.test_discord_btn = MagicMock()

    @patch('urllib.request.urlopen')
    def test_send_discord_alert_invalid_url(self, mock_urlopen):
        invalid_urls = [
            "https://discord.com@attacker.com/",
            "http://discord.com/api/webhooks/123",
            "https://discord.com.attacker.com/api/webhooks/123",
            "https://discord.com/api/webhooks/../"
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                mock_urlopen.reset_mock()
                self.app_instance.config["integrations"]["discord_webhook"] = url

                with patch('threading.Thread') as mock_thread:
                    def start_mock():
                        kwargs = mock_thread.call_args.kwargs
                        if 'target' in kwargs:
                            kwargs['target']()
                    mock_thread.return_value.start.side_effect = start_mock

                    self.app_instance.send_discord_alert("Test Title")

                # Assert urlopen was NOT called because of invalid url
                mock_urlopen.assert_not_called()

if __name__ == '__main__':
    unittest.main()
