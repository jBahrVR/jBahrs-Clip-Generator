import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import requests

from event_bus import EventBus, Event
from social_publisher import (
    SocialPlatform,
    PublishPrivacy,
    PublishPayload,
    YouTubeShortsClient,
    TikTokClient,
    InstagramReelsClient,
    SocialPublishManager,
    get_social_publish_manager
)


class TestPublishPayload(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self.temp_file.write(b"dummy video data")
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_validation_nonexistent_file_raises(self):
        payload = PublishPayload(file_path="nonexistent_video.mp4")
        with self.assertRaises(ValueError) as ctx:
            payload.validate()
        self.assertIn("Video file not found", str(ctx.exception))

    def test_validation_invalid_privacy_raises(self):
        payload = PublishPayload(file_path=self.temp_file.name, privacy="secret_hidden")
        with self.assertRaises(ValueError) as ctx:
            payload.validate()
        self.assertIn("Invalid privacy", str(ctx.exception))

    def test_validation_success(self):
        payload = PublishPayload(file_path=self.temp_file.name, privacy="public")
        payload.validate()  # Should not raise

    def test_format_youtube_title_appends_shorts(self):
        payload = PublishPayload(file_path=self.temp_file.name, title="Epic Gaming Clutch")
        formatted = payload.format_youtube_title()
        self.assertEqual(formatted, "Epic Gaming Clutch #Shorts")

    def test_format_youtube_title_does_not_duplicate_shorts(self):
        payload = PublishPayload(file_path=self.temp_file.name, title="Crazy VR Glitch #Shorts")
        formatted = payload.format_youtube_title()
        self.assertEqual(formatted, "Crazy VR Glitch #Shorts")

    def test_format_youtube_title_truncates_to_100_chars(self):
        long_title = "A" * 120
        payload = PublishPayload(file_path=self.temp_file.name, title=long_title)
        formatted = payload.format_youtube_title()
        self.assertLessEqual(len(formatted), 100)
        self.assertTrue(formatted.endswith("#Shorts"))

    def test_format_full_description(self):
        payload = PublishPayload(
            file_path=self.temp_file.name,
            description="Best moment of the stream!",
            tags=["Gaming", "TwitchClips"]
        )
        desc = payload.format_full_description()
        self.assertIn("Best moment of the stream!", desc)
        self.assertIn("#Gaming", desc)
        self.assertIn("#TwitchClips", desc)
        self.assertIn("#Shorts", desc)


class TestYouTubeShortsClient(unittest.TestCase):

    def setUp(self):
        self.client = YouTubeShortsClient()
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self.temp_file.write(b"x" * 1024)
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_verify_credentials_missing(self):
        success, msg = self.client.verify_credentials({})
        self.assertFalse(success)
        self.assertIn("Missing", msg)

    @patch("requests.post")
    def test_verify_credentials_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "ya29.test_token"}
        mock_post.return_value = mock_resp

        config = {
            "social": {
                "youtube": {
                    "client_id": "test_id",
                    "client_secret": "test_secret",
                    "refresh_token": "test_refresh"
                }
            }
        }
        success, msg = self.client.verify_credentials(config)
        self.assertTrue(success)
        self.assertIn("verified successfully", msg)

    @patch("requests.post")
    def test_verify_credentials_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error_description": "invalid_grant"}
        mock_post.return_value = mock_resp

        config = {
            "social": {
                "youtube": {
                    "client_id": "test_id",
                    "client_secret": "test_secret",
                    "refresh_token": "bad_token"
                }
            }
        }
        success, msg = self.client.verify_credentials(config)
        self.assertFalse(success)
        self.assertIn("invalid_grant", msg)

    @patch("requests.put")
    @patch("requests.post")
    def test_upload_success(self, mock_post, mock_put):
        # Step 1: Token response
        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "ya29.valid_token"}

        # Step 2: Init resumable upload response
        init_resp = MagicMock()
        init_resp.status_code = 200
        init_resp.headers = {"Location": "https://upload.youtube.com/resumable/123"}

        mock_post.side_effect = [token_resp, init_resp]

        # Step 3: Put chunk response
        put_resp = MagicMock()
        put_resp.status_code = 200
        put_resp.json.return_value = {"id": "yt_short_12345"}
        mock_put.return_value = put_resp

        payload = PublishPayload(file_path=self.temp_file.name, title="Epic Short")
        config = {
            "social": {
                "youtube": {
                    "client_id": "id",
                    "client_secret": "sec",
                    "refresh_token": "ref"
                }
            }
        }
        progress_calls = []
        logs = []

        result = self.client.upload(
            payload,
            config,
            progress_callback=lambda f: progress_calls.append(f),
            logger=lambda m: logs.append(m)
        )

        self.assertEqual(result, "https://youtube.com/shorts/yt_short_12345")
        self.assertGreaterEqual(len(progress_calls), 1)
        self.assertTrue(any("Published to YouTube Shorts" in log for log in logs))

    def test_upload_missing_credentials_raises(self):
        payload = PublishPayload(file_path=self.temp_file.name)
        with self.assertRaises(ValueError) as ctx:
            self.client.upload(payload, {})
        self.assertIn("YouTube OAuth is not configured", str(ctx.exception))


