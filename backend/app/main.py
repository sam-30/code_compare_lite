import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="Code Compare Lite")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
