import os
import unittest
from unittest.mock import MagicMock, patch
from queue_manager import QueueItem, QueueManager
from event_bus import EventBus, Event
import gui

class TestQueueItem(unittest.TestCase):
    def test_default_values(self):
        item = QueueItem(source="video.mp4")
        self.assertTrue(len(item.id) >= 6)
        self.assertEqual(item.source, "video.mp4")
        self.assertEqual(item.prompt_profile, "Omni-Genre Broad Net")
        self.assertEqual(item.target_orientation, "Both (16:9 + 9:16)")
        self.assertEqual(item.status, "Queued")
        self.assertEqual(item.progress, 0.0)
        self.assertEqual(item.created_clips, [])
        self.assertIsNone(item.error_message)

    def test_display_name_local_path(self):
        item = QueueItem(source="C:/Videos/Stream_2025_09.mp4")
        self.assertEqual(item.display_name, "Stream_2025_09.mp4")

    def test_display_name_url(self):
        short_url = "https://youtube.com/watch?v=abc123"
        item = QueueItem(source=short_url)
        self.assertEqual(item.display_name, short_url)

        long_url = "https://youtube.com/watch?v=very_long_url_with_many_parameters_and_tracking_tokens_12345"
        item_long = QueueItem(source=long_url)
        self.assertTrue(item_long.display_name.endswith("..."))
        self.assertLessEqual(len(item_long.display_name), 46)

    def test_to_and_from_dict(self):
        item = QueueItem(
            id="test_id_1",
            source="test.mp4",
            prompt_profile="Jump Scares Only",
            target_orientation="Vertical Only (9:16)",
            status="Done",
            progress=1.0,
            created_clips=["clip1.mp4", "clip1_vertical.mp4"]
        )
        d = item.to_dict()
        self.assertEqual(d["id"], "test_id_1")
        self.assertEqual(d["prompt_profile"], "Jump Scares Only")
        self.assertEqual(d["target_orientation"], "Vertical Only (9:16)")
        self.assertEqual(len(d["created_clips"]), 2)

        restored = QueueItem.from_dict(d)
        self.assertEqual(restored.id, "test_id_1")
        self.assertEqual(restored.prompt_profile, "Jump Scares Only")
        self.assertEqual(restored.target_orientation, "Vertical Only (9:16)")
        self.assertEqual(restored.status, "Done")
        self.assertEqual(restored.created_clips, ["clip1.mp4", "clip1_vertical.mp4"])


class TestQueueManager(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.qm = QueueManager(event_bus=self.bus)

    def test_add_item_and_items(self):
        item1 = self.qm.add_item("vid1.mp4", prompt_profile="Profile A")
        self.assertEqual(len(self.qm.get_items()), 1)
        self.assertEqual(item1.source, "vid1.mp4")
        self.assertEqual(item1.prompt_profile, "Profile A")

        added = self.qm.add_items(["vid2.mp4", "vid3.mp4"], prompt_profile="Profile B")
        self.assertEqual(len(added), 2)
        self.assertEqual(len(self.qm.get_items()), 3)

    def test_remove_item(self):
        item = self.qm.add_item("vid1.mp4")
        self.assertTrue(self.qm.remove_item(item.id))
        self.assertEqual(len(self.qm.get_items()), 0)
        self.assertFalse(self.qm.remove_item("nonexistent"))

    def test_clear_completed(self):
        i1 = self.qm.add_item("vid1.mp4")
        i2 = self.qm.add_item("vid2.mp4")
        i3 = self.qm.add_item("vid3.mp4")

        self.qm.update_item_status(i1.id, "Done", 1.0)
        self.qm.update_item_status(i2.id, "Failed", 0.0, error="Corrupt")
        
        # i3 is still "Queued"
        cleared = self.qm.clear_completed()
        self.assertEqual(cleared, 2)
        remaining = self.qm.get_items()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, i3.id)

    def test_clear_all(self):
        self.qm.add_items(["v1.mp4", "v2.mp4"])
        self.assertEqual(len(self.qm.get_items()), 2)
        self.qm.clear_all()
        self.assertEqual(len(self.qm.get_items()), 0)

    def test_update_item_profile_and_orientation(self):
        item = self.qm.add_item("vid.mp4", prompt_profile="Old", target_orientation="Both (16:9 + 9:16)")
        self.assertTrue(self.qm.update_item_profile(item.id, "New Profile"))
        self.assertTrue(self.qm.update_item_orientation(item.id, "Vertical Only (9:16)"))

        updated = self.qm.get_item(item.id)
        self.assertEqual(updated.prompt_profile, "New Profile")
        self.assertEqual(updated.target_orientation, "Vertical Only (9:16)")

    def test_get_summary(self):
        i1 = self.qm.add_item("v1.mp4")
        i2 = self.qm.add_item("v2.mp4")
        i3 = self.qm.add_item("v3.mp4")

        self.qm.update_item_status(i1.id, "Done", 1.0)
        self.qm.update_item_status(i2.id, "Transcribing", 0.3)

        summary = self.qm.get_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["done"], 1)
        self.assertEqual(summary["processing"], 1)
        self.assertEqual(summary["queued"], 1)
        self.assertEqual(summary["failed"], 0)

    def test_event_bus_publishing(self):
        events_received = []
        self.bus.subscribe(Event.QUEUE_UPDATED, lambda **kw: events_received.append(kw))

        self.qm.add_item("test.mp4")
        self.assertGreater(len(events_received), 0)
        self.assertEqual(events_received[-1]["summary"]["total"], 1)


