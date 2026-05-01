# Redis-project

## 项目简介

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
docker compose up
```

如果需要重新构建镜像：

```bash
docker compose up --build
```

查看 Redis 数据：

```bash
docker exec -it accessguard-redis redis-cli -a redispwd
```
