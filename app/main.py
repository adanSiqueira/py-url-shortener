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

#Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    
    Responsibilities:
    - Initialize the database at application startup.
    - Yield control to allow app to start normally.
    - Ensure any startup tasks are completed before serving requests.
    """
    await init_db()
    yield

# App Definition
app = FastAPI(title="URL Shortener API", lifespan=lifespan)

# URL Model
class URLCreate(BaseModel):
    """
    Schema for URL shortening requests.

    Attributes:
    - url: Original URL to shorten (validated as HttpUrl)
    - expires_in: Optional expiration time in seconds
    """
    url: HttpUrl
    expires_in: int | None = None  # segundos

# Random Code Generator
def generate_code(url: str, size=6):
    """
    Generate a pseudo-random code for a given URL.

    Process:
    - Converts the Pydantic HttpUrl to string
    - Hashes the string using SHA-256
    - Maps the first `size` bytes of the hash to letters and digits
    - Returns a short code of `size` length

    Args:
        url: URL string to generate code for
        size: Desired length of the short code (default: 6)

    Returns:
        Short string code
    """
    url_str = str(url)
    hash_bytes = hashlib.sha256(url_str.encode()).digest()
    chars = string.ascii_letters + string.digits
    code = ''.join(chars[b % len(chars)] for b in hash_bytes[:size])
    return code

# Endpoint to shorten the original URL
@app.post("/api/v1/shorten")
async def shorten_url(data: URLCreate, db: AsyncSession = Depends(get_db)):        
    """
    Create a shortened URL.

    Process:
    - Generates a unique code using `generate_code`
    - Checks database to avoid duplicates
    - Computes expiration datetime if `expires_in` is provided
    - Stores the new URL in the database

    Args:
        data: URLCreate object containing the original URL and optional expiration
        db: Async SQLAlchemy session injected via dependency

    Returns:
        JSON containing:
        - short_url: full shortened URL
        - code: internal unique code
        - expires_at: expiration timestamp (or None)
    
    Raises:
        HTTPException(500) on unexpected errors
    """
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

# Endpoint to make the encurted URL redirect to the original URL
@app.get("/r/{code}")
async def redirect_url(code: str, db: AsyncSession = Depends(get_db)):
    """
    Redirect to the original URL.

    Process:
    - Query the database for the given short code
    - Raise 404 if code is not found
    - Raise 410 if URL has expired
    - Otherwise, return a RedirectResponse to the original URL

    Args:
        code: Short code in the path
        db: Async SQLAlchemy session injected via dependency

    Returns:
        RedirectResponse to the original URL
    
    Raises:
        HTTPException(404) if URL not found
        HTTPException(410) if URL has expired
    """
    result = await db.execute(select(URL).where(URL.code == code))
    url = result.scalar_one_or_none()

    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    if url.expires_at and datetime.utcnow() > url.expires_at:
        raise HTTPException(status_code=410, detail="URL expired")

    #Redirect to the original URL
    return RedirectResponse(url.original_url)
