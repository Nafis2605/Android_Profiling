#!/usr/bin/env python3
import re
import json

def extract_gpu_memory(input_file, output_file):
    gpu_memories = []

    # Regex to capture floating-point numbers before "MB"
    pattern = re.compile(r"Global GPU memory:\s+([\d\.]+)\s+MB")

    with open(input_file, "r") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                value = float(match.group(1))
                gpu_memories.append(value)

    # Wrap in dictionary as requested
    data = {"memory_utilization": gpu_memories}

    # Save JSON
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    extract_gpu_memory("memory.txt", "memory_util.json")
