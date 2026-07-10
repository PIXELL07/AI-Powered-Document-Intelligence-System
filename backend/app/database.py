from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Connection pool sizing matters once real concurrent traffic shows up --
# SQLAlchemy's default (pool_size=5, max_overflow=10) is fine for local
# dev but will exhaust under a few hundred concurrent requests, each
# holding a connection for the duration of a request. These are
# deliberately explicit rather than left as defaults, and are safe
# no-ops for SQLite (which doesn't use a real connection pool -- it's
# single-file and single-writer regardless of pool settings, which is
# also why SQLite is a dev/demo choice here, not the target for real
# concurrent load; see README "Scaling to concurrent users").
engine_kwargs = {"pool_pre_ping": True}
if not is_sqlite:
    engine_kwargs.update(
        pool_size=20,
        max_overflow=20,
        pool_recycle=1800,  # recycle connections every 30 min, avoids stale-connection errors
        pool_timeout=30,
    )

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models so they register on Base.metadata before create_all
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
