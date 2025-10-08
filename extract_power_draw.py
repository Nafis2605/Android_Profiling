#!/usr/bin/env python3
import csv, json, math, pathlib

IN_CSV  = "power_dumpsys_log.csv"
OUT_JSON = "power_draw.json"

def parse_float(s):
    try:
        return float(s)
    except Exception:
        return math.nan

values = []
with open(IN_CSV, newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        raw_i = parse_float(row.get("battery_current_mA", "nan"))
        raw_v = parse_float(row.get("battery_voltage_mV", "nan"))

        V = raw_v / 1000.0 if math.isfinite(raw_v) else float("nan")

        # auto-detect units
        if math.isfinite(raw_i):
            if raw_i > 10000:     # treat as µA
                I = raw_i / 1_000_000.0
            else:                 # treat as mA
                I = raw_i / 1000.0
        else:
            I = float("nan")

        if math.isfinite(I) and math.isfinite(V):
            power_W = round(I * V, 3)
            values.append(power_W)

out = {"power_draw": values}

with open(OUT_JSON, "w") as f:
    json.dump(out, f, indent=2)

print(f"Wrote {OUT_JSON} with {len(values)} entries at {pathlib.Path(OUT_JSON).resolve()}")
