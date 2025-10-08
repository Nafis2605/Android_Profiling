# Android GPU & Battery Monitoring Scripts

This repository contains Python scripts for monitoring GPU and battery metrics on Android devices via ADB, and for post-processing the collected logs.

---

## Files Overview

### **gpu-monitor.py**
This script connects to an Android device via `adb` and repeatedly queries `dumpsys gpu` to capture GPU memory usage.  
It displays the global GPU memory consumption and per-process breakdown (PID, memory usage, and process names) in a readable table.

### **android_battery_dumpsys_logger.py**
This script connects to an Android device over ADB and continuously logs system metrics using `dumpsys battery`, CPU stats, and GPU queries.  
It saves timestamped data such as battery current, voltage, temperature, power draw, CPU utilization/frequencies, and GPU usage/frequency into a CSV file.

### **extract_gpu_utilization.py**
This script reads `power_dumpsys_log.csv` and extracts GPU utilization percentages (`gpu_util_percent`) from each row.  
It saves these values in a JSON file (`gpu_util.json`) under the key `"gpu_utilization"`.

### **extract_memory.py**
This script parses text logs for global GPU memory usage values (in MB).  
It extracts the numeric values and stores them in a JSON file under the key `"memory_utilization"`.

### **extract_power_draw.py**
This script computes power draw in watts from battery current and voltage values found in `power_dumpsys_log.csv`.  
It outputs the results into a JSON file (`power_draw.json`) under the key `"power_draw"`.

---

## How to Run

Follow these steps to start logging GPU and battery metrics:

1. **Run GPU Monitor (logs GPU usage into `gpu_log.csv`):**
   ```bash
   python3 gpu-monitor.py --device adb --interval 1 --output gpu_log.csv

2. **Run Battery + CPU/GPU Logger (logs into `power_dumpsys_log.csv`):**
   ```bash
   ./android_battery_dumpsys_logger.py --out power_dumpsys_log.csv --interval 1

3. **After logging, run the extract scripts to process results (optional):**
   ```bash
   python3 extract_gpu_utilization.py
   python3 extract_memory.py
   python3 extract_power_draw.py
