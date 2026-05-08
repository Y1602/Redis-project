from fastapi import FastAPI, Request
from redis_project import RedisProject  # 复用你现有类

app = FastAPI()
redis_instance = RedisProject()  # 初始化 Redis 连接

@app.post("/logs/ingest")
async def ingest_log(request: Request):
        """
        接收日志文本，通过 RedisProject.process() 写入 Redis
        支持多条日志一次性发送
        """
        body = await request.body()
        text = body.decode()
        lines = text.strip().split("\n")
        results = []
        for line in lines:
            if line.strip():  # 忽略空行
                try:
                    res = redis_instance.process(line)
                    results.append(res)
                except Exception as e:
                    print(f"日志处理异常: {line}, {e}")
        return {"status": "ok", "lines_processed": len(lines)}
