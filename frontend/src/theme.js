import { createTheme } from "@mui/material";

export const makeTheme = (mode) =>
  createTheme({
    palette: {
      mode,
      primary: { main: "#FFCC00", contrastText: "#2F2F2F" },
      secondary: { main: "#2F2F2F" },
      background: mode === "dark" ? { default: "#1f1f1f", paper: "#2F2F2F" } : { default: "#f4f4f4", paper: "#ffffff" },
    },
    shape: { borderRadius: 8 },
    components: {
      MuiAppBar: { styleOverrides: { root: { backgroundColor: "#FFCC00", color: "#2F2F2F" } } },
      MuiButton: { styleOverrides: { root: { textTransform: "none", fontWeight: 600 } } },
    },
  });
