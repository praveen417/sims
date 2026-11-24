"""Admin: ping servers from the portal and write the result into the Remarks field."""
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import auditlog
from ..config import settings
from ..database import get_db
from ..deps import client_ip, require
from ..models import Inventory
from ..schemas import AssetOut

router = APIRouter(prefix="/api/assets", tags=["ping"])
TARGET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


def pick_target(a: Inventory):
    for c in (a.ip_address, a.fqdn, a.hostname):
        if c and TARGET_RE.match(c.strip()):
            return c.strip()
    return None


def ping_host(target):
    """Returns (ok, message). target is validated; no shell is used."""
    if not shutil.which("ping"):
        return False, "ping command is not installed in the backend container"
    if not target:
        return False, "No valid IP address or hostname on this asset"
    n, t = settings.PING_COUNT, settings.PING_TIMEOUT
    try:
        p = subprocess.run(["ping", "-c", str(n), "-W", str(t), "-n", target],
                           capture_output=True, text=True, timeout=n * t + 8)
    except subprocess.TimeoutExpired:
        return False, "Ping timed out"
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode == 0:
        recv = re.search(r"(\d+) received", out)
        rtt = re.search(r"= [\d.]+/([\d.]+)/", out)
        return True, f"Reply received ({recv.group(1) if recv else '?'}/{n} replies" + (f", avg {rtt.group(1)} ms)" if rtt else ")")
    loss = re.search(r"(\d+)% packet loss", out)
    why = re.search(r"(Destination [A-Za-z ]+Unreachable|Network is unreachable)", out)
    if loss:
        return False, f"No reply ({loss.group(1)}% packet loss" + (f", {why.group(1)})" if why else ")")
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return False, (lines[-1] if lines else "Ping failed")[:300]


def stamp(remarks, ok, msg):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = f"[Ping {now}] {'OK' if ok else 'FAILED'} - {msg}"
    rest = [l for l in (remarks or "").splitlines() if not l.startswith("[Ping ")]
    return "\n".join([line, *rest]).strip()


def _apply(db, a, target, ok, msg, user, ip):
    old = a.remarks
    a.remarks = stamp(old, ok, msg)
    auditlog.log(db, user.username, "ASSET_PING", ip, a.id, {"remarks": old},
                 {"remarks": a.remarks, "target": target, "ok": ok})


class BulkPing(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)


@router.post("/ping-bulk")
def ping_bulk(body: BulkPing, request: Request, db: Session = Depends(get_db), user=Depends(require("asset:write"))):
    assets = db.scalars(select(Inventory).where(Inventory.id.in_(body.ids))).all()
    targets = [pick_target(a) for a in assets]
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(ping_host, targets))
    out = []
    for a, tgt, (ok, msg) in zip(assets, targets, results):
        _apply(db, a, tgt, ok, msg, user, client_ip(request))
        out.append({"id": a.id, "hostname": a.hostname, "ok": ok, "message": msg})
    db.commit()
    return {"results": out, "ok": sum(1 for r in out if r["ok"]), "failed": sum(1 for r in out if not r["ok"])}


@router.post("/{asset_id}/ping")
def ping_one(asset_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require("asset:write"))):
    a = db.get(Inventory, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    tgt = pick_target(a)
    ok, msg = ping_host(tgt)
    _apply(db, a, tgt, ok, msg, user, client_ip(request))
    db.commit()
    db.refresh(a)
    return {"ok": ok, "message": msg, "target": tgt, "asset": AssetOut.model_validate(a)}
