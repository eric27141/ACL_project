import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt

# ==========================================
# CONFIGURATION
# ==========================================
CSV_FILE_PATH = "20260529_141503_Headless_FullBody.csv"  
TARGET_SENSORS = ("R_Hip", "R_Shank", "R_Ankle", "L_Hip", "L_Shank", "L_Ankle") 
MADGWICK_BETA = 0.05                  
SAMPLE_FREQ = 100.0                   

# ==========================================
# MADGWICK FILTER CLASS (6DOF)
# ==========================================
class Madgwick:
    def __init__(self, beta=0.033, freq=100.0):
        self.beta = beta
        self.freq = freq
        self.q = np.array([1.0, 0.0, 0.0, 0.0])

    def update_6dof(self, gx, gy, gz, ax, ay, az):
        q = self.q
        dt = 1.0 / self.freq 
        
        norm = np.sqrt(ax*ax + ay*ay + az*az)
        if norm == 0: return
        ax, ay, az = ax/norm, ay/norm, az/norm

        qDot = 0.5 * np.array([
            -q[1]*gx - q[2]*gy - q[3]*gz,
             q[0]*gx + q[2]*gz - q[3]*gy,
             q[0]*gy - q[1]*gz + q[3]*gx,
             q[0]*gz + q[1]*gy - q[2]*gx
        ])

        f = np.array([
            2*(q[1]*q[3] - q[0]*q[2]) - ax,
            2*(q[0]*q[1] + q[2]*q[3]) - ay,
            2*(0.5 - q[1]**2 - q[2]**2) - az
        ])
        J = np.array([
            [-2*q[2],  2*q[3], -2*q[0],  2*q[1]],
            [ 2*q[1],  2*q[0],  2*q[3],  2*q[2]],
            [ 0,      -4*q[1], -4*q[2],  0     ]
        ])
        step = J.T @ f

        norm_step = np.linalg.norm(step)
        if norm_step > 0:
            step /= norm_step

        qDot -= self.beta * step
        q += qDot * dt
        self.q = q / np.linalg.norm(q)

    def get_euler_degrees(self):
        w, x, y, z = self.q
        roll = math.atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))
        
        sinp = 2*(w*y - z*x)
        sinp = max(-1.0, min(1.0, sinp)) 
        pitch = math.asin(sinp)
        
        yaw = math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))
        
        return math.degrees(roll), math.degrees(pitch), (math.degrees(yaw) + 360.0) % 360.0

# ==========================================
# MAIN SCRIPT
# ==========================================
def process_and_plot():
    print(f"📂 Loading data from {CSV_FILE_PATH}...")
    try:
        df = pd.read_csv(CSV_FILE_PATH)
    except FileNotFoundError:
        print("❌ CSV file not found. Please check the file path.")
        return

    # Map sensors to specific subplot grid coordinates (Row, Col)
    grid_positions = {
        "R_Hip": (0, 0), "R_Shank": (0, 1), "R_Ankle": (0, 2),
        "L_Hip": (1, 0), "L_Shank": (1, 1), "L_Ankle": (1, 2)
    }

    # Set up the 2x3 Grid
    print("📊 Generating 6-Node Graphs...")
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True)
    fig.suptitle("Full Body Offline Kinematic Analysis (DMP vs Madgwick)", fontsize=16, fontweight='bold')

    for sensor in TARGET_SENSORS:
        print(f"🔄 Processing {sensor}...")
        
        # Extract data for just this one sensor
        df_sensor = df[df['sensor_name'] == sensor].copy()
        if df_sensor.empty:
            print(f"   ⚠️ No data found for {sensor}, skipping...")
            continue
            
        # 1. Generate Timeline
        start_time = df_sensor['esp32_hw_time'].iloc[0]
        time_sec = (df_sensor['esp32_hw_time'] - start_time) / 1000.0

        # 2. Reconstruct Eulers directly from DMP Quaternions
        w, x, y, z = df_sensor['q0'], df_sensor['q1'], df_sensor['q2'], df_sensor['q3']
        dmp_roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x**2 + y**2)))
        sinp = np.clip(2 * (w * y - z * x), -1.0, 1.0)
        dmp_pitch = np.degrees(np.arcsin(sinp))
        dmp_yaw = (np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y**2 + z**2))) + 360.0) % 360.0

        # 3. Process Raw IMU data through Madgwick
        filter_6dof = Madgwick(beta=MADGWICK_BETA, freq=SAMPLE_FREQ)
        madg_roll, madg_pitch, madg_yaw = [], [], []
        
        for i in range(len(df_sensor)):
            ax_val = df_sensor['ax'].iloc[i]
            ay_val = df_sensor['ay'].iloc[i]
            az_val = df_sensor['az'].iloc[i]
            
            gx = math.radians(df_sensor['gx'].iloc[i])
            gy = math.radians(df_sensor['gy'].iloc[i])
            gz = math.radians(df_sensor['gz'].iloc[i])
            
            filter_6dof.update_6dof(gx, gy, gz, ax_val, ay_val, az_val)
            r, p, y_deg = filter_6dof.get_euler_degrees()
            
            madg_roll.append(r)
            madg_pitch.append(p)
            madg_yaw.append(y_deg)

        # 4. Plot to the correct grid location
        if sensor in grid_positions:
            row, col = grid_positions[sensor]
            ax = axes[row][col]

            ax.set_title(f"{sensor}", fontweight='bold')
            ax.grid(True, linestyle='--', alpha=0.6)
            
            # To keep the 6 lines readable: Solid lines = DMP | Dashed = Madgwick
            ax.plot(time_sec, dmp_roll, label="DMP Roll", color='#FF4B4B', linewidth=1.5)
            ax.plot(time_sec, dmp_pitch, label="DMP Pitch", color='#4CAF50', linewidth=1.5)
            ax.plot(time_sec, dmp_yaw, label="DMP Yaw", color='#008CBA', linewidth=1.5)
            
            ax.plot(time_sec, madg_roll, label="Madg Roll", color='darkred', linestyle='--', alpha=0.8)
            ax.plot(time_sec, madg_pitch, label="Madg Pitch", color='darkgreen', linestyle='--', alpha=0.8)
            ax.plot(time_sec, madg_yaw, label="Madg Yaw", color='darkblue', linestyle='--', alpha=0.8)
            
            # Lock Y-axis boundaries
            ax.set_ylim(-180, 360) 
            
            # Only put the legend on the very first graph to save visual space
            if row == 0 and col == 0:
                ax.legend(loc="upper right", fontsize='small', ncol=2)
                
            if row == 1:
                ax.set_xlabel("Hardware Time (Seconds)", fontweight='bold')
            if col == 0:
                ax.set_ylabel("Degrees (°)", fontweight='bold')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    process_and_plot()