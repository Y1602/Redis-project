from fastapi import FastAPI, Request

from redis_project_docker import RedisProject

app = FastAPI()
redis_instance = RedisProject()


@app.get("/health")
async def health():
    redis_instance.redis_client.ping()
    redis_instance.mysql_client.ping()
    return {"status": "ok"}


@app.post("/logs/ingest")
async def ingest_log(request: Request):
    body = await request.body()
    text = body.decode("utf-8", errors="replace")
    lines = text.strip().splitlines()
    results = []

    for line in lines:
        if not line.strip():
            continue
        try:
            results.append(redis_instance.process(line))
        except Exception as e:
            print(f"Error processing log line: {line}, {e}")

    return {
        "status": "ok",
        "lines_received": len(lines),
        "lines_processed": sum(1 for result in results if result),
    }
