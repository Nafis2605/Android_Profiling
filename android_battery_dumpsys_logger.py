#!/usr/bin/env python3
import subprocess, csv, time, datetime as dt, re, sys, argparse, shlex

def sh(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(err or f"cmd failed: {' '.join(cmd)}")
    return out

def adb_shell(cmd):
    return sh(["adb", "shell", cmd]).strip()

def parse_dumpsys_battery():
    """
    Returns dict with keys:
      current_mA (int or None)
      voltage_mV (int or None)
      temperature_dC (int or None)  # tenths of °C if present
    Works across variants: 'current now', 'Current', 'voltage', 'Voltage' etc.
    """
    out = adb_shell("dumpsys battery")
    cur = None; volt = None; temp = None
    for line in out.splitlines():
        # current in mA (may be negative)
        if re.search(r'\bcurrent\b', line, re.I) and re.search(r'\bnow\b|\bcurrent\b', line, re.I):
            m = re.search(r'(-?\d+)', line)
            if m: cur = int(m.group(1))
        # voltage in mV
        if re.search(r'\bvoltage\b', line, re.I):
            m = re.search(r'(\d+)', line)
            if m: volt = int(m.group(1))
        # temperature (often in tenths of °C)
        if re.search(r'\btemp', line, re.I):
            m = re.search(r'(-?\d+)', line)
            if m: temp = int(m.group(1))
    return {"current_mA": cur, "voltage_mV": volt, "temperature_dC": temp}

# ---- CPU util (delta from /proc/stat) ----
_prev_cpu = None
def read_proc_stat():
    try:
        txt = adb_shell("cat /proc/stat | head -n 1")
        parts = txt.split()
        if parts[0] != "cpu": return None
        return list(map(int, parts[1:]))
    except Exception:
        return None

def cpu_total_util_percent():
    global _prev_cpu
    cur = read_proc_stat()
    if cur is None:
        return None
    if _prev_cpu is None:
        _prev_cpu = cur
        return None
    prev = _prev_cpu
    _prev_cpu = cur
    idle = cur[3] + cur[4]
    prev_idle = prev[3] + prev[4]
    total = sum(cur)
    prev_total = sum(prev)
    dtot = total - prev_total
    didle = idle - prev_idle
    if dtot <= 0:
        return None
    return (dtot - didle) / dtot * 100.0

def list_cpu_cores():
    try:
        n = int(adb_shell("ls -d /sys/devices/system/cpu/cpu[0-9]* 2>/dev/null | wc -l"))
        return list(range(n))
    except Exception:
        return []

def read_cpu_freq_khz(cpu_idx):
    for p in (
        f"/sys/devices/system/cpu/cpu{cpu_idx}/cpufreq/scaling_cur_freq",
        f"/sys/devices/system/cpu/cpu{cpu_idx}/cpufreq/cpuinfo_cur_freq",
    ):
        try:
            val = adb_shell(f"cat {shlex.quote(p)}")
            m = re.search(r'(\d+)', val)
            if m: return int(m.group(1))
        except Exception:
            pass
    return None

# ---- GPU (kgsl/Mali best-effort) ----
def read_gpu_info():
    # Qualcomm KGSL
    kgsl_busy = "/sys/class/kgsl/kgsl-3d0/gpubusy"
    kgsl_freq = "/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq"
    try:
        out = adb_shell(f"[ -e {kgsl_busy} ] && cat {kgsl_busy} || echo ''")
        if out:
            util = None
            nums = list(map(int, re.findall(r"\d+", out)))
            if len(nums) >= 2 and nums[1] > 0:
                util = nums[0] / nums[1] * 100.0
            freq = None
            f = adb_shell(f"[ -e {kgsl_freq} ] && cat {kgsl_freq} || echo ''")
            if f:
                m = re.search(r'(\d+)', f)
                if m: freq = int(m.group(1))
            return {"backend": "kgsl", "util_percent": util, "freq_hz": freq}
    except Exception:
        pass

    # Mali fallbacks
    util = None; freq = None
    try:
        out = adb_shell('for f in /sys/class/devfreq/*gpu*/utilization /sys/devices/platform/*/mali/utilization; do [ -e "$f" ] && cat "$f"; done | head -n 1')
        if out:
            m = re.findall(r'(\d+)', out)
            if m: util = float(m[0])
    except Exception:
        pass
    try:
        out = adb_shell('for f in /sys/class/devfreq/*gpu*/cur_freq /sys/devices/platform/*/mali/devfreq/devfreq*/cur_freq; do [ -e "$f" ] && cat "$f"; done | head -n 1')
        if out:
            m = re.search(r'(\d+)', out)
            if m: freq = int(m.group(1))
    except Exception:
        pass
    backend = "mali" if (util is not None or freq is not None) else None
    return {"backend": backend, "util_percent": util, "freq_hz": freq}

def main():
    ap = argparse.ArgumentParser(description="Log device power via dumpsys battery + CPU/GPU metrics")
    ap.add_argument("--out", default="power_dumpsys_log.csv")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=0.0, help="0 = until Ctrl+C")
    args = ap.parse_args()

    # Check device
    try:
        if sh(["adb", "get-state"]).strip() != "device":
            print("ADB device not connected/authorized.", file=sys.stderr); sys.exit(1)
    except Exception:
        print("ADB not available.", file=sys.stderr); sys.exit(1)

    cores = list_cpu_cores()
    headers = ["timestamp","battery_current_mA","battery_voltage_mV","device_power_mW","battery_temp_C","cpu_total_util_percent"]
    for c in cores: headers.append(f"cpu{c}_freq_kHz")
    headers += ["gpu_backend","gpu_util_percent","gpu_freq_Hz"]

    print(f"Logging to {args.out}")
    with open(args.out, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(headers)

        _ = cpu_total_util_percent()  # prime /proc/stat delta
        t0 = time.time()
        while True:
            ts = dt.datetime.now().isoformat(timespec="seconds")

            # Battery via dumpsys
            b = parse_dumpsys_battery()
            cur_mA = b["current_mA"]; volt_mV = b["voltage_mV"]; temp_dC = b["temperature_dC"]
            power_mW = None
            if cur_mA is not None and volt_mV is not None:
                power_mW = abs(cur_mA) * (volt_mV / 1000.0)  # mA * V

            # CPU
            cpu_util = cpu_total_util_percent()
            freqs = [read_cpu_freq_khz(c) for c in cores]

            # GPU
            gpu = read_gpu_info()

            row = [
                ts,
                "" if cur_mA is None else cur_mA,
                "" if volt_mV is None else volt_mV,
                "" if power_mW is None else f"{power_mW:.1f}",
                "" if temp_dC is None else f"{temp_dC/10.0:.1f}",
                "" if cpu_util is None else f"{cpu_util:.1f}",
            ]
            row += [("" if v is None else v) for v in freqs]
            row += [
                "" if not gpu.get("backend") else gpu["backend"],
                "" if gpu.get("util_percent") is None else f"{gpu['util_percent']:.1f}",
                "" if gpu.get("freq_hz") is None else gpu["freq_hz"],
            ]
            wr.writerow(row); f.flush()

            if args.duration > 0 and (time.time() - t0) >= args.duration:
                break
            time.sleep(max(0.0, args.interval))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
