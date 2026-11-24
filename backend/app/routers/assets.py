from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import auditlog
from ..assets_query import SORTABLE, build_stmt
from ..database import get_db
from ..deps import client_ip, require
from ..fields import FIELD_NAMES, LABELS, OPTION_FIELDS, UNIQUE_FIELDS
from ..models import Inventory, Opco
from ..schemas import AssetCreate, AssetOut, AssetUpdate, BulkUpdate, validate_changes

router = APIRouter(prefix="/api/assets", tags=["assets"])


def snapshot(a: Inventory, keys=None) -> dict:
    return {k: auditlog.ser(getattr(a, k)) for k in (keys or FIELD_NAMES)}


def ensure_opco(db: Session, name):
    if name and not db.scalar(select(Opco.id).where(func.lower(Opco.name) == name.lower())):
        db.add(Opco(name=name))


def check_unique(db: Session, data: dict, exclude_id=None):
    for f in UNIQUE_FIELDS:
        v = data.get(f)
        if not v:
            continue
        col = getattr(Inventory, f)
        cond = func.lower(col) == v.lower() if f == "hostname" else col == v
        stmt = select(Inventory.id).where(cond)
        if exclude_id:
            stmt = stmt.where(Inventory.id != exclude_id)
        if db.scalar(stmt.limit(1)):
            raise HTTPException(409, f"{LABELS[f]} '{v}' already exists")


@router.get("")
def list_assets(request: Request, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500),
                q: str | None = None, sort_by: str = "id", sort_dir: str = "asc",
                db: Session = Depends(get_db), user=Depends(require("asset:read"))):
    stmt = build_stmt(dict(request.query_params), q)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    col = getattr(Inventory, sort_by if sort_by in SORTABLE else "id")
    stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc(), Inventory.id)
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [AssetOut.model_validate(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


@router.get("/meta/options")
def options(db: Session = Depends(get_db), user=Depends(require("asset:read"))):
    out = {}
    for f in OPTION_FIELDS:
        col = getattr(Inventory, f)
        out[f] = [v for v in db.scalars(select(col).where(col.is_not(None)).distinct().order_by(col))]
    return out


@router.patch("/bulk")
def bulk_update(body: BulkUpdate, request: Request, db: Session = Depends(get_db),
                user=Depends(require("asset:write"))):
    bad = [k for k in body.changes if k not in FIELD_NAMES or k in UNIQUE_FIELDS]
    if bad:
        raise HTTPException(422, f"Cannot bulk-edit: {', '.join(bad)}")
    changes = validate_changes(body.changes)
    if not changes:
        raise HTTPException(422, "No changes supplied")
    ensure_opco(db, changes.get("opco"))
    n = 0
    for a in db.scalars(select(Inventory).where(Inventory.id.in_(body.ids))):
        old, new = {}, {}
        for k, v in changes.items():
            if getattr(a, k) != v:
                old[k], new[k] = auditlog.ser(getattr(a, k)), auditlog.ser(v)
                setattr(a, k, v)
        if new:
            n += 1
            auditlog.log(db, user.username, "ASSET_BULK_UPDATE", client_ip(request), a.id, old, new)
    db.commit()
    return {"updated": n}


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db), user=Depends(require("asset:read"))):
    a = db.get(Inventory, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    return a


@router.post("", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetCreate, request: Request, db: Session = Depends(get_db),
                 user=Depends(require("asset:write"))):
    data = payload.model_dump()
    check_unique(db, data)
    ensure_opco(db, data.get("opco"))
    a = Inventory(**data)
    db.add(a)
    db.flush()
    auditlog.log(db, user.username, "ASSET_CREATE", client_ip(request), a.id, None, snapshot(a))
    db.commit()
    db.refresh(a)
    return a


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: int, payload: AssetUpdate, request: Request, db: Session = Depends(get_db),
                 user=Depends(require("asset:write"))):
    a = db.get(Inventory, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    changes = payload.model_dump(exclude_unset=True)  # sending null/"" clears a field
    if "hostname" in changes and not changes["hostname"]:
        raise HTTPException(422, "Hostname cannot be blank")
    check_unique(db, changes, exclude_id=a.id)
    ensure_opco(db, changes.get("opco"))
    old, new = {}, {}
    for k, v in changes.items():
        if getattr(a, k) != v:
            old[k], new[k] = auditlog.ser(getattr(a, k)), auditlog.ser(v)
            setattr(a, k, v)
    if new:
        auditlog.log(db, user.username, "ASSET_UPDATE", client_ip(request), a.id, old, new)
        db.commit()
        db.refresh(a)
    return a


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, request: Request, db: Session = Depends(get_db),
                 user=Depends(require("asset:delete"))):
    a = db.get(Inventory, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    auditlog.log(db, user.username, "ASSET_DELETE", client_ip(request), a.id, snapshot(a), None)
    db.delete(a)
    db.commit()
    return {"detail": "Deleted"}