class TestTikTokClient(unittest.TestCase):

    def setUp(self):
        self.client = TikTokClient()
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self.temp_file.write(b"x" * 512)
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_verify_credentials_missing_token(self):
        success, msg = self.client.verify_credentials({})
        self.assertFalse(success)
        self.assertIn("Missing TikTok Access Token", msg)

    @patch("requests.get")
    def test_verify_credentials_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "error": {"code": "ok"},
            "data": {"user": {"display_name": "TestGamer"}}
        }
        mock_get.return_value = mock_resp

        config = {"social": {"tiktok": {"access_token": "valid_tk_token"}}}
        success, msg = self.client.verify_credentials(config)
        self.assertTrue(success)
        self.assertIn("TestGamer", msg)

    @patch("requests.put")
    @patch("requests.post")
    def test_upload_success(self, mock_post, mock_put):
        init_resp = MagicMock()
        init_resp.status_code = 200
        init_resp.json.return_value = {
            "error": {"code": "ok"},
            "data": {
                "upload_url": "https://tiktok.upload/chunk",
                "publish_id": "tk_pub_999"
            }
        }
        mock_post.return_value = init_resp

        put_resp = MagicMock()
        put_resp.status_code = 200
        mock_put.return_value = put_resp

        payload = PublishPayload(file_path=self.temp_file.name, title="TikTok Viral")
        config = {"social": {"tiktok": {"access_token": "act.test_token"}}}

        progress_calls = []
        result = self.client.upload(
            payload,
            config,
            progress_callback=lambda f: progress_calls.append(f)
        )

        self.assertEqual(result, "https://www.tiktok.com/@post/tk_pub_999")
        self.assertEqual(progress_calls, [1.0])

    def test_upload_missing_token_raises(self):
        payload = PublishPayload(file_path=self.temp_file.name)
        with self.assertRaises(ValueError) as ctx:
            self.client.upload(payload, {})
        self.assertIn("TikTok is not configured", str(ctx.exception))


class TestInstagramReelsClient(unittest.TestCase):

    def setUp(self):
        self.client = InstagramReelsClient()
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self.temp_file.write(b"x" * 256)
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_verify_credentials_missing_keys(self):
        success, msg = self.client.verify_credentials({})
        self.assertFalse(success)
        self.assertIn("Missing Instagram", msg)

    @patch("requests.get")
    def test_verify_credentials_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "17841400", "username": "cliperator_official"}
        mock_get.return_value = mock_resp

        config = {"social": {"instagram": {"user_id": "17841400", "access_token": "valid_token"}}}
        success, msg = self.client.verify_credentials(config)
        self.assertTrue(success)
        self.assertIn("@cliperator_official", msg)

    @patch("requests.post")
    def test_upload_success(self, mock_post):
        # Step 1: Container creation
        init_resp = MagicMock()
        init_resp.status_code = 200
        init_resp.json.return_value = {"id": "container_123", "uri": "https://rupload.facebook.com/reel"}

        # Step 2: Chunk upload
        upload_resp = MagicMock()
        upload_resp.status_code = 200

        # Step 3: Publish container
        pub_resp = MagicMock()
        pub_resp.status_code = 200
        pub_resp.json.return_value = {"id": "ig_reel_888"}

        mock_post.side_effect = [init_resp, upload_resp, pub_resp]

        payload = PublishPayload(file_path=self.temp_file.name, description="Awesome Reel")
        config = {"social": {"instagram": {"user_id": "17841400", "access_token": "EAA_test"}}}

        result = self.client.upload(payload, config)
        self.assertEqual(result, "https://www.instagram.com/reel/ig_reel_888/")

    def test_upload_missing_keys_raises(self):
        payload = PublishPayload(file_path=self.temp_file.name)
        with self.assertRaises(ValueError) as ctx:
            self.client.upload(payload, {})
        self.assertIn("Instagram is not configured", str(ctx.exception))


