import os
import json
import time
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import app
from gallery_manager import GalleryMetadataCache, ThumbnailCache, scan_and_filter_clips

class TestGalleryManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.clips_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_metadata_cache_hit_and_miss(self):
        cache = GalleryMetadataCache()
        json_path = os.path.join(self.clips_dir, "test_clip.json")
        initial_data = {"virality_score": 8.5, "reasoning": "High-octane clutch"}
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        # Cache miss: reads from disk
        data1 = cache.get_metadata(json_path)
        self.assertEqual(data1, initial_data)
        self.assertEqual(cache.size(), 1)

        # Overwrite file with new content without updating mtime (or verify cache returns cached copy)
        # Even if file is deleted, cached content is returned if we mock or test hit
        data2 = cache.get_metadata(json_path)
        self.assertEqual(data2, initial_data)

    def test_metadata_cache_mtime_invalidation(self):
        cache = GalleryMetadataCache()
        json_path = os.path.join(self.clips_dir, "test_clip.json")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"virality_score": 4.0}, f)
        
        data1 = cache.get_metadata(json_path)
        self.assertEqual(data1.get("virality_score"), 4.0)

        # Update file and forward mtime
        time.sleep(0.05)
        new_mtime = time.time() + 10.0
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"virality_score": 9.5}, f)
        os.utime(json_path, (new_mtime, new_mtime))

        data2 = cache.get_metadata(json_path)
        self.assertEqual(data2.get("virality_score"), 9.5)

    def test_metadata_cache_corrupt_file_and_missing(self):
        cache = GalleryMetadataCache()
        # Non-existent
        self.assertIsNone(cache.get_metadata(os.path.join(self.clips_dir, "nonexistent.json")))

        # Corrupted JSON
        corrupt_path = os.path.join(self.clips_dir, "corrupt.json")
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write("INVALID JSON CONTENT {")

        self.assertIsNone(cache.get_metadata(corrupt_path))

    def test_metadata_cache_invalidate(self):
        cache = GalleryMetadataCache()
        p1 = os.path.join(self.clips_dir, "clip1.json")
        p2 = os.path.join(self.clips_dir, "clip2.json")
        for p in [p1, p2]:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"score": 5}, f)
            cache.get_metadata(p)

        self.assertEqual(cache.size(), 2)
        cache.invalidate(p1)
        self.assertEqual(cache.size(), 1)
        cache.invalidate()
        self.assertEqual(cache.size(), 0)

    def test_metadata_cache_get_score(self):
        cache = GalleryMetadataCache()
        json_path = os.path.join(self.clips_dir, "clip_sample.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"virality_score": 7.8}, f)

        # Resolves horizontal clip name
        self.assertAlmostEqual(cache.get_score(self.clips_dir, "clip_sample.mp4"), 7.8)
        # Resolves vertical clip companion name
        self.assertAlmostEqual(cache.get_score(self.clips_dir, "clip_sample_vertical.mp4"), 7.8)
        # Clamped out of bounds score
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"virality_score": 15.0}, f)
        os.utime(json_path, (time.time() + 5, time.time() + 5))
        self.assertEqual(cache.get_score(self.clips_dir, "clip_sample.mp4"), 10.0)

    def test_thumbnail_lru_cache_capacity_eviction(self):
        cache = ThumbnailCache(maxsize=3)
        files = []
        for i in range(4):
            path = os.path.join(self.clips_dir, f"img_{i}.jpg")
            with open(path, "wb") as f:
                f.write(b"fake_image_bytes")
            files.append(path)

        loader = MagicMock(side_effect=lambda p: f"loaded_{os.path.basename(p)}")

        # Load first 3
        cache.get_thumbnail(files[0], loader)
        cache.get_thumbnail(files[1], loader)
        cache.get_thumbnail(files[2], loader)
        self.assertEqual(cache.size(), 3)
        self.assertEqual(loader.call_count, 3)

        # Loading 4th should evict files[0] (oldest)
        cache.get_thumbnail(files[3], loader)
        self.assertEqual(cache.size(), 3)

        # Calling files[1] and files[2] should be cache hits (loader NOT called again for them)
        loader.reset_mock()
        cache.get_thumbnail(files[1], loader)
        cache.get_thumbnail(files[2], loader)
        loader.assert_not_called()

        # Calling files[0] should be a cache miss (evicted), calling loader
        cache.get_thumbnail(files[0], loader)
        loader.assert_called_once_with(files[0])

    def test_thumbnail_lru_cache_mru_order(self):
        cache = ThumbnailCache(maxsize=3)
        files = []
        for i in range(4):
            path = os.path.join(self.clips_dir, f"img_{i}.jpg")
            with open(path, "wb") as f:
                f.write(b"data")
            files.append(path)

        loader = lambda p: f"obj_{p}"

        cache.get_thumbnail(files[0], loader)
        cache.get_thumbnail(files[1], loader)
        cache.get_thumbnail(files[2], loader)

        # Access files[0] to make it MRU (order: 1, 2, 0)
        cache.get_thumbnail(files[0], loader)

        # Inserting files[3] should evict files[1] (now oldest) instead of files[0]
        cache.get_thumbnail(files[3], loader)

        # files[0] should still be in cache!
        mock_loader = MagicMock()
        cache.get_thumbnail(files[0], mock_loader)
        mock_loader.assert_not_called()

    def test_thumbnail_evict(self):
        cache = ThumbnailCache(maxsize=10)
        path = os.path.join(self.clips_dir, "test.jpg")
        with open(path, "wb") as f:
            f.write(b"data")

        cache.get_thumbnail(path, lambda p: "image_obj")
        self.assertEqual(cache.size(), 1)
        cache.evict(path)
        self.assertEqual(cache.size(), 0)

    def test_scan_and_filter_clips(self):
        # Create test clips with companion json
        clips = [
            ("gameplay_1.mp4", 4.0, 100),
            ("gameplay_1_vertical.mp4", 4.0, 101),
            ("gameplay_2.mp4", 8.5, 200),
            ("gameplay_2_vertical.mp4", 8.5, 201),
            ("gameplay_3.mp4", 6.0, 150),
        ]

        for fname, score, ctime in clips:
            fpath = os.path.join(self.clips_dir, fname)
            with open(fpath, "wb") as f:
                f.write(b"mp4_content")
            os.utime(fpath, (ctime, ctime))

            # Base json
            base_json = fname.replace("_vertical.mp4", ".mp4").replace(".mp4", ".json")
            jpath = os.path.join(self.clips_dir, base_json)
            if not os.path.exists(jpath):
                with open(jpath, "w", encoding="utf-8") as jf:
                    json.dump({"virality_score": score}, jf)

        cache = GalleryMetadataCache()

        # Test orientation filtering
        all_clips = scan_and_filter_clips(self.clips_dir, type_filter="All", meta_cache=cache)
        self.assertEqual(len(all_clips), 5)

        h_clips = scan_and_filter_clips(self.clips_dir, type_filter="Horizontal", meta_cache=cache)
        self.assertEqual(len(h_clips), 3)
        self.assertTrue(all("_vertical" not in x["filename"] for x in h_clips))

        v_clips = scan_and_filter_clips(self.clips_dir, type_filter="Vertical", meta_cache=cache)
        self.assertEqual(len(v_clips), 2)
        self.assertTrue(all("_vertical" in x["filename"] for x in v_clips))

        # Test score filtering with Date sorting (critical bug fix test)
        high_score_clips = scan_and_filter_clips(
            self.clips_dir,
            sort_mode="Date (Newest)",
            type_filter="All",
            score_filter="7+",
            meta_cache=cache
        )
        self.assertEqual(len(high_score_clips), 2)  # gameplay_2 and gameplay_2_vertical
        self.assertTrue(all(x["score"] >= 7.0 for x in high_score_clips))

        # Test sorting
        date_sorted = scan_and_filter_clips(self.clips_dir, sort_mode="Date (Newest)", meta_cache=cache)
        self.assertEqual(date_sorted[0]["filename"], "gameplay_2_vertical.mp4")

        virality_sorted = scan_and_filter_clips(self.clips_dir, sort_mode="Virality (High)", meta_cache=cache)
        self.assertEqual(virality_sorted[0]["score"], 8.5)


