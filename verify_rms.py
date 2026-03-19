import numpy as np

def original_logic(chunk, peak_detection, combat_detection):
    prefix_tags = []

    loudness = 0
    if peak_detection:
        rms = np.sqrt(np.mean(chunk**2))
        loudness = min(100, int((rms / 0.1) * 100))
        prefix_tags.append(f"[LOUDNESS: {loudness}%]")

    if combat_detection and len(chunk) > 160: # At least 10ms
        window_size = 160
        num_windows = len(chunk) // window_size

        if num_windows > 0:
            transient_count = 0
            seg_rms = np.sqrt(np.mean(chunk**2)) + 0.001
            windows = chunk[:num_windows*window_size].reshape(-1, window_size)
            peaks = np.max(np.abs(windows), axis=1)
            transients = (peaks > (seg_rms * 4.5)) & (peaks > 0.15)
            transient_count = np.sum(transients)
            duration = 1.0 # mock
            if duration > 0 and (transient_count / duration) >= 1.5:
                prefix_tags.append("[ACTION: COMBAT]")
    return " ".join(prefix_tags)

def new_logic(chunk, peak_detection, combat_detection):
    prefix_tags = []

    loudness = 0
    rms = None
    if peak_detection or combat_detection:
        rms = np.sqrt(np.mean(chunk**2))

    if peak_detection:
        loudness = min(100, int((rms / 0.1) * 100))
        prefix_tags.append(f"[LOUDNESS: {loudness}%]")

    if combat_detection and len(chunk) > 160: # At least 10ms
        window_size = 160
        num_windows = len(chunk) // window_size

        if num_windows > 0:
            transient_count = 0
            seg_rms = rms + 0.001
            windows = chunk[:num_windows*window_size].reshape(-1, window_size)
            peaks = np.max(np.abs(windows), axis=1)
            transients = (peaks > (seg_rms * 4.5)) & (peaks > 0.15)
            transient_count = np.sum(transients)
            duration = 1.0 # mock
            if duration > 0 and (transient_count / duration) >= 1.5:
                prefix_tags.append("[ACTION: COMBAT]")
    return " ".join(prefix_tags)

if __name__ == "__main__":
    np.random.seed(42)
    # Generate some mock audio data
    chunk_normal = np.random.randn(200).astype(np.float32) * 0.05
    chunk_loud = np.random.randn(200).astype(np.float32) * 0.5
    chunk_transient = np.random.randn(200).astype(np.float32) * 0.05
    chunk_transient[10] = 1.0 # mock a spike
    chunk_transient[170] = 1.0

    chunks = [chunk_normal, chunk_loud, chunk_transient]

    for i, c in enumerate(chunks):
        for pd in [True, False]:
            for cd in [True, False]:
                orig = original_logic(c, pd, cd)
                new = new_logic(c, pd, cd)
                assert orig == new, f"Mismatch on chunk {i}, pd={pd}, cd={cd}: orig='{orig}', new='{new}'"

    print("All assertions passed!")
