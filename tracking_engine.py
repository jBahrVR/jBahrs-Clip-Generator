import os
from typing import Optional, Tuple, List
import numpy as np
import cv2

try:
    import av
    HAS_AV = True
except ImportError:
    HAS_AV = False


class TrajectorySmoother:
    """
    Exponential Moving Average (EMA) filter with deadband margin.
    Smooths camera coordinates and eliminates micro-jitter from head twitches or noise.
    """

    def __init__(self, alpha: float = 0.35, deadband_px: float = 25.0):
        self.alpha = max(0.01, min(1.0, alpha))
        self.deadband_px = max(0.0, deadband_px)
        self.current_val: Optional[float] = None

    def update(self, new_val: float) -> float:
        if self.current_val is None:
            self.current_val = float(new_val)
            return self.current_val

        # Deadband rejection: ignore tiny movements within threshold
        diff = abs(new_val - self.current_val)
        if diff < self.deadband_px:
            return self.current_val

        # Exponential moving average filter
        self.current_val = self.alpha * new_val + (1.0 - self.alpha) * self.current_val
        return self.current_val

    def reset(self):
        self.current_val = None


class FaceTracker:
    """
    Detects streamer face and webcam region of interest using chromatic YCrCb
    skin-tone distribution, facial geometry contours, and motion cues.
    """

    def detect_face_candidate(self, frame_bgr: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Analyzes a BGR frame and returns the bounding box (x, y, w, h) of the most prominent
        face or streamer webcam candidate, or None if no face is detected.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return None

        h, w = frame_bgr.shape[:2]
        total_area = float(w * h)

        # Convert to YCrCb for robust illumination-invariant skin segmentation
        ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
        # Universal chromatic skin thresholds: Cr in [133, 173], Cb in [77, 127]
        skin_mask = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))

        # Morphological open to remove noise, close to merge facial components
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        best_candidate = None
        max_score = 0.0

        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            area_ratio = area / total_area

            # A webcam/face typically occupies between 0.5% and 25% of the total 16:9 canvas
            if area_ratio < 0.005 or area_ratio > 0.25:
                continue

            aspect_ratio = float(bw) / max(1, bh)
            # Human face/head aspect ratio typically ranges from 0.65 to 1.35
            if aspect_ratio < 0.5 or aspect_ratio > 1.6:
                continue

            # Prioritize candidate: area weight + preference for upper half of frame (standard webcam placement)
            upper_bonus = 1.3 if (by + bh / 2) < (h * 0.7) else 1.0
            score = area * upper_bonus

            if score > max_score:
                max_score = score
                best_candidate = (bx, by, bw, bh)

        return best_candidate


class ActionTracker:
    """
    Detects the primary horizontal focus of gameplay action using temporal frame
    differencing and spatial contrast energy centroids.
    """

    def __init__(self):
        self.prev_gray: Optional[np.ndarray] = None

    def detect_action_centroid(self, frame_bgr: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Computes the (centroid_x, centroid_y) of motion between successive frames.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return None

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 0)

        if self.prev_gray is None or self.prev_gray.shape != gray.shape:
            self.prev_gray = gray
            return None

        diff = cv2.absdiff(self.prev_gray, gray)
        self.prev_gray = gray

        # Threshold significant movement
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        moments = cv2.moments(thresh)

        if moments["m00"] < 500:
            return None

        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
        return cx, cy

    def reset(self):
        self.prev_gray = None


def sample_frames_from_video(
    video_path: str,
    start_time: float,
    end_time: float,
    sample_fps: float = 2.0
) -> List[Tuple[float, np.ndarray]]:
    """
    Samples frames across [start_time, end_time] at approximately sample_fps.
    Returns list of (timestamp_sec, bgr_image_array).
    """
    samples = []
    if not os.path.exists(video_path):
        return samples

    if HAS_AV:
        try:
            container = av.open(video_path)
            if not container.streams.video:
                container.close()
                return samples

            stream = container.streams.video[0]
            time_base = stream.time_base or av.time.time_base

            # Seek to keyframe before start_time
            target_pts = int(start_time / time_base) if time_base else 0
            container.seek(target_pts, stream=stream, backward=True)

            step_sec = 1.0 / max(0.5, sample_fps)
            next_target = start_time

            for frame in container.decode(stream):
                cur_t = float(frame.pts * time_base) if frame.pts is not None and time_base else 0.0
                if cur_t < start_time:
                    continue
                if cur_t > end_time:
                    break

                if cur_t >= next_target:
                    # Convert to BGR for OpenCV
                    img = frame.to_ndarray(format="bgr24")
                    samples.append((cur_t, img))
                    next_target = cur_t + step_sec

            container.close()
            return samples
        except Exception:
            pass

    # Fallback to cv2.VideoCapture
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000.0)

        step_frames = int(max(1, fps / sample_fps))
        frame_idx = int(start_time * fps)
        end_frame_idx = int(end_time * fps)

        while cap.isOpened() and frame_idx <= end_frame_idx:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            cur_sec = frame_idx / fps
            samples.append((cur_sec, frame))
            for _ in range(step_frames - 1):
                cap.grab()
            frame_idx += step_frames

        cap.release()
    except Exception:
        pass

    return samples


def calculate_optimal_crop_window(
    video_path: str,
    start_time: float,
    end_time: float,
    mode: str = "face",
    sample_fps: float = 2.0,
    video_width: int = 1920,
    video_height: int = 1080
) -> Tuple[int, int, int, int]:
    """
    Computes an optimal 9:16 vertical crop window (x, y, w, h) based on AI face detection
    or action motion tracking.
    Guarantees coordinates are safely clamped within the video dimensions.
    If no face/motion is detected, gracefully falls back to the centered crop.
    """
    # 9:16 target width given the source height
    crop_h = video_height
    crop_w = int(video_height * 9 / 16)
    # Ensure even width for FFmpeg encoder constraints
    if crop_w % 2 != 0:
        crop_w -= 1

    max_x = max(0, video_width - crop_w)
    center_fallback_x = max_x // 2

    samples = sample_frames_from_video(video_path, start_time, end_time, sample_fps=sample_fps)
    if not samples:
        return center_fallback_x, 0, crop_w, crop_h

    detected_centers = []
    smoother = TrajectorySmoother(alpha=0.35, deadband_px=25.0)

    if mode == "face":
        tracker = FaceTracker()
        for _, frame in samples:
            face_box = tracker.detect_face_candidate(frame)
            if face_box:
                fx, fy, fw, fh = face_box
                face_center_x = fx + fw / 2.0
                detected_centers.append(face_center_x)
    elif mode == "action":
        tracker = ActionTracker()
        for _, frame in samples:
            action_pt = tracker.detect_action_centroid(frame)
            if action_pt:
                detected_centers.append(action_pt[0])

    if not detected_centers:
        # No target found; return standard center crop
        return center_fallback_x, 0, crop_w, crop_h

    # Compute smoothed focal center
    smoothed_center = center_fallback_x + (crop_w / 2.0)
    for c in detected_centers:
        smoothed_center = smoother.update(c)

    # Convert focal center to top-left crop coordinate
    target_crop_x = int(round(smoothed_center - (crop_w / 2.0)))
    target_crop_x = max(0, min(max_x, target_crop_x))

    return target_crop_x, 0, crop_w, crop_h
