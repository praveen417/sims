import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Box, Card, CardActionArea, CardContent, Grid, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";
import { api, errMsg } from "../api";

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

// [summary key, label, inventory preset ("" = no filter)]
const WIDGETS = [
  ["total", "Total Servers", ""], ["physical", "Physical Servers", "physical"], ["virtual", "Virtual Servers", "virtual"],
  ["production", "Production Servers", "prod"], ["dr", "DR Servers", "dr"], ["uat", "UAT Servers", "uat"],
  ["linux", "Linux Servers", "linux"], ["windows", "Windows Servers", "windows"], ["oracle_databases", "Oracle Databases", "oracle_db"],
  ["backup_protected", "Backup Protected Assets", "protected"], ["non_protected", "Non-Protected Assets", "non_protected"],
  ["end_of_support", "End of Support Assets", "eos_expired"], ["end_of_life", "End of Life Assets", "eol_expired"],
];
const PALETTE = ["#FFCC00", "#2F2F2F", "#8d8d8d", "#ffe066", "#b38f00", "#5c5c5c", "#d9d9d9", "#ffd633", "#7a6200", "#a6a6a6", "#c9a400"];

function ChartCard({ title, data, type = "bar", onPick }) {
  const t = useTheme();
  const txt = t.palette.text.primary;
  const ds = { labels: data?.labels || [], datasets: [{ data: data?.data || [], backgroundColor: type === "bar" ? "#FFCC00" : PALETTE, borderColor: t.palette.mode === "dark" ? "#555" : "#fff" }] };
  const click = (_, els) => { if (els.length && onPick) onPick(ds.labels[els[0].index]); };
  const hover = (e, els) => { if (e.native?.target) e.native.target.style.cursor = els.length ? "pointer" : "default"; };
  const common = { responsive: true, maintainAspectRatio: false, onClick: click, onHover: hover };
  const opts = type === "bar"
    ? { ...common, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: txt } }, y: { ticks: { color: txt }, beginAtZero: true } } }
    : { ...common, plugins: { legend: { position: "right", labels: { color: txt } } } };
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{title}</Typography>
        <Typography variant="caption" color="text.secondary">Click to see the servers</Typography>
        <Box sx={{ height: 260, mt: 1 }}>{type === "bar" ? <Bar data={ds} options={opts} /> : <Doughnut data={ds} options={opts} />}</Box>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const nav = useNavigate();
  const [sum, setSum] = useState(null);
  const [ch, setCh] = useState(null);
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      const [a, b] = await Promise.all([api.get("/dashboard/summary"), api.get("/dashboard/charts")]);
      setSum(a.data); setCh(b.data); setErr("");
    } catch (e) { setErr(errMsg(e)); }
  };
  useEffect(() => { load(); const id = setInterval(load, 60000); return () => clearInterval(id); }, []);

  const go = (params) => nav(`/inventory?${new URLSearchParams(params)}`);
  const byField = (field) => (label) => {
    if (label === "Other") return;                       // grouped bucket, no single filter
    go({ [field]: label === "Unknown" ? "=__blank__" : `=${label}` });
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Dashboard</Typography>
      {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
      <Grid container spacing={2} sx={{ mb: 1 }}>
        {WIDGETS.map(([k, label, preset]) => (
          <Grid item xs={6} sm={4} md={3} lg={2.4} key={k}>
            <Card sx={{ borderTop: "4px solid #FFCC00" }}>
              <CardActionArea onClick={() => go(preset ? { preset } : {})}>
                <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                  <Typography variant="caption" color="text.secondary">{label}</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 800 }}>{sum ? sum[k].toLocaleString() : "-"}</Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
      {ch && (
        <Grid container spacing={2} sx={{ mt: 0 }}>
          <Grid item xs={12} md={6}><ChartCard title="Asset Count by OPCO" data={ch.opco} onPick={byField("opco")} /></Grid>
          <Grid item xs={12} md={6}><ChartCard title="Asset Count by Domain" data={ch.domain} onPick={byField("domain")} /></Grid>
          <Grid item xs={12} md={6} lg={4}><ChartCard title="Asset Count by Environment" data={ch.environment} type="doughnut" onPick={byField("environment")} /></Grid>
          <Grid item xs={12} md={6} lg={4}><ChartCard title="OS Distribution" data={ch.os} type="doughnut" onPick={byField("operating_system")} /></Grid>
          <Grid item xs={12} md={6} lg={4}><ChartCard title="Backup Compliance" data={ch.backup} type="doughnut" onPick={(l) => go({ preset: l === "Protected" ? "protected" : "non_protected" })} /></Grid>
          <Grid item xs={12} md={6} lg={4}><ChartCard title="Physical vs Virtual" data={ch.physical_virtual} type="doughnut" onPick={byField("physical_virtual")} /></Grid>
          <Grid item xs={12} md={6} lg={4}><ChartCard title="Oracle Version Distribution" data={ch.oracle_versions} onPick={byField("db_version")} /></Grid>
          <Grid item xs={12} md={6} lg={4}><ChartCard title="Hardware Vendor Distribution" data={ch.vendors} onPick={byField("hardware_vendor")} /></Grid>
        </Grid>
      )}
    </Box>
  );
}
