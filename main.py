import os
import requests
import sys

def api_post(url, **kwargs):
    response = requests.post(url, timeout=(10, 30), **kwargs)
    response.raise_for_status()
    return response.json()

def send_slack(webhook, text):
    # One attempt only: never replay an uncertain POST outcome.
    response = requests.post(webhook, json={"text": text}, timeout=(10, 30))
    if 200 <= response.status_code < 300 and response.text.strip() == "ok":
        print("Slack delivery confirmed.")
        return
    raise RuntimeError(f"Slack delivery not confirmed (HTTP {response.status_code}); no automatic replay.")

# --- SETTINGS ---
TARGET_SENSOR_NAME = "SP010 - Product Store"
SAFE_MIN_C = 12.0 
SAFE_MAX_C = 25.0
LOW_BATTERY_THRESHOLD = 2.6

def run_watchdog():
    try:
        EMAIL = os.environ.get('SENSORPUSH_EMAIL')
        PASSWORD = os.environ.get('SENSORPUSH_PASSWORD')
        SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')

        if not all([EMAIL, PASSWORD, SLACK_WEBHOOK]):
            raise RuntimeError('Required monitor configuration missing.')

        # 1. Authenticate
        auth_resp = api_post("https://api.sensorpush.com/api/v1/oauth/authorize", 
                                  json={"email": EMAIL, "password": PASSWORD})
        token_resp = api_post("https://api.sensorpush.com/api/v1/oauth/accesstoken", 
                                   json={"authorization": auth_resp['authorization']})
        headers = {"Authorization": f"Bearer {token_resp['accesstoken']}"}

        # 2. Get Data
        sensor_data = api_post("https://api.sensorpush.com/api/v1/devices/sensors", 
                                    json={}, headers=headers)
        samples = api_post("https://api.sensorpush.com/api/v1/samples", 
                                json={"limit": 1}, headers=headers)

        # 3. Logic
        matched = False
        if not isinstance(samples.get("sensors"), dict):
            raise RuntimeError("SensorPush samples missing from response.")
        for sensor_id, readings in samples['sensors'].items():
            if not readings: continue
            info = sensor_data.get(sensor_id, {})
            if info.get('name') == TARGET_SENSOR_NAME:
                matched = True
                temp_c = round((readings[0]['temperature'] - 32) * 5/9, 2)
                battery_v = info.get('battery_voltage')
                
                if temp_c > SAFE_MAX_C:
                    send_slack(SLACK_WEBHOOK, f"🔥 *ALERT:* {TARGET_SENSOR_NAME} is {temp_c}°C")
                elif temp_c < SAFE_MIN_C:
                    send_slack(SLACK_WEBHOOK, f"❄️ *ALERT:* {TARGET_SENSOR_NAME} is {temp_c}°C")
                
                if battery_v and battery_v < LOW_BATTERY_THRESHOLD:
                    send_slack(SLACK_WEBHOOK, f"🪫 *LOW BATTERY:* {TARGET_SENSOR_NAME} is {battery_v}V")
                break
        if not matched:
            raise RuntimeError("Configured Product Store sensor has no sample or was not found.")
        print("Sensor check completed. Target evaluated; any required Slack deliveries confirmed.")
    except Exception as e:
        # Do not print exception strings that can contain credential-bearing webhook URLs.
        print(f"Monitor failed: {type(e).__name__}. No automatic retry.", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    if os.environ.get('PRODUCT_STORE_DELIVERY_TEST') == 'true':
        webhook = os.environ.get('SLACK_WEBHOOK_URL')
        if not webhook:
            raise SystemExit('Webhook configuration missing.')
        try:
            send_slack(webhook, "TEST - Product Store alert delivery. This is a test message, not a temperature excursion. Checking the SensorPush monitor's connection to this channel.")
        except Exception as e:
            print(f"Delivery test not confirmed: {type(e).__name__}. Do not repeat without checking Slack.", file=sys.stderr)
            raise SystemExit(1)
    else:
        run_watchdog()
