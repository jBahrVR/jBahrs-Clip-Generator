import unittest
from unittest.mock import MagicMock, patch
from event_bus import EventBus, Event, get_event_bus
import gui


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        received = []
        def handler(data, count=0):
            received.append((data, count))

        self.bus.subscribe(Event.LOG, handler)
        self.assertEqual(self.bus.subscriber_count(Event.LOG), 1)

        self.bus.publish(Event.LOG, "Hello EventBus", count=5)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], ("Hello EventBus", 5))

    def test_unsubscribe(self):
        received = []
        def handler(msg):
            received.append(msg)

        self.bus.subscribe("test_topic", handler)
        self.bus.publish("test_topic", "first")
        self.bus.unsubscribe("test_topic", handler)
        self.bus.publish("test_topic", "second")

        self.assertEqual(received, ["first"])
        self.assertEqual(self.bus.subscriber_count("test_topic"), 0)

    def test_subscriber_isolation_on_exception(self):
        results = []
        def faulty_subscriber(val):
            raise RuntimeError("Boom!")

        def healthy_subscriber(val):
            results.append(val)

        self.bus.subscribe("error_event", faulty_subscriber)
        self.bus.subscribe("error_event", healthy_subscriber)

        # Should not raise exception, healthy subscriber must still execute
        self.bus.publish("error_event", "safe")
        self.assertEqual(results, ["safe"])

    def test_clear_subscribers(self):
        self.bus.subscribe("e1", lambda: None)
        self.bus.subscribe("e2", lambda: None)
        self.assertEqual(self.bus.subscriber_count("e1"), 1)
        self.assertEqual(self.bus.subscriber_count("e2"), 1)

        self.bus.clear()
        self.assertEqual(self.bus.subscriber_count("e1"), 0)
        self.assertEqual(self.bus.subscriber_count("e2"), 0)

    def test_get_event_bus_singleton(self):
        b1 = get_event_bus()
        b2 = get_event_bus()
        self.assertIs(b1, b2)


class TestSidebarEncapsulation(unittest.TestCase):

    def setUp(self):
        self.sidebar = gui.Sidebar.__new__(gui.Sidebar)
        self.sidebar.on_navigate = MagicMock()
        self.sidebar.on_quick_action = MagicMock()
        self.sidebar.nav_manual_btn = MagicMock()
        self.sidebar.nav_auto_btn = MagicMock()
        self.sidebar.nav_prompt_btn = MagicMock()
        self.sidebar.nav_settings_btn = MagicMock()
        self.sidebar.nav_gallery_btn = MagicMock()

    def test_navigation_callback(self):
        self.sidebar._trigger_navigate("settings")
        self.sidebar.on_navigate.assert_called_once_with("settings")

    def test_navigation_fallback_master(self):
        self.sidebar.on_navigate = None
        mock_master = MagicMock()
        self.sidebar.master = mock_master
        self.sidebar._trigger_navigate("gallery")
        mock_master.show_gallery_frame.assert_called_once()

    def test_quick_action_callback(self):
        self.sidebar._trigger_quick_action("download_dir")
        self.sidebar.on_quick_action.assert_called_once_with("download_dir")

    def test_quick_action_fallback_master(self):
        self.sidebar.on_quick_action = None
        mock_master = MagicMock()
        self.sidebar.master = mock_master
        self.sidebar._trigger_quick_action("logs")
        mock_master.open_logs.assert_called_once()

    def test_set_active_tab(self):
        self.sidebar.set_active_tab("auto")
        self.sidebar.nav_auto_btn.configure.assert_called_with(fg_color="#1f538d")
        self.sidebar.nav_manual_btn.configure.assert_called_with(fg_color="transparent")
        self.sidebar.nav_prompt_btn.configure.assert_called_with(fg_color="transparent")
        self.sidebar.nav_settings_btn.configure.assert_called_with(fg_color="transparent")
        self.sidebar.nav_gallery_btn.configure.assert_called_with(fg_color="transparent")


