import React, { useState } from "react";
import { Alert, Box, Button, Paper, Stack, Typography } from "@mui/material";
import { download } from "../api";

export default function ExportData() {
  const [msg, setMsg] = useState(null);
  const go = async (fmt) => {
    setMsg(null);
    try { await download(`/export/${fmt}`); setMsg({ sev: "success", t: "Export downloaded." }); }
    catch { setMsg({ sev: "error", t: "Export failed." }); }
  };
  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Export Data</Typography>
      <Paper sx={{ p: 2 }}>
        <Typography sx={{ mb: 2 }}>Download the full inventory. Files are named ServerInventory_YYYYMMDD.</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="contained" onClick={() => go("excel")}>Full inventory - XLSX</Button>
          <Button variant="contained" onClick={() => go("csv")}>Full inventory - CSV</Button>
        </Stack>
        <Alert severity="info" sx={{ mt: 2 }}>To export only the current filtered data or selected records, use the Export menu on the Server Inventory page.</Alert>
        {msg && <Alert severity={msg.sev} sx={{ mt: 2 }}>{msg.t}</Alert>}
      </Paper>
    </Box>
  );
}
