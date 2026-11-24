import React, { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField, Typography } from "@mui/material";
import { api, errMsg } from "../api";

const ACTIONS = ["LOGIN", "LOGOUT", "LOGIN_FAILED", "ACCOUNT_LOCKED", "ASSET_CREATE", "ASSET_UPDATE", "ASSET_UPDATE_IMPORT", "ASSET_BULK_UPDATE", "ASSET_DELETE", "ASSET_PING", "ASSET_UPDATE_APPROVED", "ASSET_CREATE_APPROVED", "CHANGE_REQUESTED", "CHANGE_APPROVED", "CHANGE_REJECTED", "CHANGE_CANCELLED", "EXCEL_IMPORT", "EXCEL_EXPORT", "USER_CREATE", "USER_UPDATE", "USER_DELETE", "USER_PASSWORD_RESET", "USER_UNLOCK", "PASSWORD_CHANGED"];

function summary(r) {
  const o = r.old_value, n = r.new_value;
  if (o && n) return Object.keys(n).map((k) => `${k}: ${o[k] ?? "(blank)"} -> ${n[k] ?? "(blank)"}`).join("; ");
  const v = n || o;
  return v ? Object.entries(v).filter(([, x]) => x !== null).slice(0, 6).map(([k, x]) => `${k}: ${x}`).join("; ") : "";
}

export default function AuditLogs() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(100);
  const [f, setF] = useState({ username: "", action: "", date_from: "", date_to: "" });
  const [applied, setApplied] = useState(f);
  const [err, setErr] = useState("");
  const [view, setView] = useState(null);

  const load = useCallback(async () => {
    try {
      const params = { page: page + 1, page_size: size };
      Object.entries(applied).forEach(([k, v]) => { if (v) params[k] = v; });
      const r = await api.get("/audit", { params }); setData(r.data); setErr("");
    } catch (e) { setErr(errMsg(e)); }
  }, [page, size, applied]);
  useEffect(() => { load(); }, [load]);

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Audit Logs</Typography>
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap", gap: 1 }}>
        <TextField size="small" label="Username" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} />
        <TextField size="small" select SelectProps={{ native: true }} label="Action" value={f.action} InputLabelProps={{ shrink: true }} onChange={(e) => setF({ ...f, action: e.target.value })} sx={{ minWidth: 200 }}>
          <option value="">(all)</option>{ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
        </TextField>
        <TextField size="small" type="date" label="From" InputLabelProps={{ shrink: true }} value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} />
        <TextField size="small" type="date" label="To" InputLabelProps={{ shrink: true }} value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value ? `${e.target.value}T23:59:59` : "" })} />
        <Button variant="contained" onClick={() => { setPage(0); setApplied(f); }}>Filter</Button>
      </Stack>
      {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead><TableRow><TableCell>Time</TableCell><TableCell>User</TableCell><TableCell>Action</TableCell><TableCell>Source IP</TableCell><TableCell>Asset ID</TableCell><TableCell>Changes</TableCell></TableRow></TableHead>
          <TableBody>
            {data.items.map((r) => (
              <TableRow key={r.id} hover onClick={() => (r.old_value || r.new_value) && setView(r)} sx={{ cursor: r.old_value || r.new_value ? "pointer" : "default" }}>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{new Date(r.timestamp).toLocaleString()}</TableCell>
                <TableCell>{r.username}</TableCell><TableCell>{r.action}</TableCell><TableCell>{r.ip_address}</TableCell><TableCell>{r.entity_id}</TableCell>
                <TableCell sx={{ maxWidth: 420, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{summary(r)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination component="div" count={data.total} page={page} rowsPerPage={size} rowsPerPageOptions={[50, 100, 250, 500]}
        onPageChange={(_, p) => setPage(p)} onRowsPerPageChange={(e) => { setSize(Number(e.target.value)); setPage(0); }} />
      <Dialog open={!!view} onClose={() => setView(null)} fullWidth maxWidth="md">
        <DialogTitle>{view?.action} - {view?.username}</DialogTitle>
        <DialogContent dividers>
          <Box component="pre" sx={{ fontSize: 12, whiteSpace: "pre-wrap", m: 0 }}>{view && JSON.stringify({ old: view.old_value, new: view.new_value }, null, 2)}</Box>
        </DialogContent>
        <DialogActions><Button onClick={() => setView(null)}>Close</Button></DialogActions>
      </Dialog>
    </Box>
  );
}
