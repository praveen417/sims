from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User
from .permissions import PERMISSIONS

ALGO = "HS256"
bearer = HTTPBearer(auto_error=False)


def create_access_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user.username, "role": user.role, "exp": exp}, settings.SECRET_KEY, algorithm=ALGO)


def client_ip(request: Request):
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(401, "Session expired or invalid")
    user = db.scalar(select(User).where(User.username == payload.get("sub")))
    if not user or user.status != "active":
        raise HTTPException(401, "Account unavailable")
    return user


def require(perm: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in PERMISSIONS[perm]:
            raise HTTPException(403, "You do not have permission to do this")
        return user
    return dep