class TestManualFrameEncapsulation(unittest.TestCase):

    def setUp(self):
        self.frame = gui.ManualFrame.__new__(gui.ManualFrame)
        self.frame.on_start_process = MagicMock()
        self.frame.on_cancel_process = MagicMock()
        self.frame.on_browse_files = MagicMock()
        self.frame.url_input = MagicMock()
        self.frame.manual_status_label = MagicMock()
        self.frame.process_btn = MagicMock()
        self.frame.cancel_btn = MagicMock()
        self.frame.local_file_btn = MagicMock()
        self.frame.manual_progress = MagicMock()
        self.frame.console_box = MagicMock()

    def test_action_callbacks(self):
        self.frame._trigger_start_process()
        self.frame.on_start_process.assert_called_once()

        self.frame._trigger_cancel_process()
        self.frame.on_cancel_process.assert_called_once()

        self.frame._trigger_browse_files()
        self.frame.on_browse_files.assert_called_once()

    def test_url_getter_and_setter(self):
        self.frame.url_input.get.return_value = "https://youtube.com/watch?v=123"
        self.assertEqual(self.frame.get_url(), "https://youtube.com/watch?v=123")

        self.frame.set_url("https://twitch.tv/vod/456")
        self.frame.url_input.delete.assert_called_with(0, "end")
        self.frame.url_input.insert.assert_called_with(0, "https://twitch.tv/vod/456")

    def test_status_and_processing_state(self):
        self.frame.set_status("Status: Processing", color="#3a7ebf")
        self.frame.manual_status_label.configure.assert_called_with(text="Status: Processing", text_color="#3a7ebf")

        self.frame.set_processing_state(True, "Working...")
        self.frame.process_btn.configure.assert_called_with(state="disabled")
        self.frame.cancel_btn.configure.assert_called_with(state="normal", text="Cancel")
        self.frame.manual_progress.start.assert_called_once()

        self.frame.set_processing_state(False)
        self.frame.process_btn.configure.assert_called_with(state="normal")
        self.frame.cancel_btn.configure.assert_called_with(state="disabled", text="Cancel")
        self.frame.manual_progress.stop.assert_called_once()

    def test_logging_and_clearing(self):
        self.frame.append_log("Test Line", "success")
        self.frame.console_box.insert.assert_called_with("end", "Test Line\n", "success")

        self.frame.clear_log()
        self.frame.console_box.delete.assert_called_with("1.0", "end")


class TestAutoFrameEncapsulation(unittest.TestCase):

    def setUp(self):
        self.frame = gui.AutoFrame.__new__(gui.AutoFrame)
        self.frame.on_toggle_auto = MagicMock()
        self.frame.auto_switch = MagicMock()
        self.frame.platform_menu = MagicMock()
        self.frame.type_menu = MagicMock()
        self.frame.target_menu = MagicMock()
        self.frame.lookback_menu = MagicMock()
        self.frame.interval_menu = MagicMock()
        self.frame.auto_prompt_menu = MagicMock()
        self.frame.auto_progress = MagicMock()
        self.frame.auto_status = MagicMock()
        self.frame.auto_console = MagicMock()

    def test_toggle_auto_callback(self):
        self.frame.auto_switch.get.return_value = 1
        self.frame._trigger_toggle_auto()
        self.frame.on_toggle_auto.assert_called_once_with(True)

    def test_scheduler_settings(self):
        self.frame.platform_menu.get.return_value = "Twitch"
        self.frame.type_menu.get.return_value = "Past Broadcasts"
        self.frame.target_menu.get.return_value = "Both (Horizontal & Vertical)"
        self.frame.lookback_menu.get.return_value = "Last 3 Days"
        self.frame.interval_menu.get.return_value = "Every 1 Hour"
        self.frame.auto_prompt_menu.get.return_value = "Gaming"

        sched = self.frame.get_scheduler_settings()
        self.assertEqual(sched["platform"], "Twitch")
        self.assertEqual(sched["check_interval"], "Every 1 Hour")

        self.frame.set_scheduler_settings({"platform": "YouTube", "check_interval": "Every 4 Hours"})
        self.frame.platform_menu.set.assert_called_with("YouTube")
        self.frame.interval_menu.set.assert_called_with("Every 4 Hours")

    def test_auto_enabled_and_status(self):
        self.frame.auto_switch.get.return_value = 1
        self.assertTrue(self.frame.is_auto_enabled())

        self.frame.set_auto_enabled(True)
        self.frame.auto_switch.select.assert_called_once()

        self.frame.set_auto_enabled(False)
        self.frame.auto_switch.deselect.assert_called_once()

        self.frame.set_status(True, "● Status: ACTIVE")
        self.frame.auto_progress.start.assert_called_once()
        self.frame.auto_status.configure.assert_called_with(text="● Status: ACTIVE", text_color="#2ecc71")

        self.frame.set_status(False)
        self.frame.auto_progress.stop.assert_called_once()


