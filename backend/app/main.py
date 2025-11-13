from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from app.api import jobs, ingest, regions

load_dotenv()

app = FastAPI(
    title="JobMap API",
    description="JobMap 백엔드 API",
    version="1.0.0"
)

# CORS設定
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(jobs.router)
app.include_router(ingest.router)
app.include_router(regions.router)

@app.get("/")
async def root():
    return {"message": "JobMap API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

