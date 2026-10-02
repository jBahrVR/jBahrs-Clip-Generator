import os
import json
import threading
from collections import OrderedDict
from typing import Optional, Dict, Any, Callable, List, Tuple

class GalleryMetadataCache:
    """
    Thread-safe in-memory cache for clip JSON metadata.
    Avoids redundant disk I/O on UI interactions, tab switches, and filtering.
    Entries are keyed by canonical JSON path and validated against file modification time (mtime).
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def get_metadata(self, json_path: str) -> Optional[dict]:
        """
        Retrieves JSON metadata for the specified path.
        Returns cached data if mtime matches; reads and caches if miss or modified.
        """
        if not json_path or not os.path.exists(json_path):
            return None

        try:
            mtime = os.path.getmtime(json_path)
        except OSError:
            return None

        with self._lock:
            if json_path in self._cache:
                cached_mtime, data = self._cache[json_path]
                if cached_mtime == mtime:
                    return data

        # Read from disk outside lock to minimize contention
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return None

        with self._lock:
            self._cache[json_path] = (mtime, data)
        return data

    def get_score(self, clips_dir: str, filename: str) -> float:
        """
        Extracts virality score for a clip filename, automatically resolving
        the base companion .json file path.
        """
        base_json_name = filename.replace("_vertical.mp4", ".mp4").replace(".mp4", ".json")
        json_path = os.path.join(clips_dir, base_json_name)
        data = self.get_metadata(json_path)
        if data and isinstance(data, dict):
            try:
                raw_score = data.get("virality_score", 0)
                score = float(raw_score)
                return max(0.0, min(10.0, score))
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    def invalidate(self, json_path: Optional[str] = None) -> None:
        """
        Invalidates a specific file entry or clears the entire cache.
        """
        with self._lock:
            if json_path is not None:
                self._cache.pop(json_path, None)
            else:
                self._cache.clear()

    def size(self) -> int:
        """Returns the number of cached entries."""
        with self._lock:
            return len(self._cache)


class ThumbnailCache:
    """
    Thread-safe LRU (Least Recently Used) cache for decoded thumbnail objects.
    Maintains a maximum capacity to prevent memory leaks during extended gallery browsing.
    """

    def __init__(self, maxsize: int = 64):
        self.maxsize = max(1, maxsize)
        self._cache: OrderedDict[Tuple[str, float], Any] = OrderedDict()
        self._lock = threading.Lock()

    def get_thumbnail(self, image_path: str, loader_func: Optional[Callable[[str], Any]] = None) -> Optional[Any]:
        """
        Retrieves a cached thumbnail object if available and mtime matches.
        If not cached, invokes loader_func(image_path) and stores the result in LRU order.
        """
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            mtime = os.path.getmtime(image_path)
        except OSError:
            return None

        key = (image_path, mtime)

        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]

        if loader_func is None:
            return None

        try:
            obj = loader_func(image_path)
        except Exception:
            return None

        if obj is None:
            return None

        with self._lock:
            # Re-check key in case another thread loaded it
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]

            self._cache[key] = obj
            self._cache.move_to_end(key)
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

        return obj

    def evict(self, image_path: Optional[str] = None) -> None:
        """
        Evicts entries matching image_path or clears the entire cache.
        """
        with self._lock:
            if image_path is not None:
                keys_to_remove = [k for k in self._cache if k[0] == image_path]
                for k in keys_to_remove:
                    self._cache.pop(k, None)
            else:
                self._cache.clear()

    def size(self) -> int:
        """Returns the number of cached items."""
        with self._lock:
            return len(self._cache)


def scan_and_filter_clips(
    clips_dir: str,
    sort_mode: str = "Date (Newest)",
    type_filter: str = "All",
    score_filter: str = "All",
    meta_cache: Optional[GalleryMetadataCache] = None
) -> List[Dict[str, Any]]:
    """
    Scans clips_dir off the main thread, extracts timestamps and virality scores,
    and returns a filtered and sorted list of clip records:
    [{"filename": str, "ctime": float, "score": float}, ...]
    """
    if not clips_dir or not os.path.exists(clips_dir):
        return []

    cache = meta_cache if meta_cache is not None else GalleryMetadataCache()

    # Parse min_score filter
    min_score = 0.0
    if score_filter and score_filter != "All":
        try:
            min_score = float(score_filter.replace("+", ""))
        except ValueError:
            min_score = 0.0

    clip_data: List[Dict[str, Any]] = []

    try:
        entries = os.listdir(clips_dir)
    except OSError:
        return []

    for f in entries:
        if not f.endswith(".mp4"):
            continue

        full_path = os.path.join(clips_dir, f)
        try:
            timestamp = os.path.getmtime(full_path)
        except OSError:
            timestamp = 0.0

        is_vertical = "_vertical" in f
        if type_filter == "Horizontal" and is_vertical:
            continue
        if type_filter == "Vertical" and not is_vertical:
            continue

        score = cache.get_score(clips_dir, f)
        if score < min_score:
            continue

        clip_data.append({
            "filename": f,
            "ctime": timestamp,
            "score": score
        })

    # Sort
    if sort_mode == "Date (Newest)":
        clip_data.sort(key=lambda x: x["ctime"], reverse=True)
    elif sort_mode == "Date (Oldest)":
        clip_data.sort(key=lambda x: x["ctime"])
    elif sort_mode == "Virality (High)":
        clip_data.sort(key=lambda x: (x["score"], x["ctime"]), reverse=True)
    elif sort_mode == "Virality (Low)":
        clip_data.sort(key=lambda x: (x["score"], -x["ctime"]))
    else:
        clip_data.sort(key=lambda x: x["ctime"], reverse=True)

    return clip_data
