import os
import requests

# Constants
EMAIL = os.environ.get('SENSORPUSH_EMAIL')
PASSWORD = os.environ.get('SENSORPUSH_PASSWORD')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')
SAFE_MIN = 65.0
SAFE_MAX = 75.0

def run_watchdog():
    # 1. Authenticate
    auth_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/authorize", 
                              json={"email": EMAIL, "password": PASSWORD}).json()
    
    token_resp = requests.post("https://api.sensorpush.com/api/v1/oauth/accesstoken", 
                               json={"authorization": auth_resp['authorization']}).json()
    
    headers = {"Authorization": f"Bearer {token_resp['accesstoken']}"}

    # 2. Get latest data
    samples = requests.post("https://api.sensorpush.com/api/v1/samples", 
                            json={"limit": 1}, headers=headers).json()

    # 3. Check thresholds
    for sensor_id, readings in samples['sensors'].items():
        if not readings: continue
        temp = readings[0]['temperature']
        
        if temp > SAFE_MAX or temp < SAFE_MIN:
            status = "🔥 TOO HOT" if temp > SAFE_MAX else "❄️ TOO COLD"
            msg = f"{status}: Sensor {sensor_id} is at {temp}°F"
            requests.post(SLACK_WEBHOOK, json={"text": msg})

if __name__ == "__main__":
    run_watchdog()
