import re
import time
from datetime import datetime,timedelta
import os
import redis
import pymysql


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
        self.mysql_client = MySQLClient()

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
        score = int(self.redis_client.zscore(f'risk:rank:{datetime.now().date()}', self.ip))
        if score is not None and score >= 20:
            ban_start = datetime.now()
            ban_end = ban_start + timedelta(seconds=60)
            self.redis_client.setex(f'ban:ip:{self.ip}', 60, 1)
            print(f"{self.ip}风险分达到阈值，加入黑名单60秒")

            # 同时写入 MySQL
            self.mysql_client.save_ban_history(
                ip=self.ip,
                ban_start=ban_start,
                ban_end=ban_end,
                reason="风险分超过阈值"
            )

    def risk_rank(self):
        top_scores = self.redis_client.zrevrangebyscore(
            f'risk:rank:{datetime.now().date()}',
            "+inf",
            0,
            withscores=True
        )
        print("查看风险排行榜（降序）：", top_scores)

class MySQLClient:
    def __init__(self):
        self.conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "mysql"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "123456"),
            db=os.getenv("MYSQL_DB", "accessguard"),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    def save_risk_event(self, ip, path, status_code, risk_score):
        with self.conn.cursor() as cur:
            sql = "INSERT INTO risk_events (ip,path,status_code,risk_score) VALUES (%s,%s,%s,%s)"
            cur.execute(sql, (ip,path,status_code,risk_score))
        self.conn.commit()

    def save_ban_history(self, ip, ban_start, ban_end, reason):
        with self.conn.cursor() as cur:
            sql = "INSERT INTO ban_history (ip,ban_start,ban_end,reason) VALUES (%s,%s,%s,%s)"
            cur.execute(sql, (ip,ban_start,ban_end,reason))
        self.conn.commit()