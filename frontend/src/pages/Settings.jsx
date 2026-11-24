import React, { useState } from "react";
import { Alert, Box, Button, Chip, FormControlLabel, Paper, Stack, Switch, TextField, Typography } from "@mui/material";
import { api, errMsg } from "../api";
import { useAuth } from "../AuthContext";
import { useMode } from "../ModeContext";

export default function Settings() {
  const { user } = useAuth();
  const { mode, toggle } = useMode();
  const [f, setF] = useState({ current_password: "", new_password: "", confirm: "" });
  const [msg, setMsg] = useState(null);

  const change = async () => {
    if (f.new_password !== f.confirm) return setMsg({ sev: "error", t: "New passwords do not match" });
    try {
      await api.post("/auth/change-password", { current_password: f.current_password, new_password: f.new_password });
      setMsg({ sev: "success", t: "Password changed" }); setF({ current_password: "", new_password: "", confirm: "" });
    } catch (e) { setMsg({ sev: "error", t: errMsg(e) }); }
  };

  return (
    <Box sx={{ maxWidth: 640 }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Settings</Typography>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{user.full_name} ({user.username})</Typography>
        <Typography variant="body2" sx={{ mb: 1 }}>Role: {user.role}</Typography>
        <Stack direction="row" sx={{ flexWrap: "wrap", gap: 0.5 }}>{user.permissions.map((p) => <Chip key={p} size="small" label={p} />)}</Stack>
        <FormControlLabel sx={{ mt: 1 }} control={<Switch checked={mode === "dark"} onChange={toggle} />} label="Dark mode" />
      </Paper>
      <Paper sx={{ p: 2, display: "grid", gap: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Change password</Typography>
        {msg && <Alert severity={msg.sev}>{msg.t}</Alert>}
        <TextField size="small" type="password" label="Current password" value={f.current_password} onChange={(e) => setF({ ...f, current_password: e.target.value })} />
        <TextField size="small" type="password" label="New password (min 8)" value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} />
        <TextField size="small" type="password" label="Confirm new password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} />
        <Button variant="contained" onClick={change} sx={{ justifySelf: "start" }}>Change password</Button>
      </Paper>
    </Box>
  );
}
