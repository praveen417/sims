import React, { useState } from "react";
import { Alert, Box, Button, Card, CardContent, Checkbox, Chip, FormControl, FormControlLabel, Grid, InputLabel, MenuItem, Paper, Select, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { api, download, errMsg } from "../api";

const Stat = ({ label, value, color }) => (
  <Card sx={{ borderTop: `4px solid ${color || "#FFCC00"}` }}><CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="h5" sx={{ fontWeight: 800 }}>{value}</Typography>
  </CardContent></Card>
);

export default function ImportAssets() {
  const [file, setFile] = useState(null);
  const [dup, setDup] = useState("update");
  const [skip, setSkip] = useState(true);
  const [report, setReport] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (mode) => {
    if (!file) return;
    setBusy(true); setErr("");
    const fd = new FormData();
    fd.append("file", file); fd.append("mode", mode); fd.append("on_duplicate", dup); fd.append("skip_invalid", String(skip));
    try { const { data } = await api.post("/import/excel", fd, { timeout: 600000 }); setReport(data); }
    catch (e) { setErr(errMsg(e)); } finally { setBusy(false); }
  };
  const errorsCsv = () => {
    const esc = (s) => `"${String(s ?? "").replace(/"/g, '""')}"`;
    const lines = ["Row,Hostname,Column,Message", ...report.errors.map((e) => [e.row, esc(e.hostname), esc(e.column), esc(e.message)].join(","))];
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
    a.download = "import_errors.csv"; a.click();
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Import Assets</Typography>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack spacing={2}>
          <Alert severity="info">
            Accepts .xlsx, .xls and .csv. Only <b>Hostname</b> is required: blank cells and blank or missing columns are fine,
            and blank cells never overwrite existing data. A "Classification" column is ignored.
          </Alert>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
            <Button variant="outlined" component="label">
              {file ? file.name : "Choose file"}
              <input hidden type="file" accept=".xlsx,.xls,.csv" onChange={(e) => { setFile(e.target.files[0] || null); setReport(null); }} />
            </Button>
            <FormControl size="small" sx={{ minWidth: 260 }}>
              <InputLabel>If hostname already exists</InputLabel>
              <Select label="If hostname already exists" value={dup} onChange={(e) => setDup(e.target.value)}>
                <MenuItem value="update">Update the existing record</MenuItem>
                <MenuItem value="skip">Skip (leave as is)</MenuItem>
                <MenuItem value="reject">Reject as an error</MenuItem>
              </Select>
            </FormControl>
            <FormControlLabel control={<Checkbox checked={skip} onChange={(e) => setSkip(e.target.checked)} />} label="Import valid rows even if some rows have errors" />
          </Stack>
          <Stack direction="row" spacing={1}>
            <Button variant="contained" disabled={!file || busy} onClick={() => run("preview")}>1. Validate (preview)</Button>
            <Button variant="contained" color="secondary" disabled={!file || busy || !report || report.committed} onClick={() => run("commit")}>2. Commit import</Button>
            <Button onClick={() => download("/import/template")}>Download template</Button>
          </Stack>
        </Stack>
      </Paper>
      {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}

      {report && (
        <>
          {report.committed
            ? <Alert severity="success" sx={{ mb: 2 }}>Import completed: {report.created} created, {report.updated} updated, {report.unchanged} unchanged.</Alert>
            : <Alert severity={report.mode === "commit" ? "warning" : "info"} sx={{ mb: 2 }}>{report.message || "Preview only - nothing has been changed yet. Review below, then press Commit."}</Alert>}
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6} md={2}><Stat label="Rows read" value={report.total_rows} /></Grid>
            <Grid item xs={6} md={2}><Stat label="To create" value={report.to_create} color="#2e7d32" /></Grid>
            <Grid item xs={6} md={2}><Stat label="To update" value={report.to_update} color="#0288d1" /></Grid>
            <Grid item xs={6} md={2}><Stat label="Skipped" value={report.skipped} color="#8d8d8d" /></Grid>
            <Grid item xs={6} md={2}><Stat label="Rejected rows" value={report.rejected} color="#d32f2f" /></Grid>
          </Grid>
          {report.new_opcos.length > 0 && <Alert severity="warning" sx={{ mb: 1 }}>New OPCOs that will be created: {report.new_opcos.join(", ")}. Check the spelling.</Alert>}
          {report.ignored_columns.length > 0 && <Box sx={{ mb: 2 }}><Typography variant="body2" sx={{ mb: 0.5 }}>Ignored columns:</Typography>{report.ignored_columns.map((c) => <Chip key={c} label={c} size="small" sx={{ mr: 0.5 }} />)}</Box>}
          {report.error_count > 0 && (
            <>
              <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{report.error_count} error(s){report.errors.length < report.error_count ? ` (showing first ${report.errors.length})` : ""}</Typography>
                <Button size="small" onClick={errorsCsv}>Download errors (CSV)</Button>
              </Stack>
              <TableContainer component={Paper} sx={{ maxHeight: 420 }}>
                <Table size="small" stickyHeader>
                  <TableHead><TableRow><TableCell>Row</TableCell><TableCell>Hostname</TableCell><TableCell>Column</TableCell><TableCell>Problem</TableCell></TableRow></TableHead>
                  <TableBody>{report.errors.map((e, i) => <TableRow key={i}><TableCell>{e.row}</TableCell><TableCell>{e.hostname}</TableCell><TableCell>{e.column}</TableCell><TableCell>{e.message}</TableCell></TableRow>)}</TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </>
      )}
    </Box>
  );
}
