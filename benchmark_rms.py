import numpy as np
import time

def analyze_audio_peaks_original(audio_array, segments, sample_rate=16000, peak_detection=True, combat_detection=True):
    enhanced_segments = []
    for seg in segments:
        start_idx = int(seg['start'] * sample_rate)
        end_idx = int(seg['end'] * sample_rate)
        start_idx = max(0, min(start_idx, len(audio_array) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(audio_array)))
        chunk = audio_array[start_idx:end_idx]
        if len(chunk) == 0:
            enhanced_segments.append(seg)
            continue
        prefix_tags = []
        loudness = 0
        if peak_detection:
            rms = np.sqrt(np.mean(chunk**2))
            loudness = min(100, int((rms / 0.1) * 100))
            prefix_tags.append(f"[LOUDNESS: {loudness}%]")
        if combat_detection and len(chunk) > 160:
            window_size = 160
            num_windows = len(chunk) // window_size
            if num_windows > 0:
                transient_count = 0
                seg_rms = np.sqrt(np.mean(chunk**2)) + 0.001
                windows = chunk[:num_windows*window_size].reshape(-1, window_size)
                peaks = np.max(np.abs(windows), axis=1)
                transients = (peaks > (seg_rms * 4.5)) & (peaks > 0.15)
                transient_count = np.sum(transients)
                duration = seg['end'] - seg['start']
                if duration > 0 and (transient_count / duration) >= 1.5:
                    prefix_tags.append("[ACTION: COMBAT]")
        tag_str = " ".join(prefix_tags)
        enhanced_text = f"{tag_str} {seg['text'].strip()}" if tag_str else seg['text'].strip()
        new_seg = seg.copy()
        new_seg['text'] = enhanced_text
        enhanced_segments.append(new_seg)
    return enhanced_segments

def analyze_audio_peaks_optimized(audio_array, segments, sample_rate=16000, peak_detection=True, combat_detection=True):
    enhanced_segments = []
    for seg in segments:
        start_idx = int(seg['start'] * sample_rate)
        end_idx = int(seg['end'] * sample_rate)
        start_idx = max(0, min(start_idx, len(audio_array) - 1))
        end_idx = max(start_idx + 1, min(end_idx, len(audio_array)))
        chunk = audio_array[start_idx:end_idx]
        if len(chunk) == 0:
            enhanced_segments.append(seg)
            continue
        prefix_tags = []

        rms = 0.0
        if peak_detection or combat_detection:
            rms = float(np.sqrt(np.mean(chunk**2)))

        loudness = 0
        if peak_detection:
            loudness = min(100, int((rms / 0.1) * 100))
            prefix_tags.append(f"[LOUDNESS: {loudness}%]")

        if combat_detection and len(chunk) > 160:
            window_size = 160
            num_windows = len(chunk) // window_size
            if num_windows > 0:
                transient_count = 0
                seg_rms = rms + 0.001
                windows = chunk[:num_windows*window_size].reshape(-1, window_size)
                peaks = np.max(np.abs(windows), axis=1)
                transients = (peaks > (seg_rms * 4.5)) & (peaks > 0.15)
                transient_count = np.sum(transients)
                duration = seg['end'] - seg['start']
                if duration > 0 and (transient_count / duration) >= 1.5:
                    prefix_tags.append("[ACTION: COMBAT]")
        tag_str = " ".join(prefix_tags)
        enhanced_text = f"{tag_str} {seg['text'].strip()}" if tag_str else seg['text'].strip()
        new_seg = seg.copy()
        new_seg['text'] = enhanced_text
        enhanced_segments.append(new_seg)
    return enhanced_segments

if __name__ == "__main__":
    np.random.seed(42)
    sample_rate = 16000
    duration_sec = 3600 # 1 hour
    audio_array = np.random.randn(sample_rate * duration_sec).astype(np.float32)

    segments = [{'start': i, 'end': i+1, 'text': 'test'} for i in range(duration_sec)]

    for _ in range(5):
        t0 = time.time()
        analyze_audio_peaks_original(audio_array, segments)
        t1 = time.time()

        t2 = time.time()
        analyze_audio_peaks_optimized(audio_array, segments)
        t3 = time.time()
        print(f"Original: {t1 - t0:.4f}s | Optimized: {t3 - t2:.4f}s")
