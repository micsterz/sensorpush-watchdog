import os
import requests

# --- SETTINGS ---
TARGET_SENSOR_NAME = "*Finished Goods" 
SAFE_MIN_C = 16.0 
SAFE_MAX_C = 25.0
# ----------------

EMAIL = os.environ.get('SENSORPUSH_EMAIL')
PASSWORD = os.environ.get('SENSORPUSH_PASSWORD')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')

def run_watchdog():
    # 1. Authenticate with SensorPush
    auth_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/authorize", 
                              json={"email": EMAIL, "password": PASSWORD}).json()
    
    token_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/accesstoken", 
                               json={"authorization": auth_resp['authorization']}).json()
    
    headers = {"Authorization": f"Bearer {token_resp['accesstoken']}"}

    # 2. Map IDs to Friendly Names
    sensor_info = requests.post("https://api.sensorpush.com/api/v1/devices/sensors", 
                                json={}, headers=headers).json()
    
    # 3. Get the latest samples
    samples = requests.post("https://api.sensorpush.com/api/v1/samples", 
                            json={"limit": 1}, headers=headers).json()

    # 4. Filter for specific room and check bounds
    for sensor_id, readings in samples['sensors'].items():
        if not readings: continue
        
        current_name = sensor_info.get(sensor_id, {}).get('name', "Unknown")
        
        if current_name == TARGET_SENSOR_NAME:
            temp_f = readings[0]['temperature']
            temp_c = round((temp_f - 32) * 5/9, 2)
            
            # ALERT LOGIC: Only posts to Slack if outside safe range
            if temp_c > SAFE_MAX_C:
                msg = f"🔥 *ALERT:* {current_name} is TOO HOT ({temp_c}°C). Max: {SAFE_MAX_C}°C"
                requests.post(SLACK_WEBHOOK, json={"text": msg})
            
            elif temp_c < SAFE_MIN_C:
                msg = f"❄️ *ALERT:* {current_name} is TOO COLD ({temp_c}°C). Min: {SAFE_MIN_C}°C"
                requests.post(SLACK_WEBHOOK, json={"text": msg})
            
            # Found the target, stop the loop
            break

if __name__ == "__main__":
    run_watchdog()
