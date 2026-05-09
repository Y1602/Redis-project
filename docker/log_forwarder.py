import os
import time

import requests

ACCESSGUARD_URL = os.getenv("ACCESSGUARD_URL", "http://accessguard-app:5000/logs/ingest")
NGINX_LOG_PATH = os.getenv("NGINX_LOG_PATH", "/logs/access.log")
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", 1))


def tail_logs(file_path, last_pos=0):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(last_pos)
        lines = f.readlines()
        return lines, f.tell()


def send_logs(lines):
    if not lines:
        return

    data = "".join(lines)
    response = requests.post(ACCESSGUARD_URL, data=data.encode("utf-8"), timeout=5)
    response.raise_for_status()
    print(f"Sent {len(lines)} lines, response: {response.json()}", flush=True)


def main():
    last_pos = 0

    while not os.path.exists(NGINX_LOG_PATH):
        print(f"Waiting for log file: {NGINX_LOG_PATH}", flush=True)
        time.sleep(SLEEP_INTERVAL)

    while True:
        try:
            lines, last_pos = tail_logs(NGINX_LOG_PATH, last_pos)
            send_logs(lines)
        except Exception as e:
            print(f"Error sending logs: {e}", flush=True)

        time.sleep(SLEEP_INTERVAL)


if __name__ == "__main__":
    main()
