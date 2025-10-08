#!/usr/bin/env python3
import subprocess
import time
import re

def adb_shell(cmd):
    return subprocess.check_output(["adb", "shell"] + cmd, text=True)

def get_gpu_snapshot():
    try:
        out = adb_shell(["dumpsys", "gpu"])
    except subprocess.CalledProcessError:
        return None
    
    gpu_data = []
    total_global = 0

    # Parse global total
    match = re.search(r"Global total:\s+(\d+)", out)
    if match:
        total_global = int(match.group(1))

    # Parse per-process lines
    for pid, mem in re.findall(r"Proc\s+(\d+)\s+total:\s+(\d+)", out):
        gpu_data.append((int(pid), int(mem)))

    return total_global, gpu_data

def get_process_names():
    out = adb_shell(["ps", "-A", "-o", "pid,name"])
    mapping = {}
    for line in out.splitlines()[1:]:
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            pid, name = parts
            mapping[int(pid)] = name
    return mapping

def format_size(bytes_val):
    if bytes_val > 1024*1024:
        return f"{bytes_val/1024/1024:.1f} MB"
    elif bytes_val > 1024:
        return f"{bytes_val/1024:.1f} KB"
    else:
        return f"{bytes_val} B"

def main(interval=2):
    while True:
        snapshot = get_gpu_snapshot()
        if not snapshot:
            print("Could not read GPU snapshot. Is `dumpsys gpu` supported on this device?")
            return

        total, gpu_data = snapshot
        proc_names = get_process_names()

        print("="*60)
        print(f"Global GPU memory: {format_size(total)}")
        print(f"{'PID':>6} {'Memory':>10}  Process")
        print("-"*60)

        for pid, mem in sorted(gpu_data, key=lambda x: -x[1]):
            name = proc_names.get(pid, "?")
            print(f"{pid:>6} {format_size(mem):>10}  {name}")

        time.sleep(interval)

if __name__ == "__main__":
    main()

