import re
import time
from datetime import datetime
import os
import redis


class RedisProject():
    def __init__(self):
        host = os.getenv("REDIS_HOST", "redis")
        password = os.getenv("REDIS_PASSWORD", "redispwd")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))

        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True
        )

    def process(self, txt):
        if self.parse_log(txt) == True:
            if self.check_ban_ip() == True:
                return
            else:
                self.update_ip_count()
                self.record_ip_info()
                self.record_logs()
                self.active_set()
                self.calculation_risk_score()
                self.ban_ip()
                self.risk_rank()
        else:
            return

    def parse_log(self, log):
        # 示例：10.134.18.100 - - [27/Apr/2026:09:50:50 +0000] "GET /login/auth HTTP/1.1" 401 896 "-" "curl/8.18.0"
        print("接收日志信息：",log)
        match = re.search(r'(\d+\.\d+\.\d+\.\d+) - - \[(.*?)] "(\w+) (.*?) HTTP.*?" (\d{3}) \d+ "-" ".*?"', log)
        if match:
            self.ip = match.group(1)
            self.time = match.group(2)
            self.method = match.group(3)
            self.path = match.group(4)
            self.status_code = match.group(5)
            print("日志解析成功！")
            return True
        else:
            print("日志格式错误!")
            return False

    def check_ban_ip(self):
        if self.redis_client.exists(f'ban:ip:{self.ip}'):
            print("IP已被封禁，无法访问")
            return True
        return False

    def update_ip_count(self):
        self.redis_client.incr(f'ip:{self.ip}:count:{datetime.now().date()}')
        print(f'{self.ip} 访问次数加 1')

    def record_ip_info(self):
        self.redis_client.hsetnx(f'ip:{self.ip}:info', 'first_seen', f'{self.time}')
        self.redis_client.hset(f'ip:{self.ip}:info', mapping={
            'last_seen': f'{self.time}',
            'last_path': f'{self.path}',
            'last_status': f'{self.status_code}'
        })
        all_fields = self.redis_client.hgetall(f'ip:{self.ip}:info')
        print(f'{self.ip} 信息记录如下：\n{all_fields}')

    def record_logs(self):
        self.redis_client.lpush(f'ip:{self.ip}:logs',f'{self.time} {self.method} {self.path} {self.status_code}')
        self.redis_client.ltrim(f'ip:{self.ip}:logs', 0, 9)
        print(f"{self.ip}日志记录成功！")

    def active_set(self):
        self.redis_client.sadd(f'active:ip:{datetime.now().date()}', f'{self.ip}')
        result = self.redis_client.smembers(f'active:ip:{datetime.now().date()}')
        print("查询今日活跃IP：", result)

    def calculation_risk_score(self):
        score = 0
        print("开始进行本次风险分数计算...")
        if "/login" in self.path:
            score += 2
        elif "/admin" in self.path:
            score += 5
        if "401" in self.status_code:
            score += 3
        elif "403" in self.status_code:
            score += 3
        elif "500" in self.status_code:
            score += 1
        print("本次访问风险分增加 ", score)
        self.redis_client.zincrby(f'risk:rank:{datetime.now().date()}', score, self.ip)

    def ban_ip(self):
        score = int(self.redis_client.zscore(f'risk:rank:{datetime.now().date()}',self.ip))
        if score is not None:
            if score >= 20:
                self.redis_client.setex(f'ban:ip:{self.ip}', 60, 1)
                print(f"{self.ip}风险分达到阈值，加入黑名单60秒")

    def risk_rank(self):
        top_scores = self.redis_client.zrevrangebyscore(f'risk:rank:{datetime.now().date()}', 100, 0, withscores=True)
        print("查看风险排行榜（降序）：", top_scores)

