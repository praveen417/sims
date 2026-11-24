from datetime import date, datetime

from sqlalchemy.orm import Session

from .models import AuditLog


def ser(v):
    return v.isoformat() if isinstance(v, (date, datetime)) else v


def log(db: Session, username, action, ip, entity_id=None, old=None, new=None):
    db.add(AuditLog(username=username, action=action, ip_address=ip, entity_id=entity_id,
                    old_value=old, new_value=new))
