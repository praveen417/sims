import React, { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, Tabs, TextField, Typography } from "@mui/material";
import { api, errMsg } from "../api";
import { useAuth } from "../AuthContext";
import { FIELDS } from "../fields";

const LABEL = Object.fromEntries(FIELDS.map((f) => [f.name, f.label]));
const COLOR = { pending: "warning", approved: "success", rejected: "error", cancelled: "default" };
const TABS = [["Pending", "pending"], ["Approved", "approved"], ["Rejected", "rejected"], ["All", ""]];
const show = (v) => (v === null || v === undefined || v === "" ? "(blank)" : String(v));

export default function ChangeRequests() {
  const { can } = useAuth();
  const approver = can("change:approve");
  const [tab, setTab] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(50);
  const [msg, setMsg] = useState(null);
  const [dlg, setDlg] = useState(null); // {cr, decision}
  const [comment, setComment] = useState("");

  const load = useCallback(async () => {
    try {
      const params = { page: page + 1, page_size: size };
      if (TABS[tab][1]) params.status = TABS[tab][1];
      const r = await api.get("/changes", { params }); setData(r.data);
    } catch (e) { setMsg({ sev: "error", t: errMsg(e) }); }
  }, [tab, page, size]);
  useEffect(() => { load(); const id = setInterval(load, 30000); return () => clearInterval(id); }, [load]);

  const decide = async () => {
    try {
      await api.post(`/changes/${dlg.cr.id}/${dlg.decision}`, { comment: comment || null });
      setMsg({ sev: "success", t: `Request #${dlg.cr.id} ${dlg.decision}d` }); setDlg(null); setComment(""); load();
    } catch (e) { setMsg({ sev: "error", t: errMsg(e) }); setDlg(null); load(); }
  };
  const cancel = async (cr) => {
    try { await api.post(`/changes/${cr.id}/cancel`); setMsg({ sev: "success", t: "Request cancelled" }); load(); }
    catch (e) { setMsg({ sev: "error", t: errMsg(e) }); }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>Change Requests</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {approver ? "Review changes requested by requesters. Approvers also receive an email with Approve / Reject links." : "Changes you asked for. They are applied once an approver accepts them."}
      </Typography>
      <Tabs value={tab} onChange={(_, v) => { setTab(v); setPage(0); }} sx={{ mb: 2 }} textColor="inherit" TabIndicatorProps={{ style: { backgroundColor: "#FFCC00" } }}>
        {TABS.map(([l]) => <Tab key={l} label={l} />)}
      </Tabs>
      {msg && <Alert severity={msg.sev} sx={{ mb: 2 }} onClose={() => setMsg(null)}>{msg.t}</Alert>}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead><TableRow>
            <TableCell>#</TableCell><TableCell>Requested</TableCell><TableCell>Server</TableCell><TableCell>By</TableCell>
            <TableCell>Request</TableCell><TableCell>Reason</TableCell><TableCell>Status</TableCell><TableCell align="right">Action</TableCell>
          </TableRow></TableHead>
          <TableBody>
            {data.items.length === 0 && <TableRow><TableCell colSpan={8}>No requests</TableCell></TableRow>}
            {data.items.map((cr) => (
              <TableRow key={cr.id} hover sx={{ verticalAlign: "top" }}>
                <TableCell>{cr.id}</TableCell>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{new Date(cr.created_date).toLocaleString()}</TableCell>
                <TableCell>{cr.hostname}{cr.request_type === "create" ? " (new)" : ""}</TableCell>
                <TableCell>{cr.requested_by}</TableCell>
                <TableCell>
                  {cr.request_type === "create" && <Chip size="small" color="primary" label="New server" sx={{ mb: 0.5 }} />}
                  {Object.entries(cr.changes).map(([k, v]) => (
                    cr.request_type === "create"
                      ? <div key={k}><b>{LABEL[k] || k}:</b> {show(v)}</div>
                      : <div key={k}><b>{LABEL[k] || k}:</b> {show(cr.old_values[k])} &rarr; <b>{show(v)}</b></div>
                  ))}
                  {cr.stale && <Chip size="small" color="warning" label="Server changed since request" sx={{ mt: 0.5 }} />}
                </TableCell>
                <TableCell sx={{ maxWidth: 240 }}>{cr.reason}</TableCell>
                <TableCell>
                  <Chip size="small" color={COLOR[cr.status]} label={cr.status} />
                  {cr.reviewed_by && <div style={{ fontSize: 12 }}>{cr.reviewed_by} ({cr.review_source}){cr.review_comment ? `: ${cr.review_comment}` : ""}</div>}
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                  {cr.status === "pending" && approver && <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                    <Button size="small" variant="contained" color="success" onClick={() => { setComment(""); setDlg({ cr, decision: "approve" }); }}>Approve</Button>
                    <Button size="small" variant="outlined" color="error" onClick={() => { setComment(""); setDlg({ cr, decision: "reject" }); }}>Reject</Button>
                  </Stack>}
                  {cr.status === "pending" && !approver && <Button size="small" onClick={() => cancel(cr)}>Cancel request</Button>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination component="div" count={data.total} page={page} rowsPerPage={size} rowsPerPageOptions={[25, 50, 100]}
        onPageChange={(_, p) => setPage(p)} onRowsPerPageChange={(e) => { setSize(Number(e.target.value)); setPage(0); }} />

      <Dialog open={!!dlg} onClose={() => setDlg(null)} fullWidth maxWidth="xs">
        <DialogTitle>{dlg?.decision === "approve" ? "Approve" : "Reject"} request #{dlg?.cr.id} ({dlg?.cr.hostname})</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          {dlg?.decision === "approve" && <Alert severity="info" sx={{ mb: 2 }}>{dlg.cr.request_type === "create" ? "The new server will be added to the inventory immediately." : "The changes will be applied to the server record immediately."}</Alert>}
          <TextField fullWidth multiline minRows={2} label="Comment (optional)" value={comment} onChange={(e) => setComment(e.target.value)} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDlg(null)}>Cancel</Button>
          <Button variant="contained" color={dlg?.decision === "approve" ? "success" : "error"} onClick={decide}>{dlg?.decision === "approve" ? "Approve" : "Reject"}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
