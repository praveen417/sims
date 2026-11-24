from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import auditlog
from ..config import settings
from ..database import get_db
from ..deps import client_ip, create_access_token, get_current_user
from ..models import User
from ..permissions import permissions_for
from ..schemas import ChangePassword, ForgotIn, LoginIn
from ..security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _profile(u: User):
    return {"username": u.username, "full_name": u.full_name, "role": u.role,
            "permissions": permissions_for(u.role)}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    now = datetime.now(timezone.utc)
    user = db.scalar(select(User).where(User.username == body.username))
    if not user:
        auditlog.log(db, body.username, "LOGIN_FAILED", ip)
        db.commit()
        raise HTTPException(401, "Invalid username or password")
    if user.status == "disabled":
        raise HTTPException(403, "Account is disabled")
    if user.status == "locked" or (user.locked_until and user.locked_until > now):
        raise HTTPException(423, "Account is locked. Try later or contact an administrator.")
    if not verify_password(body.password, user.password_hash):
        user.failed_attempts += 1
        auditlog.log(db, user.username, "LOGIN_FAILED", ip)
        if user.failed_attempts >= settings.MAX_FAILED_LOGINS:
            if settings.LOCKOUT_MINUTES == 0:
                user.status = "locked"  # stays locked until an admin unlocks
            else:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
            user.failed_attempts = 0
            auditlog.log(db, user.username, "ACCOUNT_LOCKED", ip)
        db.commit()
        raise HTTPException(401, "Invalid username or password")
    user.failed_attempts, user.locked_until, user.last_login = 0, None, now
    auditlog.log(db, user.username, "LOGIN", ip)
    db.commit()
    return {"access_token": create_access_token(user), "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "user": _profile(user)}


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    auditlog.log(db, user.username, "LOGOUT", client_ip(request))
    db.commit()
    return {"detail": "Logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _profile(user)


@router.post("/forgot-password")
def forgot(body: ForgotIn, request: Request, db: Session = Depends(get_db)):
    # Same answer whether or not the user exists. Email delivery is added with notifications.
    auditlog.log(db, body.username, "PASSWORD_RESET_REQUESTED", client_ip(request))
    db.commit()
    return {"detail": "If the account exists, an administrator has been notified to reset the password."}


@router.post("/change-password")
def change_password(body: ChangePassword, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    auditlog.log(db, user.username, "PASSWORD_CHANGED", client_ip(request))
    db.commit()
    return {"detail": "Password changed"}
