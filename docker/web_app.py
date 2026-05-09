from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def index():
    return {"service": "demo-web", "message": "ok"}


@app.get("/login")
async def login():
    return {"service": "demo-web", "page": "login"}


@app.get("/admin")
async def admin():
    return {"service": "demo-web", "page": "admin"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(path: str, request: Request):
    return {
        "service": "demo-web",
        "method": request.method,
        "path": f"/{path}",
    }
