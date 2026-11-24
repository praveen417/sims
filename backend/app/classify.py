"""One place that defines what 'Linux', 'backup protected', etc. mean, so dashboard counts,
click-through inventory filters and reports always agree. Edit the constants to match your data."""
from datetime import date

from sqlalchemy import func, or_

from .models import Inventory as I

PROTECTED = {"yes", "y", "protected", "backed up", "enabled", "true", "active", "configured"}
ORACLE_SUPPORTED = {"yes", "y", "supported", "active", "valid", "true"}
LINUX = ["%linux%", "%rhel%", "%red hat%", "%centos%", "%ubuntu%", "%suse%", "%debian%", "%rocky%", "%alma%", "%oracle%"]


def protected():
    return func.lower(func.trim(I.backup_status)).in_(PROTECTED)


def non_protected():
    return or_(I.backup_status.is_(None), ~protected())


def oracle_row():
    return or_(I.db_version.is_not(None), I.oracle_support.is_not(None))


def linux():
    return or_(*[I.operating_system.ilike(p) for p in LINUX])


def windows():
    return I.operating_system.ilike("%windows%")


PRESETS = {
    "physical": lambda: func.lower(I.physical_virtual) == "physical",
    "virtual": lambda: func.lower(I.physical_virtual) == "virtual",
    "prod": lambda: func.lower(I.environment) == "prod",
    "dr": lambda: func.lower(I.environment) == "dr",
    "uat": lambda: func.lower(I.environment) == "uat",
    "linux": linux,
    "windows": windows,
    "oracle_db": oracle_row,
    "protected": protected,
    "non_protected": non_protected,
    "eos_expired": lambda: I.end_of_support < date.today(),
    "eol_expired": lambda: I.end_of_life < date.today(),
}
