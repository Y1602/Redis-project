# Redis-project项目简介

本项目是一个基于 Redis 的访问监控与简单风控练习项目。

项目通过 Python 模拟解析 Nginx 访问日志，将访问 IP、请求路径、状态码等信息写入 Redis，并基于 Redis 的多种数据结构实现访问统计、IP 信息记录、最近访问日志、活跃 IP 去重、风险排行榜和临时封禁功能。

该项目主要用于练习 Redis 在运维、安全监控和风控场景中的基础应用。

---

## 项目目标

通过该项目完成以下目标：

1. 熟悉 Redis 常见数据结构的使用场景
2. 理解 String、Hash、List、Set、ZSet、TTL 在实际项目中的作用
3. 使用 Python 操作 Redis
4. 模拟访问日志解析与风险评分
5. 实现简单的 IP 临时封禁机制
6. 为后续 Docker 化和 Redis 高可用实验打基础

## Docker 运行方式

当前 Docker Compose 版本包含以下容器：

- `nginx`：对外暴露 80 端口，反向代理到 Web 服务，并生成访问日志
- `web`：简单的测试 Web 服务，用于模拟客户端访问
- `accessguard`：接收日志并写入 Redis / MySQL
- `log-forwarder`：读取 Nginx access.log，发送到 AccessGuard
- `redis`：保存访问统计、IP 信息、风险排行和封禁状态
- `mysql`：保存风险事件和封禁历史

### 阿里云 ECS 部署说明

本项目部署在阿里云 ECS 云服务器，建议使用 Docker Compose 在服务器上统一启动所有容器。

ECS 安全组至少需要放行：

- `80`：客户端访问 Nginx
- `22`：SSH 登录服务器

如果只是本项目内部容器访问 Redis 和 MySQL，不建议在安全组中对公网开放 `3306` 和 `6380`。当前 Compose 文件虽然映射了这两个端口，主要用于调试；正式部署时可以按需去掉端口映射，只保留容器内部访问。

部署到 ECS 后，访问链路为：

```text
客户端 -> ECS 公网 IP:80 -> Nginx -> Web 服务 -> Nginx access.log -> log-forwarder -> AccessGuard -> Redis / MySQL
```

### 方式一：Python 容器连接宿主机 Redis

```bash
docker build -t accessguard:1.0 .

docker run --rm \
  --network host \
  -e REDIS_HOST=127.0.0.1 \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=redispwd \
  -e REDIS_DB=0 \
  accessguard:1.0
```

### 方式二：Docker Compose 编排运行

```bash
cd docker
docker compose up
```

如果需要重新构建镜像：

```bash
docker compose up --build
```

启动后可以通过 curl 模拟访问 Nginx：

```bash
curl http://127.0.0.1/
curl http://127.0.0.1/login
curl http://127.0.0.1/admin
curl -X POST http://127.0.0.1/api/test
```

如果在本地访问部署在 ECS 上的服务，将 `127.0.0.1` 替换为 ECS 公网 IP：

```bash
curl http://<ECS公网IP>/
curl http://<ECS公网IP>/login
curl http://<ECS公网IP>/admin
curl -X POST http://<ECS公网IP>/api/test
```

访问链路：

```text
客户端 -> Nginx -> Web 服务 -> Nginx access.log -> log-forwarder -> AccessGuard -> Redis / MySQL
```

查看 Redis 数据：

```bash
docker exec -it accessguard-redis redis-cli -a redispwd
```

查看 MySQL 数据：

```bash
docker exec -it accessguard-mysql mysql -uroot -p123456 accessguard

SELECT * FROM risk_events ORDER BY id DESC LIMIT 10;
SELECT * FROM ban_history ORDER BY id DESC LIMIT 10;
```