class TestPromptFrameEncapsulation(unittest.TestCase):

    def setUp(self):
        self.frame = gui.PromptFrame.__new__(gui.PromptFrame)
        self.frame.on_profile_change = MagicMock()
        self.frame.on_new_profile = MagicMock()
        self.frame.on_save_prompt = MagicMock()
        self.frame.on_delete_profile = MagicMock()
        self.frame.profile_dropdown = MagicMock()
        self.frame.prompt_textbox = MagicMock()
        self.frame.save_prompt_btn = MagicMock()
        self.frame.after = MagicMock()

    def test_callbacks(self):
        self.frame._trigger_profile_change("IRL")
        self.frame.on_profile_change.assert_called_once_with("IRL")

        self.frame._trigger_new_profile()
        self.frame.on_new_profile.assert_called_once()

        self.frame._trigger_save_prompt()
        self.frame.on_save_prompt.assert_called_once()

        self.frame._trigger_delete_profile()
        self.frame.on_delete_profile.assert_called_once()

    def test_prompt_editor_api(self):
        self.frame.profile_dropdown.get.return_value = "Gaming"
        self.assertEqual(self.frame.get_active_profile(), "Gaming")

        self.frame.prompt_textbox.get.return_value = "Analyze action."
        self.assertEqual(self.frame.get_prompt_text(), "Analyze action.")

        self.frame.set_prompt_text("Updated prompt text")
        self.frame.prompt_textbox.delete.assert_called_with("1.0", "end")
        self.frame.prompt_textbox.insert.assert_called_with("1.0", "Updated prompt text")

        self.frame.set_profiles(["Gaming", "IRL"], active="IRL")
        self.frame.profile_dropdown.configure.assert_called_with(values=["Gaming", "IRL"])
        self.frame.profile_dropdown.set.assert_called_with("IRL")


