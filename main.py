import os
import requests

# --- SETTINGS ---
TARGET_SENSOR_NAME = "7C - Temp Dry" 
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
        
        current_name = sensor_info.get(sensor_id, {}).get('name', "Unknown")
        
        if current_name == TARGET_SENSOR_NAME:
            temp_f = readings[0]['temperature']
            temp_c = round((temp_f - 32) * 5/9, 2)
            
            # CHECK BOUNDS
            if temp_c > SAFE_MAX_C:
                msg = f"🔥 *ALERT:* {current_name} is TOO HOT ({temp_c}°C)"
            elif temp_c < SAFE_MIN_C:
                msg = f"❄️ *ALERT:* {current_name} is TOO COLD ({temp_c}°C)"
            else:
                # THIS IS YOUR "JUST RIGHT" MESSAGE
                msg = f"✅ *STATUS:* {current_name} is {temp_c}°C (Within 16-25°C range)"
            
            # Send whatever message was generated to Slack
            requests.post(SLACK_WEBHOOK, json={"text": msg})
            break

if __name__ == "__main__":
    run_watchdog()
