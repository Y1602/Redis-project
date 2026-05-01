import re
import time
from datetime import datetime

import redis


class RedisProject():
    def __init__(self):
        host = input("请输入Redis主机IP: ")
        password = input("请输入Redis密码: ")
        port = int(input("请输入Redis端口(默认6379): ") or '6379')
        db = int(input("请输入数据库编号(默认0): ") or '0')

        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True
        )

    def process(self, txt):
        self.parse_log(txt)
        self.check_ban_ip()
        self.update_ip_count()
        self.record_ip_info()
        self.active_set()
        self.calculation_risk_score()
        self.risk_rank()

    def parse_log(self, log):
        # 示例：156.195.148.18 - - [27/Apr/2026:09:49:50 +0000] "GET / HTTP/1.1" 200 896 "-" "curl/8.18.0" "-"
        match = re.search(r'(\d+\.\d+\.\d+\.\d+) .*? \[(.*?)] "(\w+) (.*?) .*?" (\d{3}) .*?', log)
        self.ip = match.group(1)
        self.time = match.group(2)
        self.method = match.group(3)
        self.path = match.group(4)
        self.status_code = match.group(5)
        print("日志解析成功！")

    def check_ban_ip(self):
        if self.redis_client.exists(f'ban:ip:{self.ip}'):
            print("IP已被封禁，无法访问")

    def update_ip_count(self):
        self.redis_client.incr(f'ip:{self.ip}:count')
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

    def active_set(self):
        self.redis_client.sadd(f'active:ip:{datetime.now().date()}', f'{self.ip}')
        result = self.redis_client.smembers(f'active:ip:{datetime.now().date()}')
        print("查询今日活跃IP：", result)

    def calculation_risk_score(self):
        sorce = 0
        print("开始进行本次风险分数计算...")
        if "/login" in self.path:
            sorce += 2
        elif "/admin" in self.path:
            sorce += 5
        else:
            print("日志路径识别错误")
        if "401" in self.status_code:
            sorce += 3
        elif "403" in self.status_code:
            sorce += 3
        elif "500" in self.status_code:
            sorce += 1
        else:
            print("日志状态码识别错误")
        print("本次访问风险分增加 ", sorce)
        self.redis_client.zincrby(f'risk:rank:{datetime.now().date()}', sorce, self.ip)

    def risk_rank(self):
        top_scores = self.redis_client.zrevrangebyscore(f'risk:rank:{datetime.now().date()}', 100, 0, withscores=True)
        for member, score in top_scores:
            if score >= 20:
                self.redis_client.setex(f'ban:ip:{self.ip}', 60, 1)
                print(f"{self.ip}风险分达到阈值，加入黑名单60秒")
        print("查看风险排行榜（降序）：", top_scores)


txt = "10.134.18.100 - - [27/Apr/2026:09:50:50 +0000] \"GET /login/auth HTTP/1.1\" 401 896 \"-\" \"curl/8.18.0" "-\""
redis_instance = RedisProject()
redis_instance.process(txt)