class TestSettingsFrameEncapsulation(unittest.TestCase):

    def setUp(self):
        self.frame = gui.SettingsFrame.__new__(gui.SettingsFrame)
        self.frame.on_save = MagicMock()
        self.frame.on_test_key = MagicMock()
        self.frame.on_browse_folder = MagicMock()
        self.frame.on_update_ytdlp = MagicMock()
        self.frame.yt_id_entry = MagicMock()
        self.frame.twitch_entry = MagicMock()
        self.frame.openai_entry = MagicMock()
        self.frame.base_url_entry = MagicMock()
        self.frame.anthropic_entry = MagicMock()
        self.frame.grok_entry = MagicMock()
        self.frame.google_entry = MagicMock()
        self.frame.discord_entry = MagicMock()
        self.frame.model_menu = MagicMock()
        self.frame.whisper_menu = MagicMock()
        self.frame.language_menu = MagicMock()
        self.frame.quality_menu = MagicMock()
        self.frame.vod_dir_entry = MagicMock()
        self.frame.clip_dir_entry = MagicMock()
        self.frame.browser_menu = MagicMock()
        self.frame.stabilize_switch = MagicMock()
        self.frame.hardware_switch = MagicMock()
        self.frame.downmix_switch = MagicMock()
        self.frame.audio_peak_switch = MagicMock()
        self.frame.combat_switch = MagicMock()
        self.frame.vertical_switch = MagicMock()
        self.frame.vertical_mode_menu = MagicMock()
        self.frame.crop_x_entry = MagicMock()
        self.frame.crop_y_entry = MagicMock()
        self.frame.crop_w_entry = MagicMock()
        self.frame.crop_h_entry = MagicMock()
        self.frame.save_btn = MagicMock()
        self.frame.after = MagicMock()

    def test_callbacks(self):
        self.frame._trigger_save()
        self.frame.on_save.assert_called_once()

        self.frame._trigger_test_key("openai")
        self.frame.on_test_key.assert_called_once_with("openai")

        self.frame._trigger_browse_folder("download_dir")
        self.frame.on_browse_folder.assert_called_once_with("download_dir")

        self.frame._trigger_update_ytdlp()
        self.frame.on_update_ytdlp.assert_called_once()

    def test_get_settings(self):
        self.frame.yt_id_entry.get.return_value = "UC_TEST"
        self.frame.twitch_entry.get.return_value = "test_user"
        self.frame.openai_entry.get.return_value = "sk-proj-test"
        self.frame.base_url_entry.get.return_value = "https://api.deepseek.com"
        self.frame.anthropic_entry.get.return_value = ""
        self.frame.grok_entry.get.return_value = ""
        self.frame.google_entry.get.return_value = ""
        self.frame.discord_entry.get.return_value = ""
        self.frame.model_menu.get.return_value = "deepseek-reasoner"
        self.frame.whisper_menu.get.return_value = "base"
        self.frame.language_menu.get.return_value = "English"
        self.frame.quality_menu.get.return_value = "1080p"
        self.frame.vod_dir_entry.get.return_value = "C:/vods"
        self.frame.clip_dir_entry.get.return_value = "C:/clips"
        self.frame.browser_menu.get.return_value = "None"
        self.frame.stabilize_switch.get.return_value = 0
        self.frame.hardware_switch.get.return_value = 1
        self.frame.downmix_switch.get.return_value = 1
        self.frame.audio_peak_switch.get.return_value = 1
        self.frame.combat_switch.get.return_value = 1
        self.frame.vertical_switch.get.return_value = 1
        self.frame.vertical_mode_menu.get.return_value = "Letterbox Blur (Blurred Background)"
        self.frame.crop_x_entry.get.return_value = "0"
        self.frame.crop_y_entry.get.return_value = "0"
        self.frame.crop_w_entry.get.return_value = "400"
        self.frame.crop_h_entry.get.return_value = "225"

        cfg = self.frame.get_settings()
        self.assertEqual(cfg["youtube"]["channel_id"], "UC_TEST")
        self.assertEqual(cfg["openai"]["base_url"], "https://api.deepseek.com")
        self.assertEqual(cfg["settings"]["vertical_mode"], "Letterbox Blur (Blurred Background)")
        self.assertTrue(cfg["settings"]["hardware_encoding"])

    def test_set_available_models(self):
        models = ["gemini-2.5-flash", "deepseek-reasoner"]
        self.frame.set_available_models(models)
        self.frame.model_menu.configure.assert_called_with(values=models)


