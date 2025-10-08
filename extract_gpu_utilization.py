#!/usr/bin/env python3
import csv, json, os

INPUT = "power_dumpsys_log.csv"
OUTPUT = "gpu_util.json"

def main():
    values = []
    with open(INPUT, newline="") as f:
        for row in csv.DictReader(f):
            val = (row.get("gpu_util_percent") or "").strip()
            if val != "":
                try:
                    values.append(float(val))
                except ValueError:
                    continue

    payload = {"gpu_utilization": values}
    with open(OUTPUT, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"✅ Wrote {OUTPUT} with {len(values)} values")

if __name__ == "__main__":
    main()
