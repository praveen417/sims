"""Change-request approval workflow.
Requesters cannot edit assets directly: they submit a change request, approvers (admin/manager)
approve or reject it in the portal or from the email link (which opens a confirmation page)."""
import html
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import auditlog
from ..auditlog import ser
from ..config import settings
from ..database import SessionLocal, get_db
from ..deps import ALGO, client_ip, require
from ..fields import FIELD_NAMES, LABELS
from ..mailer import send_mail
from ..models import ChangeRequest, Inventory, User
from ..permissions import PERMISSIONS
from ..schemas import validate_changes, validate_create
from .assets import check_unique, ensure_opco

router = APIRouter(tags=["change-requests"])


class ChangeIn(BaseModel):
    changes: dict[str, Any]
    reason: str = Field(min_length=3, max_length=2000)


class DecisionIn(BaseModel):
    comment: str | None = Field(None, max_length=2000)


def _now():
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ email
def _base():
    return settings.PUBLIC_URL.rstrip("/")


def _token(cr_id: int, username: str) -> str:
    exp = _now() + timedelta(hours=settings.APPROVAL_LINK_HOURS)
    return jwt.encode({"cr": cr_id, "who": username, "p": "cr-email", "exp": exp}, settings.SECRET_KEY, algorithm=ALGO)


def _diff_rows(cr: ChangeRequest) -> str:
    rows = ""
    for k, new in cr.changes.items():
        old = None if cr.request_type == "update" else "-"
        old = cr.old_values.get(k) if cr.request_type == "update" else old
        rows += (f"<tr><td style='padding:6px;border:1px solid #ddd'><b>{html.escape(LABELS.get(k, k))}</b></td>"
                 f"<td style='padding:6px;border:1px solid #ddd'>{html.escape(str(old if old is not None else '(blank)'))}</td>"
                 f"<td style='padding:6px;border:1px solid #ddd'>{html.escape(str(new if new is not None else '(blank)'))}</td></tr>")
    return ("<table style='border-collapse:collapse;font-family:Arial;font-size:13px'>"
            "<tr style='background:#FFCC00'><th style='padding:6px;border:1px solid #ddd'>Field</th>"
            "<th style='padding:6px;border:1px solid #ddd'>Current</th><th style='padding:6px;border:1px solid #ddd'>Requested</th></tr>"
            + rows + "</table>")


def _btn(url, label, bg, fg):
    return (f"<a href='{url}' style='display:inline-block;padding:10px 22px;margin-right:10px;background:{bg};"
            f"color:{fg};text-decoration:none;border-radius:6px;font-weight:bold;font-family:Arial'>{label}</a>")


def notify_approvers(cr_id: int):
    with SessionLocal() as db:
        cr = db.get(ChangeRequest, cr_id)
        if not cr:
            return
        for u in db.scalars(select(User).where(User.role.in_(PERMISSIONS["change:approve"]), User.status == "active")):
            if not u.email:
                continue
            t = _token(cr.id, u.username)
            new = cr.request_type == "create"
            what = "add a NEW server" if new else "change this server"
            body = (f"<div style='font-family:Arial'><h3>Approval needed: {'new server' if new else 'change to'} {html.escape(cr.hostname)} (request #{cr.id})</h3>"
                    f"<p><b>{html.escape(cr.requested_by)}</b> asked to {what}.<br><b>Reason:</b> {html.escape(cr.reason or '')}</p>"
                    f"{_diff_rows(cr)}<p style='margin-top:18px'>"
                    f"{_btn(f'{_base()}/api/approvals/email/{t}?action=approve', 'Approve', '#2e7d32', '#fff')}"
                    f"{_btn(f'{_base()}/api/approvals/email/{t}?action=reject', 'Reject', '#d32f2f', '#fff')}"
                    f"{_btn(f'{_base()}/changes', 'Open in portal', '#2F2F2F', '#FFCC00')}</p>"
                    f"<p style='color:#777;font-size:12px'>The buttons open a confirmation page; nothing changes until you confirm.</p></div>")
            send_mail(u.email, f"[SIMS] Approval needed: {'new server ' if new else ''}{cr.hostname} (#{cr.id})", body)


