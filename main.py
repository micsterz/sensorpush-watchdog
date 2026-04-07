import os
import requests
from flask import Flask

app = Flask(__name__)

# --- SETTINGS ---
TARGET_SENSOR_NAME = "*Finished Goods"
SAFE_MIN_C = 15.0 
SAFE_MAX_C = 25.0
LOW_BATTERY_THRESHOLD = 2.6
# ----------------

@app.route("/", methods=["GET", "POST"])
def run_watchdog(request=None):
    try:
        EMAIL = os.environ.get('SENSORPUSH_EMAIL')
        PASSWORD = os.environ.get('SENSORPUSH_PASSWORD')
        SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')

        # 1. Auth
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
        
        return "Check Complete", 200
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
