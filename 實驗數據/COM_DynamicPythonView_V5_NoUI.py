import serial
import math
import time
import os
import csv
from datetime import datetime
import numpy as np
import threading
import queue
import msvcrt  # Built-in Windows library for background key presses

# ==========================================
# CONFIGURATION
# ==========================================
COM_PORTS = ['COM10', 'COM11'] 
BAUD_RATE = 921600        

CALIBRATION_TIME_SEC = 5.0  

RIGHT_LEG = ["R_Hip", "R_Shank", "R_Ankle"]
LEFT_LEG = ["L_Hip", "L_Shank", "L_Ankle"]
SENSOR_NAMES = RIGHT_LEG + LEFT_LEG

LOG_ENABLED = True          
LOG_DIRECTORY = "."         

# ==========================================
# DATA STORAGE & STATE
# ==========================================
first_hw_timestamp = {name: None for name in SENSOR_NAMES}

# Baseline Calibration Memory
baseline_computed = {name: False for name in SENSOR_NAMES}
baseline_offsets = {name: {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0} for name in SENSOR_NAMES}
calibration_data = {name: {'roll': [], 'pitch': [], 'yaw': []} for name in SENSOR_NAMES}

# Diagnostic Tracking
stats_lock = threading.Lock()
hz_counters = {name: 0 for name in SENSOR_NAMES}
current_hz = {name: 0.0 for name in SENSOR_NAMES}

running = True
is_paused = False  

# ==========================================
# FAST CSV LOGGING THREAD (All 6 Devices)
# ==========================================
log_queue = queue.Queue()

def csv_writer_worker():
    if not LOG_ENABLED: return
        
    now = datetime.now()
    csv_filename = os.path.join(LOG_DIRECTORY, f"{now.strftime('%Y%m%d_%H%M%S')}_Headless_FullBody.csv")
    print(f"💾 Opening Master CSV log file: {csv_filename}")
    
    headers = [
        'python_time', 'esp32_hw_time', 'sensor_name', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz', 
        'q0', 'q1', 'q2', 'q3', 'quat_roll', 'quat_pitch', 'quat_yaw', 'is_paused_flag'
    ]
    
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        
        while running or not log_queue.empty():
            try:
                row_data = log_queue.get(timeout=1.0)
                (py_ts, hw_ts, name, ax, ay, az, gx, gy, gz, mx, my, mz, q, r, p, y, paused) = row_data
                row = [
                    py_ts, hw_ts, name, 
                    round(ax,4), round(ay,4), round(az,4), 
                    round(gx,2), round(gy,2), round(gz,2), 
                    round(mx,2), round(my,2), round(mz,2), 
                    round(q[0],6), round(q[1],6), round(q[2],6), round(q[3],6), 
                    round(r,2), round(p,2), round(y,2), 
                    1 if paused else 0
                ]
                writer.writerow(row)
                
                # Flush to disk safely when queue is empty
                if log_queue.qsize() == 0:
                    file.flush() 
                    
            except queue.Empty:
                pass
                
    print("\n✅ Master CSV file closed and saved successfully.")

# ==========================================
# BACKGROUND KEYBOARD LISTENER (Spacebar)
# ==========================================
def keyboard_listener():
    global is_paused, running
    while running:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b' ':
                is_paused = not is_paused
        time.sleep(0.05)