def notify_requester(cr_id: int):
    with SessionLocal() as db:
        cr = db.get(ChangeRequest, cr_id)
        if not cr or not cr.requester_email:
            return
        colour = "#2e7d32" if cr.status == "approved" else "#d32f2f"
        body = (f"<div style='font-family:Arial'><h3>Your change request #{cr.id} for {html.escape(cr.hostname)} was "
                f"<span style='color:{colour}'>{cr.status}</span></h3>"
                f"<p>Reviewed by {html.escape(cr.reviewed_by or '')}"
                + (f"<br>Comment: {html.escape(cr.review_comment)}" if cr.review_comment else "") + f"</p>{_diff_rows(cr)}</div>")
        send_mail(cr.requester_email, f"[SIMS] Change request #{cr.id} {cr.status}", body)


# ------------------------------------------------------------------ core logic
def decide(db: Session, cr_id: int, decision: str, reviewer: str, comment: str | None, source: str, ip: str | None):
    cr = db.scalar(select(ChangeRequest).where(ChangeRequest.id == cr_id).with_for_update())
    if not cr:
        raise HTTPException(404, "Change request not found")
    if cr.status != "pending":
        raise HTTPException(409, f"Already {cr.status}" + (f" by {cr.reviewed_by}" if cr.reviewed_by else ""))
    if decision == "approve":
        if cr.request_type == "create":
            data = validate_create(cr.changes)
            check_unique(db, data)
            ensure_opco(db, data.get("opco"))
            a = Inventory(**data)
            db.add(a)
            db.flush()
            cr.asset_id = a.id
            auditlog.log(db, reviewer, "ASSET_CREATE_APPROVED", ip, a.id, None, {k: ser(v) for k, v in data.items()})
        else:
            a = db.get(Inventory, cr.asset_id) if cr.asset_id else None
            if not a:
                raise HTTPException(409, "The asset no longer exists")
            changes = validate_changes(cr.changes)
            check_unique(db, changes, exclude_id=a.id)
            ensure_opco(db, changes.get("opco"))
            old, new = {}, {}
            for k, v in changes.items():
                if getattr(a, k) != v:
                    old[k], new[k] = ser(getattr(a, k)), ser(v)
                    setattr(a, k, v)
            if new:
                auditlog.log(db, reviewer, "ASSET_UPDATE_APPROVED", ip, a.id, old, new)
        cr.status = "approved"
    else:
        cr.status = "rejected"
    cr.reviewed_by, cr.review_comment, cr.review_source, cr.reviewed_date = reviewer, (comment or None), source, _now()
    auditlog.log(db, reviewer, "CHANGE_APPROVED" if decision == "approve" else "CHANGE_REJECTED", ip, cr.asset_id, None,
                 {"change_request": cr.id, "requested_by": cr.requested_by, "source": source, "comment": comment})
    db.commit()
    return cr


# ------------------------------------------------------------------ API
@router.post("/api/assets/{asset_id}/change-request", status_code=201)
def request_change(asset_id: int, body: ChangeIn, request: Request, bg: BackgroundTasks,
                   db: Session = Depends(get_db), user=Depends(require("change:request"))):
    a = db.get(Inventory, asset_id)
    if not a:
        raise HTTPException(404, "Asset not found")
    bad = [k for k in body.changes if k not in FIELD_NAMES]
    if bad:
        raise HTTPException(422, f"Unknown field(s): {', '.join(bad)}")
    parsed = validate_changes(body.changes)
    if "hostname" in parsed and not parsed["hostname"]:
        raise HTTPException(422, "Hostname cannot be blank")
    changes = {k: v for k, v in parsed.items() if getattr(a, k) != v}
    if not changes:
        raise HTTPException(422, "Nothing to change - the values are the same as the current ones")
    check_unique(db, changes, exclude_id=a.id)
    cr = ChangeRequest(request_type="update", asset_id=a.id, hostname=a.hostname, requested_by=user.username, requester_email=user.email,
                       changes={k: ser(v) for k, v in changes.items()},
                       old_values={k: ser(getattr(a, k)) for k in changes}, reason=body.reason.strip(), status="pending")
    db.add(cr)
    db.flush()
    auditlog.log(db, user.username, "CHANGE_REQUESTED", client_ip(request), a.id, cr.old_values, cr.changes)
    db.commit()
    bg.add_task(notify_approvers, cr.id)
    return {"id": cr.id, "status": cr.status}


