import numpy as np
import time

# Mock 1 hour of audio (16kHz, 16-bit)
# 16000 samples/sec * 3600 sec = 57,600,000 samples
# 2 bytes/sample = 115.2 MB buffer
mock_stdout = np.random.randint(-32768, 32767, size=16000*3600, dtype=np.int16).tobytes()

def original_extract(stdout):
    return np.frombuffer(stdout, np.int16).flatten().astype(np.float32) / 32768.0

def optimized_extract(stdout):
    arr = np.frombuffer(stdout, np.int16).astype(np.float32)
    arr /= 32768.0
    return arr

# Warmup
original_extract(mock_stdout)
optimized_extract(mock_stdout)

t0 = time.time()
for _ in range(10):
    original_extract(mock_stdout)
t1 = time.time()

t2 = time.time()
for _ in range(10):
    optimized_extract(mock_stdout)
t3 = time.time()

orig_time = t1 - t0
opt_time = t3 - t2
print(f"Original: {orig_time:.4f}s")
print(f"Optimized: {opt_time:.4f}s")
print(f"Improvement: {(orig_time - opt_time) / orig_time * 100:.2f}%")

# Memory difference
import sys
import tracemalloc

tracemalloc.start()
original_extract(mock_stdout)
current, peak1 = tracemalloc.get_traced_memory()
tracemalloc.stop()

tracemalloc.start()
optimized_extract(mock_stdout)
current, peak2 = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Peak memory Original: {peak1 / 10**6:.2f} MB")
print(f"Peak memory Optimized: {peak2 / 10**6:.2f} MB")
