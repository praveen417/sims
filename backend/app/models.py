from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String,
                        Text, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="readonly")  # admin|manager|developer|requester|readonly
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | disabled | locked
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Opco(Base):
    __tablename__ = "opcos"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    country: Mapped[str | None] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Inventory(Base):
    """Only hostname is mandatory; every other column may be blank."""
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(primary_key=True)
    opco: Mapped[str | None] = mapped_column(String(100), index=True)
    domain: Mapped[str | None] = mapped_column(String(100), index=True)
    asset_type: Mapped[str | None] = mapped_column(String(100))
    hostname: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str | None] = mapped_column(String(50))
    ip_address: Mapped[str | None] = mapped_column(String(45), unique=True)
    backup_status: Mapped[str | None] = mapped_column(String(50), index=True)
    ilo_ip: Mapped[str | None] = mapped_column(String(45))
    serial_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    application: Mapped[str | None] = mapped_column(Text)
    application_owner: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(String(20), index=True)
    bia_class: Mapped[str | None] = mapped_column(String(50))
    physical_virtual: Mapped[str | None] = mapped_column(String(20), index=True)
    base_machine: Mapped[str | None] = mapped_column(Text)
    base_machine_ip: Mapped[str | None] = mapped_column(Text)
    virtualization_platform: Mapped[str | None] = mapped_column(String(100))
    operating_system: Mapped[str | None] = mapped_column(String(150), index=True)
    memory_gb: Mapped[int | None] = mapped_column(Integer)
    fqdn: Mapped[str | None] = mapped_column(Text)
    processor_count: Mapped[int | None] = mapped_column(Integer)
    processor_name: Mapped[str | None] = mapped_column(Text)
    mac_address: Mapped[str | None] = mapped_column(Text)
    product_name: Mapped[str | None] = mapped_column(Text)
    hardware_vendor: Mapped[str | None] = mapped_column(String(100))
    support_type: Mapped[str | None] = mapped_column(String(30))
    server_role: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    ito_non_ito: Mapped[str | None] = mapped_column(String(20))
    end_of_life: Mapped[date | None] = mapped_column(Date, index=True)
    end_of_support: Mapped[date | None] = mapped_column(Date, index=True)
    oracle_support: Mapped[str | None] = mapped_column(String(50))
    db_version: Mapped[str | None] = mapped_column(String(50))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    filter_json: Mapped[dict] = mapped_column(JSONB)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChangeRequest(Base):
    __tablename__ = "change_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_type: Mapped[str] = mapped_column(String(10), default="update")  # update | create
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("inventory.id", ondelete="CASCADE"), index=True)
    hostname: Mapped[str] = mapped_column(String(255))
    requested_by: Mapped[str] = mapped_column(String(100), index=True)
    requester_email: Mapped[str | None] = mapped_column(String(255))
    changes: Mapped[dict] = mapped_column(JSONB)
    old_values: Mapped[dict] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|approved|rejected|cancelled
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    review_comment: Mapped[str | None] = mapped_column(Text)
    review_source: Mapped[str | None] = mapped_column(String(20))  # portal | email
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
