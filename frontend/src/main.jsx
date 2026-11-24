import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { CssBaseline, ThemeProvider } from "@mui/material";
import App from "./App";
import { AuthProvider } from "./AuthContext";
import { makeTheme } from "./theme";
import { ModeCtx } from "./ModeContext";

function Root() {
  const [mode, setMode] = useState(() => localStorage.getItem("sims_mode") || "light");
  const toggle = () => setMode((m) => { const n = m === "light" ? "dark" : "light"; localStorage.setItem("sims_mode", n); return n; });
  const theme = useMemo(() => makeTheme(mode), [mode]);
  return (
    <ModeCtx.Provider value={{ mode, toggle }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </ModeCtx.Provider>
  );
}
createRoot(document.getElementById("root")).render(<Root />);
