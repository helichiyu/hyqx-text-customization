"""Minimal FastAPI integration example for the auth interceptor."""

from fastapi import FastAPI
from auth.auth_guard import docs_off_kwargs, install_auth

app = FastAPI(title="Example Operator Service", version="1.0.0", **docs_off_kwargs())
install_auth(app)


@app.get("/health")
async def health():
    return {"code": 0, "msg": "success"}


@app.get("/operators")
async def operators():
    return {"code": 0, "msg": "success", "data": []}
