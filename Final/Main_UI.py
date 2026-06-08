import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import winsound  # Built-in Windows library for audio beeps
from IMU_Data_Engine2 import IMUDataEngine  # Import our new engine
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from collections import deque
import time

CONFIG_FILE = "imu_config.json"

# Updated default settings to include Left/Right ports and Subject History
DEFAULT_CONFIG = {
    "com_port_left": "COM10",
    "com_port_right": "COM11",
    "save_directory": "./data",
    "last_subject_id": "",
    "subject_history": [],
    "baud_rate": 921600
}

class ConfigManager:
    @staticmethod
    def load_config():
        config = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    # Update defaults with loaded data to prevent missing key errors
                    config.update(loaded) 
            except Exception as e:
                print(f"Error loading config: {e}")
        return config

    @staticmethod
    def save_config(config_data):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)

# class IMUDashboard(tk.Tk):
#     def __init__(self):
#         super().__init__()
#         self.title("Multi-IMU Posture Logging System")
#         self.geometry("500x400")
#         self.config_data = ConfigManager.load_config()
        
#         self.setup_main_menu()

#     def setup_main_menu(self):
#         # Clear existing widgets
#         for widget in self.winfo_children():
#             widget.destroy()

#         # Title
#         tk.Label(self, text="Kinematic Data Gatherer", font=("Arial", 18, "bold")).pack(pady=20)

#         # Subject ID Input (Now a Combobox with history)
#         id_frame = tk.Frame(self)
#         id_frame.pack(pady=10)
#         tk.Label(id_frame, text="Subject ID:", font=("Arial", 12)).pack(side=tk.LEFT)
        
#         self.subject_id_var = tk.StringVar(value=self.config_data.get("last_subject_id", ""))
#         self.subject_combo = ttk.Combobox(id_frame, textvariable=self.subject_id_var, font=("Arial", 12), width=15)
#         # Load previous IDs into the dropdown
#         self.subject_combo['values'] = self.config_data.get("subject_history", []) 
#         self.subject_combo.pack(side=tk.LEFT, padx=10)

#         # Test A Button
#         tk.Button(self, text="Start Test A: Squat Protocol", font=("Arial", 14), bg="#4CAF50", fg="white", 
#                   command=self.launch_test_a).pack(pady=15, fill=tk.X, padx=50)

#         # Settings Button
#         tk.Button(self, text="⚙️ Settings", font=("Arial", 12), command=self.open_settings).pack(pady=10)

#         # --- NEW: HARDWARE DIAGNOSTICS PANEL ---
#         diag_frame = tk.LabelFrame(self, text="Hardware Diagnostics", font=("Arial", 10, "bold"), padx=10, pady=10)
#         diag_frame.pack(pady=10, fill=tk.X, padx=20)
        
#         # Status Indicators (Dictionaries to hold the UI labels)
#         self.status_labels = {}
#         sensors = ["R_Hip", "R_Shank", "R_Ankle", "L_Hip", "L_Shank", "L_Ankle"]
        
#         grid_frame = tk.Frame(diag_frame)
#         grid_frame.pack()
        
#         for i, name in enumerate(sensors):
#             lbl = tk.Label(grid_frame, text=f"🔴 {name} (Bat: ?)", width=16, anchor="w", font=("Arial", 10))
#             lbl.grid(row=i//3, column=i%3, padx=5, pady=5)
#             self.status_labels[name] = lbl
            
#         btn_frame = tk.Frame(diag_frame)
#         btn_frame.pack(pady=(10,0))
        
#         tk.Button(btn_frame, text="🔍 Ping Sensors", bg="#FF9800", fg="white", command=self.run_ping).pack(side=tk.LEFT, padx=5)
#         tk.Button(btn_frame, text="⚡ Reset ESP32", bg="#f44336", fg="white", command=self.run_reset).pack(side=tk.LEFT, padx=5)
#         tk.Button(btn_frame, text="📊 Open Plotter", bg="#2196F3", fg="white", command=self.open_plotter).pack(side=tk.LEFT, padx=5)
#         # ---------------------------------------

#     def open_settings(self):
#         SettingsDialog(self, self.config_data)

#     def launch_test_a(self):
#         subject_id = self.subject_id_var.get().strip()
#         if not subject_id:
#             messagebox.showwarning("Missing Info", "Please enter or select a Subject ID before starting.")
#             return
            
#         # Update Config with new Subject ID and History
#         self.config_data["last_subject_id"] = subject_id
#         history = self.config_data.get("subject_history", [])
#         if subject_id not in history:
#             history.append(subject_id)
#             self.config_data["subject_history"] = history
#         ConfigManager.save_config(self.config_data)

#         # Create directory and file paths
#         base_dir = self.config_data.get("save_directory", "./data")
#         subject_dir = os.path.join(base_dir, subject_id)
#         os.makedirs(subject_dir, exist_ok=True)
        
#         file_name = f"{subject_id}_TestA_Squat_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
#         final_path = os.path.join(subject_dir, file_name)
        
#         # Launch the Phase 3 Test Window
#         TestAWindow(self, self.config_data, subject_id, final_path)
#     def run_ping(self):
#         coms = [self.config_data.get("com_port_left", ""), self.config_data.get("com_port_right", "")]
#         engine = IMUDataEngine(coms, "temp.csv")
        
#         # Unpack both the active status and the battery levels
#         active_dict, bat_dict = engine.ping_sensors()
        
#         for name, is_active in active_dict.items():
#             bat_percent = bat_dict.get(name, "?")
#             if is_active:
#                 self.status_labels[name].config(text=f"🟢 {name} (Bat: {bat_percent})", fg="green")
#             else:
#                 self.status_labels[name].config(text=f"🔴 {name} (Bat: ?)", fg="red")

#     def run_reset(self):
#         coms = [self.config_data.get("com_port_left", ""), self.config_data.get("com_port_right", "")]
#         engine = IMUDataEngine(coms, "temp.csv")
#         engine.hardware_reset()
#         messagebox.showinfo("Reset", "Hardware Reset Signal Sent.\nWait 2 seconds, then Ping Sensors.")

#     def open_plotter(self):
#         # Let the operator choose which file to analyze
#         filepath = filedialog.askopenfilename(
#             initialdir=self.config_data.get("save_directory", "./data"),
#             title="Select CSV to Plot",
#             filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
#         )
#         if filepath:
#             EmbeddedPlotterWindow(self, filepath)

class IMUDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Multi-IMU Posture Logging System")
        self.geometry("500x480")  # Expanded slightly for clean framing
        self.config_data = ConfigManager.load_config()
        
        # Instantiate a SINGLE persistent background data engine
        coms = [self.config_data.get("com_port_left", ""), self.config_data.get("com_port_right", "")]
        self.engine = IMUDataEngine(coms)
        self.engine.start_passive_monitor() # Boot background listeners instantly
        
        self.setup_main_menu()
        
        # Start the automated 1-second live diagnostics refresh task
        self.last_hz_check_time = time.time()
        self.periodic_diagnostics_refresh()

    def setup_main_menu(self):
        for widget in self.winfo_children(): widget.destroy()

        tk.Label(self, text="Kinematic Data Gatherer", font=("Arial", 18, "bold")).pack(pady=15)

        id_frame = tk.Frame(self)
        id_frame.pack(pady=5)
        tk.Label(id_frame, text="Subject ID:", font=("Arial", 12)).pack(side=tk.LEFT)
        
        self.subject_id_var = tk.StringVar(value=self.config_data.get("last_subject_id", ""))
        self.subject_combo = ttk.Combobox(id_frame, textvariable=self.subject_id_var, font=("Arial", 12), width=15)
        self.subject_combo['values'] = self.config_data.get("subject_history", [])
        self.subject_combo.pack(side=tk.LEFT, padx=10)

        tk.Button(self, text="Start Test A: Squat Protocol", font=("Arial", 14), bg="#4CAF50", fg="white", 
                  command=self.launch_test_a).pack(pady=10, fill=tk.X, padx=50)

        # --- LIVE DIAGNOSTICS DISPLAY PANEL ---
        diag_frame = tk.LabelFrame(self, text="Live Hardware Diagnostics", font=("Arial", 10, "bold"), padx=10, pady=10)
        diag_frame.pack(pady=10, fill=tk.X, padx=20)
        
        self.status_labels = {}
        sensors = ["R_Hip", "R_Shank", "R_Ankle", "L_Hip", "L_Shank", "L_Ankle"]
        grid_frame = tk.Frame(diag_frame)
        grid_frame.pack()
        
        for i, name in enumerate(sensors):
            # Formatted box framework to handle changing battery/Hz sizes safely
            lbl = tk.Label(grid_frame, text=f"🔴 {name} (??%)", width=18, anchor="w", font=("Courier", 9, "bold"), fg="red")
            lbl.grid(row=i//3, column=i%3, padx=5, pady=5)
            self.status_labels[name] = lbl
            
        btn_frame = tk.Frame(diag_frame)
        btn_frame.pack(pady=(10,0))
        
        tk.Button(btn_frame, text="🔍 Check Calibration", bg="#9C27B0", fg="white", font=("Arial", 9, "bold"), command=self.open_validator).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="⚡ Reset Links", bg="#f44336", fg="white", font=("Arial", 9, "bold"), command=self.run_reset).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📊 Open Plotter", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=self.open_plotter).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="⚙️ Settings", font=("Arial", 9), command=self.open_settings).pack(side=tk.LEFT, padx=5)

    def periodic_diagnostics_refresh(self):
        """Runs silently every 1 second in the background, updating UI states out of cache."""
        now = time.time()
        elapsed = now - self.last_hz_check_time
        self.last_hz_check_time = now
        
        # Request a new frequency snap evaluation out of background threads
        self.engine.calculate_hz_snapshot(elapsed)
        stats = self.engine.get_latest_diagnostics()
        
        for name, info in stats.items():
            if info["connected"]:
                text_layout = f"🟢 {name:<7} ({info['battery']:>4}) {int(info['hz']):>3}Hz"
                self.status_labels[name].config(text=text_layout, fg="#2E7D32")
            else:
                text_layout = f"🔴 {name:<7} ( ??%)   0Hz"
                self.status_labels[name].config(text=text_layout, fg="#C62828")
                
        # Register next execution hook loop 1000ms from now
        self.after(1000, self.periodic_diagnostics_refresh)

    def run_reset(self):
        self.engine.hardware_reset()
        messagebox.showinfo("Reset", "ESP32 Reset command sent successfully.\nRe-establishing links within 3 seconds.")

    def open_settings(self):
        SettingsDialog(self, self.config_data)
        # Update engine parameters if ports were altered in modal window
        coms = [self.config_data.get("com_port_left", ""), self.config_data.get("com_port_right", "")]
        self.engine.com_ports = coms

    def open_validator(self):
        """Launches the 6-sensor live magnetometer and accelerometer validator window."""
        SensorSelectorDialog(self, self.engine)

    def open_plotter(self):
        filepath = filedialog.askopenfilename(initialdir=self.config_data.get("save_directory", "./data"), title="Open Subject Log", filetypes=(("CSV Files", "*.csv"), ("All files", "*.*")))
        if filepath: EmbeddedPlotterWindow(self, filepath)

    def launch_test_a(self):
        subject_id = self.subject_id_var.get().strip()
        if not subject_id:
            messagebox.showwarning("Missing Info", "Please enter a valid Subject ID.")
            return
            
        base_dir = self.config_data.get("save_directory", "./data")
        subject_dir = os.path.join(base_dir, subject_id)
        
        # ---> ADD THIS LINE HERE <---
        os.makedirs(subject_dir, exist_ok=True) 
        
        file_name = f"{subject_id}_TestA_Squat_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        final_path = os.path.join(subject_dir, file_name)
        
        # Engage file writing mode on our single running engine instance
        self.engine.start_active_logging(final_path)
        TestAWindow(self, self.engine, subject_id)


class SensorSelectorDialog(tk.Toplevel):
    def __init__(self, parent, engine):
        super().__init__(parent)
        self.title("Calibration Target Selection")
        self.geometry("380x220")
        self.resizable(False, False)
        
        self.parent = parent
        self.engine = engine
        
        # Keep focus on this modal dialog window
        self.transient(parent)
        self.grab_set()
        
        tk.Label(self, text="Select Sensor Node to Validate", font=("Arial", 12, "bold")).pack(pady=20)
        
        # Dropdown selection menu
        self.sensor_var = tk.StringVar(value=self.engine.sensor_names[0])
        self.combo = ttk.Combobox(self, textvariable=self.sensor_var, values=self.engine.sensor_names, font=("Arial", 11), state="readonly", width=18)
        self.combo.pack(pady=10)
        
        # Action Launch Button
        tk.Button(self, text="Launch Live Validator 🚀", bg="#9C27B0", fg="white", font=("Arial", 11, "bold"), 
                  padx=10, pady=5, command=self.launch_target_validator).pack(pady=15)

    def launch_target_validator(self):
        selected_node = self.sensor_var.get()
        # Launch the high-speed single sensor validation window
        SingleCalibrationValidatorWindow(self.parent, self.engine, selected_node)
        self.destroy()


# class SingleCalibrationValidatorWindow(tk.Toplevel):
#     def __init__(self, parent, engine, sensor_name):
#         super().__init__(parent)
#         self.title(f"Live Calibration Check - Target: {sensor_name}")
#         self.geometry("750x650")
        
#         self.engine = engine
#         self.sensor_name = sensor_name
#         self.is_active = True
#         self.fig = None
        
#         self.protocol("WM_DELETE_WINDOW", self.on_close)
        
#         # Clean rolling history arrays dedicated ONLY to this single sensor
#         self.history_x = deque(maxlen=400) # Expanded history size since processing is much faster
#         self.history_y = deque(maxlen=400)
#         self.accel_z_min = 99.0
#         self.accel_z_max = -99.0
        
#         self.graph_frame = tk.Frame(self)
#         self.graph_frame.pack(fill=tk.BOTH, expand=True)
        
#         # Setup a single elegant Matplotlib plot layout (1 row, 1 column)
#         import matplotlib.pyplot as plt
#         self.fig, self.ax = plt.subplots(figsize=(6, 5))
#         self.fig.suptitle(f"Hardware Validation Diagnostic Panel [{sensor_name}]", fontsize=12, fontweight='bold')
        
#         # Configure Plot Frame Bounds and Markers
#         self.ax.set_xlim(-100, 100)
#         self.ax.set_ylim(-100, 100)
#         self.ax.set_xlabel("Magnetometer X (µT)", fontweight='bold')
#         self.ax.set_ylabel("Magnetometer Y (µT)", fontweight='bold')
#         self.ax.grid(True, linestyle='--', alpha=0.5)
#         self.ax.axhline(0, color='black', linewidth=1, alpha=0.4)
#         self.ax.axvline(0, color='black', linewidth=1, alpha=0.4)
        
#         # Initialize light graphic marker handles
#         self.scatter_plot, = self.ax.plot([], [], 'b.', markersize=6, alpha=0.5, label="Mag Trace")
#         self.heading_line, = self.ax.plot([], [], 'r-', linewidth=2, label="Current Vector")
#         self.center_marker, = self.ax.plot([], [], 'gX', markersize=12, label="Calculated Center")
        
#         # Text display card for numerical metric overlays
#         self.text_display = self.ax.text(0.04, 0.96, '', transform=self.ax.transAxes, verticalalignment='top',
#                                          fontname='monospace', fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))
        
#         self.ax.legend(loc="lower right", fontsize='small')
#         self.fig.tight_layout()
        