# ==========================================
# SERIAL READER THREAD
# ==========================================
def read_serial(com_port):
    global running, is_paused
    ser = None
    
    last_raw_esp_ts = {name: 0 for name in SENSOR_NAMES}
    shift_accumulator = {name: 0 for name in SENSOR_NAMES}
    
    try:
        ser = serial.Serial()
        ser.port = com_port
        ser.baudrate = BAUD_RATE
        ser.timeout = 0.5
        ser.setDTR(False)
        ser.setRTS(False)
        ser.open()
        
        while running:
            # Drain buffer as fast as possible without UI locks
            while ser.in_waiting > 0 and running:
                try:
                    line_bytes = ser.readline()
                    if not line_bytes: continue
                    
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                    if not line or ',' not in line: continue
                    
                    parts = line.split(',')
                    if len(parts) != 16: continue 
                    
                    device_name = parts[0]
                    if device_name not in SENSOR_NAMES: continue
                    
                    raw_esp32_ts = int(parts[1])
                    
                    # 10ms Batch Shifter
                    if raw_esp32_ts == last_raw_esp_ts[device_name]:
                        shift_accumulator[device_name] += 10 
                    else:
                        shift_accumulator[device_name] = 0   
                        
                    last_raw_esp_ts[device_name] = raw_esp32_ts
                    adjusted_esp32_ts = raw_esp32_ts + shift_accumulator[device_name]

                    # Time tracking for the 5-second calibration phase
                    if first_hw_timestamp[device_name] is None:
                        first_hw_timestamp[device_name] = adjusted_esp32_ts
                    plot_time_sec = (adjusted_esp32_ts - first_hw_timestamp[device_name]) / 1000.0

                    # Extract raw sensor values
                    ax = int(parts[3]) / 10000.0
                    ay = int(parts[4]) / 10000.0
                    az = int(parts[5]) / 10000.0
                    gx_dps = int(parts[6]) / 100.0
                    gy_dps = int(parts[7]) / 100.0
                    gz_dps = int(parts[8]) / 100.0
                    mx = int(parts[9]) / 100.0
                    my = int(parts[10]) / 100.0
                    mz = int(parts[11]) / 100.0
                    
                    # Quaternion to Euler Math
                    q0 = int(parts[12]) / 32767.0
                    q1 = int(parts[13]) / 32767.0
                    q2 = int(parts[14]) / 32767.0
                    q3 = int(parts[15]) / 32767.0
                        
                    w, x, y, z = q0, q1, q2, q3
                    
                    roll_rad = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
                    sinp = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
                    pitch_rad = math.asin(sinp)
                    yaw_rad = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))

                    raw_roll = math.degrees(roll_rad)
                    raw_pitch = math.degrees(pitch_rad)
                    raw_yaw = (math.degrees(yaw_rad) + 360.0) % 360.0

                    # Baseline Calibration Logic
                    if plot_time_sec < CALIBRATION_TIME_SEC:
                        calibration_data[device_name]['roll'].append(raw_roll)
                        calibration_data[device_name]['pitch'].append(raw_pitch)
                        calibration_data[device_name]['yaw'].append(raw_yaw)
                        roll_out, pitch_out, yaw_out = 0.0, 0.0, 0.0
                    else:
                        if not baseline_computed[device_name] and len(calibration_data[device_name]['roll']) > 0:
                            baseline_offsets[device_name]['roll'] = np.mean(calibration_data[device_name]['roll'])
                            baseline_offsets[device_name]['pitch'] = np.mean(calibration_data[device_name]['pitch'])
                            yaws = np.radians(calibration_data[device_name]['yaw'])
                            mean_yaw_rad = np.arctan2(np.mean(np.sin(yaws)), np.mean(np.cos(yaws)))
                            baseline_offsets[device_name]['yaw'] = (np.degrees(mean_yaw_rad) + 360) % 360
                            baseline_computed[device_name] = True
                            
                        roll_out = raw_roll - baseline_offsets[device_name]['roll']
                        pitch_out = raw_pitch - baseline_offsets[device_name]['pitch']
                        yaw_out = raw_yaw - baseline_offsets[device_name]['yaw']
                        
                        for val, name_var in [(yaw_out, 'yaw'), (roll_out, 'roll'), (pitch_out, 'pitch')]:
                            if val > 180: val -= 360
                            elif val < -180: val += 360

                    # Send directly to the master CSV queue
                    if LOG_ENABLED:
                        log_queue.put((
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], adjusted_esp32_ts, device_name, 
                            ax, ay, az, gx_dps, gy_dps, gz_dps, mx, my, mz, 
                            [q0,q1,q2,q3], roll_out, pitch_out, yaw_out, is_paused
                        ))
                        
                    # Safely increment the Hz counter
                    with stats_lock:
                        hz_counters[device_name] += 1
                    
                except Exception:
                    pass
                
    except serial.SerialException as e:
        print(f"❌ {com_port} Error: {e}")
    finally:
        if ser and ser.is_open: ser.close()

# ==========================================
# MAIN TERMINAL DASHBOARD
# ==========================================
def print_dashboard():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("="*50)
    print(" 🚀 HEADLESS 6-NODE IMU LOGGER ACTIVE")
    print("="*50)
    
    if is_paused:
        print(" 🔴 RECORDING FLAG: [1] (Spacebar to toggle)")
    else:
        print(" ⚪ RECORDING FLAG: [0] (Spacebar to toggle)")
        
    print("-" * 50)
    print(f" {'Sensor Node':<15} | {'Frequency (Hz)':<15}")
    print("-" * 50)
    
    with stats_lock:
        for name in SENSOR_NAMES:
            print(f" {name:<15} | {current_hz[name]:>6.1f} Hz")
            
    print("="*50)
    print(" Queue Backlog: ", log_queue.qsize(), "packets")
    print(" Press Ctrl+C to stop and save CSV.")

if __name__ == "__main__":
    print("Booting Serial Threads...")
    
    # Start CSV and Keyboard threads
    threading.Thread(target=csv_writer_worker, daemon=False).start()
    threading.Thread(target=keyboard_listener, daemon=True).start()
    
    # Start Serial threads
    for port in COM_PORTS:
        threading.Thread(target=read_serial, args=(port,), daemon=True).start()
    
    try:
        # Update terminal dashboard every 3 seconds
        while True:
            time.sleep(3.0)
            
            with stats_lock:
                for name in SENSOR_NAMES:
                    # Divide by 3 because we are checking every 3 seconds
                    current_hz[name] = hz_counters[name] / 3.0
                    hz_counters[name] = 0
            
            print_dashboard()
            
    except KeyboardInterrupt:
        running = False
        print("\n\n🛑 Shutting down... waiting for CSV write buffer to empty.")