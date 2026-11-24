"""Sheet import: parsing/validation (pure functions) + DB commit.

Rules: only Hostname is mandatory. Blank cells, blank columns, blank-header columns and
missing columns are all fine. Blank cells never overwrite existing data on update.
"""
import io
import re
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func, select

from .auditlog import log as audit_log, ser
from .fields import FIELDS, KIND, LABELS, MAXLEN, UNIQUE_FIELDS
from .models import Inventory, Opco

NA_VALUES = {"", "na", "n/a", "nil", "none", "null", "-", "--", "nan", "tbd"}
IGNORED = {"classification", "createddate", "lastmodifieddate", "modifieddate", "updateddate",
           "id", "sno", "srno", "slno"}
DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d-%b-%Y",
                "%d %b %Y", "%d-%b-%y", "%d/%m/%y", "%Y/%m/%d", "%b %d, %Y", "%d %B %Y", "%m/%d/%Y"]
ENV_MAP = {"prod": "Prod", "production": "Prod", "prd": "Prod", "dr": "DR", "disaster recovery": "DR",
           "uat": "UAT", "dev": "Dev", "development": "Dev", "test": "Test", "testing": "Test", "qa": "Test"}
PV_MAP = {"physical": "Physical", "phy": "Physical", "virtual": "Virtual", "vm": "Virtual"}


class ImportFileError(Exception):
    pass


def norm_header(h) -> str:
    return re.sub(r"[^a-z0-9]", "", str(h).lower())


ALIASES = {norm_header(label): name for name, _, _, label in FIELDS}
ALIASES.update({
    "ip": "ip_address", "ilo": "iloip", "serial": "serial_number", "appowner": "application_owner",
    "env": "environment", "class": "bia_class", "bia": "bia_class", "biaclass": "bia_class",
    "os": "operating_system", "memory": "memory_gb", "mac": "mac_address", "vendor": "hardware_vendor",
    "endoflifedate": "end_of_life", "eol": "end_of_life", "endofsupportdate": "end_of_support",
    "eos": "end_of_support", "databaseversion": "db_version", "dbversion": "db_version",
    "itononito": "ito_non_ito", "itononito ": "ito_non_ito", "physicalvirtual": "physical_virtual",
    "virtualizationplatform": "virtualization_platform", "oraclesupport": "oracle_support",
})
ALIASES["iloip"] = "ilo_ip"


def resolve_column(header: str):
    h = str(header)
    for cand in (norm_header(h), norm_header(re.sub(r"\(.*?\)", "", h))):
        if cand in ALIASES:
            return ALIASES[cand]
        if cand in IGNORED:
            return "__ignored__"
    return None


def parse_date(v: str) -> date:
    if v.isdigit() and 20000 < int(v) < 80000:  # Excel serial number
        return (datetime(1899, 12, 30) + timedelta(days=int(v))).date()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date '{v}' (use YYYY-MM-DD or DD/MM/YYYY)")


def clean_value(name: str, raw):
    """Return (value, error). Blank -> (None, None)."""
    v = str(raw).strip() if raw is not None else ""
    if v == "":
        return None, None
    kind = KIND[name]
    if (kind in ("int", "date") or name in UNIQUE_FIELDS) and v.lower() in NA_VALUES:
        return None, None
    try:
        if kind == "int":
            return int(float(v.replace(",", ""))), None
        if kind == "date":
            return parse_date(v), None
    except ValueError as e:
        return None, str(e) if kind == "date" else f"'{v}' is not a number"
    if name == "environment":
        mapped = ENV_MAP.get(v.lower())
        if not mapped:
            return None, f"unknown environment '{v}' (allowed: Prod, DR, UAT, Dev, Test)"
        return mapped, None
    if name == "physical_virtual":
        v = PV_MAP.get(v.lower(), v)
    if kind == "str" and MAXLEN[name] and len(v) > MAXLEN[name]:
        return None, f"too long ({len(v)} chars, max {MAXLEN[name]})"
    return v, None


def read_table(filename: str, content: bytes) -> pd.DataFrame:
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    try:
        if ext in ("xlsx", "xls"):
            return pd.read_excel(io.BytesIO(content), dtype=str, keep_default_na=False)
        if ext == "csv":
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content.decode("cp1252")
            df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
            if df.shape[1] == 1 and ";" in str(df.columns[0]):
                df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, sep=";")
            return df
    except Exception as e:  # corrupt file, wrong format, etc.
        raise ImportFileError(f"Could not read file: {e}")
    raise ImportFileError("Unsupported file type. Use .xlsx, .xls or .csv")


