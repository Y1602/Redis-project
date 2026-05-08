import requests
import time

ACCESSGUARD_URL = "http://accessguard-app:5000/logs/ingest"  # Compose 网络服务名
NGINX_LOG_PATH = "/var/log/nginx/access.log"  # Nginx 容器里日志路径
SLEEP_INTERVAL = 5  # 每隔 5 秒发送一次

def tail_logs(file_path, last_pos=0):
    with open(file_path, "r") as f:
        f.seek(last_pos)
        lines = f.readlines()
        last_pos = f.tell()
    return lines, last_pos

def send_logs(lines):
    if lines:
        data = "\n".join(lines)
        try:
            response = requests.post(ACCESSGUARD_URL, data=data)
            print(f"Sent {len(lines)} lines, response: {response.json()}")
        except Exception as e:
            print(f"Error sending logs: {e}")

def main():
    last_pos = 0
    while True:
        lines, last_pos = tail_logs(NGINX_LOG_PATH, last_pos)
        send_logs(lines)
        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    main()