@router.post("/api/changes/new-asset", status_code=201)
def request_new_asset(body: ChangeIn, request: Request, bg: BackgroundTasks,
                      db: Session = Depends(get_db), user=Depends(require("change:request"))):
    """A requester proposes a brand-new server; it is only added when an approver accepts."""
    bad = [k for k in body.changes if k not in FIELD_NAMES]
    if bad:
        raise HTTPException(422, f"Unknown field(s): {', '.join(bad)}")
    data = validate_create(body.changes)
    check_unique(db, data)
    if db.scalar(select(ChangeRequest.id).where(ChangeRequest.request_type == "create", ChangeRequest.status == "pending",
                                                func.lower(ChangeRequest.hostname) == data["hostname"].lower()).limit(1)):
        raise HTTPException(409, f"A request to add '{data['hostname']}' is already waiting for approval")
    cr = ChangeRequest(request_type="create", asset_id=None, hostname=data["hostname"], requested_by=user.username,
                       requester_email=user.email, changes={k: ser(v) for k, v in data.items()}, old_values={},
                       reason=body.reason.strip(), status="pending")
    db.add(cr)
    db.flush()
    auditlog.log(db, user.username, "CHANGE_REQUESTED", client_ip(request), None, None, cr.changes)
    db.commit()
    bg.add_task(notify_approvers, cr.id)
    return {"id": cr.id, "status": cr.status}


@router.get("/api/changes")
def list_changes(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                 db: Session = Depends(get_db), user=Depends(require("change:view"))):
    stmt = select(ChangeRequest)
    if user.role == "requester":
        stmt = stmt.where(ChangeRequest.requested_by == user.username)
    if status:
        stmt = stmt.where(ChangeRequest.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(ChangeRequest.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    assets = {a.id: a for a in db.scalars(select(Inventory).where(Inventory.id.in_([r.asset_id for r in rows if r.asset_id])))}
    items = []
    for r in rows:
        a = assets.get(r.asset_id)
        stale = bool(r.status == "pending" and a and any(ser(getattr(a, k)) != r.old_values.get(k) for k in r.changes))
        items.append({"id": r.id, "request_type": r.request_type, "asset_id": r.asset_id, "hostname": r.hostname, "requested_by": r.requested_by,
                      "changes": r.changes, "old_values": r.old_values, "reason": r.reason, "status": r.status,
                      "reviewed_by": r.reviewed_by, "review_comment": r.review_comment, "review_source": r.review_source,
                      "created_date": r.created_date, "reviewed_date": r.reviewed_date, "stale": stale})
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _portal_decision(decision: str):
    def endpoint(cr_id: int, body: DecisionIn, request: Request, bg: BackgroundTasks,
                 db: Session = Depends(get_db), user=Depends(require("change:approve"))):
        decide(db, cr_id, decision, user.username, body.comment, "portal", client_ip(request))
        bg.add_task(notify_requester, cr_id)
        return {"detail": f"Request {decision}d"}
    endpoint.__name__ = f"{decision}_change_request"
    return endpoint


router.post("/api/changes/{cr_id}/approve")(_portal_decision("approve"))
router.post("/api/changes/{cr_id}/reject")(_portal_decision("reject"))


@router.post("/api/changes/{cr_id}/cancel")
def cancel(cr_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require("change:request"))):
    cr = db.get(ChangeRequest, cr_id)
    if not cr or cr.requested_by != user.username:
        raise HTTPException(404, "Change request not found")
    if cr.status != "pending":
        raise HTTPException(409, f"Already {cr.status}")
    cr.status, cr.reviewed_date = "cancelled", _now()
    auditlog.log(db, user.username, "CHANGE_CANCELLED", client_ip(request), cr.asset_id, None, {"change_request": cr.id})
    db.commit()
    return {"detail": "Cancelled"}


# ------------------------------------------------------------------ email approval pages (token protected)
def _page(title: str, body: str, code: int = 200) -> HTMLResponse:
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>SIMS</title></head><body style='margin:0;background:#f4f4f4;font-family:Arial'>"
           f"<div style='background:#FFCC00;padding:14px 20px;font-weight:bold;color:#2F2F2F'>SIMS - Server Inventory Management System</div>"
           f"<div style='max-width:720px;margin:24px auto;background:#fff;padding:24px;border-radius:8px'><h2>{html.escape(title)}</h2>{body}</div></body></html>")
    return HTMLResponse(doc, status_code=code)


