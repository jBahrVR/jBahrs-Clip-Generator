import os
import time
import threading
from typing import Optional, Tuple, Callable
from PIL import Image

try:
    import av
    HAS_AV = True
except ImportError:
    HAS_AV = False


class VideoDecoder:
    """
    High-performance, hardware-accelerated video stream decoder powered by PyAV (FFmpeg).
    Provides fast random-access seeking and sequential frame decoding.
    """

    def __init__(self, filepath: str):
        if not HAS_AV:
            raise RuntimeError("PyAV ('av') is not installed. Video decoding unavailable.")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Video file not found: {filepath}")

        self.filepath = filepath
        self.lock = threading.Lock()
        self.container = av.open(filepath)
        
        if not self.container.streams.video:
            self.container.close()
            raise ValueError(f"No video streams found in file: {filepath}")

        self.stream = self.container.streams.video[0]
        # Enable multi-threaded frame/slice decoding
        try:
            self.stream.codec_context.thread_type = 'AUTO'
        except Exception:
            pass

        self.width: int = self.stream.width or 1920
        self.height: int = self.stream.height or 1080
        self.aspect_ratio: float = self.width / max(1, self.height)

        # Determine frame rate
        if self.stream.average_rate and float(self.stream.average_rate) > 0:
            self.fps: float = float(self.stream.average_rate)
        elif self.stream.base_rate and float(self.stream.base_rate) > 0:
            self.fps = float(self.stream.base_rate)
        else:
            self.fps = 30.0

        # Determine duration
        if self.stream.duration and self.stream.time_base:
            self.duration: float = float(self.stream.duration * self.stream.time_base)
        elif self.container.duration:
            self.duration = float(self.container.duration / av.time.time_base)
        else:
            self.duration = 0.0

        self.time_base = self.stream.time_base
        self._decode_iterator = None
        self._current_time: float = 0.0
        self._closed: bool = False
        self._init_iterator()

    def _init_iterator(self):
        with self.lock:
            if self._closed:
                return
            self._decode_iterator = self.container.decode(self.stream)

    def read_next_frame(self) -> Optional[Tuple[float, Image.Image]]:
        """
        Sequentially reads the next frame from the stream.
        Returns a tuple of (timestamp_seconds, PIL.Image), or None at EOF.
        """
        with self.lock:
            if self._closed or not self._decode_iterator:
                return None
            try:
                frame = next(self._decode_iterator)
                if frame.pts is not None and self.time_base:
                    self._current_time = float(frame.pts * self.time_base)
                else:
                    self._current_time += (1.0 / self.fps)
                return self._current_time, frame.to_image()
            except (StopIteration, av.FFmpegError, Exception):
                return None

    def seek_to(self, timestamp_sec: float) -> Optional[Tuple[float, Image.Image]]:
        """
        Seeks to the nearest keyframe preceding timestamp_sec and decodes forward
        until reaching the exact target frame.
        """
        with self.lock:
            if self._closed:
                return None

            timestamp_sec = max(0.0, min(timestamp_sec, max(0.0, self.duration - 0.01)))
            target_pts = int(timestamp_sec / self.time_base) if self.time_base else 0

            try:
                self.container.seek(target_pts, stream=self.stream, backward=True)
                self._decode_iterator = self.container.decode(self.stream)

                best_frame = None
                best_time = 0.0

                for frame in self._decode_iterator:
                    if frame.pts is not None and self.time_base:
                        cur_t = float(frame.pts * self.time_base)
                    else:
                        cur_t = best_time + (1.0 / self.fps)

                    best_frame = frame
                    best_time = cur_t

                    if cur_t >= timestamp_sec:
                        break

                if best_frame:
                    self._current_time = best_time
                    return best_time, best_frame.to_image()
                return None
            except Exception:
                return None

    def close(self):
        """Closes the underlying container and frees decoding resources."""
        with self.lock:
            if not self._closed:
                self._closed = True
                self._decode_iterator = None
                try:
                    self.container.close()
                except Exception:
                    pass

    @property
    def current_time(self) -> float:
        return self._current_time

    @property
    def is_closed(self) -> bool:
        return self._closed


