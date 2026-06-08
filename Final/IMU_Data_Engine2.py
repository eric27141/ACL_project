import serial
import math
import time
import os
import csv
from datetime import datetime
import numpy as np
import threading
import queue

class IMUDataEngine:
    def __init__(self, com_ports):
        self.com_ports = com_ports
        self.baud_rate = 921600
        self.calibration_time_sec = 5.0
        self.sensor_names = ["R_Hip", "R_Shank", "R_Ankle", "L_Hip", "L_Shank", "L_Ankle"]
        
        # Threads and Flags
        self.is_engine_alive = False
        self.is_logging_active = False  # Controls writing to CSV file
        self.is_t_pose = False
        self.threads = []
        self.log_queue = queue.Queue()
        self.stats_lock = threading.Lock()
        # ---> ADD THIS LINE <---
        self.pause_serial = False
        
        # Persistent Memory Cache (Your 6 state variables)
        self.battery_levels = {name: "?" for name in self.sensor_names}
        self.latest_raw_cache = {name: {"ax": 0.0, "ay": 0.0, "az": 0.0, "mx": 0.0, "my": 0.0, "mz": 0.0} for name in self.sensor_names} #
        self.last_seen_timestamps = {name: 0.0 for name in self.sensor_names}
        self.hz_counters = {name: 0 for name in self.sensor_names}
        self.current_hz = {name: 0.0 for name in self.sensor_names}
        
        # Kinematic Memory Structures
        self.output_filepath = ""
        self.first_hw_timestamp = {name: None for name in self.sensor_names}
        self.baseline_computed = {name: False for name in self.sensor_names}
        self.baseline_offsets = {name: {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0} for name in self.sensor_names}
        self.calibration_data = {name: {'roll': [], 'pitch': [], 'yaw': []} for name in self.sensor_names}

    def start_passive_monitor(self):
        """Starts background serial listeners immediately upon UI boot to track health."""
        if self.is_engine_alive: return
        self.is_engine_alive = True
        
        # Start Master CSV Consumer Thread
        csv_t = threading.Thread(target=self._csv_writer_worker, daemon=True)
        csv_t.start()
        self.threads.append(csv_t)
        
        # Start Individual Port Listeners
        for port in self.com_ports:
            if port.strip():
                t = threading.Thread(target=self._read_serial, args=(port.strip(),), daemon=True)
                t.start()
                self.threads.append(t)
        print("📡 Background Passive Health Monitoring System Active.")

    def start_active_logging(self, filepath):
        """Enables saving streaming data into a formal subject file path."""
        self.output_filepath = filepath
        # Reset calibration states for a clean run
        self.first_hw_timestamp = {name: None for name in self.sensor_names}
        self.baseline_computed = {name: False for name in self.sensor_names}
        self.calibration_data = {name: {'roll': [], 'pitch': [], 'yaw': []} for name in self.sensor_names}
        
        self.is_logging_active = True 
        print(f"💾 Active Trial Recording Engaged -> {filepath}")

    def stop_active_logging(self):
        """Disengages file writing but leaves passive diagnostics running."""
        self.is_logging_active = False
        print("⚪ Active Trial Recording Disengaged. Reverting to Passive Monitoring.")

    def set_t_pose(self, state: bool):
        self.is_t_pose = state

    def get_latest_diagnostics(self):
        """Returns live connection status, battery levels, and frequency data from memory."""
        now = time.time()
        diagnostics = {}
        with self.stats_lock:
            for name in self.sensor_names:
                # If we received ANY packet in the last 4.5 seconds, mark it alive
                is_connected = (now - self.last_seen_timestamps[name]) < 4.5
                diagnostics[name] = {
                    "connected": is_connected,
                    "battery": self.battery_levels[name] if is_connected else "?",
                    "hz": self.current_hz[name] if is_connected else 0.0
                }
        return diagnostics

    def calculate_hz_snapshot(self, elapsed_seconds):
        """Calculates current frequency metrics based on internal counters."""
        # ---> ADD THIS PROTECTION LINE <---
        if elapsed_seconds <= 0: 
            return
            
        with self.stats_lock:
            for name in self.sensor_names:
                self.current_hz[name] = self.hz_counters[name] / elapsed_seconds
                self.hz_counters[name] = 0

    def get_raw_data_snapshot(self):
        """Returns a safe copy of the latest raw sensor values for the validator."""
        with self.stats_lock:
            return {name: data.copy() for name, data in self.latest_raw_cache.items()}

    # def hardware_reset(self):
    #     """Sends a hardware reboot sequence to the ESP32 adapters."""
    #     print("⚡ Resetting ESP32 Link layers...")
    #     for port in self.com_ports:
    #         if not port.strip(): continue
    #         try:
    #             ser = serial.Serial()
    #             ser.port = port.strip()
    #             ser.baudrate = self.baud_rate
    #             ser.timeout = 0.1
    #             ser.setDTR(True); ser.setRTS(True)
    #             time.sleep(0.1)
    #             ser.setDTR(False); ser.setRTS(False)
    #             ser.open(); ser.close()
    #         except Exception as e:
    #             print(f"Warning resetting {port}: {e}")
    def hardware_reset(self):
        """Sends a hardware reboot sequence to the ESP32 adapters."""
        print("⚡ Resetting ESP32 Link layers...")
        
        # 1. Force background readers to close their ports
        self.pause_serial = True
        time.sleep(0.5) 
        
        for port in self.com_ports:
            if not port.strip(): continue
            try:
                ser = serial.Serial()
                ser.port = port.strip()
                ser.baudrate = self.baud_rate
                ser.timeout = 0.1
                ser.open()
                
                # Trigger the ESP32 Reset (Pulls EN line low)
                ser.setDTR(False)
                ser.setRTS(True)
                time.sleep(0.1)
                
                # Release the lines
                ser.setDTR(False)
                ser.setRTS(False)
                ser.close()
                print(f"✅ Reset signal sent successfully to {port}")
            except Exception as e:
                print(f"Warning resetting {port}: {e}")
                
        # 2. Allow background readers to reconnect
        self.pause_serial = False

    # ==========================================
    # CORE BACKGROUND PARSING WORKERS
    # ==========================================
    # def _read_serial(self, com_port):
    #     ser = None
    #     last_raw_esp_ts = {name: 0 for name in self.sensor_names}
    #     shift_accumulator = {name: 0 for name in self.sensor_names}
        
    #     try:
    #         ser = serial.Serial()
    #         ser.port = com_port
    #         ser.baudrate = self.baud_rate
    #         ser.timeout = 0.5
    #         ser.setDTR(False); ser.setRTS(False)
    #         ser.open()
            
    #         while self.is_engine_alive:
    #             while ser.in_waiting > 0 and self.is_engine_alive:
    #                 try:
    #                     line_bytes = ser.readline()
    #                     if not line_bytes: continue
    #                     line = line_bytes.decode('utf-8', errors='ignore').strip()
    #                     if not line or ',' not in line: continue
                        
    #                     parts = line.split(',')
                        
    #                     # --- INTERCEPT BATTERY TELEMETRY ---
    #                     if parts[0] == "BAT" and len(parts) == 3:
    #                         dev_name = parts[1]
    #                         if dev_name in self.sensor_names:
    #                             with self.stats_lock:
    #                                 self.battery_levels[dev_name] = f"{parts[2]}%"
    #                                 self.last_seen_timestamps[dev_name] = time.time()
    #                         continue
                        
    #                     # --- PROCESS STANDARD STRUCT PACKETS ---
    #                     if len(parts) != 16: continue
    #                     device_name = parts[0]
    #                     if device_name not in self.sensor_names: continue

    #                     # Extract raw values immediately for health & live calibration tracking
    #                     ax = int(parts[3]) / 10000.0
    #                     ay = int(parts[4]) / 10000.0
    #                     az = int(parts[5]) / 10000.0
    #                     mx = int(parts[9]) / 100.0
    #                     my = int(parts[10]) / 100.0
    #                     mz = int(parts[11]) / 100.0
                        
    #                     # Update live hardware status variables immediately
    #                     with self.stats_lock:
    #                         self.last_seen_timestamps[device_name] = time.time()
    #                         self.hz_counters[device_name] += 1
    #                         # ---> NEW: Save to the live validation memory cache <---
    #                         self.latest_raw_cache[device_name] = {
    #                             "ax": ax, "ay": ay, "az": az,
    #                             "mx": mx, "my": my, "mz": mz
    #                         }
                        
    #                     # Drop packet immediately if not actively saving a trial
    #                     if not self.is_logging_active: continue
                        
    #                     raw_esp32_ts = int(parts[1])
    #                     if raw_esp32_ts == last_raw_esp_ts[device_name]:
    #                         shift_accumulator[device_name] += 10
    #                     else:
    #                         shift_accumulator[device_name] = 0
    #                     last_raw_esp_ts[device_name] = raw_esp32_ts
    #                     adjusted_esp32_ts = raw_esp32_ts + shift_accumulator[device_name]

    #                     if self.first_hw_timestamp[device_name] is None:
    #                         self.first_hw_timestamp[device_name] = adjusted_esp32_ts
    #                     plot_time_sec = (adjusted_esp32_ts - self.first_hw_timestamp[device_name]) / 1000.0

    #                     ax, ay, az = int(parts[3])/10000.0, int(parts[4])/10000.0, int(parts[5])/10000.0
    #                     gx_dps, gy_dps, gz_dps = int(parts[6])/100.0, int(parts[7])/100.0, int(parts[8])/100.0
    #                     mx, my, mz = int(parts[9])/100.0, int(parts[10])/100.0, int(parts[11])/100.0
    #                     q0, q1, q2, q3 = int(parts[12])/32767.0, int(parts[13])/32767.0, int(parts[14])/32767.0, int(parts[15])/32767.0
                        
    #                     roll_rad = math.atan2(2.0*(q0*q1 + q2*q3), 1.0 - 2.0*(q1*q1 + q2*q2))
    #                     sinp = max(-1.0, min(1.0, 2.0 * (q0 * q2 - q3 * q1)))
    #                     pitch_rad = math.asin(sinp)
    #                     yaw_rad = math.atan2(2.0*(q0*q3 + q1*q2), 1.0 - 2.0*(q2 * q2 + q3 * q3))

    #                     raw_roll, raw_pitch = math.degrees(roll_rad), math.degrees(pitch_rad)
    #                     raw_yaw = (math.degrees(yaw_rad) + 360.0) % 360.0

    #                     if plot_time_sec < self.calibration_time_sec:
    #                         self.calibration_data[device_name]['roll'].append(raw_roll)
    #                         self.calibration_data[device_name]['pitch'].append(raw_pitch)
    #                         self.calibration_data[device_name]['yaw'].append(raw_yaw)
    #                         roll_out, pitch_out, yaw_out = 0.0, 0.0, 0.0
    #                     else:
    #                         if not self.baseline_computed[device_name] and len(self.calibration_data[device_name]['roll']) > 0:
    #                             self.baseline_offsets[device_name]['roll'] = np.mean(self.calibration_data[device_name]['roll'])
    #                             self.baseline_offsets[device_name]['pitch'] = np.mean(self.calibration_data[device_name]['pitch'])
    #                             yaws = np.radians(self.calibration_data[device_name]['yaw'])
    #                             mean_yaw_rad = np.arctan2(np.mean(np.sin(yaws)), np.mean(np.cos(yaws)))
    #                             self.baseline_offsets[device_name]['yaw'] = (np.degrees(mean_yaw_rad) + 360) % 360
    #                             self.baseline_computed[device_name] = True
                                
    #                         roll_out = raw_roll - self.baseline_offsets[device_name]['roll']
    #                         pitch_out = raw_pitch - self.baseline_offsets[device_name]['pitch']
    #                         yaw_out = raw_yaw - self.baseline_offsets[device_name]['yaw']
                            
    #                         for val, name_var in [(yaw_out, 'yaw'), (roll_out, 'roll'), (pitch_out, 'pitch')]:
    #                             if val > 180: val -= 360
    #                             elif val < -180: val += 360

    #                     self.log_queue.put((
    #                         datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], adjusted_esp32_ts, device_name, 
    #                         ax, ay, az, gx_dps, gy_dps, gz_dps, mx, my, mz, 
    #                         [q0, q1, q2, q3], roll_out, pitch_out, yaw_out, self.is_t_pose
    #                     ))
    #                 except Exception:
    #                     pass
    #     except Exception as e:
    #         print(f"Serial interface crash on {com_port}: {e}")
    #     finally:
    #         if ser and ser.is_open: ser.close()

    def _read_serial(self, com_port):
        ser = None
        last_raw_esp_ts = {name: 0 for name in self.sensor_names}
        shift_accumulator = {name: 0 for name in self.sensor_names}
        
        # Wrap in an outer loop so it constantly tries to reconnect if paused or unplugged
        while self.is_engine_alive:
            if self.pause_serial:
                time.sleep(0.1)
                continue
                
            try:
                ser = serial.Serial()
                ser.port = com_port
                ser.baudrate = self.baud_rate
                ser.timeout = 0.5
                ser.setDTR(False); ser.setRTS(False)
                ser.open()
                
                # Inner loop monitors the flag to know when to gracefully drop the connection
                while self.is_engine_alive and not self.pause_serial:
                    while ser.in_waiting > 0 and self.is_engine_alive and not self.pause_serial:
                        try:
                            line_bytes = ser.readline()
                            if not line_bytes: continue
                            line = line_bytes.decode('utf-8', errors='ignore').strip()
                            if not line or ',' not in line: continue
                            
                            parts = line.split(',')
                            
                            # ... [KEEP ALL YOUR EXISTING PACKET PARSING LOGIC HERE] ...
                            
                        except Exception:
                            pass
            except Exception as e:
                # If port doesn't exist (e.g. COM15 is empty), wait a second before retrying
                # This stops the console from spamming "FileNotFoundError"
                time.sleep(1.0) 
            finally:
                if ser and ser.is_open: ser.close()

    def _csv_writer_worker(self):
        while self.is_engine_alive:
            if not self.is_logging_active or self.log_queue.empty():
                time.sleep(0.1)
                continue
                
            headers = ['python_time', 'esp32_hw_time', 'sensor_name', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz', 'q0', 'q1', 'q2', 'q3', 'quat_roll', 'quat_pitch', 'quat_yaw', 'is_paused_flag', 't_pose_flag']
            
            try:
                with open(self.output_filepath, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(headers)
                    
                    while self.is_logging_active:
                        try:
                            row_data = self.log_queue.get(timeout=0.5)
                            (py_ts, hw_ts, name, ax, ay, az, gx, gy, gz, mx, my, mz, q, r, p, y, t_pose) = row_data
                            writer.writerow([py_ts, hw_ts, name, round(ax,4), round(ay,4), round(az,4), round(gx,2), round(gy,2), round(gz,2), round(mx,2), round(my,2), round(mz,2), round(q[0],6), round(q[1],6), round(q[2],6), round(q[3],6), round(r,2), round(p,2), round(y,2), 0, 1 if t_pose else 0])
                            if self.log_queue.qsize() == 0: file.flush()
                        except queue.Empty:
                            if not self.is_logging_active: break
            except Exception as e:
                print(f"CSV Writer File IO Error: {e}")