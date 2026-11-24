import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import SessionLocal
from .models import User
from .routers import assets, audit, auth, changes, dashboard, importexport, ping, users
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("sims")


def seed():
    """Create the first admin if there are no users. OPCOs are created automatically on import."""
    with SessionLocal() as db:
        if not db.scalar(select(User.id).limit(1)):
            db.add(User(username=settings.ADMIN_USERNAME, full_name="System Administrator",
                        email=settings.ADMIN_EMAIL, role="admin",
                        password_hash=hash_password(settings.ADMIN_PASSWORD)))
            try:
                db.commit()
                log.info("Seeded admin user '%s'", settings.ADMIN_USERNAME)
            except IntegrityError:
                db.rollback()  # another uvicorn worker created it first


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    yield


app = FastAPI(title="Enterprise Server Inventory Management System (SIMS)",
              version="0.3.0", lifespan=lifespan, docs_url="/docs", openapi_url="/openapi.json")
for r in (auth.router, assets.router, users.router, importexport.router, audit.router, dashboard.router, changes.router, ping.router):
    app.include_router(r)


@app.get("/api/health", tags=["system"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}
