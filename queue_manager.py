import os
import uuid
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from event_bus import get_event_bus, Event

@dataclass
class QueueItem:
    """
    Represents an individual video job in the processing queue.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    source: str = ""
    prompt_profile: str = "Omni-Genre Broad Net"
    target_orientation: str = "Both (16:9 + 9:16)"
    status: str = "Queued"  # "Queued", "Downloading", "Transcribing", "Analyzing AI", "Cutting Clips", "Done", "Failed", "Cancelled"
    progress: float = 0.0
    created_clips: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    @property
    def display_name(self) -> str:
        """Returns a user-friendly label for the source file or URL."""
        if not self.source:
            return "Empty Item"
        is_url = (
            self.source.startswith("http://") or
            self.source.startswith("https://") or
            "twitch.tv" in self.source or
            "youtu" in self.source
        )
        if not is_url:
            return os.path.basename(self.source) or self.source
        # Trim long URL for presentation
        if len(self.source) > 45:
            return self.source[:42] + "..."
        return self.source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "display_name": self.display_name,
            "prompt_profile": self.prompt_profile,
            "target_orientation": self.target_orientation,
            "status": self.status,
            "progress": self.progress,
            "created_clips": list(self.created_clips),
            "error_message": self.error_message,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueItem":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:8]),
            source=data.get("source", ""),
            prompt_profile=data.get("prompt_profile", "Omni-Genre Broad Net"),
            target_orientation=data.get("target_orientation", "Both (16:9 + 9:16)"),
            status=data.get("status", "Queued"),
            progress=data.get("progress", 0.0),
            created_clips=data.get("created_clips", []),
            error_message=data.get("error_message"),
            created_at=data.get("created_at", time.time())
        )


class QueueManager:
    """
    Thread-safe coordinator for batch video processing.
    Supports individual prompt profiles, target orientations, dynamic progress tracking,
    and event publishing via EventBus.
    """

    def __init__(self, event_bus=None) -> None:
        self._items: List[QueueItem] = []
        self._lock = threading.RLock()
        self._event_bus = event_bus or get_event_bus()
        self._is_processing = False
        self._cancel_requested = False
        self._current_item: Optional[QueueItem] = None

    @property
    def is_processing(self) -> bool:
        with self._lock:
            return self._is_processing

    @property
    def cancel_requested(self) -> bool:
        with self._lock:
            return self._cancel_requested

    @property
    def current_item(self) -> Optional[QueueItem]:
        with self._lock:
            return self._current_item

    def add_item(
        self,
        source: str,
        prompt_profile: str = "Omni-Genre Broad Net",
        target_orientation: str = "Both (16:9 + 9:16)"
    ) -> QueueItem:
        """Adds a single video source to the queue."""
        with self._lock:
            item = QueueItem(
                source=source.strip(),
                prompt_profile=prompt_profile,
                target_orientation=target_orientation
            )
            self._items.append(item)
            self._notify_updated()
            return item

    def add_items(
        self,
        sources: List[str],
        prompt_profile: str = "Omni-Genre Broad Net",
        target_orientation: str = "Both (16:9 + 9:16)"
    ) -> List[QueueItem]:
        """Adds multiple video sources to the queue."""
        with self._lock:
            added = []
            for src in sources:
                cleaned = src.strip()
                if cleaned:
                    item = QueueItem(
                        source=cleaned,
                        prompt_profile=prompt_profile,
                        target_orientation=target_orientation
                    )
                    self._items.append(item)
                    added.append(item)
            if added:
                self._notify_updated()
            return added

    def remove_item(self, item_id: str) -> bool:
        """Removes an item by ID from the queue."""
        with self._lock:
            for i, it in enumerate(self._items):
                if it.id == item_id:
                    if it.status in ["Downloading", "Transcribing", "Analyzing AI", "Cutting Clips"]:
                        it.status = "Cancelled"
                    self._items.pop(i)
                    self._notify_updated()
                    return True
            return False

    def clear_completed(self) -> int:
        """Removes all finished (Done, Failed, Cancelled) items from the queue."""
        with self._lock:
            initial_count = len(self._items)
            self._items = [it for it in self._items if it.status not in ["Done", "Failed", "Cancelled"]]
            removed = initial_count - len(self._items)
            if removed > 0:
                self._notify_updated()
            return removed

    def clear_all(self) -> None:
        """Clears all items from the queue."""
        with self._lock:
            self._items.clear()
            self._notify_updated()

    def get_items(self) -> List[QueueItem]:
        """Returns a snapshot copy of all items in the queue."""
        with self._lock:
            return list(self._items)

    def get_item(self, item_id: str) -> Optional[QueueItem]:
        """Retrieves a specific item by ID."""
        with self._lock:
            for it in self._items:
                if it.id == item_id:
                    return it
            return None

    def get_pending_items(self) -> List[QueueItem]:
        """Returns all items currently waiting in 'Queued' status."""
        with self._lock:
            return [it for it in self._items if it.status == "Queued"]

    def update_item_profile(self, item_id: str, new_profile: str) -> bool:
        """Updates the prompt profile for a queued item."""
        with self._lock:
            it = self.get_item(item_id)
            if it:
                it.prompt_profile = new_profile
                self._notify_updated()
                return True
            return False

    def update_item_orientation(self, item_id: str, new_orientation: str) -> bool:
        """Updates the target orientation format for a queued item."""
        with self._lock:
            it = self.get_item(item_id)
            if it:
                it.target_orientation = new_orientation
                self._notify_updated()
                return True
            return False

    def update_item_status(
        self,
        item_id: str,
        status: str,
        progress: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        """Updates the status and progress of an item and fires notifications."""
        with self._lock:
            it = self.get_item(item_id)
            if it:
                it.status = status
                it.progress = max(0.0, min(1.0, progress))
                if error:
                    it.error_message = error
                self._notify_item_status(it)

    def get_summary(self) -> Dict[str, int]:
        """Returns counts of items categorized by their status."""
        with self._lock:
            queued = sum(1 for it in self._items if it.status == "Queued")
            processing = sum(1 for it in self._items if it.status in [
                "Downloading", "Transcribing", "Analyzing AI", "Cutting Clips", "Processing"
            ])
            done = sum(1 for it in self._items if it.status == "Done")
            failed = sum(1 for it in self._items if it.status in ["Failed", "Cancelled"])
            return {
                "queued": queued,
                "processing": processing,
                "done": done,
                "failed": failed,
                "total": len(self._items)
            }

    def cancel(self) -> None:
        """Signals cancellation to all workers and marks the active item as Cancelled."""
        with self._lock:
            self._cancel_requested = True
            if self._current_item and self._current_item.status not in ["Done", "Failed"]:
                self._current_item.status = "Cancelled"
                self._notify_item_status(self._current_item)
            self._notify_updated()

    def reset_cancel(self) -> None:
        """Resets the cancellation flag."""
        with self._lock:
            self._cancel_requested = False

    def process_queue(
        self,
        process_video_fn: Callable[..., Optional[List[str]]],
        download_fn: Callable[..., Optional[str]],
        get_video_id_fn: Callable[[str], Optional[str]],
        logger: Optional[Callable[[str], None]] = None,
        on_item_complete: Optional[Callable[[QueueItem], None]] = None
    ) -> int:
        """
        Executes all queued items sequentially in the calling thread.
        
        Args:
            process_video_fn: Function to analyze and cut clips from a local video file.
            download_fn: Function to download a remote video via yt-dlp.
            get_video_id_fn: Function to resolve a URL into a video ID.
            logger: Callback for logging output.
            on_item_complete: Callback invoked when an item finishes successfully.
            
        Returns:
            Number of successfully processed items.
        """
        with self._lock:
            self._is_processing = True
            self._cancel_requested = False

        completed_count = 0
        try:
            while True:
                with self._lock:
                    if self._cancel_requested:
                        break
                    pending = self.get_pending_items()
                    if not pending:
                        break
                    item = pending[0]
                    self._current_item = item

                local_path: Optional[str] = None
                is_url = (
                    item.source.startswith("http://") or
                    item.source.startswith("https://") or
                    "twitch.tv" in item.source or
                    "youtu" in item.source
                )

                try:
                    if is_url:
                        self.update_item_status(item.id, "Downloading", 0.05)
                        if logger:
                            logger(f"🌐 [{item.id}] Downloading remote stream: {item.source}")

                        v_id = get_video_id_fn(item.source)
                        if not v_id:
                            self.update_item_status(item.id, "Failed", 0.0, error="Invalid Video ID")
                            if logger:
                                logger(f"❌ [{item.id}] Failed to resolve video ID for: {item.source}")
                            continue

                        if self._cancel_requested:
                            self.update_item_status(item.id, "Cancelled", 0.0)
                            break

                        local_path = download_fn(
                            item.source,
                            v_id,
                            logger_callback=logger,
                            force_manual=True,
                            is_cancelled=lambda: self._cancel_requested
                        )
                        if self._cancel_requested:
                            self.update_item_status(item.id, "Cancelled", 0.0)
                            break
                        if not local_path or not os.path.exists(local_path):
                            self.update_item_status(item.id, "Failed", 0.0, error="Download failed")
                            if logger:
                                logger(f"❌ [{item.id}] Download failed for: {item.source}")
                            continue
                    else:
                        local_path = item.source
                        if not os.path.exists(local_path):
                            self.update_item_status(item.id, "Failed", 0.0, error="File does not exist")
                            if logger:
                                logger(f"❌ [{item.id}] Local file not found: {local_path}")
                            continue

                    # Local file ready -> Begin extraction pipeline
                    self.update_item_status(item.id, "Transcribing", 0.15)
                    if logger:
                        logger(f"🎬 [{item.id}] Processing '{item.display_name}' with profile '{item.prompt_profile}' [{item.target_orientation}]")

                    def dynamic_item_logger(msg: str) -> None:
                        if logger:
                            logger(msg)
                        # Derive pipeline state from logger messages
                        lower = msg.lower()
                        if "transcrib" in lower or "vad" in lower or "audio" in lower:
                            self.update_item_status(item.id, "Transcribing", 0.3)
                        elif "gemini" in lower or "claude" in lower or "openai" in lower or "ai" in lower or "tokens" in lower:
                            self.update_item_status(item.id, "Analyzing AI", 0.6)
                        elif "ffmpeg" in lower or "clip" in lower or "render" in lower or "burn" in lower:
                            self.update_item_status(item.id, "Cutting Clips", 0.85)

                    created_clips = process_video_fn(
                        local_path,
                        prompt_profile=item.prompt_profile,
                        logger=dynamic_item_logger,
                        is_cancelled=lambda: self._cancel_requested,
                        target_orientation=item.target_orientation
                    )

                    with self._lock:
                        if self._cancel_requested:
                            self.update_item_status(item.id, "Cancelled", 0.0)
                            break
                        item.status = "Done"
                        item.progress = 1.0
                        item.created_clips = list(created_clips) if created_clips else []
                        self._notify_item_status(item)
                        completed_count += 1

                    if on_item_complete:
                        try:
                            on_item_complete(item)
                        except Exception:
                            pass

                except Exception as exc:
                    self.update_item_status(item.id, "Failed", 0.0, error=str(exc))
                    if logger:
                        logger(f"❌ [{item.id}] Error processing item: {exc}")

        finally:
            with self._lock:
                self._is_processing = False
                self._current_item = None
                self._notify_updated()

        return completed_count

    def _notify_updated(self) -> None:
        if self._event_bus:
            self._event_bus.publish(
                Event.QUEUE_UPDATED,
                items=self.get_items(),
                summary=self.get_summary()
            )

    def _notify_item_status(self, item: QueueItem) -> None:
        if self._event_bus:
            self._event_bus.publish(Event.QUEUE_ITEM_STATUS, item=item)
            self._event_bus.publish(
                Event.QUEUE_UPDATED,
                items=self.get_items(),
                summary=self.get_summary()
            )