#         # Embed the single figure canvas into the Tkinter window container
#         self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
#         self.canvas.draw()
#         self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
#         # Launch optimized background data parsing query hook at 50ms intervals
#         self.update_validator_loop()

#     def update_validator_loop(self):
#         """Pulls raw data out of cache and drives the high-speed rendering frame update."""
#         if not self.is_active: return
        
#         # Fetch thread-safe raw data cache block map from background engine context
#         raw_snapshot = self.engine.get_raw_data_snapshot()
        
#         # Directly grab the data for the SINGLE selected sensor (No for loop needed!)
#         data = raw_snapshot.get(self.sensor_name)
        
#         if data:
#             mx, my, mz = data["mx"], data["my"], data["mz"]
#             az_actual = data["az"]
            
#             # Track Accel bounds
#             if az_actual != 0.0:
#                 if az_actual < self.accel_z_min: self.accel_z_min = az_actual
#                 if az_actual > self.accel_z_max: self.accel_z_max = az_actual
            
#             # Update history queues only if magnetometer has real data frames coming in
#             if not (mx == 0.0 and my == 0.0 and mz == 0.0):
#                 self.history_x.append(mx)
#                 self.history_y.append(my)
                
#                 # Commit updated vector streams directly to lines
#                 self.scatter_plot.set_data(list(self.history_x), list(self.history_y))
#                 self.heading_line.set_data([0, mx], [0, my])
                
#                 # Perform geometric center tracking
#                 if len(self.history_x) > 2:
#                     max_x, min_x = max(self.history_x), min(self.history_x)
#                     max_y, min_y = max(self.history_y), min(self.history_y)
                    
#                     offset_x = (max_x + min_x) / 2.0
#                     offset_y = (max_y + min_y) / 2.0
#                     self.center_marker.set_data([offset_x], [offset_y])
                    
#                     info_string = (
#                         f"Target Node: {self.sensor_name}\n"
#                         f"------------------------\n"
#                         f"Mag Offset X: {offset_x:+.1f} uT\n"
#                         f"Mag Offset Y: {offset_y:+.1f} uT\n"
#                         f"Accel Z Max : {self.accel_z_max:+.2f} g\n"
#                         f"Accel Z Min : {self.accel_z_min:+.2f} g"
#                     )
#                     self.text_display.set_text(info_string)

#         # Trigger a lightweight interface repaint step
#         self.canvas.draw_idle()
        
#         # Schedule the next single-sensor render frame step 50 milliseconds from now
#         self.after(50, self.update_validator_loop)

#     def on_close(self):
#         """Safely cleans up figure allocations out of RAM memory upon window exit."""
#         self.is_active = False
#         import matplotlib.pyplot as plt
#         if self.fig:
#             plt.close(self.fig)
#         self.destroy()