class TestQueueManagerProcessing(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.qm = QueueManager(event_bus=self.bus)

    @patch('os.path.exists', return_value=True)
    def test_process_queue_local_files_success(self, mock_exists):
        self.qm.add_item("local1.mp4", prompt_profile="Action Focus", target_orientation="Horizontal Only (16:9)")
        self.qm.add_item("local2.mp4", prompt_profile="Funny Moments", target_orientation="Vertical Only (9:16)")

        mock_process_video = MagicMock(return_value=["clip1.mp4"])
        mock_download = MagicMock()
        mock_video_id = MagicMock()
        mock_complete = MagicMock()

        count = self.qm.process_queue(
            process_video_fn=mock_process_video,
            download_fn=mock_download,
            get_video_id_fn=mock_video_id,
            on_item_complete=mock_complete
        )

        self.assertEqual(count, 2)
        self.assertEqual(mock_process_video.call_count, 2)
        self.assertEqual(mock_complete.call_count, 2)
        
        # Verify first call arguments
        call1 = mock_process_video.call_args_list[0]
        self.assertEqual(call1[0][0], "local1.mp4")
        self.assertEqual(call1[1]["prompt_profile"], "Action Focus")
        self.assertEqual(call1[1]["target_orientation"], "Horizontal Only (16:9)")

        # Verify second call arguments
        call2 = mock_process_video.call_args_list[1]
        self.assertEqual(call2[0][0], "local2.mp4")
        self.assertEqual(call2[1]["prompt_profile"], "Funny Moments")
        self.assertEqual(call2[1]["target_orientation"], "Vertical Only (9:16)")

    def test_process_queue_local_file_missing(self):
        self.qm.add_item("nonexistent_video_path.mp4")
        mock_process_video = MagicMock()
        
        count = self.qm.process_queue(
            process_video_fn=mock_process_video,
            download_fn=MagicMock(),
            get_video_id_fn=MagicMock()
        )

        self.assertEqual(count, 0)
        mock_process_video.assert_not_called()
        item = self.qm.get_items()[0]
        self.assertEqual(item.status, "Failed")
        self.assertIn("File does not exist", item.error_message)

    @patch('os.path.exists', return_value=True)
    def test_process_queue_remote_url_success(self, mock_exists):
        self.qm.add_item("https://youtube.com/watch?v=xyz789")

        mock_video_id = MagicMock(return_value="xyz789")
        mock_download = MagicMock(return_value="downloaded_xyz789.mp4")
        mock_process_video = MagicMock(return_value=["clip.mp4"])

        count = self.qm.process_queue(
            process_video_fn=mock_process_video,
            download_fn=mock_download,
            get_video_id_fn=mock_video_id
        )

        self.assertEqual(count, 1)
        mock_video_id.assert_called_once_with("https://youtube.com/watch?v=xyz789")
        mock_download.assert_called_once()
        mock_process_video.assert_called_once()
        self.assertEqual(self.qm.get_items()[0].status, "Done")

    def test_process_queue_cancellation(self):
        with patch('os.path.exists', return_value=True):
            self.qm.add_item("item1.mp4")
            self.qm.add_item("item2.mp4")

            def cancel_side_effect(*args, **kwargs):
                self.qm.cancel()
                return []

            mock_process = MagicMock(side_effect=cancel_side_effect)

            count = self.qm.process_queue(
                process_video_fn=mock_process,
                download_fn=MagicMock(),
                get_video_id_fn=MagicMock()
            )

            # Only item 1 ran and triggered cancellation
            self.assertEqual(mock_process.call_count, 1)
            items = self.qm.get_items()
            self.assertEqual(items[0].status, "Cancelled")
            self.assertEqual(items[1].status, "Queued")


class TestManualFrameQueueUI(unittest.TestCase):
    def setUp(self):
        self.frame = gui.ManualFrame.__new__(gui.ManualFrame)
        self.frame.on_start_process = MagicMock()
        self.frame.on_cancel_process = MagicMock()
        self.frame.on_browse_files = MagicMock()
        self.frame.on_add_to_queue = MagicMock()
        self.frame.on_remove_queue_item = MagicMock()
        self.frame.on_clear_completed = MagicMock()
        self.frame.on_clear_all = MagicMock()
        self.frame.on_item_profile_changed = MagicMock()
        self.frame.on_item_orientation_changed = MagicMock()
        self.frame.on_files_dropped = MagicMock()

        self.frame.url_input = MagicMock()
        self.frame.manual_status_label = MagicMock()
        self.frame.process_btn = MagicMock()
        self.frame.cancel_btn = MagicMock()
        self.frame.local_file_btn = MagicMock()
        self.frame.add_queue_btn = MagicMock()
        self.frame.manual_progress = MagicMock()
        self.frame.console_box = MagicMock()
        self.frame.queue_card = MagicMock()
        self.frame.queue_scroll = MagicMock()
        self.frame.queue_summary_label = MagicMock()
        self.frame.available_profiles = ["Omni-Genre Broad Net", "Gaming Focus"]

    def test_queue_action_triggers(self):
        self.frame.url_input.get.return_value = "https://youtube.com/watch?v=123"
        self.frame._trigger_add_to_queue()
        self.frame.on_add_to_queue.assert_called_once_with("https://youtube.com/watch?v=123")

        self.frame._trigger_remove_item("item_123")
        self.frame.on_remove_queue_item.assert_called_once_with("item_123")

        self.frame._trigger_clear_completed()
        self.frame.on_clear_completed.assert_called_once()

        self.frame._trigger_clear_all()
        self.frame.on_clear_all.assert_called_once()

        self.frame._trigger_profile_changed("item_123", "Custom Profile")
        self.frame.on_item_profile_changed.assert_called_once_with("item_123", "Custom Profile")

        self.frame._trigger_orientation_changed("item_123", "Vertical Only (9:16)")
        self.frame.on_item_orientation_changed.assert_called_once_with("item_123", "Vertical Only (9:16)")

    def test_drop_files_trigger(self):
        with patch('os.path.exists', return_value=True):
            self.frame._on_drop_files([b"C:/vod1.mp4", "C:/vod2.mkv"])
            self.frame.on_files_dropped.assert_called_once()
            called_files = self.frame.on_files_dropped.call_args[0][0]
            self.assertIn("C:/vod1.mp4", called_files)
            self.assertIn("C:/vod2.mkv", called_files)

    def test_set_available_profiles(self):
        new_profiles = ["Profile 1", "Profile 2", "Profile 3"]
        self.frame.set_available_profiles(new_profiles)
        self.assertEqual(self.frame.available_profiles, new_profiles)


class TestAppQueueIntegration(unittest.TestCase):
    def test_app_queue_methods(self):
        import app
        clip_app = app.ClipGenApp.__new__(app.ClipGenApp)
        clip_app.queue_manager = MagicMock()
        clip_app.config = {"prompts": {"active_profile": "Gaming Focus"}}
        clip_app.log_to_console = MagicMock()
        clip_app.manual_frame = MagicMock()
        clip_app.after = MagicMock()

        # Add manual input to queue
        clip_app.add_manual_input_to_queue("video1.mp4;video2.mp4")
        clip_app.queue_manager.add_items.assert_called_once_with(
            ["video1.mp4", "video2.mp4"],
            prompt_profile="Gaming Focus"
        )

        # Remove queue item
        clip_app.remove_queue_item("item_1")
        clip_app.queue_manager.remove_item.assert_called_once_with("item_1")

        # Clear completed
        clip_app.queue_manager.clear_completed.return_value = 2
        clip_app.clear_completed_queue()
        clip_app.queue_manager.clear_completed.assert_called_once()

        # Update profile and orientation
        clip_app.on_queue_item_profile_changed("item_1", "New Profile")
        clip_app.queue_manager.update_item_profile.assert_called_once_with("item_1", "New Profile")

        clip_app.on_queue_item_orientation_changed("item_1", "Vertical Only (9:16)")
        clip_app.queue_manager.update_item_orientation.assert_called_once_with("item_1", "Vertical Only (9:16)")

        # Cancel
        clip_app.cancel_manual_process()
        self.assertTrue(clip_app.cancel_requested)
        clip_app.queue_manager.cancel.assert_called_once()
