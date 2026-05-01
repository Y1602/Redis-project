## 2. `docs/docker-compose-summary.md`

# AccessGuard Docker Compose 编排实验总结

## 1. 阶段目标

本阶段目标是使用 Docker Compose 编排 AccessGuard 和 Redis，实现一条命令启动完整实验环境。 Compose 编排后，AccessGuard 不再连接宿主机 Redis，而是连接 Compose 中的 Redis 服务。

## 2. 服务结构

本次实验包含两个服务：

accessguard-app
accessguard-redis

整体结构：

```text
AccessGuard Python 容器
        ↓
通过服务名 redis 连接
        ↓
Redis 容器
```


## 3. docker-compose.yml 示例

```yaml
services:
  redis:
    image: redis:latest
    container_name: accessguard-redis
    ports:
      - "6379:6379"
    command: redis-server --requirepass redispwd
    restart: unless-stopped

  accessguard:
    image: accessguard:1.0
    container_name: accessguard-app
    environment:
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: redispwd
      REDIS_DB: 0
    depends_on:
      - redis
```

## 4. 配置说明

### 4.1 Redis 服务

```yaml
redis:
  image: redis:latest
```

使用 Redis 官方镜像启动 Redis 服务。


### 4.2 Redis 容器名

```yaml
container_name: accessguard-redis
```

指定 Redis 容器名称，方便查看和进入容器。

### 4.3 端口映射

```yaml
ports:
  - "6379:6379"
```

含义：

```text
宿主机 6379 端口 → Redis 容器 6379 端口
```

该配置用于宿主机访问 Redis。

AccessGuard 容器访问 Redis 时，不依赖宿主机端口映射，而是通过 Compose 内部网络访问服务名 `redis`。


### 4.4 Redis 启动命令

```yaml
command: redis-server --requirepass redispwd
```

含义：

启动 Redis 服务，并设置访问密码为 `redispwd`。

注意：

```text
--requirepass redispwd
```

是服务端设置密码。

客户端连接时使用：

```bash
redis-cli -a redispwd
```

或者 Python 中配置：

```python
password="redispwd"
```

### 4.5 restart 策略

```yaml
restart: unless-stopped
```

含义：

容器异常退出时自动重启，除非用户手动停止容器。

适合 Redis 这类长期运行的服务。


### 4.6 AccessGuard 服务

```yaml
accessguard:
  image: accessguard:1.0
```

表示使用本地已经构建好的 `accessguard:1.0` 镜像运行 Python 程序。

如果使用：

```yaml
build: .
```

则 Compose 会重新构建镜像。


### 4.7 环境变量

```yaml
environment:
  REDIS_HOST: redis
  REDIS_PORT: 6379
  REDIS_PASSWORD: redispwd
  REDIS_DB: 0
```

这些值会传入 AccessGuard 容器。

Python 程序通过 `os.getenv()` 读取这些配置。

其中：

```text
REDIS_HOST=redis
```

表示连接 Compose 内部名为 `redis` 的服务。


### 4.8 depends_on

```yaml
depends_on:
  - redis
```

含义：

先启动 Redis 服务，再启动 AccessGuard 服务。

注意：

`depends_on` 只保证启动顺序，不保证 Redis 已经完全准备好。


## 5. 启动命令

如果使用本地已构建好的镜像：

```bash
docker compose up
```

如果需要重新构建镜像：

```bash
docker compose up --build
```

但如果 Docker Hub 网络不稳定，且本地已经存在 `accessguard:1.0` 镜像，建议不要使用 `--build`。


## 6. 查看容器

```bash
docker ps
```

查看所有容器，包括已退出容器：

```bash
docker ps -a
```

说明：

AccessGuard 当前是一次性脚本，执行完成后容器会退出，这是正常现象。

Redis 是长期运行服务，会保持运行状态。


## 7. 查看 Redis 数据

进入 Redis 容器：

```bash
docker exec -it accessguard-redis redis-cli -a redispwd
```

验证命令：

```redis
KEYS *
```

注意：

项目代码中使用的是：

```python
datetime.now().date()
```

所以 Redis key 中的日期是容器运行当天日期，不一定是日志内容中的日期。


## 8. 遇到的问题

### 8.1 Docker Hub 超时

错误信息：

```text
failed to resolve source metadata for docker.io/library/python:3.11-slim
i/o timeout
```

原因：

执行 `docker compose up --build` 时，Compose 重新构建镜像并访问 Docker Hub 获取基础镜像元数据，网络超时。

解决方式：

如果本地已经存在 `accessguard:1.0`，可以在 compose 中使用：

```yaml
image: accessguard:1.0
```

并执行：

```bash
docker compose up
```

不要加 `--build`。


### 8.2 restart 拼写错误

错误信息：

```text
invalid restart policy: unknown policy 'unles-stopped'
```

原因：

将：

```yaml
restart: unless-stopped
```

误写成了：

```yaml
restart: unles-stopped
```

解决：

使用正确写法：

```yaml
restart: unless-stopped
```

### 8.3 本地有基础镜像仍访问 Docker Hub

现象：

本地存在 `python:3.11-slim`，但 `docker compose up --build` 仍然尝试访问 Docker Hub。

原因：

BuildKit 构建时可能会检查远程镜像元数据。

解决：

优先使用已构建镜像：

```yaml
image: accessguard:1.0
```

如必须重新构建，可尝试：

```bash
docker build --pull=false -t accessguard:1.0 .
```


## 9. 本阶段总结

本阶段完成了 AccessGuard 的 Docker Compose 编排实验。

通过本次实验，理解了：

* Python 容器与 Redis 容器之间的通信方式
* Compose 服务名可以作为容器间访问地址
* `command` 用于覆盖容器默认启动命令
* `--requirepass` 是 Redis 服务端密码配置
* `redis-cli -a` 是客户端认证参数
* `restart: unless-stopped` 的作用
* `depends_on` 的启动顺序控制
* AccessGuard 作为一次性脚本运行完成后退出是正常现象

本阶段是 AccessGuard 从单脚本练习进入容器化部署阶段。
