import csv
import io
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import auditlog
from ..assets_query import build_stmt
from ..database import get_db
from ..deps import client_ip, require
from ..fields import FIELDS, FIELD_NAMES
from ..importer import ImportFileError, parse_upload, run_import
from ..models import Inventory

router = APIRouter(tags=["import-export"])
UPLOAD_DIR = "/app/uploads/imports"


@router.post("/api/import/excel")
def import_excel(request: Request, file: UploadFile = File(...), mode: str = Form("preview"),
                 on_duplicate: str = Form("update"), skip_invalid: bool = Form(True),
                 db: Session = Depends(get_db), user=Depends(require("asset:import"))):
    """mode=preview validates only; mode=commit writes. on_duplicate: update | skip | reject."""
    if mode not in ("preview", "commit"):
        raise HTTPException(422, "mode must be preview or commit")
    if on_duplicate not in ("update", "skip", "reject"):
        raise HTTPException(422, "on_duplicate must be update, skip or reject")
    content = file.file.read()
    try:
        parsed = parse_upload(file.filename, content)
    except ImportFileError as e:
        raise HTTPException(400, str(e))
    report = run_import(db, parsed, on_duplicate, skip_invalid, mode == "commit",
                        user.username, client_ip(request))
    if report["committed"]:
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(os.path.join(UPLOAD_DIR, f"{stamp}_{user.username}_{os.path.basename(file.filename)}"), "wb") as fh:
                fh.write(content)
        except OSError:
            pass
    return report


@router.get("/api/import/template")
def template(user=Depends(require("asset:import"))):
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"
    ws.append([f[3] for f in FIELDS])
    ws.append(["Zambia", "ITO UNIX", "Server", "examplehost01", "Active", "10.0.0.10"])
    buf = io.BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="ServerInventory_Template.xlsx"'})


def _export(request: Request, fmt: str, ids: str | None, q: str | None, db: Session, user):
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    stmt = build_stmt(dict(request.query_params), q, id_list).order_by(Inventory.id)
    headers = [f[3] for f in FIELDS]
    rows = ([auditlog.ser(getattr(a, n)) for n in FIELD_NAMES]
            for a in db.execute(stmt).scalars().yield_per(2000))
    name = f"ServerInventory_{datetime.now():%Y%m%d}"
    count = 0
    if fmt == "xlsx":
        wb = Workbook(write_only=True)
        ws = wb.create_sheet("Inventory")
        ws.append(headers)
        for r in rows:
            ws.append(r)
            count += 1
        buf = io.BytesIO()
        wb.save(buf)
        body, mime = buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)
            count += 1
        body, mime = ("\ufeff" + buf.getvalue()).encode("utf-8"), "text/csv"
    auditlog.log(db, user.username, "EXCEL_EXPORT", client_ip(request), None, None,
                 {"format": fmt, "records": count, "selected_ids": bool(id_list)})
    db.commit()
    return Response(body, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'})


@router.get("/api/export/excel")
def export_excel(request: Request, ids: str | None = None, q: str | None = None,
                 db: Session = Depends(get_db), user=Depends(require("asset:export"))):
    """No params = full inventory; filter params = filtered data; ids=1,2,3 = selected records."""
    return _export(request, "xlsx", ids, q, db, user)


@router.get("/api/export/csv")
def export_csv(request: Request, ids: str | None = None, q: str | None = None,
               db: Session = Depends(get_db), user=Depends(require("asset:export"))):
    return _export(request, "csv", ids, q, db, user)