def _load(db: Session, token: str):
    try:
        p = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        if p.get("p") != "cr-email":
            raise JWTError("purpose")
    except JWTError:
        return None, None, _page("Link invalid or expired", "<p>Please open the portal to review this request.</p>", 400)
    user = db.scalar(select(User).where(User.username == p["who"]))
    if not user or user.status != "active" or user.role not in PERMISSIONS["change:approve"]:
        return None, None, _page("Not allowed", "<p>This account can no longer approve requests.</p>", 403)
    cr = db.get(ChangeRequest, p["cr"])
    if not cr:
        return None, None, _page("Not found", "<p>This change request no longer exists.</p>", 404)
    return cr, user, None


@router.get("/api/approvals/email/{token}", response_class=HTMLResponse, include_in_schema=False)
def email_page(token: str, action: str = "approve", db: Session = Depends(get_db)):
    cr, user, err = _load(db, token)
    if err:
        return err
    if cr.status != "pending":
        return _page(f"Already {cr.status}", f"<p>Request #{cr.id} for <b>{html.escape(cr.hostname)}</b> was {cr.status}"
                     f" by {html.escape(cr.reviewed_by or '-')}.</p>")
    sel = lambda a: "font-weight:bold;outline:3px solid #2F2F2F;" if a == action else ""
    form = (f"<form method='post'><p><b>Comment</b> (optional)<br><textarea name='comment' rows='3' style='width:100%'></textarea></p>"
            f"<button name='action' value='approve' style='padding:10px 22px;background:#2e7d32;color:#fff;border:0;border-radius:6px;{sel('approve')}'>Approve</button> "
            f"<button name='action' value='reject' style='padding:10px 22px;background:#d32f2f;color:#fff;border:0;border-radius:6px;{sel('reject')}'>Reject</button></form>")
    return _page(f"{'New server request' if cr.request_type == 'create' else 'Change request'} #{cr.id}: {cr.hostname}",
                 f"<p>Requested by <b>{html.escape(cr.requested_by)}</b><br>Reason: {html.escape(cr.reason or '')}</p>"
                 f"{_diff_rows(cr)}<p>You are signing in as <b>{html.escape(user.username)}</b>.</p>{form}")


@router.post("/api/approvals/email/{token}", response_class=HTMLResponse, include_in_schema=False)
def email_decide(token: str, request: Request, bg: BackgroundTasks, action: str = Form(...), comment: str = Form(""),
                 db: Session = Depends(get_db)):
    cr, user, err = _load(db, token)
    if err:
        return err
    if action not in ("approve", "reject"):
        return _page("Invalid action", "<p>Please use the Approve or Reject button.</p>", 400)
    try:
        decide(db, cr.id, action, user.username, comment.strip()[:2000] or None, "email", client_ip(request))
    except HTTPException as e:
        return _page("Could not complete", f"<p>{html.escape(str(e.detail))}</p>", e.status_code)
    bg.add_task(notify_requester, cr.id)
    return _page(f"Request {action}d", f"<p>Change request #{cr.id} for <b>{html.escape(cr.hostname)}</b> was {action}d. You can close this page.</p>")
