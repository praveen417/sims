"""Dashboard widgets/charts and report endpoints. Category definitions live in app/classify.py.
All report endpoints accept category filters as repeated query params, e.g. ?opco=Zambia&opco=Ghana&environment=Prod"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import and_, case, func, or_, select, true
from sqlalchemy.orm import Session

from .. import classify as C
from ..database import get_db
from ..deps import require
from ..models import Inventory as I

router = APIRouter(prefix="/api", tags=["dashboard & reports"])

REPORT_CATEGORIES = ["opco", "domain", "environment", "physical_virtual", "hardware_vendor", "operating_system",
                     "location", "asset_type", "ito_non_ito", "bia_class", "application_owner",
                     "virtualization_platform", "support_type", "status"]


def report_filters(request: Request) -> list:
    conds = []
    for f in REPORT_CATEGORIES:
        vals = [v.strip().lower() for v in request.query_params.getlist(f) if v.strip()]
        if vals:
            conds.append(func.lower(getattr(I, f)).in_(vals))
    return conds


def W(*conds):
    return and_(true(), *conds)


def _group(db: Session, col, where=None, limit=None):
    stmt = select(col, func.count()).group_by(col).order_by(func.count().desc())
    if where is not None:
        stmt = stmt.where(where)
    items = [(r[0] or "Unknown", r[1]) for r in db.execute(stmt).all()]
    if limit and len(items) > limit:
        rest = sum(c for _, c in items[limit:])
        items = items[:limit] + [("Other", rest)]
    return {"labels": [i[0] for i in items], "data": [i[1] for i in items]}


def _pairs(g):
    return [{"label": l, "count": c} for l, c in zip(g["labels"], g["data"])]


def _brief(a: I):
    return {"id": a.id, "hostname": a.hostname, "opco": a.opco, "ip_address": a.ip_address,
            "environment": a.environment, "application": a.application,
            "backup_status": a.backup_status, "oracle_support": a.oracle_support,
            "db_version": a.db_version, "end_of_life": a.end_of_life, "end_of_support": a.end_of_support}


# ------------------------------------------------------------------ dashboard
@router.get("/dashboard/summary")
def summary(db: Session = Depends(get_db), user=Depends(require("asset:read"))):
    P = C.PRESETS
    row = db.execute(select(
        func.count().label("total"),
        func.count().filter(P["physical"]()).label("physical"),
        func.count().filter(P["virtual"]()).label("virtual"),
        func.count().filter(P["prod"]()).label("production"),
        func.count().filter(P["dr"]()).label("dr"),
        func.count().filter(P["uat"]()).label("uat"),
        func.count().filter(P["linux"]()).label("linux"),
        func.count().filter(P["windows"]()).label("windows"),
        func.count().filter(P["oracle_db"]()).label("oracle_databases"),
        func.count().filter(P["protected"]()).label("backup_protected"),
        func.count().filter(P["non_protected"]()).label("non_protected"),
        func.count().filter(P["eos_expired"]()).label("end_of_support"),
        func.count().filter(P["eol_expired"]()).label("end_of_life"),
    ).select_from(I)).one()._mapping
    return dict(row)


@router.get("/dashboard/charts")
def charts(db: Session = Depends(get_db), user=Depends(require("asset:read"))):
    prot = db.scalar(select(func.count()).select_from(I).where(C.protected()))
    total = db.scalar(select(func.count()).select_from(I))
    return {
        "opco": _group(db, I.opco),
        "domain": _group(db, I.domain, limit=12),
        "environment": _group(db, I.environment),
        "os": _group(db, I.operating_system, limit=10),
        "backup": {"labels": ["Protected", "Not protected"], "data": [prot, total - prot]},
        "physical_virtual": _group(db, I.physical_virtual),
        "oracle_versions": _group(db, I.db_version, where=I.db_version.is_not(None), limit=10),
        "vendors": _group(db, I.hardware_vendor, limit=10),
    }


# ------------------------------------------------------------------ reports
@router.get("/reports/summary")
def report_summary(group_by: str | None = None, db: Session = Depends(get_db),
                   cf: list = Depends(report_filters), user=Depends(require("report:view"))):
    w = W(*cf)
    out = {"total": db.scalar(select(func.count()).select_from(I).where(w)),
           "by_opco": _pairs(_group(db, I.opco, w)), "by_domain": _pairs(_group(db, I.domain, w)),
           "by_environment": _pairs(_group(db, I.environment, w))}
    if group_by in REPORT_CATEGORIES:
        out["custom"] = {"group_by": group_by, "rows": _pairs(_group(db, getattr(I, group_by), w))}
    return out


def _windows(db, col, cf):
    today = date.today()
    spec = {"expired": (None, today - timedelta(days=1)), "d30": (today, today + timedelta(days=30)),
            "d90": (today, today + timedelta(days=90)), "d180": (today, today + timedelta(days=180))}
    counts, items = {}, {}
    for key, (a, b) in spec.items():
        cond = [col.is_not(None), col <= b, *cf]
        if a:
            cond.append(col >= a)
        counts[key] = db.scalar(select(func.count()).select_from(I).where(W(*cond)))
        items[key] = [_brief(x) for x in db.scalars(select(I).where(W(*cond)).order_by(col).limit(500))]
    return {"counts": counts, "items": items}


@router.get("/reports/eol")
def report_eol(db: Session = Depends(get_db), cf: list = Depends(report_filters), user=Depends(require("report:view"))):
    return _windows(db, I.end_of_life, cf)


@router.get("/reports/eos")
def report_eos(db: Session = Depends(get_db), cf: list = Depends(report_filters), user=Depends(require("report:view"))):
    today = date.today()
    cat = case((C.oracle_row(), "oracle"), (I.support_type.ilike("%hardware%"), "hardware"), else_="vendor")
    base = [I.end_of_support.is_not(None), I.end_of_support <= today + timedelta(days=180), *cf]
    expired = I.end_of_support < today
    counts = {c: {"expired": 0, "upcoming": 0} for c in ("vendor", "oracle", "hardware")}
    for c, e, n in db.execute(select(cat, expired, func.count()).where(W(*base)).group_by(cat, expired)):
        counts[c]["expired" if e else "upcoming"] = n
    items = {c: [_brief(x) for x in db.scalars(select(I).where(W(*base, cat == c)).order_by(I.end_of_support).limit(500))]
             for c in counts}
    return {"counts": counts, "items": items}


@router.get("/reports/backup")
def report_backup(db: Session = Depends(get_db), cf: list = Depends(report_filters), user=Depends(require("report:view"))):
    prot, w = C.protected(), W(*cf)
    total = db.scalar(select(func.count()).select_from(I).where(w))
    p = db.scalar(select(func.count()).select_from(I).where(W(*cf, prot)))
    by = []
    for opco, tot, pc in db.execute(select(I.opco, func.count(), func.count().filter(prot)).where(w).group_by(I.opco).order_by(I.opco)):
        by.append({"label": opco or "Unknown", "protected": pc, "unprotected": tot - pc,
                   "pct": round(100 * pc / tot, 1) if tot else 0})
    un = db.scalars(select(I).where(W(*cf, C.non_protected())).order_by(I.opco, I.hostname).limit(500))
    return {"protected": p, "unprotected": total - p, "compliance_pct": round(100 * p / total, 1) if total else 0,
            "by_opco": by, "unprotected_items": [_brief(x) for x in un]}


@router.get("/reports/virtualization")
def report_virt(db: Session = Depends(get_db), cf: list = Depends(report_filters), user=Depends(require("report:view"))):
    plat = case((I.virtualization_platform.ilike("%vmware%"), "VMware"),
                (I.virtualization_platform.ilike("%hyper%"), "Hyper-V"),
                (or_(I.product_name.ilike("%vmware%"), I.hardware_vendor.ilike("%vmware%")), "VMware"),
                (or_(I.product_name.ilike("%hyper%"), I.hardware_vendor.ilike("%hyper%")), "Hyper-V"),
                else_="Other / Unspecified")
    rows = db.execute(select(plat, func.count()).where(W(*cf, func.lower(I.physical_virtual) == "virtual"))
                      .group_by(plat).order_by(func.count().desc())).all()
    physical = db.scalar(select(func.count()).select_from(I).where(W(*cf, func.lower(I.physical_virtual) == "physical")))
    d = {r[0]: r[1] for r in rows}
    return {"vmware": d.get("VMware", 0), "hyperv": d.get("Hyper-V", 0), "physical": physical,
            "other_virtual": d.get("Other / Unspecified", 0), "platforms": [{"label": k, "count": v} for k, v in d.items()]}


@router.get("/reports/oracle")
def report_oracle(db: Session = Depends(get_db), cf: list = Depends(report_filters), user=Depends(require("report:view"))):
    sup = func.lower(func.trim(I.oracle_support)).in_(C.ORACLE_SUPPORTED)
    base = [C.oracle_row(), *cf]
    total = db.scalar(select(func.count()).select_from(I).where(W(*base)))
    s = db.scalar(select(func.count()).select_from(I).where(W(*base, sup)))
    un = db.scalars(select(I).where(W(*base, or_(I.oracle_support.is_(None), ~sup))).order_by(I.opco, I.hostname).limit(500))
    return {"supported": s, "unsupported": total - s,
            "versions": _pairs(_group(db, I.db_version, W(*cf, I.db_version.is_not(None)))),
            "unsupported_items": [_brief(x) for x in un]}
