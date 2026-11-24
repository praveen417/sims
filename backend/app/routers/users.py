from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import auditlog
from ..database import get_db
from ..deps import client_ip, require
from ..models import User
from ..permissions import PERMISSIONS, ROLES
from ..schemas import PasswordReset, UserCreate, UserOut, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/roles")
def roles(user=Depends(require("user:manage"))):
    return {r: sorted(p for p, rs in PERMISSIONS.items() if r in rs) for r in ROLES}


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user=Depends(require("user:manage"))):
    return db.scalars(select(User).order_by(User.username)).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, request: Request, db: Session = Depends(get_db),
                admin=Depends(require("user:manage"))):
    if db.scalar(select(User.id).where(func.lower(User.username) == body.username.lower())):
        raise HTTPException(409, "Username already exists")
    if db.scalar(select(User.id).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(409, "Email already in use")
    u = User(username=body.username, full_name=body.full_name, email=body.email,
             role=body.role, password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    auditlog.log(db, admin.username, "USER_CREATE", client_ip(request), u.id, None,
                 {"username": u.username, "role": u.role})
    db.commit()
    db.refresh(u)
    return u


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, request: Request, db: Session = Depends(get_db),
                admin=Depends(require("user:manage"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    changes = body.model_dump(exclude_unset=True)
    if u.id == admin.id and (changes.get("role", u.role) != "admin" or changes.get("status", u.status) != "active"):
        raise HTTPException(400, "You cannot demote or disable your own account")
    old = {k: getattr(u, k) for k in changes}
    for k, v in changes.items():
        setattr(u, k, v)
    auditlog.log(db, admin.username, "USER_UPDATE", client_ip(request), u.id, old, changes)
    db.commit()
    db.refresh(u)
    return u


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, body: PasswordReset, request: Request, db: Session = Depends(get_db),
                   admin=Depends(require("user:manage"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    u.password_hash = hash_password(body.new_password)
    u.failed_attempts, u.locked_until = 0, None
    if u.status == "locked":
        u.status = "active"
    auditlog.log(db, admin.username, "USER_PASSWORD_RESET", client_ip(request), u.id)
    db.commit()
    return {"detail": "Password reset"}


@router.post("/{user_id}/unlock")
def unlock(user_id: int, request: Request, db: Session = Depends(get_db),
           admin=Depends(require("user:manage"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    u.failed_attempts, u.locked_until = 0, None
    if u.status == "locked":
        u.status = "active"
    auditlog.log(db, admin.username, "USER_UNLOCK", client_ip(request), u.id)
    db.commit()
    return {"detail": "Unlocked"}


@router.delete("/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db),
                admin=Depends(require("user:manage"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id:
        raise HTTPException(400, "You cannot delete your own account")
    auditlog.log(db, admin.username, "USER_DELETE", client_ip(request), u.id, {"username": u.username}, None)
    db.delete(u)
    db.commit()
    return {"detail": "Deleted"}