def parse_upload(filename: str, content: bytes) -> dict:
    df = read_table(filename, content)
    colmap, ignored = {}, []
    for col in df.columns:
        target = resolve_column(col)
        if target is None:
            if not str(col).startswith("Unnamed") and str(col).strip():
                ignored.append(str(col))
        elif target == "__ignored__":
            ignored.append(str(col))
        elif target in colmap.values():
            ignored.append(f"{col} (duplicate of an earlier column)")
        else:
            colmap[col] = target
    if "hostname" not in colmap.values():
        raise ImportFileError("No 'Hostname' column found. Hostname is the only required column.")

    rows = []
    for idx, rec in enumerate(df.to_dict("records")):
        data, errors = {}, []
        for col, name in colmap.items():
            val, err = clean_value(name, rec.get(col))
            data[name] = val
            if err:
                errors.append((LABELS[name], err))
        if all(v is None for v in data.values()) and not errors:
            continue  # fully blank row
        if not data.get("hostname") and not any(c == LABELS["hostname"] for c, _ in errors):
            errors.append((LABELS["hostname"], "Hostname is required"))
        rows.append({"row": idx + 2, "data": data, "errors": errors})

    first_seen = {f: {} for f in UNIQUE_FIELDS}  # in-file duplicate detection
    for r in rows:
        for f in UNIQUE_FIELDS:
            v = r["data"].get(f)
            if not v:
                continue
            key = v.lower() if f == "hostname" else v
            if key in first_seen[f]:
                r["errors"].append((LABELS[f], f"duplicate of row {first_seen[f][key]} in this file"))
            else:
                first_seen[f][key] = r["row"]
    return {"rows": rows, "ignored_columns": ignored, "columns_found": sorted(colmap.values())}


def _chunks(seq, n=5000):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run_import(db, parsed, on_duplicate, skip_invalid, commit, username, ip) -> dict:
    rows = parsed["rows"]
    host_keys = [r["data"]["hostname"].lower() for r in rows if r["data"].get("hostname")]
    existing = {}
    for ch in _chunks(host_keys):
        for a in db.scalars(select(Inventory).where(func.lower(Inventory.hostname).in_(ch))):
            existing[a.hostname.lower()] = a
    owners = {"ip_address": {}, "serial_number": {}}
    for f in owners:
        vals = [r["data"][f] for r in rows if r["data"].get(f)]
        col = getattr(Inventory, f)
        for ch in _chunks(vals):
            for _id, v in db.execute(select(Inventory.id, col).where(col.in_(ch))):
                owners[f][v] = _id

    opco_names = {o.lower(): o for o in db.scalars(select(Opco.name))}
    new_opcos, plan_new, plan_upd, errors = {}, [], [], []
    skipped = rejected = 0
    for r in rows:
        d, errs = r["data"], list(r["errors"])
        a = existing.get((d.get("hostname") or "").lower()) if d.get("hostname") else None
        if not errs:
            if a and on_duplicate == "reject":
                errs.append((LABELS["hostname"], "Hostname already exists"))
            for f in owners:
                v = d.get(f)
                if v and v in owners[f] and (not a or owners[f][v] != a.id):
                    errs.append((LABELS[f], f"'{v}' already belongs to another asset"))
        if errs:
            rejected += 1
            errors += [{"row": r["row"], "hostname": d.get("hostname"), "column": c, "message": m} for c, m in errs]
            continue
        if d.get("opco"):
            canon = opco_names.get(d["opco"].lower())
            if canon:
                d["opco"] = canon
            else:
                opco_names[d["opco"].lower()] = d["opco"]
                new_opcos[d["opco"]] = True
        if a:
            if on_duplicate == "skip":
                skipped += 1
            else:
                plan_upd.append((a, {k: v for k, v in d.items() if v is not None}))
        else:
            plan_new.append(d)

    report = {"mode": "commit" if commit else "preview", "total_rows": len(rows),
              "to_create": len(plan_new), "to_update": len(plan_upd), "skipped": skipped,
              "rejected": rejected, "new_opcos": sorted(new_opcos),
              "ignored_columns": parsed["ignored_columns"], "columns_found": parsed["columns_found"],
              "error_count": len(errors), "errors": errors[:2000], "committed": False}
    if not commit:
        return report
    if rejected and not skip_invalid:
        report["message"] = "Nothing imported: fix the errors or re-run with skip_invalid=true."
        return report

    updated = unchanged = 0
    for name in new_opcos:
        db.add(Opco(name=name))
    for d in plan_new:
        db.add(Inventory(**d))
    for a, changes in plan_upd:
        old, new = {}, {}
        for k, v in changes.items():
            if getattr(a, k) != v:
                old[k], new[k] = ser(getattr(a, k)), ser(v)
                setattr(a, k, v)
        if new:
            updated += 1
            audit_log(db, username, "ASSET_UPDATE_IMPORT", ip, a.id, old, new)
        else:
            unchanged += 1
    audit_log(db, username, "EXCEL_IMPORT", ip, None, None,
              {"created": len(plan_new), "updated": updated, "unchanged": unchanged,
               "skipped": skipped, "rejected": rejected, "on_duplicate": on_duplicate})
    db.commit()
    report.update({"committed": True, "created": len(plan_new), "updated": updated, "unchanged": unchanged})
    return report
