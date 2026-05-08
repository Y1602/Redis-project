import requests
import time
import os

# FastAPI 接口地址（app容器内可解析服务名）
ACCESSGUARD_URL = os.getenv("ACCESSGUARD_URL", "http://accessguard-app:5000/logs/ingest")

# Nginx 日志文件路径（挂载卷后）
NGINX_LOG_PATH = os.getenv("NGINX_LOG_PATH", "/var/log/nginx/access.log")

# 每秒发送一次
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", 1))

def tail_logs(file_path, last_pos=0):
    """读取日志文件新增行"""
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