txt1 = '10.134.18.100 - - [27/Apr/2026:09:50:50 +0000] "GET /login/auth HTTP/1.1" 401 896 "-" "curl/8.18.0"'
txt2 = '10.134.18.100 - - [27/Apr/2026:09:51:10 +0000] "GET /admin HTTP/1.1" 403 1024 "-" "curl/8.18.0"'
txt3 = '10.134.18.100 - - [27/Apr/2026:09:51:30 +0000] "GET /admin/settings HTTP/1.1" 403 1024 "-" "curl/8.18.0"'
txt4 = '10.134.18.100 - - [27/Apr/2026:09:51:50 +0000] "GET /login HTTP/1.1" 401 896 "-" "curl/8.18.0"'
txt5 = '10.134.18.101 - - [27/Apr/2026:09:52:10 +0000] "GET / HTTP/1.1" 200 512 "-" "Mozilla/5.0"'
txt6 = '10.134.18.101 - - [27/Apr/2026:09:52:30 +0000] "GET /api/user HTTP/1.1" 200 768 "-" "Mozilla/5.0"'
txt7 = '10.134.18.102 - - [27/Apr/2026:09:53:00 +0000] "POST /login HTTP/1.1" 200 900 "-" "PostmanRuntime/7.0"'
txt8 = '10.134.18.102 - - [27/Apr/2026:09:53:20 +0000] "GET /api/order HTTP/1.1" 500 1200 "-" "PostmanRuntime/7.0"'
txt9 = '10.134.18.103 - - [27/Apr/2026:09:54:00 +0000] "GET /admin HTTP/1.1" 200 1000 "-" "curl/8.18.0"'
txt10 = 'invalid log format test'
txt11 = '10.134.18.104 - - [27/Apr/2026:09:54:20 +0000] "GET /login HTTP/1.1" 403 880 "-" "curl/8.18.0"'
txt12 = '10.134.18.104 - - [27/Apr/2026:09:54:40 +0000] "POST /login/auth HTTP/1.1" 401 900 "-" "curl/8.18.0"'
txt13 = '10.134.18.104 - - [27/Apr/2026:09:55:00 +0000] "GET /admin HTTP/1.1" 403 1000 "-" "curl/8.18.0"'
txt14 = '10.134.18.104 - - [27/Apr/2026:09:55:20 +0000] "GET /admin/config HTTP/1.1" 403 1000 "-" "curl/8.18.0"'
txt15 = '10.134.18.105 - - [27/Apr/2026:09:55:40 +0000] "GET /api/product HTTP/1.1" 200 700 "-" "Mozilla/5.0"'
txt16 = '10.134.18.105 - - [27/Apr/2026:09:56:00 +0000] "GET /api/order HTTP/1.1" 200 760 "-" "Mozilla/5.0"'
txt17 = '10.134.18.105 - - [27/Apr/2026:09:56:20 +0000] "GET /api/cart HTTP/1.1" 200 640 "-" "Mozilla/5.0"'
txt18 = '10.134.18.106 - - [27/Apr/2026:09:56:40 +0000] "GET /admin HTTP/1.1" 200 930 "-" "curl/8.18.0"'
txt19 = '10.134.18.106 - - [27/Apr/2026:09:57:00 +0000] "GET /admin/panel HTTP/1.1" 403 930 "-" "curl/8.18.0"'
txt20 = '10.134.18.106 - - [27/Apr/2026:09:57:20 +0000] "GET /login HTTP/1.1" 401 900 "-" "curl/8.18.0"'
txt21 = '10.134.18.107 - - [27/Apr/2026:09:57:40 +0000] "GET / HTTP/1.1" 200 500 "-" "Mozilla/5.0"'
txt22 = '10.134.18.107 - - [27/Apr/2026:09:58:00 +0000] "GET /static/app.js HTTP/1.1" 200 1500 "-" "Mozilla/5.0"'
txt23 = '10.134.18.107 - - [27/Apr/2026:09:58:20 +0000] "GET /static/style.css HTTP/1.1" 200 1300 "-" "Mozilla/5.0"'
txt24 = '10.134.18.108 - - [27/Apr/2026:09:58:40 +0000] "POST /login HTTP/1.1" 401 890 "-" "PostmanRuntime/7.0"'
txt25 = '10.134.18.108 - - [27/Apr/2026:09:59:00 +0000] "POST /login HTTP/1.1" 401 890 "-" "PostmanRuntime/7.0"'
txt26 = '10.134.18.108 - - [27/Apr/2026:09:59:20 +0000] "POST /login HTTP/1.1" 401 890 "-" "PostmanRuntime/7.0"'
txt27 = '10.134.18.108 - - [27/Apr/2026:09:59:40 +0000] "GET /admin HTTP/1.1" 403 1000 "-" "PostmanRuntime/7.0"'
txt28 = '10.134.18.109 - - [27/Apr/2026:10:00:00 +0000] "GET /api/user HTTP/1.1" 500 1100 "-" "Mozilla/5.0"'
txt29 = '10.134.18.109 - - [27/Apr/2026:10:00:20 +0000] "GET /api/order HTTP/1.1" 500 1200 "-" "Mozilla/5.0"'
txt30 = '10.134.18.109 - - [27/Apr/2026:10:00:40 +0000] "GET /api/pay HTTP/1.1" 500 1300 "-" "Mozilla/5.0"'
txt31 = '10.134.18.110 - - [27/Apr/2026:10:01:00 +0000] "GET /admin HTTP/1.1" 403 1000 "-" "curl/8.18.0"'
txt32 = '10.134.18.110 - - [27/Apr/2026:10:01:20 +0000] "GET /admin/login HTTP/1.1" 401 980 "-" "curl/8.18.0"'
txt33 = '10.134.18.110 - - [27/Apr/2026:10:01:40 +0000] "GET /admin/config HTTP/1.1" 403 1000 "-" "curl/8.18.0"'
txt34 = '10.134.18.110 - - [27/Apr/2026:10:02:00 +0000] "GET /admin/users HTTP/1.1" 403 1000 "-" "curl/8.18.0"'
txt35 = '10.134.18.111 - - [27/Apr/2026:10:02:20 +0000] "GET /login HTTP/1.1" 200 900 "-" "Mozilla/5.0"'
txt36 = '10.134.18.111 - - [27/Apr/2026:10:02:40 +0000] "GET /profile HTTP/1.1" 200 950 "-" "Mozilla/5.0"'
txt37 = '10.134.18.111 - - [27/Apr/2026:10:03:00 +0000] "GET /api/message HTTP/1.1" 200 850 "-" "Mozilla/5.0"'
txt38 = '10.134.18.112 - - [27/Apr/2026:10:03:20 +0000] "GET /admin HTTP/1.1" 500 1300 "-" "curl/8.18.0"'
txt39 = '10.134.18.112 - - [27/Apr/2026:10:03:40 +0000] "GET /admin/debug HTTP/1.1" 500 1400 "-" "curl/8.18.0"'
txt40 = '10.134.18.112 - - [27/Apr/2026:10:04:00 +0000] "GET /admin/debug HTTP/1.1" 403 1400 "-" "curl/8.18.0"'
txt41 = '10.134.18.113 - - [27/Apr/2026:10:04:20 +0000] "GET / HTTP/1.1" 200 512 "-" "Mozilla/5.0"'
txt42 = '10.134.18.113 - - [27/Apr/2026:10:04:40 +0000] "GET /about HTTP/1.1" 200 620 "-" "Mozilla/5.0"'
txt43 = '10.134.18.114 - - [27/Apr/2026:10:05:00 +0000] "GET /login HTTP/1.1" 401 890 "-" "curl/8.18.0"'
txt44 = '10.134.18.114 - - [27/Apr/2026:10:05:20 +0000] "GET /login HTTP/1.1" 401 890 "-" "curl/8.18.0"'
txt45 = '10.134.18.114 - - [27/Apr/2026:10:05:40 +0000] "GET /login HTTP/1.1" 401 890 "-" "curl/8.18.0"'
txt46 = '10.134.18.114 - - [27/Apr/2026:10:06:00 +0000] "GET /login HTTP/1.1" 401 890 "-" "curl/8.18.0"'
txt47 = '10.134.18.115 - - [27/Apr/2026:10:06:20 +0000] "GET /api/search HTTP/1.1" 200 780 "-" "Mozilla/5.0"'
txt48 = '10.134.18.115 - - [27/Apr/2026:10:06:40 +0000] "GET /api/search HTTP/1.1" 200 790 "-" "Mozilla/5.0"'
txt49 = '10.134.18.116 - - [27/Apr/2026:10:07:00 +0000] "GET /admin HTTP/1.1" 403 1000 "-" "curl/8.18.0"'
txt50 = 'bad log line without nginx format'
redis_instance = RedisProject()
for i in range(1,51):
    redis_instance.process(globals()[f'txt{i}'])

