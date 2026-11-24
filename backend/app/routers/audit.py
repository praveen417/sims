from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require
from ..models import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500),
               username: str | None = None, action: str | None = None, entity_id: int | None = None,
               date_from: datetime | None = None, date_to: datetime | None = None,
               db: Session = Depends(get_db), user=Depends(require("audit:view"))):
    stmt = select(AuditLog)
    if username:
        stmt = stmt.where(AuditLog.username.ilike(f"%{username}%"))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if date_from:
        stmt = stmt.where(AuditLog.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.timestamp <= date_to)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "page": page, "page_size": page_size, "items": [
        {"id": r.id, "username": r.username, "action": r.action, "ip_address": r.ip_address,
         "entity_id": r.entity_id, "old_value": r.old_value, "new_value": r.new_value,
         "timestamp": r.timestamp} for r in rows]}