class DualVideoSyncController:
    """
    Coordinates synchronized playback, real-time scrubbing, and frame extraction
    for a primary video and an optional companion video (e.g. 16:9 and 9:16 vertical cuts).
    """

    def __init__(
        self,
        primary_path: str,
        companion_path: Optional[str] = None,
        on_frame: Optional[Callable[[float, Image.Image, Optional[Image.Image]], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None
    ):
        self.primary_path = primary_path
        self.companion_path = companion_path
        self.on_frame = on_frame
        self.on_state_change = on_state_change

        self.primary_decoder: Optional[VideoDecoder] = VideoDecoder(primary_path)
        self.companion_decoder: Optional[VideoDecoder] = None
        if companion_path and os.path.exists(companion_path):
            try:
                self.companion_decoder = VideoDecoder(companion_path)
            except Exception:
                self.companion_decoder = None

        self.duration: float = self.primary_decoder.duration
        if self.companion_decoder and self.companion_decoder.duration > self.duration:
            self.duration = self.companion_decoder.duration

        self.fps: float = self.primary_decoder.fps
        self.current_time: float = 0.0
        self.is_playing: bool = False
        self.loop: bool = True

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def play(self):
        """Starts real-time synchronized playback."""
        with self._lock:
            if self.is_playing:
                return
            self.is_playing = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._thread.start()

        if self.on_state_change:
            self.on_state_change("playing")

    def pause(self):
        """Pauses synchronized playback."""
        with self._lock:
            if not self.is_playing:
                return
            self.is_playing = False
            self._stop_event.set()

        if self.on_state_change:
            self.on_state_change("paused")

    def toggle_play(self):
        """Toggles between play and pause states."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        """Stops playback and rewinds to beginning."""
        self.pause()
        self.seek(0.0)
        if self.on_state_change:
            self.on_state_change("stopped")

    def seek(self, timestamp_sec: float) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
        """
        Seeks both primary and companion decoders to the requested timestamp.
        Dispatches updated frames immediately.
        """
        timestamp_sec = max(0.0, min(timestamp_sec, self.duration))
        self.current_time = timestamp_sec

        prim_img = None
        comp_img = None

        if self.primary_decoder and not self.primary_decoder.is_closed:
            res = self.primary_decoder.seek_to(timestamp_sec)
            if res:
                prim_img = res[1]

        if self.companion_decoder and not self.companion_decoder.is_closed:
            res = self.companion_decoder.seek_to(timestamp_sec)
            if res:
                comp_img = res[1]

        if self.on_frame and prim_img:
            self.on_frame(self.current_time, prim_img, comp_img)

        return prim_img, comp_img

    def step(self, delta_sec: float):
        """Steps forward or backward by delta_sec."""
        target = self.current_time + delta_sec
        if target > self.duration:
            target = 0.0 if self.loop else self.duration
        elif target < 0.0:
            target = 0.0
        self.seek(target)

    def _playback_loop(self):
        frame_interval = 1.0 / max(1.0, self.fps)
        next_frame_time = time.perf_counter()

        while not self._stop_event.is_set():
            loop_start = time.perf_counter()

            # Read frames from decoders
            prim_res = self.primary_decoder.read_next_frame() if self.primary_decoder else None
            comp_res = self.companion_decoder.read_next_frame() if self.companion_decoder else None

            if prim_res is None:
                # End of primary stream reached
                if self.loop:
                    self.seek(0.0)
                    next_frame_time = time.perf_counter()
                    continue
                else:
                    self.pause()
                    break

            t_sec, prim_img = prim_res
            self.current_time = t_sec
            comp_img = comp_res[1] if comp_res else None

            if self.on_frame:
                self.on_frame(self.current_time, prim_img, comp_img)

            # Precise clock regulation
            next_frame_time += frame_interval
            sleep_duration = next_frame_time - time.perf_counter()
            if sleep_duration > 0.001:
                time.sleep(sleep_duration)
            elif sleep_duration < -frame_interval:
                # Frame drop / catch up clock
                next_frame_time = time.perf_counter()

    def close(self):
        """Stops playback threads and releases both decoders."""
        self.pause()
        if self.primary_decoder:
            self.primary_decoder.close()
            self.primary_decoder = None
        if self.companion_decoder:
            self.companion_decoder.close()
            self.companion_decoder = None
