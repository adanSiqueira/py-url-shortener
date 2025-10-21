from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from pydantic import BaseModel, HttpUrl
import string, hashlib
from contextlib import asynccontextmanager
from .database import get_db, init_db, Base
from .models import URL

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="URL Shortener API", lifespan=lifespan)

# Pydantic schema
class URLCreate(BaseModel):
    url: HttpUrl
    expires_in: int | None = None  # segundos

def generate_code(url: str, size=6):
    url_str = str(url)
    hash_bytes = hashlib.sha256(url_str.encode()).digest()
    chars = string.ascii_letters + string.digits
    code = ''.join(chars[b % len(chars)] for b in hash_bytes[:size])
    return code

@app.post("/api/v1/shorten")
async def shorten_url(data: URLCreate, db: AsyncSession = Depends(get_db)):        
    try:
        code = generate_code(data.url)
        while (await db.execute(select(URL).where(URL.code == code))).scalar_one_or_none():
            code = generate_code(data.url)

        expires_at = None
        if data.expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=data.expires_in)

        new_url = URL(code=code, original_url=str(data.url), expires_at=expires_at)
        db.add(new_url)
        await db.commit()
        await db.refresh(new_url)

        return {
            "short_url": f"http://localhost/r/{new_url.code}",
            "code": new_url.code,
            "expires_at": new_url.expires_at
        }
    except Exception as e:
        print("ERROR: ", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/r/{code}")
async def redirect_url(code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(URL).where(URL.code == code))
    url = result.scalar_one_or_none()

    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    if url.expires_at and datetime.utcnow() > url.expires_at:
        raise HTTPException(status_code=410, detail="URL expired")

    return RedirectResponse(url.original_url)
