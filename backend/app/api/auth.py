from fastapi import HTTPException, Header
import os

async def verify_api_key(x_api_key: str = Header(...)):
    """API Key検証ミドルウェア"""
    api_key = os.getenv("API_KEY")
    if not api_key or x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


