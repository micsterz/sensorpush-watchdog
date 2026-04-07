import os
import requests

# --- SETTINGS ---
TARGET_SENSOR_NAME = "*Finished Goods"  # Exact name from SensorPush app
SAFE_MIN_C = 15.0 
SAFE_MAX_C = 25.0
LOW_BATTERY_THRESHOLD = 2.6  # Alert if battery falls below 2.6V
# ----------------

EMAIL = os.environ.get('SENSORPUSH_EMAIL')
PASSWORD = os.environ.get('SENSORPUSH_PASSWORD')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')

def run_watchdog():
    try:
        # 1. Authenticate with SensorPush
        auth_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/authorize", 
                                  json={"email": EMAIL, "password": PASSWORD}).json()
        
        token_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/accesstoken", 
                                   json={"authorization": auth_resp['authorization']}).json()
        
        headers = {"Authorization": f"Bearer {token_resp['accesstoken']}"}

        # 2. Get Sensor Details (Battery info)
        sensor_data = requests.post("https://api.sensorpush.com/api/v1/devices/sensors", 
                                    json={}, headers=headers).json()
        
        # 3. Get latest samples (Temperature info)
        samples = requests.post("https://api.sensorpush.com/api/v1/samples", 
                                json={"limit": 1}, headers=headers).json()

        # 4. Filter for specific room and check bounds
        for sensor_id, readings in samples['sensors'].items():
            if not readings: continue
            
            # Look up sensor info using the ID
            info = sensor_data.get(sensor_id, {})
            current_name = info.get('name', "Unknown")
            battery_v = info.get('battery_voltage')
            
            if current_name == TARGET_SENSOR_NAME:
                temp_f = readings[0]['temperature']
                temp_c = round((temp_f - 32) * 5/9, 2)
                
                # --- TEMPERATURE CHECK ---
                if temp_c > SAFE_MAX_C:
                    requests.post(SLACK_WEBHOOK, json={"text": f"🔥 *ALERT:* {current_name} is TOO HOT ({temp_c}°C). Limit: {SAFE_MAX_C}°C"})
                elif temp_c < SAFE_MIN_C:
                    requests.post(SLACK_WEBHOOK, json={"text": f"❄️ *ALERT:* {current_name} is TOO COLD ({temp_c}°C). Limit: {SAFE_MIN_C}°C"})
                
                # --- BATTERY CHECK ---
                if battery_v and
