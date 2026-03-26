import time
import io

# Current implementation in editor.py
def original_parse(raw_msg):
    clean_msg = raw_msg.split("]")[1].strip() if "]" in raw_msg else raw_msg
    timestamp = raw_msg.split("]")[0].replace("[", "").split("-->")[0].strip() if "-->" in raw_msg else ""
    return timestamp, clean_msg

# Proposed implementation: Partition
def optimized_partition(raw_msg):
    if "]" in raw_msg:
        t_part, _, clean_msg = raw_msg.partition("]")
        clean_msg = clean_msg.strip()
        timestamp = t_part.replace("[", "").partition("-->")[0].strip()
    else:
        clean_msg = raw_msg
        timestamp = raw_msg.partition("-->")[0].strip()
    return timestamp, clean_msg

# Benchmark
test_msg = "[00:00.000 --> 00:05.000] Hello world"
test_msg_no_bracket = "00:00.000 --> 00:05.000 Hello world"

def run_benchmark(func, iterations=1000000):
    start = time.time()
    for _ in range(iterations):
        func(test_msg)
        func(test_msg_no_bracket)
    return time.time() - start

if __name__ == "__main__":
    iterations = 500000
    t_orig = run_benchmark(original_parse, iterations)
    t_opt_part = run_benchmark(optimized_partition, iterations)

    print(f"Original: {t_orig:.4f}s")
    print(f"Opt Partition: {t_opt_part:.4f}s ({(t_orig - t_opt_part)/t_orig*100:.2f}% improvement)")

    # Verify correctness
    print(f"\nVerification for '{test_msg}':")
    print(f"Original:  {original_parse(test_msg)}")
    print(f"Opt Part: {optimized_partition(test_msg)}")

    print(f"\nVerification for '{test_msg_no_bracket}':")
    print(f"Original:  {original_parse(test_msg_no_bracket)}")
    print(f"Opt Part: {optimized_partition(test_msg_no_bracket)}")
