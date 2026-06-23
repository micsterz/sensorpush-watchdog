import os
import requests

# --- SETTINGS ---
TARGET_SENSOR_NAME = "*Finished Goods"
SAFE_MIN_C = 12.0 
SAFE_MAX_C = 25.0
LOW_BATTERY_THRESHOLD = 2.6

def run_watchdog():
    try:
        EMAIL = os.environ.get('SENSORPUSH_EMAIL')
        PASSWORD = os.environ.get('SENSORPUSH_PASSWORD')
        SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')

        # 1. Authenticate
        auth_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/authorize", 
                                  json={"email": EMAIL, "password": PASSWORD}).json()
        token_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/accesstoken", 
                                   json={"authorization": auth_resp['authorization']}).json()
        headers = {"Authorization": f"Bearer {token_resp['accesstoken']}"}

        # 2. Get Data
        sensor_data = requests.post("https://api.sensorpush.com/api/v1/devices/sensors", 
                                    json={}, headers=headers).json()
        samples = requests.post("https://api.sensorpush.com/api/v1/samples", 
                                json={"limit": 1}, headers=headers).json()

        # 3. Logic
        for sensor_id, readings in samples['sensors'].items():
            if not readings: continue
            info = sensor_data.get(sensor_id, {})
            if info.get('name') == TARGET_SENSOR_NAME:
                temp_c = round((readings[0]['temperature'] - 32) * 5/9, 2)
                battery_v = info.get('battery_voltage')
                
                if temp_c > SAFE_MAX_C:
                    requests.post(SLACK_WEBHOOK, json={"text": f"🔥 *ALERT:* {TARGET_SENSOR_NAME} is {temp_c}°C"})
                elif temp_c < SAFE_MIN_C:
                    requests.post(SLACK_WEBHOOK, json={"text": f"❄️ *ALERT:* {TARGET_SENSOR_NAME} is {temp_c}°C"})
                
                if battery_v and battery_v < LOW_BATTERY_THRESHOLD:
                    requests.post(SLACK_WEBHOOK, json={"text": f"🪫 *LOW BATTERY:* {TARGET_SENSOR_NAME} is {battery_v}V"})
                break
        print("Check completed successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_watchdog()
