# SIMS - Enterprise Server Inventory Management System

Stage 4: full portal (React UI + FastAPI backend): inventory, import/export, reports, audit, users, change-request approvals, ping.

## Run

```bash
cp .env.example .env      # edit passwords and SECRET_KEY
docker compose up -d --build
```
Swagger: http://SERVER_IP/docs   Health: http://SERVER_IP/api/health
Migrations run automatically on backend start (`alembic upgrade head`).

## Roles (edit `backend/app/permissions.py` to change)

| Permission   | admin | manager | developer | requester | readonly |
|--------------|:-----:|:-------:|:---------:|:---------:|:--------:|
| view assets  |  yes  |   yes   |    yes    |    yes    |   yes    |
| create/edit/bulk edit/delete, import | yes | - | - | - | - |
| export       |  yes  |   yes   |    yes    |     -     |   yes    |
| reports      |  yes  |   yes   |    yes    |     -     |   yes    |
| audit logs   |  yes  |   yes   |     -     |     -     |    -     |
| manage users |  yes  |    -    |     -     |     -     |    -     |

## Import rules
- Only **Hostname** is required. Blank cells, blank columns and missing columns are accepted.
- Blank cells never overwrite existing data when updating an existing host.
- "Classification" and unknown columns are ignored and listed in the report.
- Unknown OPCO names are created automatically.
- `POST /api/import/excel` with `mode=preview` (no changes) then `mode=commit`;
  `on_duplicate` = update (default) | skip | reject; `skip_invalid=true` imports the good rows.
- `GET /api/import/template` downloads a blank template.

## Editing
`PUT /api/assets/{id}` (admin) changes any field, sending null/"" clears it;
`PATCH /api/assets/bulk` updates many rows. Every change is stored in the audit log with old/new values.

## Change-request approval (requester role)
A requester cannot edit servers directly. In Server Inventory they open a server, change fields, give a reason and
**Submit for approval**. To add a server they use **Request new server** (the same form plus a reason); the server is only
created when an approver accepts. Admins and managers (the CMDB managers) are notified by email and in the portal (Change Requests page, badge in the menu).
- **Portal:** Change Requests -> Approve / Reject (optional comment). Approval applies the change and writes it to the audit log.
- **Email:** each approver gets Approve / Reject buttons. They open a confirmation page; nothing changes until the approver
  presses the button there (this stops mail scanners from approving by accident). Links are personal and expire after 7 days.
- The requester is emailed the outcome. The first decision wins; later attempts are told the request was already decided.
- Email needs `SMTP_*` and `PUBLIC_URL` in `.env`; approvers need an email address on their user. Without SMTP the portal flow still works.

## Ping (admin)
The network icon on a row, or **Ping selected**, pings from the backend container and writes the result at the top of Remarks:
`[Ping 2026-11-19 10:15 UTC] OK - Reply received (3/3 replies, avg 1.2 ms)` or `FAILED - <reason>`.
The previous ping line is replaced; other remark text is kept. Target order: IP address, FQDN, hostname.

## Dashboard click-through and report filters
Dashboard widgets and chart bars open Server Inventory already filtered (the same rules as the counts, see `backend/app/classify.py`).
Reports -> "Filter by category" limits every report to the chosen categories (OPCO, domain, environment, vendor, OS, location, ...);
the Asset Summary tab can also group by any category.
