from fastapi import FastAPI, Depends, HTTPException, Request, APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, HttpUrl
from typing import List
import string, hashlib
from contextlib import asynccontextmanager
from .database import get_db, init_db, Base
from .models import URL,Click

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

# App and Router Definition
app = FastAPI(title="URL Shortener API", lifespan=lifespan)
router = APIRouter()

# URL Model
class URLCreate(BaseModel):
    """
    Schema for URL shortening requests.

    Attributes:
    - url: Original URL to shorten (validated as HttpUrl)
    - expires_in: Optional expiration time in seconds
    """
    url: HttpUrl
    expires_in: int | None = None #Minutes

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

        created_at = datetime.now()

        expires_at = datetime.now() + timedelta(days=1)
        if data.expires_in:
            expires_at = datetime.now() + timedelta(minutes = data.expires_in)

        new_url = URL(code=code, original_url=str(data.url), expires_at=expires_at)
        db.add(new_url)
        await db.commit()
        await db.refresh(new_url)

        return {
            "short_url": f"http://localhost/r/{new_url.code}",
            "code": new_url.code,
            "created_at": created_at,
            "expires_at": new_url.expires_at
        }
    
    except Exception as e:
        print("ERROR: ", e)
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to make the encurted URL redirect to the original URL
@app.get("/r/{code}")
async def redirect_url(code: str, request: Request, db: AsyncSession = Depends(get_db)):
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
    try:
        result = await db.execute(select(URL).where(URL.code == code))
        url = result.scalar_one_or_none()

        if not url:
            raise HTTPException(status_code=404, detail="URL not found")

        if url.expires_at and datetime.now(timezone.utc) > url.expires_at:
            raise HTTPException(status_code=410, detail="URL expired")
        
        new_click = Click(
                url_id=url.id,
                ip=request.client.host,
                user_agent=request.headers.get("user-agent"),
                referer=request.headers.get("referer")
            )
        
        db.add(new_click)
        await db.commit()
    except Exception as e:
        print("ERROR IN REDIRECTIG URL: ", e)
        raise HTTPException(status_code=500, detail = str(e))

    #Redirect to the original URL
    return RedirectResponse(url.original_url)

#Endpoint to get the stats of a link
@router.get("/api/v1/stats/{code}")
async def stats(code: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve statistics for a shortened URL.

    Args:
        code (str): The unique short code of the URL.
        db (AsyncSession): Async SQLAlchemy session provided via dependency.

    Returns:
        dict: Contains URL info and click statistics:
            - code: The short code
            - original_url: The original URL
            - created_at: Datetime when URL was created
            - expires_at: Datetime when URL will expire
            - total_clicks: Total number of clicks
            - last_click_at: Datetime of the last click
            - clicks: List of all click events, each with:
                - click_id
                - time (ISO format)

    Raises:
        HTTPException(404): If URL with given code does not exist
    """
    # 1) Get URL by code
    result = await db.execute(select(URL).where(URL.code == code))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    # 2) Total clicks
    total_q = await db.execute(
        select(func.count(Click.id)).where(Click.url_id == url.id)
    )
    total_clicks = total_q.scalar_one() or 0

    # 3) Last click
    last_q = await db.execute(
        select(func.max(Click.occurred_at)).where(Click.url_id == url.id)
    )
    last_click_at = last_q.scalar_one()

    # 4) All click events (id + occurred_at)
    clicks_q = await db.execute(
        select(Click.id, Click.occurred_at)
        .where(Click.url_id == url.id)
        .order_by(Click.occurred_at.asc())
    )

    clicks_rows = clicks_q.all()

    clicks = [
        {
            "click_id": c.id,
            "time": c.occurred_at.isoformat() if c.occurred_at else None
        }
        for c in clicks_rows
    ]

    # 5) Response
    return {
        "code": url.code,
        "original_url": url.original_url,
        "created_at": url.created_at.isoformat() if url.created_at else None,
        "expires_at": url.expires_at.isoformat() if url.expires_at else None,
        "total_clicks": total_clicks,
        "last_click_at": last_click_at.isoformat() if last_click_at else None,
        "clicks": clicks
    }

app.include_router(router)