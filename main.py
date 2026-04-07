import os
import requests

# --- SETTINGS (In Celsius) ---
SAFE_MIN_C = 16.0 
SAFE_MAX_C = 25.0
# -----------------------------

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

    # 2. Get Sensor Names (to match IDs to Names)
    sensor_info = requests.post("https://api.sensorpush.com/api/v1/devices/sensors", 
                                json={}, headers=headers).json()
    
    # 3. Get latest samples
    samples = requests.post("https://api.sensorpush.com/api/v1/samples", 
                            json={"limit": 1}, headers=headers).json()

    # 4. Process and Convert
    for sensor_id, readings in samples['sensors'].items():
        if not readings: continue
        
        # Get friendly name from our sensor_info list, fallback to ID if not found
        sensor_name = sensor_info.get(sensor_id, {}).get('name', sensor_id)
        
        temp_f = readings[0]['temperature']
        temp_c = round((temp_f - 32) * 5/9, 2) # Convert F to C
        
        # Check thresholds in Celsius
        if temp_c > SAFE_MAX_C or temp_c < SAFE_MIN_C:
            status = "🔥 TOO HOT" if temp_c > SAFE_MAX_C else "❄️ TOO COLD"
            msg = f"{status}: *{sensor_name}* is at {temp_c}°C (Threshold: {SAFE_MIN_C}-{SAFE_MAX_C}°C)"
            requests.post(SLACK_WEBHOOK, json={"text": msg})

if __name__ == "__main__":
    run_watchdog()
