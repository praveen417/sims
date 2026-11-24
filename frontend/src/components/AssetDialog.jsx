import React, { useEffect, useState } from "react";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid, MenuItem, TextField } from "@mui/material";
import { api, errMsg } from "../api";
import { FIELDS, coerce } from "../fields";

const toForm = (a) => Object.fromEntries(FIELDS.map((f) => [f.name, a?.[f.name] ?? ""]));

/** mode: "edit" (admin, saves directly) | "request" (requester, needs approval) | "view" */
export default function AssetDialog({ open, asset, mode, onClose, onSaved }) {
  const [form, setForm] = useState(toForm(asset));
  const [reason, setReason] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setForm(toForm(asset)); setReason(""); setErr(""); } }, [open, asset]);
  const editable = mode === "edit" || mode === "request" || !asset;

  const save = async () => {
    setBusy(true); setErr("");
    try {
      const payload = {};
      for (const f of FIELDS) {
        const v = coerce(f.name, form[f.name]);
        if (!asset) { if (v !== null) payload[f.name] = v; }
        else if (v !== coerce(f.name, asset[f.name])) payload[f.name] = v; // only what changed
      }
      if (!asset && !payload.hostname) throw new Error("Hostname is required");
      if (asset && !Object.keys(payload).length) { onClose(); return; }
      if (mode === "request") {
        if (reason.trim().length < 3) throw new Error(asset ? "Please give a reason for the change" : "Please say why this server should be added");
        const { data } = asset
          ? await api.post(`/assets/${asset.id}/change-request`, { changes: payload, reason })
          : await api.post("/changes/new-asset", { changes: payload, reason });
        onSaved(data, "request");
      } else {
        const { data } = asset ? await api.put(`/assets/${asset.id}`, payload) : await api.post("/assets", payload);
        onSaved(data, "edit");
      }
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(false); }
  };

  const title = !asset ? (mode === "request" ? "Request new server" : "Add asset") : mode === "edit" ? `Edit asset: ${asset.hostname}` : mode === "request" ? `Request change: ${asset.hostname}` : `Asset: ${asset.hostname}`;
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent dividers>
        {mode === "request" && <Alert severity="info" sx={{ mb: 2 }}>{asset ? "Your changes will not be applied immediately. They are sent to an approver (portal and email) and take effect once approved." : "The new server is not added yet. Your request goes to the CMDB manager for approval (portal and email) and the server is added once approved."}</Alert>}
        {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
        <Grid container spacing={2} sx={{ pt: 1 }}>
          {FIELDS.map((f) => (
            <Grid item xs={12} sm={6} md={4} key={f.name}>
              <TextField fullWidth size="small" label={f.label} value={form[f.name]} disabled={!editable}
                required={f.name === "hostname"}
                select={!!f.options} type={f.kind === "date" ? "date" : f.kind === "int" ? "number" : "text"}
                multiline={f.kind === "text"} maxRows={4}
                InputLabelProps={f.kind === "date" ? { shrink: true } : undefined}
                onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}>
                {f.options && [<MenuItem key="" value=""><em>(blank)</em></MenuItem>, ...f.options.map((o) => <MenuItem key={o} value={o}>{o}</MenuItem>)]}
              </TextField>
            </Grid>
          ))}
          {mode === "request" && (
            <Grid item xs={12}>
              <TextField fullWidth required multiline minRows={2} label={asset ? "Reason for the change" : "Why should this server be added?"} value={reason} onChange={(e) => setReason(e.target.value)} />
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{editable ? "Cancel" : "Close"}</Button>
        {editable && <Button variant="contained" onClick={save} disabled={busy}>{mode === "request" ? (asset ? "Submit for approval" : "Submit new server for approval") : "Save"}</Button>}
      </DialogActions>
    </Dialog>
  );
}