class TestAppGalleryAsync(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app_instance = app.ClipGenApp.__new__(app.ClipGenApp)
        self.app_instance.config = {"settings": {"clips_dir": self.temp_dir.name}}
        self.app_instance.clip_listbox = MagicMock()
        self.app_instance.clip_listbox.winfo_children.return_value = []
        self.app_instance.sort_menu = MagicMock()
        self.app_instance.sort_menu.get.return_value = "Date (Newest)"
        self.app_instance.type_filter_menu = MagicMock()
        self.app_instance.type_filter_menu.get.return_value = "All"
        self.app_instance.score_filter_menu = MagicMock()
        self.app_instance.tk = MagicMock()
        self.app_instance.select_all_var = MagicMock()
        self.app_instance.gallery_meta_cache = GalleryMetadataCache()
        self.app_instance.thumbnail_cache = ThumbnailCache()
        self.app_instance._gallery_scan_id = 0
        self.app_instance.after = MagicMock()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_populate_gallery_dispatches_worker(self):
        with patch("customtkinter.CTkLabel"), patch("customtkinter.CTkFont"), patch("threading.Thread") as mock_thread:
            self.app_instance.populate_gallery()
            self.assertEqual(self.app_instance._gallery_scan_id, 1)
            mock_thread.assert_called_once()
            # Verify worker was started as daemon
            args = mock_thread.call_args[1]
            self.assertTrue(args.get("daemon"))

    def test_scan_gallery_worker_ignores_stale_scan_id(self):
        # Current app scan ID is 2, worker runs with scan_id 1
        self.app_instance._gallery_scan_id = 2
        self.app_instance._scan_gallery_worker(1, self.temp_dir.name, "Date (Newest)", "All", "All")
        # Stale scan should NOT schedule UI render
        self.app_instance.after.assert_not_called()

    def test_scan_gallery_worker_schedules_render_when_valid(self):
        self.app_instance._gallery_scan_id = 1
        self.app_instance._scan_gallery_worker(1, self.temp_dir.name, "Date (Newest)", "All", "All")
        # Should call self.after(0, self._render_gallery_items, 1, ..., clips_dir)
        self.app_instance.after.assert_called_once()
        args = self.app_instance.after.call_args[0]
        self.assertEqual(args[0], 0)
        self.assertEqual(args[1], self.app_instance._render_gallery_items)
        self.assertEqual(args[2], 1)


if __name__ == '__main__':
    unittest.main()