class TestGalleryFrameEncapsulation(unittest.TestCase):

    def setUp(self):
        self.frame = gui.GalleryFrame.__new__(gui.GalleryFrame)
        self.frame.on_filter_changed = MagicMock()
        self.frame.on_refresh = MagicMock()
        self.frame.on_delete_marked = MagicMock()
        self.frame.sort_menu = MagicMock()
        self.frame.type_filter_menu = MagicMock()
        self.frame.score_filter_menu = MagicMock()
        self.frame.clip_listbox = MagicMock()
        self.frame.select_all_var = MagicMock()
        self.frame.marked_for_deletion = {}
        self.frame.detail_title = MagicMock()
        self.frame.detail_score = MagicMock()
        self.frame.detail_reasoning = MagicMock()
        self.frame.detail_thumbnail = MagicMock()
        self.frame.play_clip_btn = MagicMock()
        self.frame.open_folder_btn = MagicMock()
        self.frame.refresh_gallery_btn = MagicMock()
        self.frame.after = MagicMock()

    def test_callbacks(self):
        self.frame._trigger_filter_changed()
        self.frame.on_filter_changed.assert_called_once()

        self.frame._trigger_refresh()
        self.frame.on_refresh.assert_called_once()

        self.frame._trigger_delete_marked()
        self.frame.on_delete_marked.assert_called_once()

    def test_filter_settings(self):
        self.frame.sort_menu.get.return_value = "Date (Newest)"
        self.frame.type_filter_menu.get.return_value = "Vertical"
        self.frame.score_filter_menu.get.return_value = "8+"

        filters = self.frame.get_filter_settings()
        self.assertEqual(filters["sort_mode"], "Date (Newest)")
        self.assertEqual(filters["type_filter"], "Vertical")
        self.assertEqual(filters["score_filter"], "8+")

    def test_marked_files_and_select_all(self):
        v1 = MagicMock()
        v1.get.return_value = True
        v2 = MagicMock()
        v2.get.return_value = False
        self.frame.marked_for_deletion = {"clip1.mp4": v1, "clip2.mp4": v2}

        self.assertEqual(self.frame.get_marked_files(), ["clip1.mp4"])

        self.frame.select_all_var.get.return_value = True
        self.frame.toggle_select_all()
        v1.set.assert_called_with(True)
        v2.set.assert_called_with(True)

    def test_clear_clip_details(self):
        self.frame.clear_clip_details()
        self.frame.detail_title.configure.assert_called_with(text="Select a clip to view details")
        self.frame.detail_score.configure.assert_called_with(text="Score: --/10")
        self.frame.play_clip_btn.configure.assert_called_with(state="disabled")
        self.frame.open_folder_btn.configure.assert_called_with(state="disabled")


class TestAppControllerIntegration(unittest.TestCase):

    def setUp(self):
        import app
        self.app_instance = app.ClipGenApp.__new__(app.ClipGenApp)
        self.app_instance.tk = MagicMock()
        self.app_instance.config = {
            "youtube": {}, "twitch": {}, "openai": {}, "prompts": {"profiles": {"default": "test"}},
            "settings": {"clips_dir": "C:/clips"}
        }
        self.app_instance.event_bus = EventBus()
        self.app_instance.after = MagicMock()

    def test_save_settings_publishes_event(self):
        published_configs = []
        self.app_instance.event_bus.subscribe(Event.CONFIG_SAVED, lambda c: published_configs.append(c))

        mock_settings_frame = MagicMock()
        mock_settings_frame.get_settings.return_value = {
            "youtube": {"channel_id": "UC_SAVED"},
            "settings": {"download_dir": "D:/Saved"}
        }
        self.app_instance.settings_frame = mock_settings_frame
        self.app_instance.log_to_console = MagicMock()
        self.app_instance.refresh_available_models = MagicMock()

        with patch("config_manager.save_config"):
            self.app_instance.save_settings()

        mock_settings_frame.show_saved_feedback.assert_called_once()
        self.assertEqual(len(published_configs), 1)
        self.assertEqual(published_configs[0]["youtube"]["channel_id"], "UC_SAVED")

    def test_save_current_prompt_publishes_event(self):
        prompts = []
        self.app_instance.event_bus.subscribe(Event.PROMPT_UPDATED, lambda name, text: prompts.append((name, text)))

        mock_prompt_frame = MagicMock()
        mock_prompt_frame.get_active_profile.return_value = "Gaming"
        mock_prompt_frame.get_prompt_text.return_value = "Find clutches."
        self.app_instance.prompt_frame = mock_prompt_frame

        with patch("config_manager.save_config"):
            self.app_instance.save_current_prompt()

        mock_prompt_frame.show_save_feedback.assert_called_once()
        self.assertEqual(prompts, [("Gaming", "Find clutches.")])

    def test_navigate_tab_publishes_event(self):
        navigated = []
        self.app_instance.event_bus.subscribe(Event.NAVIGATE, lambda tab: navigated.append(tab))
        self.app_instance.show_manual_frame = MagicMock()

        self.app_instance.navigate_tab("manual")
        self.app_instance.show_manual_frame.assert_called_once()
        self.assertEqual(navigated, ["manual"])


if __name__ == "__main__":
    unittest.main()
