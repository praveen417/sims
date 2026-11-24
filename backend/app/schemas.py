from datetime import date, datetime
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError, ConfigDict, EmailStr, Field, create_model, model_validator

from .fields import FIELDS
from .permissions import ROLES

_PY = {"str": str, "text": str, "int": int, "date": date}


class _Blank2None(BaseModel):
    """Trim strings; blank strings become NULL."""
    @model_validator(mode="before")
    @classmethod
    def _clean(cls, data: Any):
        if isinstance(data, dict):
            out = {}
            for k, v in data.items():
                if isinstance(v, str):
                    v = v.strip() or None
                out[k] = v
            return out
        return data


def _fields(required_hostname: bool):
    spec = {}
    for name, kind, maxlen, _ in FIELDS:
        t = _PY[kind]
        kw = {"max_length": maxlen} if kind == "str" and maxlen else {}
        if name == "hostname" and required_hostname:
            spec[name] = (t, Field(..., min_length=1, **kw))
        else:
            spec[name] = (Optional[t], Field(None, **kw))
    return spec


AssetCreate = create_model("AssetCreate", __base__=_Blank2None, **_fields(True))
AssetUpdate = create_model("AssetUpdate", __base__=_Blank2None, **_fields(False))
_out = {n: (Optional[_PY[k]], None) for n, k, _, _ in FIELDS}
AssetOut = create_model("AssetOut", __config__=ConfigDict(from_attributes=True),
                        id=(int, ...), created_date=(Optional[datetime], None),
                        updated_date=(Optional[datetime], None), **_out)


class BulkUpdate(BaseModel):
    ids: list[int] = Field(min_length=1)
    changes: dict[str, Any]


class LoginIn(BaseModel):
    username: str
    password: str


class ForgotIn(BaseModel):
    username: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str

    @model_validator(mode="after")
    def _role(self):
        if self.role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}")
        return self


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None  # active | disabled

    @model_validator(mode="after")
    def _chk(self):
        if self.role is not None and self.role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}")
        if self.status is not None and self.status not in ("active", "disabled"):
            raise ValueError("status must be active or disabled")
        return self


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    email: str
    role: str
    status: str
    last_login: Optional[datetime] = None
    created_date: Optional[datetime] = None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


def validate_changes(changes: dict) -> dict:
    """Validate a partial asset update dict; returns only the supplied fields (typed)."""
    try:
        return AssetUpdate(**changes).model_dump(exclude_unset=True)
    except ValidationError as e:
        raise HTTPException(422, "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()))


def validate_create(data: dict) -> dict:
    """Validate a full new-asset payload (hostname required); returns only the non-blank values."""
    try:
        m = AssetCreate(**data)
    except ValidationError as e:
        raise HTTPException(422, "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()))
    return {k: v for k, v in m.model_dump().items() if v is not None}
