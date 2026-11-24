"""Role -> permission matrix. Edit this one dict to change who can do what."""
ROLES = ["admin", "manager", "developer", "requester", "readonly"]
_ALL = set(ROLES)

PERMISSIONS = {
    "asset:read":   _ALL,
    "asset:write":  {"admin"},                       # create / edit / bulk edit
    "asset:delete": {"admin"},
    "asset:import": {"admin"},
    "asset:export": {"admin", "manager", "developer", "readonly"},
    "report:view":  {"admin", "manager", "developer", "readonly"},
    "audit:view":   {"admin", "manager"},
    "user:manage":  {"admin"},
    "change:request": {"requester"},                 # requester edits go through approval
    "change:approve": {"admin", "manager"},
    "change:view":    {"admin", "manager", "requester"},
}


def permissions_for(role: str) -> list[str]:
    return sorted(p for p, roles in PERMISSIONS.items() if role in roles)
