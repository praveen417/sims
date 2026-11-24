from sqlalchemy import func, or_, select

from .classify import PRESETS
from .fields import FIELD_NAMES, KIND, SEARCH_FIELDS
from .models import Inventory

SORTABLE = set(FIELD_NAMES) | {"id", "created_date", "updated_date"}


def like_pattern(v: str) -> str:
    """User text -> ILIKE pattern. '*' and '?' are wildcards; plain text means 'contains'."""
    v = v.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    if "*" in v or "?" in v:
        return v.replace("*", "%").replace("?", "_")
    return f"%{v}%"


def build_stmt(params: dict, q: str | None = None, ids: list[int] | None = None):
    """Filters: field=text (contains / wildcard), field==Exact (exact, case-insensitive),
    field==__blank__ (empty), preset=<name> (dashboard categories), q=global search."""
    stmt = select(Inventory)
    if ids:
        stmt = stmt.where(Inventory.id.in_(ids))
    for name in FIELD_NAMES:
        v = params.get(name)
        if v is None or str(v).strip() == "":
            continue
        col = getattr(Inventory, name)
        kind = KIND[name]
        s = str(v).strip()
        if kind in ("str", "text"):
            if s.startswith("="):
                val = s[1:]
                stmt = stmt.where(col.is_(None) if val == "__blank__" else func.lower(col) == val.lower())
            else:
                stmt = stmt.where(col.ilike(like_pattern(s), escape="\\"))
        elif kind == "int":
            try:
                stmt = stmt.where(col == int(s))
            except ValueError:
                pass
    preset = params.get("preset")
    if preset in PRESETS:
        stmt = stmt.where(PRESETS[preset]())
    for key, col in (("eol_before", Inventory.end_of_life), ("eos_before", Inventory.end_of_support)):
        if params.get(key):
            stmt = stmt.where(col <= params[key])
    if q and q.strip():
        pat = like_pattern(q)
        stmt = stmt.where(or_(*[getattr(Inventory, f).ilike(pat, escape="\\") for f in SEARCH_FIELDS]))
    return stmt
