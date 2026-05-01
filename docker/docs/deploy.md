## 1. docs/docker-deploy.md

# AccessGuard Dockerfile 部署说明

## 1. 阶段目标

本阶段目标是将 AccessGuard Python 程序打包为 Docker 镜像，实现容器化运行。

当前实验方式：

- Redis 运行在宿主机
- AccessGuard 运行在 Python 容器中
- Python 容器通过环境变量读取 Redis 连接信息
- Python 容器连接宿主机 Redis 完成日志处理和数据写入


## 2. Dockerfile 内容

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

CMD ["python", "redis_project.py"]
````


## 3. Dockerfile 说明

### 3.1 基础镜像

```dockerfile
FROM python:3.11-slim
```

使用 Python 3.11 精简版镜像作为基础运行环境。

### 3.2 设置工作目录

```dockerfile
WORKDIR /app
```

指定容器内工作目录为 `/app`。


### 3.3 复制依赖文件

```dockerfile
COPY requirements.txt .
```

先复制依赖文件，便于 Docker 构建时缓存依赖安装步骤。


### 3.4 安装 Python 依赖

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

安装项目所需 Python 依赖。

使用清华源是为了解决构建过程中访问 PyPI 超时的问题。


### 3.5 复制项目代码

```dockerfile
COPY . .
```

将当前目录下项目文件复制到容器 `/app` 目录。


### 3.6 启动命令

```dockerfile
CMD ["python", "redis_project.py"]
```

容器启动后执行 Python 脚本。


## 4. requirements.txt

项目依赖：

```txt
redis==5.0.1
```

说明：

Python 官方镜像只包含 Python 运行环境，不包含第三方库。

由于项目代码中使用了：

```python
import redis
```

所以必须通过 `requirements.txt` 安装 `redis-py` 依赖。

---

## 5. 构建镜像

在 Dockerfile 所在目录执行：

```bash
docker build -t accessguard:1.0 .
```

说明：

* `-t accessguard:1.0`：指定镜像名称和版本
* `.`：表示使用当前目录作为构建上下文

注意：

Docker 镜像名必须小写，例如：

```bash
accessguard:1.0
```

不能写成：

```bash
AccessGuard:1.0
```


## 6. 运行容器连接宿主机 Redis

如果 Redis 运行在宿主机上，可以使用 host 网络模式：

```bash
docker run --rm \
  --network host \
  -e REDIS_HOST=127.0.0.1 \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=redispwd \
  -e REDIS_DB=0 \
  accessguard:1.0
```


## 7. 参数说明

### 7.1 `--rm`

容器退出后自动删除，适合一次性脚本任务。


### 7.2 `--network host`

让容器直接使用宿主机网络。

在 Linux 环境下，容器访问：

```text
127.0.0.1:6379
```

等价于访问宿主机 Redis。


### 7.3 `-e`

用于向容器传入环境变量。

示例：

```bash
-e REDIS_HOST=127.0.0.1
```

Python 程序通过：

```python
os.getenv("REDIS_HOST")
```

读取该值。


## 8. 代码中 Redis 连接配置

Docker 化后，Redis 连接信息不再建议通过 `input()` 输入，而是通过环境变量读取。

示例：

```python
host = os.getenv("REDIS_HOST", "127.0.0.1")
password = os.getenv("REDIS_PASSWORD", "redispwd")
port = int(os.getenv("REDIS_PORT", "6379"))
db = int(os.getenv("REDIS_DB", "0"))
```


## 9. 遇到的问题

### 9.1 镜像名大写导致构建失败

错误信息：

```text
repository name must be lowercase
```

原因：

Docker 镜像名必须小写。

解决：

```bash
docker build -t accessguard:1.0 .
```


### 9.2 pip 下载依赖超时

错误信息：

```text
Read timed out
```

原因：

构建镜像时访问 PyPI 超时。

解决：

Dockerfile 中使用国内 pip 源：

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```


### 9.3 不传环境变量时连接失败

错误信息：

```text
Error -2 connecting to redis:6379. Name or service not known.
```

原因：

程序默认连接 `redis` 主机名，但当前不是 docker-compose 环境，没有名为 `redis` 的服务。

解决方式：

* 单容器连接宿主机 Redis：默认值使用 `127.0.0.1`
* docker-compose 环境：使用 `REDIS_HOST=redis`


## 10. 本阶段总结

本阶段完成了 AccessGuard 的基础容器化，将 Python 程序打包为 Docker 镜像，并通过环境变量实现 Redis 连接配置。

该阶段重点理解了：

* Dockerfile 构建流程
* Python 镜像与 Python 依赖的区别
* `requirements.txt` 的作用
* `docker run --network host` 的使用
* `-e` 环境变量传参
* 镜像构建后代码变更需要重新 build
