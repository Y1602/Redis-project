import os
import re
from datetime import datetime, timedelta

import pymysql
import redis


class RedisProject:
    LOG_RE = re.compile(
        r'^(?P<ip>\d{1,3}(?:\.\d{1,3}){3}) \S+ \S+ '
        r'\[(?P<time>[^\]]+)] '
        r'"(?P<request>[^"]*)" '
        r'(?P<status>\d{3}) '
        r'(?P<body_bytes>\S+) '
        r'"(?P<referer>[^"]*)" '
        r'"(?P<user_agent>[^"]*)"(?:\s+"(?P<extra>[^"]*)")?'
    )

    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", "redispwd"),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
        )
        self.mysql_client = MySQLClient()

    def process(self, txt):
        if not self.parse_log(txt):
            return False

        if self.check_ban_ip():
            return False

        self.update_ip_count()
        self.record_ip_info()
        self.record_logs()
        self.active_set()
        risk_score = self.calculation_risk_score()
        self.mysql_client.save_risk_event(
            ip=self.ip,
            path=self.path,
            status_code=int(self.status_code),
            risk_score=risk_score,
        )
        self.ban_ip()
        self.risk_rank()
        return True

    def parse_log(self, log):
        print(f"Received log: {log}", flush=True)
        match = self.LOG_RE.search(log.strip())
        if not match:
            print("Log format mismatch", flush=True)
            return False

        request = match.group("request")
        parts = request.split()
        if len(parts) < 3 or not parts[2].startswith("HTTP/"):
            print(f"Unsupported request field: {request}", flush=True)
            return False

        self.ip = match.group("ip")
        self.time = match.group("time")
        self.method = parts[0]
        self.path = parts[1]
        self.status_code = match.group("status")
        print("Log parsed successfully", flush=True)
        return True

    def check_ban_ip(self):
        if self.redis_client.exists(f"ban:ip:{self.ip}"):
            print("IP is already banned", flush=True)
            return True
        return False

    def update_ip_count(self):
        self.redis_client.incr(f"ip:{self.ip}:count:{datetime.now().date()}")
        print(f"{self.ip} count +1", flush=True)

    def record_ip_info(self):
        self.redis_client.hsetnx(f"ip:{self.ip}:info", "first_seen", self.time)
        self.redis_client.hset(
            f"ip:{self.ip}:info",
            mapping={
                "last_seen": self.time,
                "last_path": self.path,
                "last_status": self.status_code,
            },
        )

    def record_logs(self):
        self.redis_client.lpush(
            f"ip:{self.ip}:logs",
            f"{self.time} {self.method} {self.path} {self.status_code}",
        )
        self.redis_client.ltrim(f"ip:{self.ip}:logs", 0, 9)

    def active_set(self):
        self.redis_client.sadd(f"active:ip:{datetime.now().date()}", self.ip)

    def calculation_risk_score(self):
        score = 0

        if "/login" in self.path:
            score += 2
        elif "/admin" in self.path:
            score += 5

        if self.status_code in {"401", "403"}:
            score += 3
        elif self.status_code.startswith("5"):
            score += 1

        self.redis_client.zincrby(f"risk:rank:{datetime.now().date()}", score, self.ip)
        print(f"{self.ip} risk score +{score}", flush=True)
        return score

    def ban_ip(self):
        score = self.redis_client.zscore(f"risk:rank:{datetime.now().date()}", self.ip)
        if score is None or score < 20:
            return

        ban_start = datetime.now()
        ban_end = ban_start + timedelta(seconds=60)
        self.redis_client.setex(f"ban:ip:{self.ip}", 60, 1)
        print(f"{self.ip} reached risk threshold and was banned for 60s", flush=True)

        self.mysql_client.save_ban_history(
            ip=self.ip,
            ban_start=ban_start,
            ban_end=ban_end,
            reason="risk score exceeded threshold",
        )

    def risk_rank(self):
        top_scores = self.redis_client.zrevrangebyscore(
            f"risk:rank:{datetime.now().date()}",
            "+inf",
            0,
            withscores=True,
        )
        print(f"Risk rank: {top_scores}", flush=True)


class MySQLClient:
    def __init__(self):
        self.conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "mysql"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "123456"),
            db=os.getenv("MYSQL_DB", "accessguard"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        self.ensure_schema()

    def ping(self):
        self.conn.ping(reconnect=True)

    def ensure_schema(self):
        self.ping()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_events (
                  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                  ip VARCHAR(45) NOT NULL,
                  path VARCHAR(2048) NOT NULL,
                  status_code INT NOT NULL,
                  risk_score INT NOT NULL,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  KEY idx_risk_events_ip_created_at (ip, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ban_history (
                  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                  ip VARCHAR(45) NOT NULL,
                  ban_start DATETIME NOT NULL,
                  ban_end DATETIME NOT NULL,
                  reason VARCHAR(255) NOT NULL,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  KEY idx_ban_history_ip_created_at (ip, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        self.conn.commit()

    def save_risk_event(self, ip, path, status_code, risk_score):
        self.ping()
        with self.conn.cursor() as cur:
            sql = (
                "INSERT INTO risk_events (ip, path, status_code, risk_score) "
                "VALUES (%s, %s, %s, %s)"
            )
            cur.execute(sql, (ip, path, status_code, risk_score))
        self.conn.commit()

    def save_ban_history(self, ip, ban_start, ban_end, reason):
        self.ping()
        with self.conn.cursor() as cur:
            sql = (
                "INSERT INTO ban_history (ip, ban_start, ban_end, reason) "
                "VALUES (%s, %s, %s, %s)"
            )
            cur.execute(sql, (ip, ban_start, ban_end, reason))
        self.conn.commit()
