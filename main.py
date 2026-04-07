import os
import requests

# --- SETTINGS ---
TARGET_SENSOR_NAME = "7C - Temp Dry"  # <--- Change this to match your app exactly
SAFE_MIN_C = 16.0 
SAFE_MAX_C = 25.0
# ----------------

EMAIL = os.environ.get('SENSORPUSH_EMAIL')
PASSWORD = os.environ.get('SENSORPUSH_PASSWORD')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')

def run_watchdog():
    # 1. Authenticate
    auth_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/authorize", 
                              json={"email": EMAIL, "password": PASSWORD}).json()
    token_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/accesstoken", 
                               json={"authorization": auth_resp['authorization']}).json()
    headers = {"Authorization": f"Bearer {token_resp['accesstoken']}"}

    # 2. Get Sensor Names
    sensor_info = requests.post("https://api.sensorpush.com/api/v1/devices/sensors", 
                                json={}, headers=headers).json()
    
    # 3. Get latest samples
    samples = requests.post("https://api.sensorpush.com/api/v1/samples", 
                            json={"limit": 1}, headers=headers).json()

    # 4. Filter and Process
    for sensor_id, readings in samples['sensors'].items():
        if not readings: continue
        
        # Look up the name for this ID
        current_name = sensor_info.get(sensor_id, {}).get('name', "Unknown")
        
        # ONLY proceed if the name matches our Target
        if current_name == TARGET_SENSOR_NAME:
            temp_f = readings[0]['temperature']
            temp_c = round((temp_f - 32) * 5/9, 2)
            
            if temp_c > SAFE_MAX_C or temp_c < SAFE_MIN_C:
                status = "🚨 ALERT: FINISHED GOODS ROOM"
                msg = f"{status}\nTemperature: {temp_c}°C\nRange: {SAFE_MIN_C}°C to {SAFE_MAX_C}°C"
                requests.post(SLACK_WEBHOOK, json={"text": msg})
            
            # Since we found our target, we can stop looking
            break

if __name__ == "__main__":
    run_watchdog()
