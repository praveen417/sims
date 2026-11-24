import React, { useState } from "react";
import { Alert, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Link, TextField, Typography } from "@mui/material";
import { api, errMsg } from "../api";
import { useAuth } from "../AuthContext";

export default function Login() {
  const { login } = useAuth();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [fp, setFp] = useState({ open: false, user: "", msg: "" });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try { await login(u, p); } catch (x) { setErr(errMsg(x)); } finally { setBusy(false); }
  };
  const forgot = async () => {
    try { const { data } = await api.post("/auth/forgot-password", { username: fp.user }); setFp({ ...fp, msg: data.detail }); }
    catch (x) { setFp({ ...fp, msg: errMsg(x) }); }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#2F2F2F", p: 2 }}>
      <Card sx={{ width: 380, maxWidth: "100%" }}>
        <Box sx={{ bgcolor: "#FFCC00", p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 800, color: "#2F2F2F" }}>SIMS</Typography>
          <Typography variant="body2" sx={{ color: "#2F2F2F" }}>Server Inventory Management System</Typography>
        </Box>
        <CardContent component="form" onSubmit={submit} sx={{ display: "grid", gap: 2 }}>
          {err && <Alert severity="error">{err}</Alert>}
          <TextField label="Username" value={u} onChange={(e) => setU(e.target.value)} autoFocus required />
          <TextField label="Password" type="password" value={p} onChange={(e) => setP(e.target.value)} required />
          <Button type="submit" variant="contained" size="large" disabled={busy}>Login</Button>
          <Link component="button" type="button" variant="body2" onClick={() => setFp({ open: true, user: u, msg: "" })}>Forgot Password</Link>
        </CardContent>
      </Card>
      <Dialog open={fp.open} onClose={() => setFp({ ...fp, open: false })} fullWidth maxWidth="xs">
        <DialogTitle>Forgot password</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField label="Username" value={fp.user} onChange={(e) => setFp({ ...fp, user: e.target.value })} sx={{ mt: 1 }} />
          {fp.msg && <Alert severity="info">{fp.msg}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFp({ ...fp, open: false })}>Close</Button>
          <Button variant="contained" onClick={forgot} disabled={!fp.user}>Request reset</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