class TestSocialPublishManager(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()
        self.manager = SocialPublishManager(event_bus=self.bus)
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self.temp_file.write(b"data")
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_verify_unsupported_platform(self):
        success, msg = self.manager.verify_platform("Twitter", {})
        self.assertFalse(success)
        self.assertIn("Unsupported platform", msg)

    def test_publish_clip_unsupported_platform_raises(self):
        payload = PublishPayload(file_path=self.temp_file.name)
        with self.assertRaises(ValueError) as ctx:
            self.manager.publish_clip("Snapchat", payload, {})
        self.assertIn("Unsupported social platform", str(ctx.exception))

    def test_publish_clip_fires_event(self):
        events_received = []
        self.bus.subscribe(Event.SOCIAL_PUBLISHED, lambda **kw: events_received.append(kw))

        # Mock the YouTube client
        mock_client = MagicMock()
        mock_client.upload.return_value = "https://youtube.com/shorts/test_url"
        self.manager.clients[SocialPlatform.YOUTUBE_SHORTS.value] = mock_client

        payload = PublishPayload(file_path=self.temp_file.name, title="Test Pub")
        result = self.manager.publish_clip(SocialPlatform.YOUTUBE_SHORTS.value, payload, {})

        self.assertEqual(result, "https://youtube.com/shorts/test_url")
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0]["url"], "https://youtube.com/shorts/test_url")
        self.assertEqual(events_received[0]["platform"], SocialPlatform.YOUTUBE_SHORTS.value)

    def test_get_social_publish_manager_singleton(self):
        m1 = get_social_publish_manager()
        m2 = get_social_publish_manager()
        self.assertIs(m1, m2)


class TestPublishDialogAndAppIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix="_vertical.mp4", delete=False)
        self.temp_file.write(b"video")
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    @patch("customtkinter.CTkOptionMenu")
    def test_dialog_init_video_sources(self, mock_option_menu):
        import gui.publish_dialog as pd
        clip_info = {
            "video_path": self.temp_file.name,
            "filename": "my_highlight_vertical.mp4",
            "reasoning": "Insane reaction"
        }
        mock_dialog = MagicMock()
        mock_dialog.clip_info = clip_info
        mock_dialog.form_card = MagicMock()

        pd.PublishDialog._init_video_source_options(mock_dialog)

        self.assertTrue(hasattr(mock_dialog, 'path_map'))
        self.assertIn("📱 9:16 Vertical Cut (Shorts / Reels / TikTok)", mock_dialog.path_map)
        mock_dialog.source_menu.set.assert_called_once()

    def test_dialog_platform_changed_formats_title(self):
        import gui.publish_dialog as pd
        mock_dialog = MagicMock()
        mock_dialog.title_entry.get.return_value = "Great Play"

        pd.PublishDialog._on_platform_changed(mock_dialog, SocialPlatform.YOUTUBE_SHORTS.value)
        mock_dialog.title_entry.delete.assert_called_with(0, "end")
        mock_dialog.title_entry.insert.assert_called_with(0, "Great Play #Shorts")

    @patch("gui.PublishDialog")
    def test_app_open_publish_dialog(self, mock_dialog_cls):
        import app
        app_inst = app.ClipGenApp.__new__(app.ClipGenApp)
        app_inst.config = {"social": {}}
        app_inst._on_social_publish_completed = MagicMock()

        app_inst.open_publish_dialog(
            video_path=self.temp_file.name,
            companion_path=None,
            filename="test_video.mp4",
            reasoning="Super viral"
        )
        mock_dialog_cls.assert_called_once()

    def test_app_verify_social_credentials_dispatch(self):
        import app
        app_inst = app.ClipGenApp.__new__(app.ClipGenApp)
        mock_settings = MagicMock()
        mock_settings.get_settings.return_value = {
            "social": {"tiktok": {"access_token": "valid"}}
        }
        app_inst.settings_frame = mock_settings
        app_inst.log_to_console = MagicMock()
        app_inst.after = MagicMock(side_effect=lambda delay, fn: fn())

        with patch("social_publisher.SocialPublishManager.verify_platform", return_value=(True, "Success")):
            with patch("threading.Thread") as mock_thread:
                app_inst.verify_social_credentials("TikTok")
                mock_thread.assert_called_once()
                target_fn = mock_thread.call_args[1]["target"]
                target_fn()
                app_inst.log_to_console.assert_called_with("[TikTok] Success")

    def test_app_social_published_event_handler(self):
        import app
        app_inst = app.ClipGenApp.__new__(app.ClipGenApp)
        app_inst.log_to_console = MagicMock()
        app_inst.send_discord_alert = MagicMock()

        app_inst._on_social_published(
            platform="YouTube Shorts",
            url="https://youtube.com/shorts/abc",
            title="My Clip"
        )

        app_inst.log_to_console.assert_called_once()
        app_inst.send_discord_alert.assert_called_once()
        self.assertIn("YouTube Shorts", app_inst.send_discord_alert.call_args[0][0])
