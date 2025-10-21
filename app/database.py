from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Declarative Base for Models
Base = declarative_base()

DATABASE_URL = "postgresql+asyncpg://urlshort:urlshortpwd@postgres:5432/urlshortdb"
""" Database connection string for local Postgres:
    - postgresql+asyncpg: driver for async Postgres connections
    - urlshort:urlshortpwd: username and password
    - postgres:5432: host and port
    - urlshortdb: database name """

# Asynchronous Engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
""" Create an async SQLAlchemy engine:
    - DATABASE_URL: the DB connection string
    - echo=True: logs SQL queries for debugging """

# Factory of Asynchronous Sessions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
""" Create a session factory:
    - bind=engine: use this engine
    - class_=AsyncSession: use async sessions
    - expire_on_commit=False: objects remain usable after commit """

# Connects the Sessions with the API Routes
async def get_db():
    """
    Dependency function to provide a database session to FastAPI routes.
    - Uses the SessionLocal factory to create an AsyncSession.
    - The session is opened asynchronously with 'async with'.
    - 'yield' provides the session to the calling endpoint function.
    - After the endpoint finishes, the session is automatically closed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Initializes the DataBase
async def init_db():
    """Function that initializes the Database connection"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
