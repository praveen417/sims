import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { Alert, Autocomplete, Box, Button, Chip, Collapse, Dialog, DialogActions, DialogContent, DialogTitle, FormControl, Grid, IconButton, InputLabel, Menu, MenuItem, Select, Snackbar, Stack, TablePagination, TextField, Tooltip, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditNoteIcon from "@mui/icons-material/EditNote";
import FilterListIcon from "@mui/icons-material/FilterList";
import DownloadIcon from "@mui/icons-material/Download";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import NetworkCheckIcon from "@mui/icons-material/NetworkCheck";
import { api, download, errMsg } from "../api";
import { useAuth } from "../AuthContext";
import { FIELDS, KIND, UNIQUE, coerce } from "../fields";
import AssetDialog from "../components/AssetDialog";

const FILTERS = ["opco", "domain", "hostname", "ip_address", "serial_number", "application", "application_owner",
  "operating_system", "environment", "physical_virtual", "backup_status", "product_name", "location", "db_version"];
const PRESET_LABEL = {
  physical: "Physical servers", virtual: "Virtual servers", prod: "Production servers", dr: "DR servers", uat: "UAT servers",
  linux: "Linux servers", windows: "Windows servers", oracle_db: "Oracle databases", protected: "Backup protected assets",
  non_protected: "Non-protected assets", eos_expired: "End of support assets", eol_expired: "End of life assets",
};
const FIELD_NAMES = FIELDS.map((f) => f.name);

// URL -> filter state (the dashboard links here with ?preset=linux or ?opco==Zambia)
function parseUrl(sp) {
  const filters = {};
  FIELD_NAMES.forEach((n) => { const v = sp.get(n); if (v) filters[n] = v; });
  return { q: sp.get("q") || "", filters, preset: sp.get("preset") || "" };
}

export default function Inventory() {
  const { can } = useAuth();
  const theme = useTheme();
  const [sp, setSp] = useSearchParams();
  const canEdit = can("asset:write");
  const mode = canEdit ? "edit" : can("change:request") ? "request" : "view";
  const init = useMemo(() => parseUrl(sp), []); // eslint-disable-line react-hooks/exhaustive-deps

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(100);
  const [sort, setSort] = useState({ sort_by: "id", sort_dir: "asc" });
  const [q, setQ] = useState(init.q);
  const [filters, setFilters] = useState(init.filters);
  const [applied, setApplied] = useState(init);
  const [options, setOptions] = useState({});
  const [showFilters, setShowFilters] = useState(Object.keys(init.filters).length > 0);
  const [selected, setSelected] = useState([]);
  const [dialog, setDialog] = useState({ open: false, asset: null });
  const [bulk, setBulk] = useState({ open: false, field: "environment", value: "" });
  const [menu, setMenu] = useState(null);
  const [snack, setSnack] = useState(null);
  const [loading, setLoading] = useState(false);
  const reqId = useRef(0);
  const first = useRef(true);

  // follow the URL when the user arrives from the dashboard (or presses back)
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    const n = parseUrl(sp);
    setQ(n.q); setFilters(n.filters); setApplied(n); setPage(0); setShowFilters(Object.keys(n.filters).length > 0);
  }, [sp.toString()]); // eslint-disable-line react-hooks/exhaustive-deps

  const queryParams = useCallback(() => {
    const p = {};
    if (applied.q) p.q = applied.q;
    if (applied.preset) p.preset = applied.preset;
    Object.entries(applied.filters).forEach(([k, v]) => { if (v) p[k] = v; });
    return p;
  }, [applied]);

  const load = useCallback(async () => {
    const id = ++reqId.current;
    setLoading(true);
    try {
      const { data } = await api.get("/assets", { params: { page: page + 1, page_size: pageSize, ...sort, ...queryParams() } });
      if (id !== reqId.current) return;           // a newer request is in flight
      setRows(data.items); setTotal(data.total); setSelected([]);
    } catch (e) { if (id === reqId.current) setSnack({ sev: "error", msg: errMsg(e) }); }
    finally { if (id === reqId.current) setLoading(false); }
  }, [page, pageSize, sort, queryParams]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get("/assets/meta/options").then((r) => setOptions(r.data)).catch(() => {}); }, []);

  const pingOne = async (p) => {
    setSnack({ sev: "info", msg: `Pinging ${p.data.hostname}...` });
    try {
      const { data } = await api.post(`/assets/${p.data.id}/ping`);
      p.node.setData(data.asset);                    // remarks updated live
      setSnack({ sev: data.ok ? "success" : "warning", msg: `${p.data.hostname}: ${data.message}` });
    } catch (e) { setSnack({ sev: "error", msg: errMsg(e) }); }
  };

  const columnDefs = useMemo(() => [
    { colId: "sel", headerName: "", width: canEdit ? 120 : 90, pinned: "left", checkboxSelection: true, headerCheckboxSelection: true,
      sortable: false, editable: false, resizable: false,
      cellRenderer: (p) => (
        <>
          <Tooltip title="Open details"><IconButton size="small" onClick={() => setDialog({ open: true, asset: p.data })}><OpenInNewIcon fontSize="small" /></IconButton></Tooltip>
          {canEdit && <Tooltip title="Ping this server"><IconButton size="small" onClick={() => pingOne(p)}><NetworkCheckIcon fontSize="small" /></IconButton></Tooltip>}
        </>
      ) },
    ...FIELDS.map((f) => ({
      field: f.name, headerName: f.label, width: f.kind === "text" ? 220 : 150, editable: canEdit, sortable: true,
      comparator: () => 0, // sorting is done by the server
      cellEditor: f.kind === "text" ? "agLargeTextCellEditor" : "agTextCellEditor",
      cellEditorPopup: f.kind === "text",
      cellEditorParams: f.kind === "text" ? { maxLength: 100000, rows: 8, cols: 50 } : undefined,
    })),
  ], [canEdit]);

  const onCellValueChanged = async (e) => {
    const field = e.colDef.field;
    try {
      const { data } = await api.put(`/assets/${e.data.id}`, { [field]: coerce(field, e.newValue) });
      e.node.setData(data);
      setSnack({ sev: "success", msg: `Saved ${e.data.hostname}` });
    } catch (err) {
      e.node.setData({ ...e.data, [field]: e.oldValue });
      setSnack({ sev: "error", msg: errMsg(err) });
    }
  };

  const delSelected = async () => {
    if (!window.confirm(`Delete ${selected.length} selected asset(s)? This cannot be undone.`)) return;
    try { for (const r of selected) await api.delete(`/assets/${r.id}`); setSnack({ sev: "success", msg: "Deleted" }); }
    catch (e) { setSnack({ sev: "error", msg: errMsg(e) }); }
    load();
  };
  const pingSelected = async () => {
    if (selected.length > 200) return setSnack({ sev: "warning", msg: "Select at most 200 servers to ping at once" });
    setSnack({ sev: "info", msg: `Pinging ${selected.length} server(s)...` });
    try {
      const { data } = await api.post("/assets/ping-bulk", { ids: selected.map((r) => r.id) }, { timeout: 300000 });
      setSnack({ sev: data.failed ? "warning" : "success", msg: `Ping finished: ${data.ok} reachable, ${data.failed} failed. Remarks updated.` });
      load();
    } catch (e) { setSnack({ sev: "error", msg: errMsg(e) }); }
  };
  const applyBulk = async () => {
    try {
      const { data } = await api.patch("/assets/bulk", { ids: selected.map((r) => r.id), changes: { [bulk.field]: coerce(bulk.field, bulk.value) } });
      setSnack({ sev: "success", msg: `Updated ${data.updated} asset(s)` });
      setBulk({ ...bulk, open: false }); load();
    } catch (e) { setSnack({ sev: "error", msg: errMsg(e) }); }
  };
  const doExport = async (fmt, sel) => {
    setMenu(null);
    try { await download(`/export/${fmt}`, sel ? { ids: selected.map((r) => r.id).join(",") } : queryParams()); }
    catch { setSnack({ sev: "error", msg: "Export failed" }); }
  };
  const search = () => { setPage(0); setApplied({ q, filters, preset: applied.preset }); };
  const clearAll = () => { setFilters({}); setQ(""); setPage(0); setApplied({ q: "", filters: {}, preset: "" }); setSp({}); };
  const dropPreset = () => { const n = new URLSearchParams(sp); n.delete("preset"); setSp(n); setApplied({ ...applied, preset: "" }); setPage(0); };

  const bulkField = FIELDS.find((f) => f.name === bulk.field);

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap", gap: 1 }} alignItems="center">
        <Typography variant="h5" sx={{ fontWeight: 700, mr: 2 }}>Server Inventory</Typography>
        <TextField size="small" placeholder="Global search (use * as wildcard)" value={q} sx={{ minWidth: 260 }}
          onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} />
        <Button variant="contained" onClick={search}>Search</Button>
        <Button startIcon={<FilterListIcon />} onClick={() => setShowFilters(!showFilters)}>Filters</Button>
        {(canEdit || mode === "request") && <Button startIcon={<AddIcon />} onClick={() => setDialog({ open: true, asset: null })}>{canEdit ? "Add asset" : "Request new server"}</Button>}
        {canEdit && <Button startIcon={<NetworkCheckIcon />} disabled={!selected.length} onClick={pingSelected}>Ping selected ({selected.length})</Button>}
        {canEdit && <Button startIcon={<EditNoteIcon />} disabled={!selected.length} onClick={() => setBulk({ ...bulk, open: true })}>Bulk edit ({selected.length})</Button>}
        {can("asset:delete") && <Button color="error" startIcon={<DeleteIcon />} disabled={!selected.length} onClick={delSelected}>Delete ({selected.length})</Button>}
        {can("asset:export") && <>
          <Button startIcon={<DownloadIcon />} onClick={(e) => setMenu(e.currentTarget)}>Export</Button>
          <Menu anchorEl={menu} open={!!menu} onClose={() => setMenu(null)}>
            <MenuItem onClick={() => doExport("excel", false)}>Filtered data - XLSX</MenuItem>
            <MenuItem onClick={() => doExport("csv", false)}>Filtered data - CSV</MenuItem>
            <MenuItem disabled={!selected.length} onClick={() => doExport("excel", true)}>Selected records - XLSX</MenuItem>
            <MenuItem disabled={!selected.length} onClick={() => doExport("csv", true)}>Selected records - CSV</MenuItem>
          </Menu>
        </>}
      </Stack>

      {(applied.preset || Object.keys(applied.filters).length > 0 || applied.q) && (
        <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: "wrap", gap: 0.5 }} alignItems="center">
          <Typography variant="body2">Showing {total.toLocaleString()} server(s) for:</Typography>
          {applied.preset && <Chip color="primary" label={PRESET_LABEL[applied.preset] || applied.preset} onDelete={dropPreset} />}
          {Object.entries(applied.filters).map(([k, v]) => <Chip key={k} label={`${FIELDS.find((f) => f.name === k)?.label}: ${v.replace(/^=/, "").replace("__blank__", "(blank)")}`} />)}
          {applied.q && <Chip label={`Search: ${applied.q}`} />}
          <Button size="small" onClick={clearAll}>Clear all</Button>
        </Stack>
      )}

      <Collapse in={showFilters}>
        <Box sx={{ p: 2, mb: 2, border: 1, borderColor: "divider", borderRadius: 2 }}>
          <Grid container spacing={1.5}>
            {FILTERS.map((f) => {
              const def = FIELDS.find((x) => x.name === f);
              return (
                <Grid item xs={6} sm={4} md={3} lg={2} key={f}>
                  <Autocomplete freeSolo size="small" options={def.options || options[f] || []} inputValue={filters[f] || ""}
                    onInputChange={(_, v) => setFilters((cur) => ({ ...cur, [f]: v }))}
                    renderInput={(params) => <TextField {...params} label={def.label} onKeyDown={(e) => e.key === "Enter" && search()} />} />
                </Grid>
              );
            })}
          </Grid>
          <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
            <Button variant="contained" onClick={search}>Apply filters</Button>
            <Button onClick={clearAll}>Clear</Button>
            <Typography variant="caption" sx={{ alignSelf: "center" }}>Text matches "contains"; use * and ? as wildcards, or start with = for an exact match.</Typography>
          </Stack>
        </Box>
      </Collapse>

      {mode === "view" && <Alert severity="info" sx={{ mb: 1 }}>Read-only view. Click the open icon on a row for details.</Alert>}
      {mode === "request" && <Alert severity="info" sx={{ mb: 1 }}>To change a server, open it and use "Submit for approval". To add one, use "Request new server". The CMDB manager must approve before anything is applied.</Alert>}
      {canEdit && <Typography variant="caption" color="text.secondary">Double-click a cell to edit; changes save immediately. Use the network icon on a row to ping the server.</Typography>}

      <div className={theme.palette.mode === "dark" ? "ag-theme-quartz-dark" : "ag-theme-quartz"} style={{ height: "calc(100vh - 290px)", minHeight: 360, width: "100%" }}>
        <AgGridReact rowData={rows} columnDefs={columnDefs} loading={loading} rowSelection="multiple"
          suppressRowClickSelection singleClickEdit={false} stopEditingWhenCellsLoseFocus
          getRowId={(p) => String(p.data.id)} defaultColDef={{ resizable: true }}
          onSelectionChanged={(e) => setSelected(e.api.getSelectedRows())}
          onSortChanged={(e) => {
            const s = e.api.getColumnState().find((c) => c.sort);
            setSort(s ? { sort_by: s.colId, sort_dir: s.sort } : { sort_by: "id", sort_dir: "asc" });
            setPage(0);
          }}
          onCellValueChanged={onCellValueChanged} />
      </div>
      <TablePagination component="div" count={total} page={page} rowsPerPage={pageSize} rowsPerPageOptions={[50, 100, 250, 500]}
        onPageChange={(_, p) => setPage(p)} onRowsPerPageChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }} />

      <AssetDialog open={dialog.open} asset={dialog.asset} mode={mode} onClose={() => setDialog({ open: false, asset: null })}
        onSaved={(data, kind) => {
          setDialog({ open: false, asset: null });
          setSnack({ sev: "success", msg: kind === "request" ? `Change request #${data.id} sent for approval` : "Saved" });
          if (kind !== "request") load();
        }} />

      <Dialog open={bulk.open} onClose={() => setBulk({ ...bulk, open: false })} fullWidth maxWidth="xs">
        <DialogTitle>Bulk edit {selected.length} asset(s)</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <FormControl size="small" sx={{ mt: 1 }}>
            <InputLabel>Field</InputLabel>
            <Select label="Field" value={bulk.field} onChange={(e) => setBulk({ ...bulk, field: e.target.value, value: "" })}>
              {FIELDS.filter((f) => !UNIQUE.includes(f.name)).map((f) => <MenuItem key={f.name} value={f.name}>{f.label}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField size="small" label="New value (leave blank to clear)" value={bulk.value} select={!!bulkField.options}
            type={KIND[bulk.field] === "date" ? "date" : "text"} InputLabelProps={KIND[bulk.field] === "date" ? { shrink: true } : undefined}
            onChange={(e) => setBulk({ ...bulk, value: e.target.value })}>
            {bulkField.options && [<MenuItem key="" value=""><em>(blank)</em></MenuItem>, ...bulkField.options.map((o) => <MenuItem key={o} value={o}>{o}</MenuItem>)]}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulk({ ...bulk, open: false })}>Cancel</Button>
          <Button variant="contained" onClick={applyBulk}>Apply</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!snack} autoHideDuration={5000} onClose={() => setSnack(null)}>
        {snack ? <Alert severity={snack.sev} onClose={() => setSnack(null)}>{snack.msg}</Alert> : undefined}
      </Snackbar>
    </Box>
  );
}