class SingleCalibrationValidatorWindow(tk.Toplevel):
    def __init__(self, parent, engine, sensor_name):
        super().__init__(parent)
        self.title(f"Live Calibration Check - Target: {sensor_name}")
        self.geometry("750x650")
        
        self.engine = engine
        self.sensor_name = sensor_name
        self.is_active = True
        self.fig = None
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Clean rolling history arrays dedicated ONLY to this single sensor
        self.history_x = deque(maxlen=400) 
        self.history_y = deque(maxlen=400)
        
        # NEW: 10-sample rolling windows for accelerometer smoothing
        # At 50ms per update, 10 samples gives a smooth 0.5-second average
        self.accel_x_history = deque(maxlen=10)
        self.accel_y_history = deque(maxlen=10)
        self.accel_z_history = deque(maxlen=10)

        self.last_data_state = None
        
        self.graph_frame = tk.Frame(self)
        self.graph_frame.pack(fill=tk.BOTH, expand=True)
        
        # Setup a single elegant Matplotlib plot layout (1 row, 1 column)
        import matplotlib.pyplot as plt
        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.fig.suptitle(f"Hardware Validation Diagnostic Panel [{sensor_name}]", fontsize=12, fontweight='bold')
        
        # Configure Plot Frame Bounds and Markers
        self.ax.set_xlim(-100, 100)
        self.ax.set_ylim(-100, 100)
        self.ax.set_xlabel("Magnetometer X (µT)", fontweight='bold')
        self.ax.set_ylabel("Magnetometer Y (µT)", fontweight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.axhline(0, color='black', linewidth=1, alpha=0.4)
        self.ax.axvline(0, color='black', linewidth=1, alpha=0.4)
        
        # Initialize light graphic marker handles
        self.scatter_plot, = self.ax.plot([], [], 'b.', markersize=6, alpha=0.5, label="Mag Trace")
        self.heading_line, = self.ax.plot([], [], 'r-', linewidth=2, label="Current Vector")
        self.center_marker, = self.ax.plot([], [], 'gX', markersize=12, label="Calculated Center")
        
        # Text display card for numerical metric overlays
        self.text_display = self.ax.text(0.04, 0.96, '', transform=self.ax.transAxes, verticalalignment='top',
                                         fontname='monospace', fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))
        
        self.ax.legend(loc="lower right", fontsize='small')
        self.fig.tight_layout()
        
        # Embed the single figure canvas into the Tkinter window container
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Launch optimized background data parsing query hook at 50ms intervals
        self.update_validator_loop()

    # def update_validator_loop(self):
    #     """Pulls raw data out of cache and drives the high-speed rendering frame update."""
    #     if not self.is_active: return
        
    #     # Fetch thread-safe raw data cache block map from background engine context
    #     raw_snapshot = self.engine.get_raw_data_snapshot()
        
    #     # Directly grab the data for the SINGLE selected sensor
    #     data = raw_snapshot.get(self.sensor_name)
        
    #     if data:
    #         mx, my, mz = data.get("mx", 0.0), data.get("my", 0.0), data.get("mz", 0.0)
    #         ax_actual = data.get("ax", 0.0)
    #         ay_actual = data.get("ay", 0.0)
    #         az_actual = data.get("az", 0.0)
            
    #         # Track and smooth Accel data if the IMU is sending valid non-zero blocks
    #         if not (ax_actual == 0.0 and ay_actual == 0.0 and az_actual == 0.0):
    #             self.accel_x_history.append(ax_actual)
    #             self.accel_y_history.append(ay_actual)
    #             self.accel_z_history.append(az_actual)
            
    #         # Update history queues only if magnetometer has real data frames coming in
    #         if not (mx == 0.0 and my == 0.0 and mz == 0.0):
    #             self.history_x.append(mx)
    #             self.history_y.append(my)
                
    #             # Commit updated vector streams directly to lines
    #             self.scatter_plot.set_data(list(self.history_x), list(self.history_y))
    #             self.heading_line.set_data([0, mx], [0, my])
                
    #             # Perform geometric center tracking
    #             if len(self.history_x) > 2:
    #                 max_x, min_x = max(self.history_x), min(self.history_x)
    #                 max_y, min_y = max(self.history_y), min(self.history_y)
                    
    #                 offset_x = (max_x + min_x) / 2.0
    #                 offset_y = (max_y + min_y) / 2.0
    #                 self.center_marker.set_data([offset_x], [offset_y])
                    
    #                 # Calculate safe rolling averages
    #                 avg_ax = sum(self.accel_x_history) / len(self.accel_x_history) if self.accel_x_history else 0.0
    #                 avg_ay = sum(self.accel_y_history) / len(self.accel_y_history) if self.accel_y_history else 0.0
    #                 avg_az = sum(self.accel_z_history) / len(self.accel_z_history) if self.accel_z_history else 0.0
                    
    #                 info_string = (
    #                     f"Target Node: {self.sensor_name}\n"
    #                     f"------------------------\n"
    #                     f"Mag Offset X : {offset_x:+.1f} uT\n"
    #                     f"Mag Offset Y : {offset_y:+.1f} uT\n"
    #                     f"------------------------\n"
    #                     f"Cur Accel X  : {avg_ax:+.2f} g\n"
    #                     f"Cur Accel Y  : {avg_ay:+.2f} g\n"
    #                     f"Cur Accel Z  : {avg_az:+.2f} g"
    #                 )
    #                 self.text_display.set_text(info_string)

    #     # Trigger a lightweight interface repaint step
    #     self.canvas.draw_idle()
        
    #     # Schedule the next single-sensor render frame step 50 milliseconds from now
    #     self.after(50, self.update_validator_loop)

    def update_validator_loop(self):
        """Pulls raw data out of cache and drives the high-speed rendering frame update."""
        if not self.is_active: return
        
        # Fetch thread-safe raw data cache block map from background engine context
        raw_snapshot = self.engine.get_raw_data_snapshot()
        
        # Directly grab the data for the SINGLE selected sensor
        data = raw_snapshot.get(self.sensor_name)
        
        if data:
            mx, my, mz = data.get("mx", 0.0), data.get("my", 0.0), data.get("mz", 0.0)
            ax_actual = data.get("ax", 0.0)
            ay_actual = data.get("ay", 0.0)
            az_actual = data.get("az", 0.0)
            
            # --- NEW: CIRCUIT BREAKER ---
            # Group the current data to see if it actually changed from the last frame
            current_state = (mx, my, mz, ax_actual, ay_actual, az_actual)
            if current_state == self.last_data_state:
                # Data hasn't changed. Skip the heavy Matplotlib redraw!
                self.after(100, self.update_validator_loop)
                return
                
            self.last_data_state = current_state
            # ----------------------------

            # Track and smooth Accel data if the IMU is sending valid non-zero blocks
            if not (ax_actual == 0.0 and ay_actual == 0.0 and az_actual == 0.0):
                self.accel_x_history.append(ax_actual)
                self.accel_y_history.append(ay_actual)
                self.accel_z_history.append(az_actual)
            
            # Update history queues only if magnetometer has real data frames coming in
            if not (mx == 0.0 and my == 0.0 and mz == 0.0):
                self.history_x.append(mx)
                self.history_y.append(my)
                
                # Commit updated vector streams directly to lines
                self.scatter_plot.set_data(list(self.history_x), list(self.history_y))
                self.heading_line.set_data([0, mx], [0, my])
                
                # Perform geometric center tracking
                if len(self.history_x) > 2:
                    max_x, min_x = max(self.history_x), min(self.history_x)
                    max_y, min_y = max(self.history_y), min(self.history_y)
                    
                    offset_x = (max_x + min_x) / 2.0
                    offset_y = (max_y + min_y) / 2.0
                    self.center_marker.set_data([offset_x], [offset_y])
                    
                    # Calculate safe rolling averages
                    avg_ax = sum(self.accel_x_history) / len(self.accel_x_history) if self.accel_x_history else 0.0
                    avg_ay = sum(self.accel_y_history) / len(self.accel_y_history) if self.accel_y_history else 0.0
                    avg_az = sum(self.accel_z_history) / len(self.accel_z_history) if self.accel_z_history else 0.0
                    
                    info_string = (
                        f"Target Node: {self.sensor_name}\n"
                        f"------------------------\n"
                        f"Mag Offset X : {offset_x:+.1f} uT\n"
                        f"Mag Offset Y : {offset_y:+.1f} uT\n"
                        f"------------------------\n"
                        f"Cur Accel X  : {avg_ax:+.2f} g\n"
                        f"Cur Accel Y  : {avg_ay:+.2f} g\n"
                        f"Cur Accel Z  : {avg_az:+.2f} g"
                    )
                    self.text_display.set_text(info_string)

            # Trigger a lightweight interface repaint step
            self.canvas.draw_idle()
        
        # Schedule the next single-sensor render frame step 100 milliseconds from now (10 FPS)
        self.after(100, self.update_validator_loop)

    def on_close(self):
        """Safely cleans up figure allocations out of RAM memory upon window exit."""
        self.is_active = False
        import matplotlib.pyplot as plt
        if self.fig:
            plt.close(self.fig)
        self.destroy()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x350")
        self.parent = parent
        self.config_data = config_data
        
        # Ensure focus stays on the dialog
        self.transient(parent)
        self.grab_set()

        # Left & Right COM Ports
        com_frame = tk.Frame(self)
        com_frame.pack(pady=(10, 10))

        tk.Label(com_frame, text="Left Leg COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.com_left = tk.Entry(com_frame, width=15)
        self.com_left.insert(0, self.config_data.get("com_port_left", "COM10"))
        self.com_left.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(com_frame, text="Right Leg COM Port:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.com_right = tk.Entry(com_frame, width=15)
        self.com_right.insert(0, self.config_data.get("com_port_right", "COM11"))
        self.com_right.grid(row=1, column=1, padx=5, pady=5)

        # Save Directory
        tk.Label(self, text="Base Save Directory:").pack(pady=(10, 0))
        dir_frame = tk.Frame(self)
        dir_frame.pack(pady=5)
        self.dir_entry = tk.Entry(dir_frame, width=30)
        self.dir_entry.insert(0, self.config_data.get("save_directory", "./data"))
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(dir_frame, text="Browse", command=self.browse_dir).pack(side=tk.LEFT)

        # Save Button
        tk.Button(self, text="Save Settings", bg="#008CBA", fg="white", command=self.save_and_close).pack(pady=20)

    def browse_dir(self):
        directory = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)

    def save_and_close(self):
        self.config_data["com_port_left"] = self.com_left.get().strip()
        self.config_data["com_port_right"] = self.com_right.get().strip()
        self.config_data["save_directory"] = self.dir_entry.get().strip()
        ConfigManager.save_config(self.config_data)
        self.destroy()


class TestAWindow(tk.Toplevel):
    def __init__(self, parent, engine, subject_id):
        super().__init__(parent)
        self.title(f"Test A Window - Subject ID: {subject_id}")
        self.geometry("800x600")
        self.configure(bg="black")
        
        self.parent = parent
        self.engine = engine # Hooks straight into the shared dashboard memory wrapper
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.info_label = tk.Label(self, text="Trial Launching...", font=("Arial", 40, "bold"), bg="black", fg="white")
        self.info_label.pack(expand=True, fill=tk.BOTH)
        
        self.reps_done = 0
        self.max_reps = 5
        self.stand_time = 3
        self.squat_time = 5
        
        self.bind('<t>', self.start_t_pose); self.bind('<T>', self.start_t_pose)
        self.update_ui("white", "black", "SUBJECT: Adopt Starting Pose\n\nOPERATOR: Strike Key 'T' to begin calibration.")

    def update_ui(self, fg, bg, text):
        self.configure(bg=bg); self.info_label.configure(fg=fg, bg=bg, text=text)

    def start_t_pose(self, event=None):
        self.unbind('<t>'); self.unbind('<T>')
        winsound.Beep(1000, 400)
        self.engine.set_t_pose(True)
        self.countdown_t_pose(5)

    def countdown_t_pose(self, seconds_left):
        if seconds_left > 0:
            self.update_ui("black", "yellow", f"CALIBRATING BASELINE WINDOW\n\nHOLD T-POSE STILL: {seconds_left}s")
            self.after(1000, self.countdown_t_pose, seconds_left - 1)
        else:
            self.engine.set_t_pose(False)
            winsound.Beep(1500, 600)
            self.prepare_squats(3)

    def prepare_squats(self, seconds_left):
        if seconds_left > 0:
            self.update_ui("white", "black", f"Prepare to execute Squats...\n\nProtocol beginning in: {seconds_left}")
            self.after(1000, self.prepare_squats, seconds_left - 1)
        else:
            self.run_stand_phase(self.stand_time)

    def run_stand_phase(self, seconds_left):
        if seconds_left > 0:
            self.update_ui("white", "blue", f"STAND STRAIGHT COMFORTABLY\n\nExecution Rep: {self.reps_done + 1}/{self.max_reps}\n\nHold: {seconds_left}s")
            if seconds_left <= 3: winsound.Beep(800, 150)
            self.after(1000, self.run_stand_phase, seconds_left - 1)
        else:
            winsound.Beep(1200, 500)
            self.run_squat_phase(self.squat_time)

    def run_squat_phase(self, seconds_left):
        if seconds_left > 0:
            self.update_ui("black", "green", f"DROP DOWN INTO SQUAT AND HOLD\n\nExecution Rep: {self.reps_done + 1}/{self.max_reps}\n\nHold: {seconds_left}s")
            self.after(1000, self.run_squat_phase, seconds_left - 1)
        else:
            self.reps_done += 1
            winsound.Beep(1500, 500)
            if self.reps_done < self.max_reps:
                self.run_stand_phase(self.stand_time)
            else:
                self.finish_test()

    def finish_test(self):
        self.update_ui("white", "black", "TEST COMPLETE!\n\nFlushing data to disk module...")
        self.engine.stop_active_logging()
        winsound.Beep(800, 150); winsound.Beep(1100, 150); winsound.Beep(1400, 350)
        self.after(2000, self.destroy)

    def on_close(self):
        self.engine.stop_active_logging()
        self.destroy()



class EmbeddedPlotterWindow(tk.Toplevel):
    def __init__(self, parent, csv_file_path):
        super().__init__(parent)
        self.title(f"Data Viewer - {os.path.basename(csv_file_path)}")
        self.geometry("1200x800")
        self.csv_file_path = csv_file_path
        self.fig = None # Store reference to prevent memory leaks
        
        # Handle memory cleanup on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.graph_frame = tk.Frame(self)
        self.graph_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- NEW: Floating Loading UI Panel ---
        self.loading_frame = tk.Frame(self.graph_frame, bg="#f0f0f0", bd=2, relief=tk.RAISED)
        self.loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=500, height=150)
        
        self.status_label = tk.Label(self.loading_frame, text="Initializing Data Engine...", font=("Arial", 14, "bold"), bg="#f0f0f0")
        self.status_label.pack(pady=(20, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.loading_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(pady=10)
        # --------------------------------------
        
        # Yield to UI so the loading panel appears, then run the heavy math
        self.after(100, self.generate_plot)

    # def generate_plot(self):
    #     # 1. Clear the "Rendering..." label
    #     for widget in self.graph_frame.winfo_children():
    #         widget.destroy()
            
    #     import pandas as pd
    #     import matplotlib.pyplot as plt
    #     import numpy as np
    #     import math
        
    #     # --- Local Madgwick Class ---
    #     class Madgwick9DoF:
    #         def __init__(self, beta=0.15):
    #             self.beta = beta
    #             self.q = np.array([1.0, 0.0, 0.0, 0.0])

    #         def update_9dof(self, gx, gy, gz, ax, ay, az, mx, my, mz, dt):
    #             q = self.q
    #             qDot1 = 0.5 * (-q[1] * gx - q[2] * gy - q[3] * gz)
    #             qDot2 = 0.5 * (q[0] * gx + q[2] * gz - q[3] * gy)
    #             qDot3 = 0.5 * (q[0] * gy - q[1] * gz + q[3] * gx)
    #             qDot4 = 0.5 * (q[0] * gz + q[1] * gy - q[2] * gx)

    #             if not (ax == 0.0 and ay == 0.0 and az == 0.0):
    #                 norm_acc = math.sqrt(ax * ax + ay * ay + az * az)
    #                 ax /= norm_acc; ay /= norm_acc; az /= norm_acc

    #                 norm_mag = math.sqrt(mx * mx + my * my + mz * mz)
    #                 if norm_mag > 0.0:
    #                     mx /= norm_mag; my /= norm_mag; mz /= norm_mag
    #                     _2q0mx = 2.0 * q[0] * mx; _2q0my = 2.0 * q[0] * my; _2q0mz = 2.0 * q[0] * mz
    #                     _2q1mx = 2.0 * q[1] * mx; _2q0 = 2.0 * q[0]; _2q1 = 2.0 * q[1]; _2q2 = 2.0 * q[2]
    #                     _2q3 = 2.0 * q[3]; _2q0q2 = 2.0 * q[0] * q[2]; _2q2q3 = 2.0 * q[2] * q[3]
    #                     q0q0 = q[0] * q[0]; q0q1 = q[0] * q[1]; q0q2 = q[0] * q[2]; q0q3 = q[0] * q[3]
    #                     q1q1 = q[1] * q[1]; q1q2 = q[1] * q[2]; q1q3 = q[1] * q[3]
    #                     q2q2 = q[2] * q[2]; q2q3 = q[2] * q[3]; q3q3 = q[3] * q[3]

    #                     hx = mx * q0q0 - _2q0my * q[3] + _2q0mz * q[2] + mx * q1q1 + _2q1 * my * q[2] + _2q1 * mz * q[3] - mx * q2q2 - mx * q3q3
    #                     hy = _2q0mx * q[3] + my * q0q0 - _2q0mz * q[1] + _2q1mx * q[2] - my * q1q1 + my * q2q2 + _2q2 * mz * q[3] - my * q3q3
    #                     _2bx = math.sqrt(hx * hx + hy * hy)
    #                     _2bz = -_2q0mx * q[2] + _2q0my * q[1] + mz * q0q0 + _2q1mx * q[3] - mz * q1q1 + _2q2 * my * q[3] - mz * q2q2 + mz * q3q3
    #                     _4bx = 2.0 * _2bx; _4bz = 2.0 * _2bz

    #                     s0 = -_2q2 * (2.0 * q1q3 - _2q0q2 - ax) + _2q1 * (2.0 * q0q1 + _2q2q3 - ay) - _2bz * q[2] * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (-_2bx * q[3] + _2bz * q[1]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + _2bx * q[2] * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
    #                     s1 = _2q3 * (2.0 * q1q3 - _2q0q2 - ax) + _2q0 * (2.0 * q0q1 + _2q2q3 - ay) - 4.0 * q[1] * (1.0 - 2.0 * q1q1 - 2.0 * q2q2 - az) + _2bz * q[3] * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (_2bx * q[2] + _2bz * q[0]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + (_2bx * q[3] - _4bz * q[1]) * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
    #                     s2 = -_2q0 * (2.0 * q1q3 - _2q0q2 - ax) + _2q3 * (2.0 * q0q1 + _2q2q3 - ay) - 4.0 * q[2] * (1.0 - 2.0 * q1q1 - 2.0 * q2q2 - az) + (-_4bx * q[2] - _2bz * q[0]) * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (_2bx * q[1] + _2bz * q[3]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + (_2bx * q[0] - _4bz * q[2]) * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
    #                     s3 = _2q1 * (2.0 * q1q3 - _2q0q2 - ax) + _2q2 * (2.0 * q0q1 + _2q2q3 - ay) + (-_4bx * q[3] + _2bz * q[1]) * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (-_2bx * q[0] + _2bz * q[2]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + _2bx * q[1] * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
                        
    #                     norm_step = math.sqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3)
    #                     if norm_step > 0.0:
    #                         s0 /= norm_step; s1 /= norm_step; s2 /= norm_step; s3 /= norm_step
    #                         qDot1 -= self.beta * s0; qDot2 -= self.beta * s1; qDot3 -= self.beta * s2; qDot4 -= self.beta * s3

    #             q[0] += qDot1 * dt; q[1] += qDot2 * dt; q[2] += qDot3 * dt; q[3] += qDot4 * dt
    #             norm_q = math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3])
    #             self.q = q / norm_q

    #         def get_euler_degrees(self):
    #             w, x, y, z = self.q
    #             roll = math.atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
    #             sinp = max(-1.0, min(1.0, 2*(w*y - z*x))) 
    #             pitch = math.asin(sinp)
    #             yaw = math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
    #             return math.degrees(roll), math.degrees(pitch), (math.degrees(yaw) - 5.0 + 360.0) % 360.0

    #     # --- Plotting Configuration ---
    #     TARGET_SENSORS = ("R_Hip", "R_Shank", "R_Ankle", "L_Hip", "L_Shank", "L_Ankle")
    #     IGNORE_SECONDS = 6.0
    #     DEFAULT_DT = 0.01

    #     try:
    #         df = pd.read_csv(self.csv_file_path)
    #     except Exception as e:
    #         tk.Label(self.graph_frame, text=f"Error loading CSV:\n{e}", fg="red").pack()
    #         return

    #     grid_positions = {"R_Hip": (0, 0), "R_Shank": (0, 1), "R_Ankle": (0, 2),
    #                       "L_Hip": (1, 0), "L_Shank": (1, 1), "L_Ankle": (1, 2)}

    #     # Define the figure explicitly and save to self.fig
    #     self.fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharex=True)
    #     self.fig.suptitle(f"Kinematic Deviation From Baseline - {os.path.basename(self.csv_file_path)}", fontsize=16, fontweight='bold')

    #     for sensor in TARGET_SENSORS:
    #         df_sensor = df[df['sensor_name'] == sensor].copy()
    #         if df_sensor.empty: continue
                
    #         start_time = df_sensor['esp32_hw_time'].iloc[0]
    #         time_sec = (df_sensor['esp32_hw_time'] - start_time) / 1000.0

    #         # DMP Calc
    #         w, x, y, z = df_sensor['q0'], df_sensor['q1'], df_sensor['q2'], df_sensor['q3']
    #         dmp_roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x**2 + y**2)))
    #         sinp = np.clip(2 * (w * y - z * x), -1.0, 1.0)
    #         dmp_pitch = np.degrees(np.arcsin(sinp))
    #         dmp_yaw = (np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y**2 + z**2))) + 360.0) % 360.0

    #         # Madgwick Calc
    #         filter_9dof = Madgwick9DoF()
    #         madg_roll, madg_pitch, madg_yaw = [], [], []
    #         last_mx, last_my, last_mz = 0.0, 0.0, 0.0
    #         last_timestamp = df_sensor['esp32_hw_time'].iloc[0]
            
    #         for i in range(len(df_sensor)):
    #             current_timestamp = df_sensor['esp32_hw_time'].iloc[i]
    #             dt = DEFAULT_DT if i == 0 else (current_timestamp - last_timestamp) / 1000.0
    #             if dt <= 0.0 or dt > 0.5: dt = DEFAULT_DT
    #             last_timestamp = current_timestamp

    #             filter_9dof.beta = 5.0 if ((current_timestamp - start_time) / 1000.0) < 2.0 else 0.15

    #             ax_val, ay_val, az_val = df_sensor['ax'].iloc[i], df_sensor['ay'].iloc[i], df_sensor['az'].iloc[i]
    #             gx, gy, gz = math.radians(df_sensor['gx'].iloc[i]), math.radians(df_sensor['gy'].iloc[i]), math.radians(df_sensor['gz'].iloc[i])
    #             mx_val, my_val, mz_val = df_sensor['mx'].iloc[i], df_sensor['my'].iloc[i], df_sensor['mz'].iloc[i]
                
    #             if mx_val != 0.0 or my_val != 0.0 or mz_val != 0.0:
    #                 last_mx, last_my, last_mz = mx_val, my_val, mz_val
                
    #             filter_9dof.update_9dof(gx, gy, gz, ax_val, ay_val, az_val, last_mx, last_my, last_mz, dt)
    #             r, p, y_deg = filter_9dof.get_euler_degrees()
    #             madg_roll.append(r); madg_pitch.append(p); madg_yaw.append(y_deg)

    #         # Filtering and Masking
    #         valid_mask = time_sec >= IGNORE_SECONDS
    #         time_sec = time_sec[valid_mask]
            
    #         t_pose_mask = (df_sensor['t_pose_flag'].values == 1)[valid_mask] if 't_pose_flag' in df_sensor.columns else np.zeros(len(time_sec), dtype=bool)

    #         dmp_roll = dmp_roll[valid_mask]
    #         dmp_pitch = dmp_pitch[valid_mask]
    #         dmp_yaw = np.degrees(np.unwrap(np.radians(dmp_yaw[valid_mask])))
            
    #         madg_roll = np.array(madg_roll)[valid_mask]
    #         madg_pitch = np.array(madg_pitch)[valid_mask]
    #         madg_yaw = np.degrees(np.unwrap(np.radians(np.array(madg_yaw)[valid_mask])))

    #         # Alignment and Fusion
    #         if np.any(t_pose_mask):
    #             yaw_offset = np.mean(dmp_yaw[t_pose_mask] - madg_yaw[t_pose_mask])
    #             dmp_yaw_aligned = dmp_yaw - yaw_offset
    #         else:
    #             dmp_yaw_aligned = dmp_yaw 
                
    #         ALPHA = 0.98 
    #         fused_roll = (ALPHA * dmp_roll) + ((1.0 - ALPHA) * madg_roll)
    #         fused_pitch = (ALPHA * dmp_pitch) + ((1.0 - ALPHA) * madg_pitch)
    #         fused_yaw = (ALPHA * dmp_yaw_aligned) + ((1.0 - ALPHA) * madg_yaw)

    #         # --- NEW LAYER: ZERO ALL THREE FUSED AXES AGAINST T-POSE BASELINE ---
    #         if np.any(t_pose_mask):
    #             baseline_roll = np.mean(fused_roll[t_pose_mask])
    #             baseline_pitch = np.mean(fused_pitch[t_pose_mask])
    #             baseline_yaw = np.mean(fused_yaw[t_pose_mask])
    #         else:
    #             # Failsafe fallback: if no T-pose flag exists, zero relative to the first valid row
    #             baseline_roll = fused_roll[0] if len(fused_roll) > 0 else 0.0
    #             baseline_pitch = fused_pitch[0] if len(fused_pitch) > 0 else 0.0
    #             baseline_yaw = fused_yaw[0] if len(fused_yaw) > 0 else 0.0

    #         # Calculate relative angular change from the posture baseline
    #         change_roll = fused_roll - baseline_roll
    #         change_pitch = fused_pitch - baseline_pitch
    #         change_yaw = fused_yaw - baseline_yaw

    #         # Calculate relative angular change from the posture baseline
    #         change_roll = fused_roll - baseline_roll
    #         change_pitch = fused_pitch - baseline_pitch
    #         change_yaw = fused_yaw - baseline_yaw

    #         # --- NEW LAYER: INVERT LEFT SENSOR DATA ---
    #         # Compensate for 180-degree physical mounting mirror
    #         if sensor.startswith("R_"):
    #             change_roll = -change_roll
    #             change_pitch = -change_pitch
    #             change_yaw = -change_yaw

    #         # Plotting
    #         if sensor in grid_positions:
    #             row, col = grid_positions[sensor]
    #             ax = axes[row][col]
    #             ax.set_title(f"{sensor}", fontweight='bold')
    #             ax.grid(True, linestyle='--', alpha=0.6)
                
    #             # Updated to plot the relative changes from zero origin
    #             ax.plot(time_sec, change_roll, label="𝚫 Roll (Side-Side)", color='#FF4B4B', linewidth=2.0)
    #             ax.plot(time_sec, change_pitch, label="𝚫 Pitch (Flexion)", color='#4CAF50', linewidth=2.0)
    #             ax.plot(time_sec, change_yaw, label="𝚫 Yaw (Rotation)", color='#008CBA', linewidth=2.0)
                
    #             if np.any(t_pose_mask):
    #                 # Draw a solid horizontal line highlighting the true 0.0 reference line
    #                 ax.axhline(0.0, color='black', linestyle='-', linewidth=1.0, alpha=0.7)
    #                 ax.fill_between(time_sec, ax.get_ylim()[0], ax.get_ylim()[1], where=t_pose_mask, color='yellow', alpha=0.15, label="T-Pose Window")
                
    #             if row == 0 and col == 0: ax.legend(loc="upper right", fontsize='small', ncol=2)
    #             if row == 1: ax.set_xlabel("Hardware Time (Seconds)", fontweight='bold')
    #             if col == 0: ax.set_ylabel("Angular Deviation (°)", fontweight='bold')

    #     for col in range(3):
    #         ax_right = axes[0][col]
    #         ax_left = axes[1][col]
                
    #         # Fetch the auto-scaled limits from both the top and bottom graphs
    #         r_min, r_max = ax_right.get_ylim()
    #         l_min, l_max = ax_left.get_ylim()
                
    #         # Find the absolute extremes across both sensors
    #         common_min = min(r_min, l_min)
    #         common_max = max(r_max, l_max)
            
    #         # Force both graphs to use this identical window
    #         ax_right.set_ylim(common_min, common_max)
    #         ax_left.set_ylim(common_min, common_max)

    #     self.fig.tight_layout()

    #     # Embed into Tkinter
    #     canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
    #     canvas.draw()
    #     canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    #     toolbar = NavigationToolbar2Tk(canvas, self.graph_frame)
    #     toolbar.update()
    #     canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    def generate_plot(self):
        import pandas as pd
        import matplotlib.pyplot as plt
        import numpy as np
        import math
        
        # --- Local Madgwick Class ---
        class Madgwick9DoF:
            def __init__(self, beta=0.15):
                self.beta = beta
                self.q = np.array([1.0, 0.0, 0.0, 0.0])

            def update_9dof(self, gx, gy, gz, ax, ay, az, mx, my, mz, dt):
                q = self.q
                qDot1 = 0.5 * (-q[1] * gx - q[2] * gy - q[3] * gz)
                qDot2 = 0.5 * (q[0] * gx + q[2] * gz - q[3] * gy)
                qDot3 = 0.5 * (q[0] * gy - q[1] * gz + q[3] * gx)
                qDot4 = 0.5 * (q[0] * gz + q[1] * gy - q[2] * gx)

                if not (ax == 0.0 and ay == 0.0 and az == 0.0):
                    norm_acc = math.sqrt(ax * ax + ay * ay + az * az)
                    ax /= norm_acc; ay /= norm_acc; az /= norm_acc

                    norm_mag = math.sqrt(mx * mx + my * my + mz * mz)
                    if norm_mag > 0.0:
                        mx /= norm_mag; my /= norm_mag; mz /= norm_mag
                        _2q0mx = 2.0 * q[0] * mx; _2q0my = 2.0 * q[0] * my; _2q0mz = 2.0 * q[0] * mz
                        _2q1mx = 2.0 * q[1] * mx; _2q0 = 2.0 * q[0]; _2q1 = 2.0 * q[1]; _2q2 = 2.0 * q[2]
                        _2q3 = 2.0 * q[3]; _2q0q2 = 2.0 * q[0] * q[2]; _2q2q3 = 2.0 * q[2] * q[3]
                        q0q0 = q[0] * q[0]; q0q1 = q[0] * q[1]; q0q2 = q[0] * q[2]; q0q3 = q[0] * q[3]
                        q1q1 = q[1] * q[1]; q1q2 = q[1] * q[2]; q1q3 = q[1] * q[3]
                        q2q2 = q[2] * q[2]; q2q3 = q[2] * q[3]; q3q3 = q[3] * q[3]

                        hx = mx * q0q0 - _2q0my * q[3] + _2q0mz * q[2] + mx * q1q1 + _2q1 * my * q[2] + _2q1 * mz * q[3] - mx * q2q2 - mx * q3q3
                        hy = _2q0mx * q[3] + my * q0q0 - _2q0mz * q[1] + _2q1mx * q[2] - my * q1q1 + my * q2q2 + _2q2 * mz * q[3] - my * q3q3
                        _2bx = math.sqrt(hx * hx + hy * hy)
                        _2bz = -_2q0mx * q[2] + _2q0my * q[1] + mz * q0q0 + _2q1mx * q[3] - mz * q1q1 + _2q2 * my * q[3] - mz * q2q2 + mz * q3q3
                        _4bx = 2.0 * _2bx; _4bz = 2.0 * _2bz

                        s0 = -_2q2 * (2.0 * q1q3 - _2q0q2 - ax) + _2q1 * (2.0 * q0q1 + _2q2q3 - ay) - _2bz * q[2] * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (-_2bx * q[3] + _2bz * q[1]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + _2bx * q[2] * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
                        s1 = _2q3 * (2.0 * q1q3 - _2q0q2 - ax) + _2q0 * (2.0 * q0q1 + _2q2q3 - ay) - 4.0 * q[1] * (1.0 - 2.0 * q1q1 - 2.0 * q2q2 - az) + _2bz * q[3] * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (_2bx * q[2] + _2bz * q[0]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + (_2bx * q[3] - _4bz * q[1]) * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
                        s2 = -_2q0 * (2.0 * q1q3 - _2q0q2 - ax) + _2q3 * (2.0 * q0q1 + _2q2q3 - ay) - 4.0 * q[2] * (1.0 - 2.0 * q1q1 - 2.0 * q2q2 - az) + (-_4bx * q[2] - _2bz * q[0]) * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (_2bx * q[1] + _2bz * q[3]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + (_2bx * q[0] - _4bz * q[2]) * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
                        s3 = _2q1 * (2.0 * q1q3 - _2q0q2 - ax) + _2q2 * (2.0 * q0q1 + _2q2q3 - ay) + (-_4bx * q[3] + _2bz * q[1]) * (_2bx * (0.5 - q2q2 - q3q3) + _2bz * (q1q3 - q0q2) - mx) + (-_2bx * q[0] + _2bz * q[2]) * (_2bx * (q1q2 - q0q3) + _2bz * (q0q1 + q2q3) - my) + _2bx * q[1] * (_2bx * (q0q2 + q1q3) + _2bz * (0.5 - q1q1 - q2q2) - mz)
                        
                        norm_step = math.sqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3)
                        if norm_step > 0.0:
                            s0 /= norm_step; s1 /= norm_step; s2 /= norm_step; s3 /= norm_step
                            qDot1 -= self.beta * s0; qDot2 -= self.beta * s1; qDot3 -= self.beta * s2; qDot4 -= self.beta * s3

                q[0] += qDot1 * dt; q[1] += qDot2 * dt; q[2] += qDot3 * dt; q[3] += qDot4 * dt
                norm_q = math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3])
                self.q = q / norm_q

            def get_euler_degrees(self):
                w, x, y, z = self.q
                roll = math.atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
                sinp = max(-1.0, min(1.0, 2*(w*y - z*x))) 
                pitch = math.asin(sinp)
                yaw = math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
                return math.degrees(roll), math.degrees(pitch), (math.degrees(yaw) - 5.0 + 360.0) % 360.0

        # --- Plotting Configuration ---
        TARGET_SENSORS = ("R_Hip", "R_Shank", "R_Ankle", "L_Hip", "L_Shank", "L_Ankle")
        IGNORE_SECONDS = 6.0
        DEFAULT_DT = 0.01

        try:
            self.status_label.config(text="Reading CSV File from Disk...")
            self.update_idletasks()
            df = pd.read_csv(self.csv_file_path)
        except Exception as e:
            self.status_label.config(text=f"Error loading CSV:\n{e}", fg="red")
            return

        grid_positions = {"R_Hip": (0, 0), "R_Shank": (0, 1), "R_Ankle": (0, 2),
                          "L_Hip": (1, 0), "L_Shank": (1, 1), "L_Ankle": (1, 2)}

        self.fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharex=True)
        self.fig.suptitle(f"Kinematic Deviation From Baseline - {os.path.basename(self.csv_file_path)}", fontsize=16, fontweight='bold')

        total_sensors = len(TARGET_SENSORS)

        for idx, sensor in enumerate(TARGET_SENSORS):
            
            # Update Macro Progress
            self.status_label.config(text=f"Processing Node {idx+1}/6: {sensor}")
            self.update_idletasks()
            
            df_sensor = df[df['sensor_name'] == sensor].copy()
            if df_sensor.empty: continue
                
            start_time = df_sensor['esp32_hw_time'].iloc[0]
            time_sec = (df_sensor['esp32_hw_time'] - start_time) / 1000.0

            # DMP Calc
            w, x, y, z = df_sensor['q0'], df_sensor['q1'], df_sensor['q2'], df_sensor['q3']
            dmp_roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x**2 + y**2)))
            sinp = np.clip(2 * (w * y - z * x), -1.0, 1.0)
            dmp_pitch = np.degrees(np.arcsin(sinp))
            dmp_yaw = (np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y**2 + z**2))) + 360.0) % 360.0

            # Madgwick Calc
            filter_9dof = Madgwick9DoF()
            madg_roll, madg_pitch, madg_yaw = [], [], []
            last_mx, last_my, last_mz = 0.0, 0.0, 0.0
            last_timestamp = df_sensor['esp32_hw_time'].iloc[0]
            
            total_rows = len(df_sensor)
            
            for i in range(total_rows):
                # --- NEW: Micro Progress Update every 200 rows ---
                if i % 200 == 0:
                    base_progress = (idx / total_sensors) * 100
                    sub_progress = (i / total_rows) * (100 / total_sensors)
                    self.progress_var.set(base_progress + sub_progress)
                    self.update_idletasks()
                # -------------------------------------------------

                current_timestamp = df_sensor['esp32_hw_time'].iloc[i]
                dt = DEFAULT_DT if i == 0 else (current_timestamp - last_timestamp) / 1000.0
                if dt <= 0.0 or dt > 0.5: dt = DEFAULT_DT
                last_timestamp = current_timestamp

                filter_9dof.beta = 5.0 if ((current_timestamp - start_time) / 1000.0) < 2.0 else 0.15

                ax_val, ay_val, az_val = df_sensor['ax'].iloc[i], df_sensor['ay'].iloc[i], df_sensor['az'].iloc[i]
                gx, gy, gz = math.radians(df_sensor['gx'].iloc[i]), math.radians(df_sensor['gy'].iloc[i]), math.radians(df_sensor['gz'].iloc[i])
                mx_val, my_val, mz_val = df_sensor['mx'].iloc[i], df_sensor['my'].iloc[i], df_sensor['mz'].iloc[i]
                
                if mx_val != 0.0 or my_val != 0.0 or mz_val != 0.0:
                    last_mx, last_my, last_mz = mx_val, my_val, mz_val
                
                filter_9dof.update_9dof(gx, gy, gz, ax_val, ay_val, az_val, last_mx, last_my, last_mz, dt)
                r, p, y_deg = filter_9dof.get_euler_degrees()
                madg_roll.append(r); madg_pitch.append(p); madg_yaw.append(y_deg)

            # Filtering and Masking
            valid_mask = time_sec >= IGNORE_SECONDS
            time_sec = time_sec[valid_mask]
            
            t_pose_mask = (df_sensor['t_pose_flag'].values == 1)[valid_mask] if 't_pose_flag' in df_sensor.columns else np.zeros(len(time_sec), dtype=bool)

            dmp_roll = dmp_roll[valid_mask]
            dmp_pitch = dmp_pitch[valid_mask]
            dmp_yaw = np.degrees(np.unwrap(np.radians(dmp_yaw[valid_mask])))
            
            madg_roll = np.array(madg_roll)[valid_mask]
            madg_pitch = np.array(madg_pitch)[valid_mask]
            madg_yaw = np.degrees(np.unwrap(np.radians(np.array(madg_yaw)[valid_mask])))

            # Alignment and Fusion
            if np.any(t_pose_mask):
                yaw_offset = np.mean(dmp_yaw[t_pose_mask] - madg_yaw[t_pose_mask])
                dmp_yaw_aligned = dmp_yaw - yaw_offset
            else:
                dmp_yaw_aligned = dmp_yaw 
                
            ALPHA = 0.98 
            fused_roll = (ALPHA * dmp_roll) + ((1.0 - ALPHA) * madg_roll)
            fused_pitch = (ALPHA * dmp_pitch) + ((1.0 - ALPHA) * madg_pitch)
            fused_yaw = (ALPHA * dmp_yaw_aligned) + ((1.0 - ALPHA) * madg_yaw)

            if np.any(t_pose_mask):
                baseline_roll = np.mean(fused_roll[t_pose_mask])
                baseline_pitch = np.mean(fused_pitch[t_pose_mask])
                baseline_yaw = np.mean(fused_yaw[t_pose_mask])
            else:
                baseline_roll = fused_roll[0] if len(fused_roll) > 0 else 0.0
                baseline_pitch = fused_pitch[0] if len(fused_pitch) > 0 else 0.0
                baseline_yaw = fused_yaw[0] if len(fused_yaw) > 0 else 0.0

            change_roll = fused_roll - baseline_roll
            change_pitch = fused_pitch - baseline_pitch
            change_yaw = fused_yaw - baseline_yaw

            if sensor.startswith("R_"):
                change_roll = -change_roll
                change_pitch = -change_pitch
                change_yaw = -change_yaw

            # Plotting
            if sensor in grid_positions:
                row, col = grid_positions[sensor]
                ax = axes[row][col]
                ax.set_title(f"{sensor}", fontweight='bold')
                ax.grid(True, linestyle='--', alpha=0.6)
                
                ax.plot(time_sec, change_roll, label="𝚫 Roll (Side-Side)", color='#FF4B4B', linewidth=2.0)
                ax.plot(time_sec, change_pitch, label="𝚫 Pitch (Flexion)", color='#4CAF50', linewidth=2.0)
                ax.plot(time_sec, change_yaw, label="𝚫 Yaw (Rotation)", color='#008CBA', linewidth=2.0)
                
                if np.any(t_pose_mask):
                    ax.axhline(0.0, color='black', linestyle='-', linewidth=1.0, alpha=0.7)
                    ax.fill_between(time_sec, ax.get_ylim()[0], ax.get_ylim()[1], where=t_pose_mask, color='yellow', alpha=0.15, label="T-Pose Window")
                
                if row == 0 and col == 0: ax.legend(loc="upper right", fontsize='small', ncol=2)
                if row == 1: ax.set_xlabel("Hardware Time (Seconds)", fontweight='bold')
                if col == 0: ax.set_ylabel("Angular Deviation (°)", fontweight='bold')

        # Final Update
        self.status_label.config(text="Synchronizing Graph Limits & Rendering...")
        self.progress_var.set(100)
        self.update_idletasks()

        for col in range(3):
            ax_right = axes[0][col]
            ax_left = axes[1][col]
            
            r_min, r_max = ax_right.get_ylim()
            l_min, l_max = ax_left.get_ylim()
            
            common_min = min(r_min, l_min)
            common_max = max(r_max, l_max)
        
            ax_right.set_ylim(common_min, common_max)
            ax_left.set_ylim(common_min, common_max)

        self.fig.tight_layout()

        # --- NEW: Destroy the loading panel before showing the graphs ---
        self.loading_frame.destroy()

        # Embed into Tkinter
        canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(canvas, self.graph_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_close(self):
        import matplotlib.pyplot as plt
        if self.fig:
            plt.close(self.fig) # Free the memory!
        self.destroy()

if __name__ == "__main__":
    app = IMUDashboard()
    app.mainloop()