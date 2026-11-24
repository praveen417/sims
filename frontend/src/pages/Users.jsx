import React, { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import KeyIcon from "@mui/icons-material/Key";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import { api, errMsg } from "../api";
import { useAuth } from "../AuthContext";
import { ROLES } from "../fields";

const EMPTY = { username: "", full_name: "", email: "", password: "", role: "requester", status: "active" };

export default function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [dlg, setDlg] = useState(null);   // {mode: create|edit, form}
  const [pw, setPw] = useState(null);     // {user, value}

  const load = useCallback(() => api.get("/users").then((r) => setUsers(r.data)).catch((e) => setErr(errMsg(e))), []);
  useEffect(() => { load(); }, [load]);

  const act = async (fn, ok) => {
    setErr(""); setMsg("");
    try { await fn(); setMsg(ok); setDlg(null); setPw(null); load(); } catch (e) { setErr(errMsg(e)); }
  };
  const save = () => {
    const f = dlg.form;
    return dlg.mode === "create"
      ? act(() => api.post("/users", { username: f.username, full_name: f.full_name, email: f.email, password: f.password, role: f.role }), "User created")
      : act(() => api.put(`/users/${f.id}`, { full_name: f.full_name, email: f.email, role: f.role, status: f.status }), "User updated");
  };
  const set = (k) => (e) => setDlg({ ...dlg, form: { ...dlg.form, [k]: e.target.value } });

  return (
    <Box>
      <Stack direction="row" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flexGrow: 1 }}>User Management</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDlg({ mode: "create", form: EMPTY })}>Add user</Button>
      </Stack>
      {err && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErr("")}>{err}</Alert>}
      {msg && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMsg("")}>{msg}</Alert>}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead><TableRow><TableCell>Username</TableCell><TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>Role</TableCell><TableCell>Status</TableCell><TableCell>Last login</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead>
          <TableBody>
            {users.map((u) => (
              <TableRow key={u.id}>
                <TableCell>{u.username}</TableCell><TableCell>{u.full_name}</TableCell><TableCell>{u.email}</TableCell>
                <TableCell><Chip size="small" label={u.role} color={u.role === "admin" ? "primary" : "default"} /></TableCell>
                <TableCell><Chip size="small" label={u.status} color={u.status === "active" ? "success" : "warning"} variant="outlined" /></TableCell>
                <TableCell>{u.last_login ? new Date(u.last_login).toLocaleString() : "never"}</TableCell>
                <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                  <Tooltip title="Edit"><IconButton size="small" onClick={() => setDlg({ mode: "edit", form: { ...u } })}><EditIcon fontSize="small" /></IconButton></Tooltip>
                  <Tooltip title="Reset password"><IconButton size="small" onClick={() => setPw({ user: u, value: "" })}><KeyIcon fontSize="small" /></IconButton></Tooltip>
                  <Tooltip title="Unlock"><IconButton size="small" onClick={() => act(() => api.post(`/users/${u.id}/unlock`), "Unlocked")}><LockOpenIcon fontSize="small" /></IconButton></Tooltip>
                  <Tooltip title="Delete"><span><IconButton size="small" color="error" disabled={u.username === me.username}
                    onClick={() => window.confirm(`Delete user ${u.username}?`) && act(() => api.delete(`/users/${u.id}`), "User deleted")}><DeleteIcon fontSize="small" /></IconButton></span></Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={!!dlg} onClose={() => setDlg(null)} fullWidth maxWidth="xs">
        <DialogTitle>{dlg?.mode === "create" ? "Add user" : "Edit user"}</DialogTitle>
        {dlg && <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField size="small" label="Username" value={dlg.form.username} onChange={set("username")} disabled={dlg.mode === "edit"} sx={{ mt: 1 }} />
          <TextField size="small" label="Full name" value={dlg.form.full_name} onChange={set("full_name")} />
          <TextField size="small" label="Email" value={dlg.form.email} onChange={set("email")} />
          {dlg.mode === "create" && <TextField size="small" label="Password (min 8)" type="password" value={dlg.form.password} onChange={set("password")} />}
          <TextField size="small" select label="Role" value={dlg.form.role} onChange={set("role")}>
            {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
          </TextField>
          {dlg.mode === "edit" && <TextField size="small" select label="Status" value={dlg.form.status === "locked" ? "disabled" : dlg.form.status} onChange={set("status")}>
            <MenuItem value="active">active</MenuItem><MenuItem value="disabled">disabled</MenuItem></TextField>}
        </DialogContent>}
        <DialogActions><Button onClick={() => setDlg(null)}>Cancel</Button><Button variant="contained" onClick={save}>Save</Button></DialogActions>
      </Dialog>

      <Dialog open={!!pw} onClose={() => setPw(null)} fullWidth maxWidth="xs">
        <DialogTitle>Reset password: {pw?.user.username}</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <TextField fullWidth size="small" type="password" label="New password (min 8)" value={pw?.value || ""} sx={{ mt: 1 }} onChange={(e) => setPw({ ...pw, value: e.target.value })} />
        </DialogContent>
        <DialogActions><Button onClick={() => setPw(null)}>Cancel</Button>
          <Button variant="contained" onClick={() => act(() => api.post(`/users/${pw.user.id}/reset-password`, { new_password: pw.value }), "Password reset")}>Reset</Button></DialogActions>
      </Dialog>
    </Box>
  );
}
