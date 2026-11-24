import React, { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { AppBar, Badge, Box, Chip, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Tooltip, Typography, useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/Menu";
import DashboardIcon from "@mui/icons-material/Dashboard";
import StorageIcon from "@mui/icons-material/Storage";
import UploadIcon from "@mui/icons-material/UploadFile";
import DownloadIcon from "@mui/icons-material/Download";
import AssessmentIcon from "@mui/icons-material/Assessment";
import HistoryIcon from "@mui/icons-material/History";
import PeopleIcon from "@mui/icons-material/People";
import SettingsIcon from "@mui/icons-material/Settings";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import { api } from "../api";
import LogoutIcon from "@mui/icons-material/Logout";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import { useAuth } from "../AuthContext";
import { useMode } from "../ModeContext";

const W = 240;
const NAV = [
  { to: "/", label: "Dashboard", icon: <DashboardIcon /> },
  { to: "/inventory", label: "Server Inventory", icon: <StorageIcon /> },
  { to: "/changes", label: "Change Requests", icon: <FactCheckIcon />, perm: "change:view", badge: true },
  { to: "/import", label: "Import Assets", icon: <UploadIcon />, perm: "asset:import" },
  { to: "/export", label: "Export Data", icon: <DownloadIcon />, perm: "asset:export" },
  { to: "/reports", label: "Reports", icon: <AssessmentIcon />, perm: "report:view" },
  { to: "/audit", label: "Audit Logs", icon: <HistoryIcon />, perm: "audit:view" },
  { to: "/users", label: "User Management", icon: <PeopleIcon />, perm: "user:manage" },
  { to: "/settings", label: "Settings", icon: <SettingsIcon /> },
];

export default function Layout() {
  const { user, can, logout } = useAuth();
  const { mode, toggle } = useMode();
  const nav = useNavigate();
  const loc = useLocation();
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up("md"));
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(0);
  useEffect(() => {
    if (!can("change:approve")) return undefined;
    const f = () => api.get("/changes", { params: { status: "pending", page_size: 1 } }).then((r) => setPending(r.data.total)).catch(() => {});
    f(); const id = setInterval(f, 60000); return () => clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const drawer = (
    <Box sx={{ bgcolor: "#2F2F2F", color: "#fff", height: "100%" }}>
      <Toolbar>
        <Typography variant="h6" sx={{ color: "#FFCC00", fontWeight: 800 }}>SIMS</Typography>
      </Toolbar>
      <List>
        {NAV.filter((n) => !n.perm || can(n.perm)).map((n) => (
          <ListItemButton key={n.to} selected={loc.pathname === n.to}
            onClick={() => { nav(n.to); setOpen(false); }}
            sx={{ "&.Mui-selected": { bgcolor: "#FFCC00", color: "#2F2F2F", "& .MuiListItemIcon-root": { color: "#2F2F2F" } }, "&.Mui-selected:hover": { bgcolor: "#ffd633" } }}>
            <ListItemIcon sx={{ color: "#FFCC00", minWidth: 40 }}>{n.badge && pending > 0 ? <Badge badgeContent={pending} color="error">{n.icon}</Badge> : n.icon}</ListItemIcon>
            <ListItemText primary={n.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          {!desktop && <IconButton edge="start" onClick={() => setOpen(true)} sx={{ mr: 1 }}><MenuIcon /></IconButton>}
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }} noWrap>Server Inventory Management System</Typography>
          {desktop && <Chip size="small" label={`${user.full_name} (${user.role})`} sx={{ mr: 1, bgcolor: "#2F2F2F", color: "#fff" }} />}
          <Tooltip title="Toggle dark mode"><IconButton onClick={toggle}>{mode === "dark" ? <LightModeIcon /> : <DarkModeIcon />}</IconButton></Tooltip>
          <Tooltip title="Log out"><IconButton onClick={logout}><LogoutIcon /></IconButton></Tooltip>
        </Toolbar>
      </AppBar>
      <Drawer variant={desktop ? "permanent" : "temporary"} open={desktop || open} onClose={() => setOpen(false)}
        sx={{ width: W, flexShrink: 0, "& .MuiDrawer-paper": { width: W, boxSizing: "border-box", border: 0 } }}>
        {drawer}
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { xs: 1.5, md: 3 } }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
