import React, { useEffect, useState } from "react";
import { Alert, Autocomplete, Box, Button, Card, CardContent, Collapse, Grid, MenuItem, Paper, Stack, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tabs, TextField, Typography } from "@mui/material";
import { api, errMsg } from "../api";

const Stat = ({ label, value, color }) => (
  <Card sx={{ borderTop: `4px solid ${color || "#FFCC00"}` }}><CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="h5" sx={{ fontWeight: 800 }}>{value}</Typography>
  </CardContent></Card>
);
const Stats = ({ items }) => <Grid container spacing={2} sx={{ mb: 2 }}>{items.map(([l, v, c]) => <Grid item xs={6} md={3} key={l}><Stat label={l} value={v} color={c} /></Grid>)}</Grid>;

function Tbl({ cols, rows, title }) {
  return (
    <Box sx={{ mb: 3 }}>
      {title && <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>{title}</Typography>}
      <TableContainer component={Paper} sx={{ maxHeight: 420 }}>
        <Table size="small" stickyHeader>
          <TableHead><TableRow>{cols.map(([, l]) => <TableCell key={l}>{l}</TableCell>)}</TableRow></TableHead>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={cols.length}>No records</TableCell></TableRow>}
            {rows.map((r, i) => <TableRow key={i}>{cols.map(([k]) => <TableCell key={k}>{r[k] ?? ""}</TableCell>)}</TableRow>)}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
const CATS = [["opco", "OPCO"], ["domain", "Domain"], ["environment", "Environment"], ["physical_virtual", "Physical / Virtual"],
  ["hardware_vendor", "Hardware Vendor"], ["operating_system", "Operating System"], ["location", "Location"], ["asset_type", "Asset Type"],
  ["ito_non_ito", "ITO / Non-ITO"], ["bia_class", "Class (BIA)"], ["application_owner", "Application Owner"],
  ["virtualization_platform", "Virtualization Platform"], ["support_type", "Support Type"], ["status", "Status"]];
const ASSET_COLS = [["hostname", "Hostname"], ["opco", "OPCO"], ["ip_address", "IP"], ["environment", "Env"], ["application", "Application"]];
const COUNT_COLS = [["label", "Name"], ["count", "Assets"]];

function Summary({ d }) {
  return <>
    <Stats items={[["Assets in this view", d.total]]} />
    {d.custom && <Tbl title={`By ${CATS.find(([k]) => k === d.custom.group_by)?.[1]}`} cols={COUNT_COLS} rows={d.custom.rows} />}
    <Grid container spacing={2}>
      {[["By OPCO", d.by_opco], ["By Domain", d.by_domain], ["By Environment", d.by_environment]].map(([t, r]) => <Grid item xs={12} md={4} key={t}><Tbl title={t} cols={COUNT_COLS} rows={r} /></Grid>)}
    </Grid>
  </>;
}
function Eol({ d }) {
  const c = d.counts;
  return <>
    <Stats items={[["Already expired", c.expired, "#d32f2f"], ["Within 30 days", c.d30, "#ed6c02"], ["Within 90 days", c.d90, "#FFCC00"], ["Within 180 days", c.d180, "#8d8d8d"]]} />
    <Typography variant="caption">Day windows are cumulative (the 90-day figure includes the 30-day ones). Lists show up to 500 rows.</Typography>
    <Tbl title="Already expired" cols={[...ASSET_COLS, ["end_of_life", "End of Life"]]} rows={d.items.expired} />
    <Tbl title="Expiring within 180 days" cols={[...ASSET_COLS, ["end_of_life", "End of Life"]]} rows={d.items.d180} />
  </>;
}
function Eos({ d }) {
  const names = { vendor: "Vendor EOS", oracle: "Oracle EOS", hardware: "Hardware EOS" };
  return <>
    <Stats items={Object.entries(d.counts).map(([k, v]) => [`${names[k]} (expired / next 180 days)`, `${v.expired} / ${v.upcoming}`])} />
    <Typography variant="caption">Oracle = rows with a database version or Oracle support value; Hardware = support type contains "Hardware"; Vendor = everything else.</Typography>
    {Object.keys(names).map((k) => <Tbl key={k} title={names[k]} cols={[...ASSET_COLS, ["end_of_support", "End of Support"]]} rows={d.items[k]} />)}
  </>;
}
function Backup({ d }) {
  return <>
    <Stats items={[["Protected", d.protected, "#2e7d32"], ["Unprotected", d.unprotected, "#d32f2f"], ["Compliance", `${d.compliance_pct}%`]]} />
    <Tbl title="By OPCO" cols={[["label", "OPCO"], ["protected", "Protected"], ["unprotected", "Unprotected"], ["pct", "Compliance %"]]} rows={d.by_opco} />
    <Tbl title="Unprotected assets" cols={[...ASSET_COLS, ["backup_status", "Backup Status"]]} rows={d.unprotected_items} />
  </>;
}
function Virt({ d }) {
  return <>
    <Stats items={[["VMware assets", d.vmware], ["Hyper-V assets", d.hyperv], ["Physical servers", d.physical, "#2F2F2F"], ["Other / unspecified virtual", d.other_virtual, "#8d8d8d"]]} />
    <Tbl title="Virtual assets by platform" cols={COUNT_COLS} rows={d.platforms} />
  </>;
}
function Oracle({ d }) {
  return <>
    <Stats items={[["Oracle supported", d.supported, "#2e7d32"], ["Oracle unsupported", d.unsupported, "#d32f2f"]]} />
    <Tbl title="Database version distribution" cols={COUNT_COLS} rows={d.versions} />
    <Tbl title="Unsupported Oracle assets" cols={[...ASSET_COLS, ["db_version", "DB Version"], ["oracle_support", "Oracle Support"]]} rows={d.unsupported_items} />
  </>;
}

const TABS = [["Asset Summary", "summary", Summary], ["End-of-Life", "eol", Eol], ["End-of-Support", "eos", Eos],
  ["Backup Compliance", "backup", Backup], ["Virtualization", "virtualization", Virt], ["Oracle Support", "oracle", Oracle]];

export default function Reports() {
  const [tab, setTab] = useState(0);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [sel, setSel] = useState({});          // { field: [values] }  user-chosen categories
  const [groupBy, setGroupBy] = useState("");
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState({});
  useEffect(() => { api.get("/assets/meta/options").then((r) => setOptions(r.data)).catch(() => {}); }, []);

  const active = Object.values(sel).filter((v) => v.length).length;
  const key = JSON.stringify([tab, sel, groupBy]);
  useEffect(() => {
    setData(null); setErr("");
    const params = {};
    Object.entries(sel).forEach(([k, v]) => { if (v.length) params[k] = v; });
    if (tab === 0 && groupBy) params.group_by = groupBy;
    api.get(`/reports/${TABS[tab][1]}`, { params }).then((r) => setData(r.data)).catch((e) => setErr(errMsg(e)));
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  const View = TABS[tab][2];

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flexGrow: 1 }}>Reports</Typography>
        <Button onClick={() => setOpen(!open)}>{open ? "Hide" : "Filter by category"}{active ? ` (${active})` : ""}</Button>
        {active > 0 && <Button onClick={() => setSel({})}>Clear filters</Button>}
      </Stack>
      <Collapse in={open}>
        <Box sx={{ p: 2, mb: 2, border: 1, borderColor: "divider", borderRadius: 2 }}>
          <Typography variant="caption" color="text.secondary">Pick any categories and values; every report below is limited to the matching servers.</Typography>
          <Grid container spacing={1.5} sx={{ mt: 0 }}>
            {CATS.map(([k, label]) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={k}>
                <Autocomplete multiple size="small" limitTags={2} options={options[k] || []} value={sel[k] || []}
                  onChange={(_, v) => setSel({ ...sel, [k]: v })} renderInput={(p) => <TextField {...p} label={label} />} />
              </Grid>
            ))}
          </Grid>
        </Box>
      </Collapse>
      {tab === 0 && (
        <TextField select size="small" label="Also group by" value={groupBy} onChange={(e) => setGroupBy(e.target.value)} sx={{ mb: 2, minWidth: 240 }}>
          <MenuItem value=""><em>(none)</em></MenuItem>
          {CATS.map(([k, l]) => <MenuItem key={k} value={k}>{l}</MenuItem>)}
        </TextField>
      )}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" scrollButtons="auto" sx={{ mb: 2 }} textColor="inherit" TabIndicatorProps={{ style: { backgroundColor: "#FFCC00" } }}>
        {TABS.map(([l]) => <Tab key={l} label={l} />)}
      </Tabs>
      {err && <Alert severity="error">{err}</Alert>}
      {data && <View d={data} />}
    </Box>
  );
}
